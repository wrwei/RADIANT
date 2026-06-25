import logging
import sys
import os
import json
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autogen import ConversableAgent
from autogen.io import IOStream
from base import Base
from eol_execution import convert_emfatic_to_ecore, execute_eol
import trace_locator

logger = logging.getLogger(__name__)


class EMFModelCreation(Base):

    def __init__(self, config_path="config.yaml", disabled_agents=None, run_id=None,
                 case_study=None):
        super().__init__(
            "emf_model_creation",
            config_path,
            disabled_agents=disabled_agents,
            run_id=run_id,
            case_study=case_study,
        )

        # Load assets
        system_desc = self.load_asset("system_description")
        few_shot_creation = self.load_asset("few_shot_model_creation")
        few_shot_checker = self.load_asset("few_shot_model_checker")
        cot_creation = self.load_asset("chain_of_thought_creation")
        cot_checker = self.load_asset("chain_of_thought_checker")
        cot_trace = self.load_asset("chain_of_thought_trace")
        concept_extraction = self.load_asset("extracted_terms")
        dsl = self.load_asset("dsl_source")
        self.accepted_eol = ""
        self.latest_eol = ""
        self.accepted_model_path: Path | None = None
        self._execution_attempt_index = 0
        repair_cfg = self.stage_config.get("execution_repair", {})
        self.execution_repair_enabled = bool(repair_cfg.get("enabled", True))
        self.max_repair_attempts = int(repair_cfg.get("max_attempts", 2))
        self.execution_timeout_seconds = int(repair_cfg.get("timeout_seconds", 60))
        repo_root = Path(__file__).resolve().parents[2]
        default_runner = repo_root / "MALCOMj" / "build" / "install" / "MALCOMj" / "bin" / "MALCOMj.bat"
        self.malcomj_runner = Path(repair_cfg.get("runner", str(default_runner)))
        self.dsl_source_path = self.resolve_asset("dsl_source")
        knowledge_file = repair_cfg.get("knowledge_file", "model/eol_repair_knowledge.md")
        self.repair_knowledge_path = self.find_asset(knowledge_file)
        self.repair_knowledge = (
            self.repair_knowledge_path.read_text(encoding="utf-8")
            if self.repair_knowledge_path.exists()
            else ""
        )

        # Model Creator agent
        self.model_creator = self.create_agent(
            name="Model_Creator",
            system_message=(
                "You are an expert in Model Driven Engineering (MDE). "
                "You are experienced in creating EMF (Eclipse Modelling Framework) models using the Epsilon Object Language (EOL). "
                "Your job is to write an EOL program to create an EMF model that conforms to the EMF metamodel (written in the Emfatic language) in here: " + dsl +
                "STRICT FEATURE FAITHFULNESS: every class you instantiate and every feature you read or assign (e.g. `obj.feature = ...`, `obj.feature.add(...)`) MUST be declared in the metamodel above on that object's class (or one of its ancestors). Do NOT invent, rename or abbreviate feature names — e.g. do not write `.ifaces` when the metamodel declares `interfaces`. Copy class and feature names verbatim from the metamodel. "
                "The description of the system to be developed is here: " + system_desc +
                "You should base your answer on the requirements provided to you by User. "
                "The Concepts extracted (in JSON) from the requirements are here: " + concept_extraction +
                "Consult the thinking process here: " + cot_creation +
                "Here are some examples based on input requirements: " + few_shot_creation +
                "IMPORTANT: You should consult and build upon the code produced by Model_Refactorer and EOL_Repairer in previous rounds. "
                "You must only include EOL code in your responses. "
                "Do not include any other contents that are not provided to you. "
                "Please do not include explanations in your answers. Do not include markdowns (no ```). "
            ),
            description="An EMF model creator using EOL, based on the inputs and responses from the User.",
        )

        # Model Checker agent
        self.model_checker = self.create_agent(
            name="Model_Checker",
            system_message=(
                "You are an expert in Model Driven Engineering (MDE). "
                "You are experienced in creating EMF (Eclipse Modelling Framework) models using the Epsilon Object Language (EOL). "
                "Your job is to check if the EOL program provided to you is correct, and respond with the correct EOL code. "
                "You should base your answer on both the EMF metamodel (written in Emfatic) here: " + dsl +
                ", and the requirements provided by User. "
                "STRICT FEATURE FAITHFULNESS — verify every feature the EOL reads or assigns is declared in the metamodel on that object's class (or an ancestor); FIX any invented/abbreviated feature name (e.g. replace `.ifaces` with the declared `interfaces`) so it matches the metamodel verbatim. "
                "The description of the system to be developed is here: " + system_desc +
                "The Concepts extracted (in JSON) from the requirements are here: " + concept_extraction +
                "Consult the thinking process in here: " + cot_checker +
                "Here are some examples of EOL model-creation programs based on inputs: " + few_shot_checker +
                "You must only include EOL code in your responses. "
                "Do not include any other contents that are not provided to you. "
                "Please do not include explanations in your answers. In addition, no markdown is permitted (no ```). "
            ),
            description="A program checker to check the syntax of the EOL code.",
        )

        # Model Refactorer agent
        self.model_refactorer = self.create_agent(
            name="Model_Refactorer",
            system_message=(
                "You are an expert in Model Driven Engineering (MDE), and you are working with some experts in creating models that conform to a metamodel written in the Emfatic language. "
                "Model_Creator has created the source code in Epsilon Object Language (EOL) based on the inputs from User. "
                "Model_Checker has checked the syntax of the EOL code. "
                "Your job is to organise and refactor the EOL code (when necessary) provided by them. "
                "When you provide your answer, you need to combine it with previous Model_Refactorer and EOL_Repairer answers and update them. "
                "Your answer needs to be correctly written in EOL. "
                "Do not include any other contents that are not provided to you. "
                "If the code is already correct and complete, output it unchanged. "
                "Please only provide EOL code in your answers. Do not explain (no ```). "
            ),
            description="A Model_Refactorer to organise and refactor the EOL code from Model_Checker.",
        )

        # JSON Generator agent for traceability
        self.json_generator = self.create_agent(
            name="Trace_Generation_Agent",
            system_message=(
                "You are an expert in Model Driven Engineering (MDE). "
                "You are experienced in creating EMF (Eclipse Modelling Framework) models using languages provided by the Eclipse Epsilon platform. "
                "Specifically, you use the Epsilon Object Language (EOL) to create EMF models programmatically. "
                "Your job is to generate a JSON element by analysing the accepted EOL code for model creation, and the requirement provided by User. "
                "The accepted EOL may be provided by Model_Checker, Model_Refactorer, or EOL_Repairer after MALCOMj execution feedback. "
                "The metamodel (created using the Emfatic language) for the model to be created is here: " + dsl +
                "Here is some guidance to help you: " + cot_trace +
                "Your answer should be in the following JSON format : "
                '{"requirement_gid" : ${the gid of the requirement provided by User}, '
                '"Model_Element" : ${the name of the class created by the EOL code}, '
                '"Model_Element_id" : ${the name or the id of the object created for the above class}, '
                '"Model_attribute": ${the name of the attributes set by the EOL code}, '
                '"Attribute_value": ${the value of the above attribute set by the EOL code}, '
                '"Model_reference":${the name of the references set by the EOL code}, '
                '"Reference_value":${the name or the id of the value set for the above reference} } '
                "If the EOL code creates multiple model elements, please create a JSON list with multiple JSON entries, like so: [$JSON entry, $JSON entry, ... $JSON entry]."
                " The Output format is JSON only, no markdown permitted (no ```), no explain."
            ),
            description="A Trace_Generation_Agent to generate a JSON element based on the accepted EOL code (from Model_Checker, Model_Refactorer, or EOL_Repairer) and the requirement provided by User.",
        )

        self.eol_repairer = ConversableAgent(
            name="EOL_Repairer",
            llm_config={**self.default_llm_config},
            system_message=(
                "You are an expert in Epsilon Object Language (EOL), EMF, and metamodel-conformant model creation. "
                "Your task is to repair a complete EOL program after MALCOMj reports a parse or runtime error. "
                "Use the exact class and feature names declared in the current Emfatic metamodel. "
                "Do not invent references or attributes that are not present in the metamodel. "
                "Preserve all model creation logic that is not related to the reported error. "
                "Return the complete repaired EOL program only. Do not include explanations or markdown fences."
            ),
            description="Repairs generated EOL using MALCOMj execution feedback.",
        )
        # The verification gate reuses EOL_Repairer to fix the EOL on a hard failure.
        self._repair_agent = self.eol_repairer
        self._repair_target = self.stage_config["output"].get("code_file")

        self.init_group_chat()

    def _trace_source_for_entry(self, entry):
        element_id = entry.get("Model_Element_id") or entry.get("Model_Element")
        file_label = self.stage_config["output"].get("code_file", "result_model.eol")
        if not element_id:
            return self._build_source(file_label, None)
        span = trace_locator.locate(
            "eol", str(element_id), self._read_code_artefact_text())
        return self._build_source(file_label, span)

    def run(self, message=""):
        """Run the model stage with execution-guided EOL acceptance."""
        chat_results = self._run_round_robin()
        output_cfg = self.stage_config["output"]

        # Write the EOL artefact FIRST so trace enrichment can locate against it.
        code_file = output_cfg.get("code_file")
        if code_file:
            final_eol = self.accepted_eol or self.latest_eol
            if final_eol:
                out_path = self.output_dir / code_file
                out_path.write_text(final_eol, encoding="utf-8")
                logger.info("Stored accepted EOL output to %s", out_path)
                self._record_artifact(out_path)
            else:
                logger.warning("No EOL output was produced")

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

        if self.accepted_model_path and self.accepted_model_path.exists():
            self._record_artifact(self.accepted_model_path)
        self._verify_and_repair()
        return chat_results

    def _run_round_robin(self):
        """Run normal agents and invoke MALCOMj after each refactored EOL candidate."""
        chat_history = []
        llm_messages = []
        stream = IOStream.get_default()
        normal_agents = [self.model_creator, self.model_checker, self.model_refactorer]

        feeds = self._feeds()
        total = len(feeds)
        for index, requirement in enumerate(feeds, start=1):
            chat_history.append({"name": self.user.name, "content": requirement})
            llm_messages.append({"role": "user", "name": self.user.name, "content": requirement})
            self._stream_chat_message(stream, self.user.name, requirement)

            for agent in normal_agents:
                if agent is None:
                    continue
                self._emit_progress(stream, index, total, agent.name)
                reply = agent.generate_reply(messages=llm_messages)
                content = self._normalise_reply_content(reply)
                chat_history.append({"name": agent.name, "content": content})
                llm_messages.append({"role": "assistant", "name": agent.name, "content": content})
                self._stream_chat_message(stream, agent.name, content)

            candidate = self._strip_markdown_fence(chat_history[-1]["content"]).strip()
            if candidate:
                accepted = self._accept_or_repair_eol(candidate, chat_history, llm_messages, stream)
                if accepted:
                    self.latest_eol = accepted

            if self.json_generator is not None:
                self._emit_progress(stream, index, total, self.json_generator.name)
                reply = self.json_generator.generate_reply(messages=llm_messages)
                content = self._normalise_reply_content(reply)
                chat_history.append({"name": self.json_generator.name, "content": content})
                llm_messages.append({"role": "assistant", "name": self.json_generator.name, "content": content})
                self._stream_chat_message(stream, self.json_generator.name, content)

        return SimpleNamespace(chat_history=chat_history)

    def _accept_or_repair_eol(self, candidate: str, chat_history, llm_messages, stream) -> str:
        self.latest_eol = candidate if candidate.endswith("\n") else candidate + "\n"
        if not self.execution_repair_enabled:
            self.accepted_eol = self.latest_eol
            return self.accepted_eol
        if not self.malcomj_runner.exists():
            logger.warning("MALCOMj runner not found at %s; skipping EOL execution", self.malcomj_runner)
            self.accepted_eol = self.latest_eol
            return self.accepted_eol

        try:
            ecore_path = self._ensure_generated_ecore()
        except Exception as ex:
            logger.warning("Unable to convert generated Emfatic to Ecore: %s", ex)
            return self.latest_eol

        current = self.latest_eol
        for repair_index in range(self.max_repair_attempts + 1):
            result = self._execute_candidate(current, ecore_path)
            if result.ok:
                self.accepted_eol = current if current.endswith("\n") else current + "\n"
                self.accepted_model_path = result.model_path
                success = (
                    "MALCOMj execution succeeded for the current EOL. "
                    f"Accepted model: {result.model_path}"
                )
                self._append_tool_message("EOL_Executor", success, chat_history, llm_messages, stream)
                return self.accepted_eol

            feedback = self._build_execution_feedback(current, result, repair_index)
            self._append_tool_message("EOL_Executor", feedback, chat_history, llm_messages, stream)
            logger.info("MALCOMj rejected EOL candidate: %s", result.error_summary)
            if repair_index >= self.max_repair_attempts:
                logger.warning("EOL repair attempts exhausted; keeping latest candidate unaccepted")
                return current if current.endswith("\n") else current + "\n"

            reply = self.eol_repairer.generate_reply(messages=llm_messages)
            repaired = self._strip_markdown_fence(self._normalise_reply_content(reply)).strip()
            if not repaired:
                logger.warning("EOL_Repairer returned an empty repair")
                return current if current.endswith("\n") else current + "\n"
            current = repaired if repaired.endswith("\n") else repaired + "\n"
            chat_history.append({"name": self.eol_repairer.name, "content": current})
            llm_messages.append({"role": "assistant", "name": self.eol_repairer.name, "content": current})
            self._stream_chat_message(stream, self.eol_repairer.name, current)
        return current

    def _ensure_generated_ecore(self) -> Path:
        ecore_path = self.output_dir / "result_dsml.generated.ecore"
        convert_emfatic_to_ecore(self.dsl_source_path, ecore_path)
        self._record_artifact(ecore_path)
        return ecore_path

    def _execute_candidate(self, eol_text: str, ecore_path: Path):
        self._execution_attempt_index += 1
        attempts_dir = self.output_dir / "eol_execution_attempts"
        candidate_path = attempts_dir / f"candidate_{self._execution_attempt_index:03d}.eol"
        attempt_model_path = attempts_dir / f"candidate_{self._execution_attempt_index:03d}.model"
        # Name the accepted EMF model after the phase's code artefact (e.g.
        # result_model.eol -> result_model.model) so it is case-study-agnostic
        # rather than the historical hard-coded "result_AUV.model".
        code_file = self.stage_config["output"].get("code_file", "result_model.eol")
        accepted_model_path = self.output_dir / (Path(code_file).stem + ".model")
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(eol_text, encoding="utf-8")
        return execute_eol(
            runner=self.malcomj_runner,
            eol_path=candidate_path,
            ecore_path=ecore_path,
            attempt_model_path=attempt_model_path,
            accepted_model_path=accepted_model_path,
            timeout_seconds=self.execution_timeout_seconds,
        )

    def _build_execution_feedback(self, eol_text: str, result, repair_index: int) -> str:
        # Distinguish a runtime/parse crash (EOL threw) from a non-conformant model
        # (EOL ran clean but the produced model violates the metamodel). The repair
        # agent needs to know which, because the fix differs.
        if getattr(result, "conformant", None) is False:
            failure_kind = "MODEL NON-CONFORMANCE — the EOL ran without error but the model it produced does not conform to the metamodel."
            diagnostics = (
                "Conformance violations (EMF Diagnostician):\n"
                f"{self._bounded_text(result.conformance_summary or result.error_summary, 4000)}\n\n"
                "Fix instruction: adjust the EOL so every created object satisfies the "
                "metamodel's multiplicities, required features, reference targets, and "
                "attribute types. Do not remove valid model-creation logic."
            )
        else:
            failure_kind = "EXECUTION ERROR — MALCOMj reported a parse or runtime error while executing the EOL."
            diagnostics = (
                f"Error summary:\n{result.error_summary}\n\n"
                "Fix instruction: return a complete EOL program that executes against the current generated metamodel."
            )
        return (
            f"MALCOMj rejected the current EOL candidate.\n\n"
            f"Failure kind: {failure_kind}\n"
            f"Repair attempt: {repair_index + 1} of {self.max_repair_attempts}\n"
            f"Exit code: {result.exit_code}\n\n"
            f"{diagnostics}\n\n"
            "Current generated Emfatic metamodel:\n"
            f"{self._bounded_text(self.dsl_source_path.read_text(encoding='utf-8'), 6000)}\n\n"
            "Current EOL candidate:\n"
            f"{self._bounded_text(eol_text, 10000)}\n\n"
            "Relevant EOL repair knowledge:\n"
            f"{self._bounded_text(self.repair_knowledge, 5000)}\n\n"
            "Return the complete repaired EOL program only (no markdown, no explanation)."
        )

    def _append_tool_message(self, name: str, content: str, chat_history, llm_messages, stream) -> None:
        chat_history.append({"name": name, "content": content})
        llm_messages.append({"role": "user", "name": name, "content": content})
        self._stream_chat_message(stream, name, content)

    @staticmethod
    def _bounded_text(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + "\n... [truncated]\n"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    EMFModelCreation().run()
