import json
import logging
import os
import re
import shutil
from types import SimpleNamespace
from pathlib import Path
from datetime import datetime, timezone

import autogen
import yaml

import llm_keys
from autogen import ConversableAgent
from autogen.io import IOStream
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _expected_roster(config_key):
    """Canonical agent roster for a stage, looked up from the LAYERS registry
    by its config key. Returns None if the stage isn't registered."""
    from pipeline import LAYERS  # local import avoids a cycle at module load
    for spec in LAYERS.values():
        if spec.config_key == config_key:
            return spec.agent_names
    return None


class Base:
    """Base class for all MALCOMp pipeline stages.

    Provides shared configuration loading, asset file reading, agent creation,
    group chat setup, and result extraction helpers.
    """

    def __init__(self, stage_name, config_path="config.yaml", disabled_agents=None,
                 run_id=None, case_study=None):
        """Initialise a stage.

        Parameters
        ----------
        stage_name : str
            Key under `stages:` in config.yaml (e.g. `"concept_extraction"`).
        config_path : str | Path
            Path to the YAML config.
        disabled_agents : Iterable[str] | None
            Names of agents to skip when this stage's __init__ calls
            `create_agent(name=...)`. The skipped names are still recorded
            so consumers (MALCOM-web, evaluation drivers) know which
            members of `AGENT_NAMES` are absent for this run.
        """
        load_dotenv()
        self.stage_name = stage_name
        self.config_path = str(Path(config_path).resolve())
        self.config = self._load_config(config_path)
        self._config_dir = Path(config_path).resolve().parent
        self._select_active_model()
        self._validate_env()
        self.stage_config = self.config["stages"][stage_name]

        # Case study selection: explicit arg (e.g. MALCOM-web, per-connection)
        # wins, then the MALCOMP_CASE_STUDY env (CLI --case-study), then config.
        self.case_study = (case_study
                           or os.environ.get("MALCOMP_CASE_STUDY", "").strip()
                           or self.config.get("case_study"))
        if not self.case_study:
            raise EnvironmentError(
                "no case study selected; set MALCOMP_CASE_STUDY or add 'case_study' to config."
            )
        # The case study supplies only requirements/ + system_description/; prompts
        # are shared (prompts_dir); chained prior-phase artefacts live in output/.
        # `_case_dir`/`_prompts_dir` allow a temp/override config (e.g. MALCOM-web's
        # requirements override) to pin absolute roots; otherwise derive them.
        self.case_dir = (Path(self.config["_case_dir"]) if self.config.get("_case_dir")
                         else self._resolve_path("case_studies") / self.case_study)
        self.prompts_dir = (Path(self.config["_prompts_dir"]) if self.config.get("_prompts_dir")
                            else self._resolve_path(self.config.get("prompts_dir", "prompts")))
        self.assets_dir = self.case_dir            # case-study inputs root
        self.requirement_file = str((self.case_dir / self.stage_config["requirement_file"]).resolve())
        # Validate the case study's required inputs BEFORE creating output/. With
        # parents=True, output/'s mkdir would otherwise silently materialise a
        # typo'd case directory, masking the mistake and deferring it to a cryptic
        # FileNotFoundError in the requirement feeder.
        self._validate_case_study()
        self.output_dir = self.case_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Asset filenames are resolved against these roots, in order:
        #   prompts_dir  — shared, generic prompt engineering
        #   output_dir   — freshly chained prior-phase artefacts (preferred)
        #   case_dir     — case-study inputs (requirements/, system_description/)
        #   case_dir/fixtures — golden prior-phase artefacts (fallback when a
        #                       phase is run standalone, before output/ is populated)
        self._asset_roots = [
            self.prompts_dir, self.output_dir, self.case_dir, self.case_dir / "fixtures",
        ]

        self.config_list = self._build_config_list()
        request_timeout = self.config["model"].get(
            "timeout_seconds",
            self.config["model"].get("timeout", 180),
        )
        self.default_llm_config = {
            "config_list": self.config_list,
            "timeout": request_timeout,
            "cache_seed": None,
        }
        # Reasoning models (e.g. GPT-5) reject an explicit temperature; let a
        # model opt out via `supports_temperature: false`.
        if self.config["model"].get("supports_temperature", True):
            self.default_llm_config["temperature"] = self.config["model"].get("temperature", 0.5)
        if self.config["model"].get("max_tokens"):
            self.default_llm_config["max_tokens"] = int(self.config["model"]["max_tokens"])

        self.user = self._create_user()
        self.agents = []
        self.disabled_agents: set[str] = set(disabled_agents or ())
        self.groupchat = None
        self.group_chat_manager = None
        self.run_id = run_id or os.environ.get("MALCOMP_RUN_ID", "").strip()
        # Requirement feeding: "sequential" (one requirement at a time, the
        # default — builds the model incrementally and gives clean per-GID
        # traceability) or "batch" (all requirements in a single pass — far
        # fewer LLM calls; the web bridge may override this per run).
        self.feed_mode = (os.environ.get("MALCOMP_FEED_MODE", "").strip()
                          or self.config.get("feed_mode") or "batch")
        # Per-phase artefact verification (structural + traceability). Recorded
        # after run(); the runner decides whether the next phase may proceed.
        self.verification_result = None
        self.verification_enabled = bool(self.config.get("verification", {}).get("enabled", True))
        # Optional FDR4 behaviour refinement check (opt-in via verification.fdr4).
        self._fdr4_config = self.config.get("verification", {}).get("fdr4", {}) or {}
        # Error-driven repair: the dedicated repair agent + the artefact it rewrites.
        # Set by each phase (model reuses EOL_Repairer); None disables repair.
        self._repair_agent = None
        self._repair_target = None

    def _resolve_path(self, relative_path):
        """Resolve a path relative to the config file's directory."""
        p = Path(relative_path)
        if p.is_absolute():
            return p
        return self._config_dir / p

    def _validate_env(self):
        """Check that the active model's key is present.

        The key is resolved through llm_keys.resolve_api_key, which reads the
        env var named by the model's own ``api_key_env`` (falling back to
        OPENAI_API_KEY). Checking OPENAI_API_KEY directly would reject a fully
        configured model whose key lives elsewhere — e.g. a `models:` entry
        declaring api_key_env: DEEPSEEK_API_KEY — even though generation would
        then have succeeded.
        """
        model_cfg = self.config["model"]
        if model_cfg.get("api_type", "openai") == "anthropic":
            if not os.environ.get(
                    model_cfg.get("api_key_env", "ANTHROPIC_API_KEY")):
                raise EnvironmentError(
                    f"{model_cfg.get('api_key_env', 'ANTHROPIC_API_KEY')} not "
                    "set. Add it to your .env file."
                )
            return
        try:
            llm_keys.resolve_api_key(model_cfg)
        except Exception as ex:
            raise EnvironmentError(str(ex)) from ex

    @staticmethod
    def _load_config(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _select_active_model(self):
        """Collapse the `models:` map into self.config['model'] for this run.

        Selection order: the MALCOMP_MODEL env var, then config['default_model'].
        A config with a bare `model:` block (no `models:` map) is left untouched
        for backward compatibility.
        """
        cfg = self.config
        if "models" in cfg:
            key = os.environ.get("MALCOMP_MODEL", "").strip() or cfg.get("default_model")
            if not key:
                raise EnvironmentError(
                    "config defines 'models' but no 'default_model'; "
                    "set MALCOMP_MODEL or add default_model."
                )
            if key not in cfg["models"]:
                raise ValueError(
                    f"unknown model {key!r}; available: {sorted(cfg['models'])}"
                )
            cfg["model"] = cfg["models"][key]
            self.active_model = key
        elif "model" in cfg:
            self.active_model = cfg["model"].get("name")
        else:
            raise ValueError("config must define either 'models' or 'model'")

    def _build_config_list(self):
        from llm_keys import resolve_api_key
        api_type = self.config["model"].get("api_type", "openai")
        if api_type == "anthropic":
            return [
                {
                    "model": self.config["model"]["name"],
                    "api_key": os.environ["ANTHROPIC_API_KEY"],
                    "api_type": "anthropic",
                }
            ]
        else:
            return [
                {
                    "model": self.config["model"]["name"],
                    "api_key": resolve_api_key(self.config["model"]),
                    "base_url": os.environ.get(
                        "OPENAI_API_BASE",
                        self.config["model"].get("api_base_url", ""),
                    ),
                }
            ]

    def find_asset(self, filename):
        """Resolve an asset filename against the search roots (prompts_dir,
        output_dir, case_dir), returning the first that exists."""
        for root in self._asset_roots:
            p = root / filename
            if p.is_file():
                return p
        raise FileNotFoundError(
            f"asset {filename!r} not found under "
            f"{[str(r) for r in self._asset_roots]}"
        )

    def resolve_asset(self, key):
        """Path of the asset configured under `asset_files[key]`."""
        return self.find_asset(self.stage_config["asset_files"][key])

    def load_asset(self, key):
        """Load the text of the asset configured under `asset_files[key]`.

        A trailing space is guaranteed so that prompts which concatenate an
        asset directly with the following sentence never glue the asset's last
        token onto it (the assets do not all end in a newline).
        """
        text = self.resolve_asset(key).read_text(encoding="utf-8")
        return text if text[-1:].isspace() else text + " "

    def create_agent(self, name, system_message, description, **agent_kwargs):
        """Create a ConversableAgent with the default llm_config.

        Any extra keyword arguments are passed directly to ConversableAgent
        (e.g. max_consecutive_auto_reply).

        If `name` is in `self.disabled_agents`, skip creating the agent and
        return None — the caller's `self.<attr> = self.create_agent(...)` then
        binds None, but downstream code (group chat, json_agent, code_agent)
        only looks up by name string, so the missing agent is simply absent
        from the round-robin order.
        """
        if name in self.disabled_agents:
            logger.info("Skipping agent %r (in disabled_agents)", name)
            return None
        llm_config = {**self.default_llm_config}
        agent = ConversableAgent(
            name=name,
            llm_config=llm_config,
            system_message=system_message,
            description=description,
            **agent_kwargs,
        )
        self.agents.append(agent)
        return agent

    def _validate_case_study(self):
        """Fail fast with an actionable message when the selected case study is
        missing its required inputs.

        Only the universally-required inputs are checked here: the case-study
        directory itself, and this stage's requirement file. Stage-specific
        assets (system_description, shared prompts, chained prior-phase
        artefacts) are still resolved — and reported, with the searched roots —
        by `find_asset` when the phase loads them.
        """
        if not self.case_dir.is_dir():
            available = self._available_case_studies()
            hint = f" Available case studies: {available}." if available else ""
            raise FileNotFoundError(
                f"case study {self.case_study!r} not found at {self.case_dir}. "
                f"A case study is a directory under case_studies/ that provides "
                f"requirements/ and system_description/.{hint}"
            )
        req_path = Path(self.requirement_file)
        if not req_path.is_file():
            raise FileNotFoundError(
                f"requirement file for stage {self.stage_name!r} not found at "
                f"{req_path} (config requirement_file "
                f"{self.stage_config['requirement_file']!r}, relative to case study "
                f"{self.case_study!r})."
            )

    def _available_case_studies(self):
        """Best-effort sibling case-study names, for the not-found error hint."""
        try:
            return sorted(p.name for p in self.case_dir.parent.iterdir() if p.is_dir())
        except OSError:
            return []

    def _create_user(self):
        return RequirementFeederAgent(
            file_path=self.requirement_file,
            name="User",
            llm_config=False,
            human_input_mode="ALWAYS",
            description="A User to provide the requirements.",
        )

    def init_group_chat(self):
        """Create GroupChat and GroupChatManager from registered agents."""
        # The LAYERS registry declares the canonical roster for this stage
        # (looked up by config key). If the `create_agent(...)` calls in
        # __init__ have drifted out of sync with that roster, fail loudly here
        # rather than letting the web UI's `disabled_agents` selector silently
        # miss an agent. Disabled agents are subtracted from the expected list
        # before the comparison, so an evaluation-style run with
        # `disabled_agents=...` is still validated against the canonical roster.
        declared = _expected_roster(self.stage_name)
        if declared is not None:
            expected = tuple(n for n in declared if n not in self.disabled_agents)
            actual = tuple(a.name for a in self.agents)
            if actual != expected:
                raise AssertionError(
                    f"{type(self).__name__} roster (expected after disabling "
                    f"{sorted(self.disabled_agents)}: {list(expected)}) does not match "
                    f"the agents actually created in __init__ ({list(actual)}). "
                    "Update the LAYERS registry whenever you add/remove a create_agent(...) call."
                )
        all_agents = [self.user] + self.agents
        self.groupchat = autogen.GroupChat(
            agents=all_agents,
            messages=[],
            speaker_selection_method="round_robin",
            max_round=self.stage_config.get("max_rounds", 100),
            send_introductions=True,
        )
        self.group_chat_manager = autogen.GroupChatManager(
            self.groupchat,
            llm_config=self.default_llm_config,
        )

    def run(self, message=""):
        """Execute the pipeline stage: initiate chat, store JSON trace and code artifact."""
        chat_results = self._run_round_robin()
        output_cfg = self.stage_config["output"]

        # Store code artifact FIRST so trace enrichment can locate against it.
        if "code_agent" in output_cfg and "code_file" in output_cfg:
            self._store_last_agent_output(
                chat_results,
                agent_name=output_cfg["code_agent"],
                file_name=str(self.output_dir / output_cfg["code_file"]),
            )

        # Store JSON traceability (if configured)
        json_agent = output_cfg.get("json_agent")
        json_file = output_cfg.get("json_file")
        json_tag = output_cfg.get("json_tag")
        if json_agent and json_file and json_tag:
            self.store_json(
                chat_results,
                agent_name=json_agent,
                file_name=str(self.output_dir / json_file),
                tag_name=json_tag,
            )

        self._verify_and_repair()
        return chat_results

    def _feeds(self):
        """Requirement payloads to feed, one per round. In 'sequential' mode
        that is one requirement at a time; in 'batch' mode it is a single
        payload containing all requirements."""
        if self.feed_mode == "batch":
            return [json.dumps(self.user.data, ensure_ascii=False)]
        return [json.dumps(item, ensure_ascii=False) for item in self.user.data]

    @staticmethod
    def _emit_progress(stream, current, total, agent):
        """Emit overall progress to a live UI stream, if it supports it."""
        if stream is not None and hasattr(stream, "send_progress"):
            try:
                stream.send_progress(current, total, agent)
            except Exception:
                logger.debug("progress emit failed", exc_info=True)

    def _run_round_robin(self):
        """Run agents deterministically without AutoGen's interactive GroupChatManager."""
        chat_history = []
        llm_messages = []
        stream = IOStream.get_default()

        feeds = self._feeds()
        total = len(feeds)
        for index, requirement in enumerate(feeds, start=1):
            chat_history.append({"name": self.user.name, "content": requirement})
            llm_messages.append({"role": "user", "name": self.user.name, "content": requirement})
            self._stream_chat_message(stream, self.user.name, requirement)

            for agent in self.agents:
                self._emit_progress(stream, index, total, agent.name)
                reply = agent.generate_reply(messages=llm_messages)
                content = self._normalise_reply_content(reply)
                chat_history.append({"name": agent.name, "content": content})
                llm_messages.append(
                    {"role": "assistant", "name": agent.name, "content": content}
                )
                self._stream_chat_message(stream, agent.name, content)

        return SimpleNamespace(chat_history=chat_history)

    @staticmethod
    def _stream_chat_message(stream, sender, content):
        """Emit round-robin messages to the active IOStream for live UIs."""
        if not stream:
            return
        try:
            if hasattr(stream, "send_agent_message"):
                stream.send_agent_message(sender, content)
            else:
                stream.print(f"{sender}:")
                stream.print(content, flush=True)
        except Exception:
            logger.debug("Unable to stream message from %s", sender, exc_info=True)

    @staticmethod
    def _normalise_reply_content(reply):
        if reply is None:
            return ""
        if isinstance(reply, str):
            return reply
        if isinstance(reply, dict):
            return str(reply.get("content", ""))
        return str(reply)

    def _trace_source_for_entry(self, entry):
        """Override per phase: return a `source` dict for one trace entry, or
        None when the stage has no locatable source. Default: no source."""
        return None

    def _enrich_trace_entries(self, entries):
        """Attach a verified `source` locator to each dict entry, via the
        stage's `_trace_source_for_entry` hook. Returns `entries` (mutated)."""
        # Invalidate the memoised artefact text so a reused stage instance (the
        # web 'refine' flow re-runs a cached stage) reads the freshly-written
        # artefact rather than the previous run's stale copy.
        self._code_artefact_cache = None
        for entry in entries:
            if isinstance(entry, dict):
                source = self._trace_source_for_entry(entry)
                if source is not None:
                    entry["source"] = source
        return entries

    @staticmethod
    def _build_source(file_label, span, char=False):
        """Build a `source` dict. `span` is (start, end) or None (unresolved)."""
        if span is None:
            return {"file": file_label, "resolved": False}
        start, end = span
        if char:
            return {"file": file_label, "char_start": start,
                    "char_end": end, "resolved": True}
        return {"file": file_label, "line_start": start,
                "line_end": end, "resolved": True}

    def _read_code_artefact_text(self):
        """Read this stage's code artefact from output/ (memoised). Empty string
        if the stage has no code_file or it has not been written yet."""
        if getattr(self, "_code_artefact_cache", None) is None:
            code_file = self.stage_config.get("output", {}).get("code_file")
            path = (self.output_dir / code_file) if code_file else None
            self._code_artefact_cache = (
                path.read_text(encoding="utf-8")
                if path and path.exists() else ""
            )
        return self._code_artefact_cache

    # Layer token used by verification.verify (matches LAYERS keys).
    _VERIFY_PHASE = {
        "concept_extraction": "concept",
        "dsml_creation": "dsml",
        "emf_model_creation": "model",
        "behaviour_model_creation": "behaviour",
    }

    def _run_verification(self):
        """Verify this phase's artefacts and record the result (no gating here —
        the runner decides whether to proceed)."""
        if not self.verification_enabled:
            return
        import verification
        phase_key = self._VERIFY_PHASE.get(self.stage_name)
        if phase_key is None:
            return
        # The runner may be set on the instance (tests) or, normally, declared
        # in config under verification.malcomj_runner / malcomj_runner. Reading
        # only the instance attribute meant a configured runner was ignored and
        # eol_executes reported UNVERIFIED even on a machine that had it built.
        runner = (getattr(self, "malcomj_runner", None)
                  or (self.config.get("verification", {}) or {}).get("malcomj_runner")
                  or self.config.get("malcomj_runner")
                  or os.environ.get("MALCOMJ_RUNNER"))
        self.verification_result = verification.verify(
            phase_key, self.output_dir,
            malcomj_runner=runner,
            requirement_data=getattr(self.user, "data", None),
            fdr4_config=getattr(self, "_fdr4_config", None),
            strict=bool(self.config.get("verification", {}).get("strict", False)),
        )
        result = self.verification_result
        stream = IOStream.get_default()
        # Distinguish "verified" from "accepted with checks that never ran":
        # collapsing the two is what makes an incomplete toolchain look clean.
        if not result.passed:
            mark = "FAILED"
        elif result.unverified:
            mark = f"passed with {len(result.unverified)} UNVERIFIED check(s)"
        else:
            mark = "passed"
        msg = f"Verification {mark} for phase '{phase_key}':\n{result.summary()}"
        if stream is not None and hasattr(stream, "send_agent_message"):
            try:
                stream.send_agent_message("system", msg)
            except Exception:
                logger.debug("verification announce failed", exc_info=True)
        logger.info(msg)

    def _verify_and_repair(self):
        """Verify; on hard failure feed the failures to this phase's repair agent
        and re-verify, up to `verification.max_repair_attempts`, before recording
        the (possibly still-failing) result for the gate."""
        if not self.verification_enabled:
            return
        max_attempts = int(self.config.get("verification", {}).get("max_repair_attempts", 2))
        self._run_verification()
        attempt = 0
        while (self.verification_result is not None
               and not self.verification_result.passed
               and attempt < max_attempts
               and self._repair_agent is not None):
            attempt += 1
            # Announce the repair agent so the UI shows it taking over (the
            # progress bar otherwise keeps the previous agent's stale label
            # during the repair agent's LLM call).
            stream = IOStream.get_default()
            self._emit_progress(stream, attempt, max_attempts, self._repair_agent.name)
            if stream is not None and hasattr(stream, "send_agent_message"):
                try:
                    stream.send_agent_message(
                        "system",
                        f"Verification failed — {self._repair_agent.name} repairing "
                        f"(attempt {attempt}/{max_attempts})…")
                except Exception:
                    logger.debug("repair-start announce failed", exc_info=True)
            if not self._repair_code(self.verification_result.hard_failures):
                break
            self._reenrich_trace()
            self._run_verification()

    def _repair_code(self, failures):
        """Send the failing artefact + verification failures to the repair agent
        and overwrite the artefact with the fix. Returns True if it changed."""
        if self._repair_agent is None or not self._repair_target:
            return False
        target = self.output_dir / self._repair_target
        if not target.exists():
            return False
        detail = "\n".join(f"- {c.name}: {c.detail}" for c in failures)
        content = target.read_text(encoding="utf-8")
        prompt = (
            "The following artefact failed verification. Fix it so the checks "
            "pass; preserve everything unrelated; output ONLY the corrected "
            "artefact, with no explanation and no markdown fences.\n\n"
            f"Failures:\n{detail}\n\nArtefact:\n{content}"
        )
        try:
            reply = self._repair_agent.generate_reply(
                messages=[{"role": "user", "content": prompt}])
        except Exception:
            logger.warning("repair agent failed", exc_info=True)
            return False
        fixed = self._strip_markdown_fence(self._normalise_reply_content(reply)).strip()
        if not fixed or fixed == content.strip():
            return False
        target.write_text(fixed + "\n", encoding="utf-8")
        stream = IOStream.get_default()
        if stream is not None and hasattr(stream, "send_agent_message"):
            try:
                stream.send_agent_message(
                    self._repair_agent.name,
                    f"Repaired {self._repair_target} after verification failure.")
            except Exception:
                logger.debug("repair announce failed", exc_info=True)
        return True

    def _reenrich_trace(self):
        """Re-run deterministic source enrichment on the trace against the
        (possibly repaired) artefact, so `source.resolved` reflects the new code."""
        output_cfg = self.stage_config.get("output", {})
        json_file = output_cfg.get("json_file")
        json_tag = output_cfg.get("json_tag")
        if not json_file or not json_tag:
            return
        path = self.output_dir / json_file
        if not path.exists():
            return
        try:
            entries = json.loads(path.read_text(encoding="utf-8")).get(json_tag, [])
        except json.JSONDecodeError:
            return
        self._code_artefact_cache = None  # force re-read of the repaired code
        entries = self._enrich_trace_entries(entries)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({json_tag: entries}, f, indent=4, ensure_ascii=False)

    def _announce_trace(self, file_name, entries):
        """Tell the live UI (and the log) whether a real trace was generated.

        A genuine trace entry is keyed to a requirement (requirement_gid / GID).
        Requirements echoed back by a confused/reasoning agent lack that key, so
        we surface a warning instead of silently writing a bogus trace."""
        from os.path import basename
        total = len(entries)
        keyed = sum(
            1 for e in entries
            if isinstance(e, dict) and any(k.lower() in ("requirement_gid", "gid") for k in e)
        )
        name = basename(str(file_name))
        if total and keyed == total:
            msg = f"✓ Traceability generated: {name} — {total} entries."
        elif keyed:
            msg = (f"✓ Traceability generated: {name} — {total} entries "
                   f"({keyed} linked to a requirement).")
        else:
            msg = (f"⚠ Traceability written but no entry is linked to a requirement "
                   f"— the trace agent output may be invalid. {name}: {total} entries.")
        stream = IOStream.get_default()
        if stream is not None and hasattr(stream, "send_agent_message"):
            try:
                stream.send_agent_message("system", msg)
            except Exception:
                logger.debug("trace announce failed", exc_info=True)
        logger.info(msg)

    def store_json(self, chat_results, agent_name, file_name, tag_name):
        """Extract JSON from an agent's messages and save to file."""
        content = [
            item["content"]
            for item in chat_results.chat_history
            if item.get("name") == agent_name
        ]
        data = {tag_name: []}
        for item in content:
            parsed_items = self._extract_json_values(item)
            if not parsed_items:
                logger.warning("Skipping unparseable JSON from %s", agent_name)
            for parsed in parsed_items:
                if isinstance(parsed, dict) and tag_name in parsed:
                    value = parsed[tag_name]
                    if isinstance(value, list):
                        data[tag_name].extend(value)
                    else:
                        data[tag_name].append(value)
                elif isinstance(parsed, list):
                    data[tag_name].extend(parsed)
                else:
                    data[tag_name].append(parsed)

        data[tag_name] = self._enrich_trace_entries(data[tag_name])
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.info("Stored JSON trace to %s", file_name)
        self._record_artifact(file_name)
        self._announce_trace(file_name, data[tag_name])

    def _store_last_agent_output(self, chat_results, agent_name, file_name):
        """Extract the last message from a named agent and write to file."""
        last_content = next(
            (
                entry["content"]
                for entry in reversed(chat_results.chat_history)
                if entry.get("name") == agent_name
            ),
            None,
        )
        if last_content:
            last_content = self._strip_markdown_fence(last_content)
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(last_content)
            logger.info("Stored %s output to %s", agent_name, file_name)
            self._record_artifact(file_name)
        else:
            logger.warning("No output found from agent %s", agent_name)

    def _record_artifact(self, file_name):
        """Copy a produced artefact into output/runs/<run_id>/ and update manifest."""
        if not self.run_id:
            return
        src = Path(file_name)
        if not src.exists() or not src.is_file():
            return

        run_dir = self.output_dir / "runs" / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        dst = run_dir / src.name
        shutil.copy2(src, dst)

        manifest_path = run_dir / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                manifest = {}
        else:
            manifest = {}

        now = datetime.now(timezone.utc).isoformat()
        manifest.setdefault("run_id", self.run_id)
        manifest.setdefault("config_path", self.config_path)
        manifest.setdefault("model", self.config.get("model", {}))
        manifest.setdefault("created_at", now)
        manifest["updated_at"] = now
        stages = manifest.setdefault("stages", {})
        stage = stages.setdefault(self.stage_name, {"artifacts": []})

        artifact = {
            "file": src.name,
            "latest_path": str(src.resolve()),
            "archived_path": str(dst.resolve()),
            "size": dst.stat().st_size,
            "updated_at": now,
        }
        stage["artifacts"] = [
            item for item in stage.get("artifacts", [])
            if item.get("file") != src.name
        ]
        stage["artifacts"].append(artifact)
        stage["updated_at"] = now

        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Archived artefact to %s", dst)

    def archive_configured_outputs(self):
        """Archive every output file configured for this stage if it exists."""
        output_cfg = self.stage_config.get("output", {})
        for key in ("json_file", "code_file"):
            name = output_cfg.get(key)
            if name:
                self._record_artifact(self.output_dir / name)

    @staticmethod
    def _strip_markdown_fence(content):
        """Return the body of a single fenced code block when one wraps output."""
        text = content.strip()
        match = re.fullmatch(r"```[A-Za-z0-9_-]*\s*\n(.*)\n```", text, re.DOTALL)
        if match:
            return match.group(1).strip() + "\n"
        return content

    @classmethod
    def _extract_json_values(cls, content):
        """Parse JSON from strict, fenced, or concatenated LLM output."""
        text = cls._strip_markdown_fence(content).strip()
        decoder = json.JSONDecoder()

        try:
            return [json.loads(text)]
        except json.JSONDecodeError:
            pass

        values = []
        index = 0
        while index < len(text):
            while index < len(text) and text[index] not in "[{":
                index += 1
            if index >= len(text):
                break
            try:
                value, end = decoder.raw_decode(text, index)
            except json.JSONDecodeError:
                index += 1
                continue
            values.append(value)
            index = end
        return values


class RequirementFeederAgent(ConversableAgent):
    """A ConversableAgent that feeds requirements from a JSON file one by one."""

    def __init__(self, file_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_path = file_path
        self.current_index = 0
        with open(self.file_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            # Support multiple input shapes:
            # 1) {"requirements": [...]}  (default MALCOMp format)
            # 2) {"req": [...]}           (some concept-extraction outputs)
            # 3) [..., ...]               (plain list of requirement objects)
            if isinstance(raw, dict):
                if "requirements" in raw:
                    self.data = raw["requirements"]
                elif "req" in raw:
                    self.data = raw["req"]
                else:
                    raise TypeError(
                        f"Unsupported requirement JSON format in {self.file_path}"
                    )
            elif isinstance(raw, list):
                self.data = raw
            else:
                raise TypeError(
                    f"Unsupported requirement JSON root type {type(raw)} "
                    f"in {self.file_path}"
                )

    def get_human_input(self, prompt):
        if self.current_index < len(self.data):
            item = self.data[self.current_index]
            reply = json.dumps(item)
            self.current_index += 1
        else:
            reply = "exit"
        self._human_input.append(reply)
        return reply
