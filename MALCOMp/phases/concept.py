import datetime
import json
import logging
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autogen import ConversableAgent
from base import Base
import trace_locator

logger = logging.getLogger(__name__)


class ConceptExtraction(Base):

    def __init__(self, config_path="config.yaml", disabled_agents=None, run_id=None,
                 case_study=None):
        super().__init__(
            "concept_extraction",
            config_path,
            disabled_agents=disabled_agents,
            run_id=run_id,
            case_study=case_study,
        )

        # Load assets
        system_desc = self.load_asset("system_description")
        cot_extraction = self.load_asset("chain_of_thought_extraction")
        cot_checker = self.load_asset("chain_of_thought_checker")
        cot_trace = self.load_asset("chain_of_thought_trace")
        few_shot = self.load_asset("few_shot_example")

        # Term extraction agent
        self.term_extractor = self.create_agent(
            name="Concept_Extraction_Agent",
            system_message=(
                "You are an expert in requirement engineering. "
                "Requirement statements can be categorised into Functional Requirements and Non-Functional Requirements. "
                "You will be provided with some requirement statements from User, which are for a system to be developed. "
                "The description of the system is here: " + system_desc +
                "Your task is to extract Concepts and their Instances from the requirement statements. "
                "The requirements will be provided by User, please note that the requirements are not ordered, and one requirement may implicitly depend on other requirements. "
                "Each requirement statement is identified by a unique GID (short for Global ID). "
                'Please extract occurrences of the following from the requirement statements: "GID", "Concepts" and "Instances". '
                "The rationale and output format for your task is here: " + cot_extraction +
                "Here are some examples to guide you: " + few_shot +
                "The Output format should be in JSON only, no markdown permitted (no ```), no explain. "
                "Include only contents provided to you."
            ),
            description="A Concept_Extraction_Agent to extract Concepts and Instances from requirement statements.",
        )

        # Feed-mode-aware scope: in batch mode all requirements arrive in ONE User
        # message and each agent gets a single turn, so instruct the checker/trace
        # agents to cover EVERY GID rather than "the most recent requirement's GID"
        # (the sequential framing, which makes them emit only one GID in batch).
        batch = getattr(self, "feed_mode", "sequential") == "batch"
        checker_scope = (
            "Validate the Concepts and Instances for ALL requirements provided by User in this "
            "message; output the complete corrected JSON covering every requirement GID. "
            if batch else
            "For each turn, validate only the most recent requirement from User. Your JSON is the "
            "complete replacement set for that requirement's GID; do not repeat entries from earlier GIDs. "
        )
        trace_scope = (
            "Emit the complete final set of traceability entries covering EVERY requirement GID "
            "provided by User in this message; do not omit any GID. "
            if batch else
            "For each turn, emit only the complete final set for the most recent User requirement's GID. "
            "Do not repeat, merge, or revise entries belonging to earlier GIDs. "
        )

        # Term checker agent (validation only — JSON output is produced by Trace_Generation_Agent)
        self.term_checker = self.create_agent(
            name="Concept_Checker_Agent",
            system_message=(
                "You are an expert in requirement engineering and Model Driven Engineering (MDE). "
                "Your task is to verify whether the Concepts and Instances extracted by Concept_Extraction_Agent are correct. "
                + checker_scope +
                "If you find errors (missing/spurious concepts, wrong Instance_of, miscategorised Functional vs Non-Functional, "
                "wrong singular/plural form, etc.), output a corrected JSON. If the extraction is correct as-is, output it unchanged. "
                "Do NOT add Concepts or Instances that User did not introduce. "
                "The description of the system to be developed is here: " + system_desc +
                "The rationale and correctness criteria for your task is here: " + cot_checker +
                "Here are some examples of the extracted models, which may help you: " + few_shot +
                "The Output format should be in JSON only, no markdown permitted (no ```), no explain. "
                "Include only contents provided to you and Concept_Extraction_Agent."
            ),
            description="A Concept_Checker_Agent to verify and correct the output from Concept_Extraction_Agent.",
        )

        # Trace generation agent — emits the final Req2Concept traceability JSON.
        # Mirrors the Trace_Generation_Agent role used in the DSML, model and behaviour phases.
        self.trace_generator = self.create_agent(
            name="Trace_Generation_Agent",
            system_message=(
                "You are an expert in Model Driven Engineering (MDE) and traceability. "
                "Your job is to emit the final Req2Concept traceability JSON, given the requirement statements "
                "from User and the validated Concepts and Instances from Concept_Checker_Agent. "
                + trace_scope +
                "Each entry must trace one requirement (by GID) to the Concepts and Instances it introduces. "
                "The description of the system to be developed is here: " + system_desc +
                "The rationale and required JSON format for your task is here: " + cot_trace +
                "Here are some examples that may help you: " + few_shot +
                "The Output format should be in JSON only, no markdown permitted (no ```), no explain. "
                "Include only Concepts and Instances confirmed by Concept_Checker_Agent."
            ),
            description="A Trace_Generation_Agent to emit the final Req2Concept traceability JSON.",
        )

        # Dedicated repair agent (side agent — not in the roster) used by the
        # verification gate. Concept has no separate code artefact, so it repairs
        # the trace JSON itself.
        self._repair_agent = ConversableAgent(
            name="Concept_Repair_Agent",
            llm_config={**self.default_llm_config},
            system_message=(
                "You are an expert in Model Driven Engineering traceability. "
                "Repair the provided Req2Concept traceability JSON so it satisfies the "
                "reported verification failures (e.g. each entry must carry a GID and a "
                "Concept or Instance). Preserve all valid entries. "
                "Return the complete corrected JSON only — no explanation, no markdown fences."
            ),
            description="Repairs the concept traceability JSON after a verification failure.",
        )
        self._repair_target = self.stage_config["output"].get("json_file")

        self.init_group_chat()

    @staticmethod
    def _canonical_gid(value):
        """Return a comparison key for requirement identifiers."""
        if value is None:
            return ""
        return re.sub(r"[^0-9a-z]+", "", str(value).strip().casefold())

    @classmethod
    def _requirement_gid(cls, content):
        """Read the GID from a requirement-feeder message."""
        try:
            requirement = json.loads(content)
        except (TypeError, json.JSONDecodeError):
            return ""
        if not isinstance(requirement, dict):
            return ""
        for field in ("gid", "GID", "id", "name"):
            gid = cls._canonical_gid(requirement.get(field))
            if gid:
                return gid
        return ""

    @staticmethod
    def _entries_from_parsed_json(parsed, tag_name):
        """Flatten one parsed Trace_Generation_Agent value into term entries."""
        if isinstance(parsed, dict) and tag_name in parsed:
            value = parsed[tag_name]
            return value if isinstance(value, list) else [value]
        if isinstance(parsed, list):
            return parsed
        return [parsed]

    @classmethod
    def _deduplicate_entries(cls, entries):
        """Deduplicate the four fields used by term-extraction evaluation."""
        fields = ("GID", "Concept", "Instance", "Instance_of")
        output = []
        seen = set()
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            key = tuple(
                re.sub(r"[^0-9a-z]+", "", str(entry.get(field) or "").strip().casefold())
                for field in fields
            )
            if key in seen:
                continue
            seen.add(key)
            output.append(entry)
        return output

    def _description_for_gid(self, gid):
        """Requirement description whose GID matches (canonicalised), or None."""
        for requirement in self.user.data:
            if not isinstance(requirement, dict):
                continue
            for field in ("gid", "GID", "id", "name"):
                if self._canonical_gid(requirement.get(field)) == gid:
                    return requirement.get("description", "")
        return None

    def _trace_source_for_entry(self, entry):
        element_id = entry.get("Instance") or entry.get("Concept")
        gid_raw = entry.get("GID")
        file_label = f"requirement:{gid_raw}"
        if not element_id:
            return self._build_source(file_label, None)
        description = self._description_for_gid(self._canonical_gid(gid_raw))
        if not description:
            return self._build_source(file_label, None)
        span = trace_locator.locate("requirement", str(element_id), description)
        return self._build_source(file_label, span, char=True)

    def store_json(self, chat_results, agent_name, file_name, tag_name):
        """Store only the final Trace_Generation_Agent result for each requirement.

        The generic Base implementation concatenates every JSON object emitted
        by an agent. A Trace_Generation_Agent reply may repeat entries from earlier
        requirements because the full chat history is visible, so concatenation
        preserves stale versions and creates duplicates. Term extraction instead
        binds each reply to the most recent User requirement, filters to that
        requirement's GID, and lets a later reply replace an earlier one.
        """
        if getattr(self, "feed_mode", "sequential") == "batch":
            return self._store_json_batch(chat_results, agent_name, file_name, tag_name)

        latest_by_gid = {}
        current_gid = ""

        for message in chat_results.chat_history:
            name = message.get("name")
            content = message.get("content", "")
            if name == self.user.name:
                current_gid = self._requirement_gid(content)
                continue
            if name != agent_name or not current_gid:
                continue

            parsed_values = self._extract_json_values(content)
            if not parsed_values:
                logger.warning(
                    "Skipping unparseable JSON from %s for GID %s",
                    agent_name,
                    current_gid,
                )
                continue

            candidates = []
            for parsed in parsed_values:
                candidates.extend(self._entries_from_parsed_json(parsed, tag_name))

            matching = [
                entry
                for entry in candidates
                if isinstance(entry, dict)
                and self._canonical_gid(entry.get("GID")) == current_gid
            ]
            latest_by_gid[current_gid] = self._deduplicate_entries(matching)

            removed = len(candidates) - len(matching)
            if removed:
                logger.info(
                    "Discarded %d cross-requirement/non-entry values from %s for GID %s",
                    removed,
                    agent_name,
                    current_gid,
                )

        ordered_entries = []
        emitted_gids = set()
        for requirement in self.user.data:
            gid = ""
            if isinstance(requirement, dict):
                for field in ("gid", "GID", "id", "name"):
                    gid = self._canonical_gid(requirement.get(field))
                    if gid:
                        break
            if gid and gid not in emitted_gids:
                ordered_entries.extend(latest_by_gid.get(gid, []))
                emitted_gids.add(gid)

        # Preserve any valid GID not present in self.user.data, while keeping
        # deterministic message order for unusual/custom requirement sources.
        for gid, entries in latest_by_gid.items():
            if gid not in emitted_gids:
                ordered_entries.extend(entries)

        ordered_entries = self._enrich_trace_entries(ordered_entries)
        with open(file_name, "w", encoding="utf-8") as handle:
            json.dump({tag_name: ordered_entries}, handle, indent=4, ensure_ascii=False)
        logger.info(
            "Stored %d deduplicated term-trace entries for %d GIDs to %s",
            len(ordered_entries),
            len(latest_by_gid),
            file_name,
        )
        self._record_artifact(file_name)
        self._announce_trace(file_name, ordered_entries)
        self._store_concept_model(ordered_entries)

    def _store_concept_model(self, entries):
        """Write the extracted concept model — the deduplicated Concepts and
        Instances — derived deterministically from the trace entries. This is the
        Phase 2 'model' artefact, sitting alongside the req->concept traceability."""
        model_file = self.stage_config.get("output", {}).get("code_file")
        if not model_file:
            return
        concepts, instances = {}, {}
        for e in entries:
            if not isinstance(e, dict):
                continue
            concept = str(e.get("Concept") or "").strip()
            if concept and concept.lower() != "null":
                desc = e.get("Concept_description") or ""
                if concept not in concepts or (not concepts[concept] and desc):
                    concepts[concept] = desc
            instance = str(e.get("Instance") or "").strip()
            if instance and instance.lower() != "null" and instance not in instances:
                instances[instance] = {
                    "Instance_of": e.get("Instance_of") or "",
                    "description": e.get("Instance_description") or "",
                }
        model = {
            "concepts": [
                {"Concept": name, "description": desc}
                for name, desc in concepts.items()
            ],
            "instances": [
                {"Instance": name, "Instance_of": meta["Instance_of"],
                 "description": meta["description"]}
                for name, meta in instances.items()
            ],
        }
        path = self.output_dir / model_file
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(model, handle, indent=4, ensure_ascii=False)
        logger.info(
            "Stored concept model (%d concepts, %d instances) to %s",
            len(concepts), len(instances), path,
        )
        self._record_artifact(path)

    def _store_json_batch(self, chat_results, agent_name, file_name, tag_name):
        """Batch-mode variant: all requirements were fed in one turn, so attribute
        each emitted entry by its own GID field rather than by the (single) User
        message. Group, deduplicate, then order by the requirement order."""
        by_gid = {}
        for message in chat_results.chat_history:
            if message.get("name") != agent_name:
                continue
            for parsed in self._extract_json_values(message.get("content", "")):
                for entry in self._entries_from_parsed_json(parsed, tag_name):
                    if not isinstance(entry, dict):
                        continue
                    gid = self._canonical_gid(entry.get("GID"))
                    if not gid:
                        continue
                    by_gid.setdefault(gid, []).append(entry)
        for gid in list(by_gid):
            by_gid[gid] = self._deduplicate_entries(by_gid[gid])

        ordered_entries = []
        emitted_gids = set()
        for requirement in self.user.data:
            gid = ""
            if isinstance(requirement, dict):
                for field in ("gid", "GID", "id", "name"):
                    gid = self._canonical_gid(requirement.get(field))
                    if gid:
                        break
            if gid and gid not in emitted_gids:
                ordered_entries.extend(by_gid.get(gid, []))
                emitted_gids.add(gid)
        for gid, entries in by_gid.items():
            if gid not in emitted_gids:
                ordered_entries.extend(entries)

        ordered_entries = self._enrich_trace_entries(ordered_entries)
        with open(file_name, "w", encoding="utf-8") as handle:
            json.dump({tag_name: ordered_entries}, handle, indent=4, ensure_ascii=False)
        logger.info(
            "Stored %d batch term-trace entries for %d GIDs to %s",
            len(ordered_entries), len(by_gid), file_name,
        )
        self._record_artifact(file_name)
        self._announce_trace(file_name, ordered_entries)
        self._store_concept_model(ordered_entries)

    def run_multiple(self, times):
        """Run term extraction multiple times with dated output files."""
        date = f"{datetime.datetime.now():%Y-%m-%d}"
        for i in range(times):
            stage = ConceptExtraction(config_path=self.config_path)
            results = stage.run()
            # Also save with dated filename. Read agent + tag from the same
            # output config that Base.run uses, so the dated artefact stays in
            # sync with the canonical one (Concept_Checker_Agent was the source before
            # Trace_Generation_Agent was added in D2 — hardcoding it here was a stale
            # reference).
            output_cfg = stage.stage_config["output"]
            output_path = stage.output_dir / f"{date}result_concept_extractor_{i + 1}.json"
            stage.store_json(
                results,
                output_cfg["json_agent"],
                str(output_path),
                output_cfg["json_tag"],
            )
            logger.info("Completed term extraction run %d/%d", i + 1, times)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ConceptExtraction().run_multiple(10)
