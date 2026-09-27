import logging
import sys
import os
import json
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autogen import ConversableAgent
from autogen.io import IOStream
from base import Base
import trace_locator

logger = logging.getLogger(__name__)


class BehaviourModelCreation(Base):

    def __init__(self, config_path="config.yaml", disabled_agents=None, run_id=None,
                 case_study=None):
        super().__init__(
            "behaviour_model_creation",
            config_path,
            disabled_agents=disabled_agents,
            run_id=run_id,
            case_study=case_study,
        )

        # Load assets
        # Upstream context (Phases 2-4 outputs) — see paper §3.9 input list
        extracted_terms = self.load_asset("extracted_terms")
        dsl_source      = self.load_asset("dsl_source")
        model_source    = self.load_asset("model_source")
        # Behaviour-model grammar + examples (paper §3.9 input 5)
        robochart_ecore = self.load_asset("robochart_ecore")
        xtext = self.load_asset("xtext")
        code1 = self.load_asset("code_snippet_1")
        code2 = self.load_asset("code_snippet_2")
        semantic = self.load_asset("semantic")

        # Behaviour_Model_Creation_Agent agent
        self.modeller = self.create_agent(
            name="Behaviour_Model_Creation_Agent",
            system_message=(
                # Role
                "You are an expert in Domain Specific Modelling and Requirement Engineering. "
                "You will be provided with requirement statements from User.\n\n"
                # Upstream pipeline context — names defined here MUST be reused verbatim
                "UPSTREAM CONTEXT (use the names defined below verbatim — do not rename or invent new identifiers):\n\n"
                "Concept/Instance terminology extracted in Phase 2:\n" + extracted_terms + "\n\n"
                "DSML (Emfatic) generated in Phase 3:\n" + dsl_source + "\n\n"
                "System model program (EOL) generated in Phase 4:\n" + model_source + "\n\n"
                # Reference materials
                "METAMODEL:\n"
                "Here is a metamodel written in the Emfatic language for RoboChart which includes a state machine and other modules:\n" + robochart_ecore + "\n\n"
                "XTEXT GRAMMAR:\n"
                "Here is an Xtext grammar that conforms to the ecore. "
                "You need to know the link between the Xtext and ecore so that you can understand the code examples below.\n" + xtext + "\n\n"
                "CODE EXAMPLES:\n"
                "Here are example codes written in the DSL which conforms to the Xtext. "
                "Please understand the codes, especially the syntax and semantics:\n" + code1 + "\n\n"
                "Here is the second example, please follow the syntax and semantics of the code:\n" + code2 + "\n\n"
                "SEMANTIC EXAMPLE:\n"
                "Here is an example of a state and a transition when an event is triggered in DSL:\n" + semantic + "\n\n"
                # Task
                "TASK:\n"
                "Please find the States, Transitions, Constants, Events and Functions. "
                "Create only one state machine written in the DSL and the syntax that conforms to the code examples. "
                "Your response must be RoboChart DSL code only. Do not output JSON, markdown fences, or explanatory text.\n\n"
                # Domain knowledge
                "STATE MACHINE CONCEPTS:\n"
                "- State machines define behaviour using States, Junctions, and the possible Transitions among them.\n"
                "- States and Transitions also make use of: Events, Variables, required Interfaces, defined Interfaces, and Clocks; such elements can be used by the States and Transitions to accomplish the state machine's function.\n"
                "- The actions of states can be specified as being executed on entry, during, or on exit of the state.\n"
                "- Actions are defined using a simple action language which contains among other things: operation calls, conditionals, event input and output.\n"
                "- States can also be composite and so contain a state machine that is executed when that state is entered.\n"
                "- Transitions connect States and Junctions and they can have any combination of triggers, guards, or action statements that specify the conditions when a transition will occur.\n"
                "- Triggers cause a transition to be taken on the occurrence of a particular event. Optional start and end deadlines can be given to triggers supporting the specification of time properties of the system.\n"
                "- Guards are a boolean expression that only allow a transition to be taken when it evaluates to true, providing greater control over the transitions between states.\n"
                "- The action statement enables any required actions to be executed on the occurrence of a transition.\n\n"
                # Rules
                "RULES:\n"
                "- Draw Events, Variables, Constants and types from the UPSTREAM CONTEXT above where they fit; reuse upstream names verbatim (case-sensitive). You MAY introduce a boolean/enumeration guard variable to capture a domain predicate (see the FDR4 rules below).\n"
                "- If an event is used as a trigger or an action, you MUST declare it (e.g. `event reqMove`). Do NOT declare an event you never use as a trigger or action.\n"
                "- The initial state is defined as i0, with exactly one initial transition out of it (e.g. `transition t0 { from i0 to FirstState }`).\n"
                "- Transitions and states are written as separate blocks.\n"
                "- Check that every Variable, Event, Constant, type and State you reference is declared.\n\n"
                # FDR4 generator-ready constraints
                "FDR4 VERIFICATION — THE OUTPUT MUST BE A GENERATOR-READY ROBOCHART STATE MACHINE:\n"
                "- Output ONE bare `stm` block (plus any `enumeration` type declarations it needs). Do NOT write a `module`, `controller`, `robotic platform`, `interface`, or `uses`/`requires` clause — the pipeline synthesises all of those around your stm automatically.\n"
                "- Use RoboChart boolean operators: `/\\` for AND, `\\/` for OR, `not` for negation. Never write the words `and`/`or`.\n"
                "- Declare every domain type as an `enumeration` with concrete literals, e.g. `enumeration Obstacle { none near far }`, written at the top level (outside the stm).\n"
                "- AVOID uninterpreted/abstract functions (e.g. `odist(x)`, `hdist(x)`): they are not verifiable. Express each domain predicate as a boolean (or enumeration) guard VARIABLE instead — e.g. replace `odist(cdyn) > 7.5` with a `var dynObstacleFar : boolean` used as `condition dynObstacleFar`.\n"
                "- Use events as plain SYNCHRONISATIONS, without data payloads: write `trigger reqVel` and `action advVel` (or `entry advVel`). Do NOT attach data with `!`/`?` (e.g. avoid `advVel ! x` or `reqVel ? x`) — the control-flow structure is what is verified. Capture any value you need as a state variable updated by an `action`, e.g. `action vel = 1`.\n"
                "- Guards are boolean expressions over the stm's variables/constants only, e.g. `condition vel < MinSafeDist /\\ not inOPEZ`.\n"
                "- Ensure every state has at least one outgoing transition that can become enabled, so the machine does not trivially deadlock.\n"
                "- Variable/constant types should be `boolean`, `int`, `nat`, `real`, or a declared `enumeration`."
            ),
            description="A Behaviour_Model_Creation_Agent to give the code based on the response from User.",
            #max_consecutive_auto_reply=1,
        )

        # Behaviour checker agent — validates and corrects the RoboChart DSL
        # produced by Behaviour_Model_Creation_Agent (mirrors the checker role in
        # the concept, dsml and model phases). Its corrected DSL is the accepted
        # code artefact (config code_agent = Behaviour_Checker_Agent).
        self.checker = self.create_agent(
            name="Behaviour_Checker_Agent",
            system_message=(
                "You are an expert in RoboChart and Domain Specific Modelling. "
                "Behaviour_Model_Creation_Agent has produced a state machine written in the RoboChart DSL. "
                "Your job is to check that DSL and return a corrected version.\n\n"
                "UPSTREAM CONTEXT (the only valid identifiers — do not invent new ones):\n\n"
                "Concept/Instance terminology extracted in Phase 2:\n" + extracted_terms + "\n\n"
                "DSML (Emfatic) generated in Phase 3:\n" + dsl_source + "\n\n"
                "System model program (EOL) generated in Phase 4:\n" + model_source + "\n\n"
                "XTEXT GRAMMAR the DSL must conform to:\n" + xtext + "\n\n"
                "SEMANTIC EXAMPLE of a state and a transition:\n" + semantic + "\n\n"
                "CHECK AND FIX the following — the output must be ONE bare, generator-ready `stm`:\n"
                "- It is a single `stm` with NO module, controller, robotic platform, interface, or `uses`/`requires` clause — remove any such wrapper (the pipeline adds it automatically).\n"
                "- Events are plain SYNCHRONISATIONS: replace any `evt ! value` or `evt ? var` with just `evt`, and capture any needed value via a state-variable action (e.g. `action speed = 1`). Use `trigger <event>` and `entry <event>`/`action <event>`.\n"
                "- Every event used as a trigger or action is declared with `event <name>`; every domain type is declared as an `enumeration` with concrete literals; variables/constants are typed boolean/int/nat/real or a declared enumeration.\n"
                "- NO uninterpreted functions: replace any function call in a guard (e.g. `odist(x) > 1`) with a boolean (or numeric) guard variable, and remove every `function ...` declaration.\n"
                "- Boolean operators are `/\\` (and), `\\/` (or), `not` — never the words `and`/`or`. There are NO trailing semicolons on declarations.\n"
                "- Exactly one `initial` node (i0) with one initial transition; every transition references existing states; states and transitions are kept as separate blocks; every state has at least one outgoing transition that can become enabled.\n"
                "- Reuse identifiers from the UPSTREAM CONTEXT where they fit (verbatim, case-sensitive); you MAY add boolean/enumeration guard variables for domain predicates.\n"
                "If the DSL is already correct, return it unchanged. "
                "Your response must be RoboChart DSL code only. Do not output JSON, markdown fences, or explanatory text."
            ),
            description="A Behaviour_Checker_Agent to validate and correct the RoboChart DSL from Behaviour_Model_Creation_Agent.",
        )

        # JSON Generator agent for traceability
        self.json_generator = self.create_agent(
            name="Trace_Generation_Agent",
            system_message=(
                "You are an expert in Model Driven Engineering (MDE). "
                "Your job is to generate JSON elements based on the requirement statements provided by User, and the code provided by Behaviour_Model_Creation_Agent. "
                "For instance, the requirement statement may contain a source state, an end state, a transition, and an id. "
                'Your answer should be in the form of a JSON format : {"requirement_gid" : ${the id of the requirement } , "source_state" : ${the source state of the requirement}, "end_state": ${the end state of the requirement}, "transition":${the transition from source to target of the requirement}'
                "The id needs to conform to the id of the original statement provided by User. "
                "The transition value must be the exact transition name declared in the RoboChart code (for example, t0 or t11), not the trigger, condition, action, or natural-language description. "
                "For the initial node, use the exact node name from the RoboChart code (usually i0), not the word initial. "
                "You may provide multiple JSON elements and organise them in one array that conforms to JSON syntax. "
                "The Output format is JSON only, no markdown permitted (no ```), no explain."
            ),
            description="A Trace_Generation_Agent to generate JSON elements based on the requirement statements provided by User and the code provided by Behaviour_Model_Creation_Agent.",
            # max_consecutive_auto_reply=1,
        )

        # Dedicated repair agent (side agent — not in the roster) used by the
        # verification gate to fix the RoboChart state machine on a hard failure.
        self._repair_agent = ConversableAgent(
            name="Behaviour_Repair_Agent",
            llm_config={**self.default_llm_config},
            system_message=(
                "You are an expert in the RoboChart DSL. "
                "Repair the provided state machine so it satisfies the reported "
                "verification failures (e.g. parse errors, or a transition a trace "
                "points to that is missing). Preserve everything unrelated. "
                "If a failure is an FDR4 refinement violation, it includes a "
                "counterexample of the form '[deadlock after trace: e1 -> e2]' (or "
                "'divergence ...'). The trace is the sequence of events that reaches "
                "the fault: the state entered after the LAST event in the trace is the "
                "one that deadlocks (it has no enabled outgoing transition) or diverges. "
                "Fix it by giving that state a usable way out — add an outgoing "
                "transition (with a trigger or a satisfiable guard), or weaken an "
                "over-restrictive guard — keeping all element names unchanged. "
                "If the failure is a generator/parse error ('no viable alternative at "
                "input', 'EntryActionImpl ... action ... must be set', 'extraneous "
                "input'), it is almost always invalid action syntax. Fix it by: "
                "(a) making every event a plain SYNCHRONISATION — remove data payloads, "
                "so `advVel ! 1` or `advVel ! x` becomes just `advVel`, and `reqVel ? x` "
                "becomes just `reqVel`; capture any needed value as a state-variable "
                "`action` such as `action vel = 1`; "
                "(b) ensuring every `entry`/`action` is a complete statement (never an "
                "empty `entry`); "
                "(c) using RoboChart boolean operators `/\\` (and), `\\/` (or), `not`; "
                "(d) keeping the surrounding module/controller/interface/connection "
                "structure exactly as given — only change the offending action lines; "
                "(e) using ONLY plain transitions, triggers, and boolean guards — never "
                "introduce timed constructs (no `after(...)`, `wait`, `since`, `clock`, "
                "or `#` resets), which break the generator. "
                "Return the complete corrected RoboChart DSL only — no explanation, no markdown fences."
            ),
            description="Repairs the RoboChart state machine after a verification failure.",
        )
        # Repair the assembled complete model (the FDR4 target), not the LLM model
        # artefact — so metrics keep comparing the unmodified LLM output.
        self._repair_target = "result_behaviour_complete.rct"

        self.init_group_chat()

    def _trace_source_for_entry(self, entry):
        element_id = entry.get("transition")
        file_label = self.stage_config["output"].get("code_file", "result_behaviour_model.rct")
        if not element_id:
            return self._build_source(file_label, None)
        span = trace_locator.locate(
            "robochart", str(element_id), self._read_code_artefact_text())
        return self._build_source(file_label, span)

    def run(self, message=""):
        """Generate one state-machine artefact from the complete requirement set."""
        # Feed the parsed requirement list (self.user.data), like every other
        # phase — not the raw file object, which would include the
        # {"requirements": [...]} wrapper key.
        prompt = (
            "Generate the complete state machine from these behaviour "
            "requirements. Return RoboChart DSL code only.\n\n"
            + json.dumps(self.user.data, ensure_ascii=False, indent=2)
        )
        if message:
            prompt += "\n\n" + message

        chat_history = [{"name": self.user.name, "content": prompt}]
        llm_messages = [{"role": "user", "name": self.user.name, "content": prompt}]

        # Emit to the active IOStream so live UIs (MALCOM-web) see each agent,
        # mirroring base/model `_run_round_robin` (this custom run() must do it
        # itself since it does not go through the round-robin).
        stream = IOStream.get_default()
        self._stream_chat_message(stream, self.user.name, prompt)

        # Phase 5 processes the whole behaviour document at once (one "round").
        self._emit_progress(stream, 1, 1, self.modeller.name)
        modeller_reply = self.modeller.generate_reply(messages=llm_messages)
        modeller_content = self._normalise_reply_content(modeller_reply)
        chat_history.append({"name": self.modeller.name, "content": modeller_content})
        llm_messages.append(
            {"role": "assistant", "name": self.modeller.name, "content": modeller_content}
        )
        self._stream_chat_message(stream, self.modeller.name, modeller_content)

        # Checker reviews and corrects the modeller's DSL (skipped if disabled).
        if self.checker is not None:
            self._emit_progress(stream, 1, 1, self.checker.name)
            checker_reply = self.checker.generate_reply(messages=llm_messages)
            checker_content = self._normalise_reply_content(checker_reply)
            chat_history.append({"name": self.checker.name, "content": checker_content})
            llm_messages.append(
                {"role": "assistant", "name": self.checker.name, "content": checker_content}
            )
            self._stream_chat_message(stream, self.checker.name, checker_content)

        self._emit_progress(stream, 1, 1, self.json_generator.name)
        json_reply = self.json_generator.generate_reply(messages=llm_messages)
        json_content = self._normalise_reply_content(json_reply)
        chat_history.append({"name": self.json_generator.name, "content": json_content})
        self._stream_chat_message(stream, self.json_generator.name, json_content)

        result = SimpleNamespace(chat_history=chat_history)
        output_cfg = self.stage_config["output"]
        # Write the RoboChart artefact FIRST so trace enrichment can locate against it.
        # The checker is the accepted code source; fall back to the modeller when
        # the checker is disabled so the artefact is still produced.
        code_agent_name = output_cfg["code_agent"]
        if self.checker is None:
            code_agent_name = self.modeller.name
        self._store_last_agent_output(
            result,
            agent_name=code_agent_name,
            file_name=str(self.output_dir / output_cfg["code_file"]),
        )
        # Assemble a complete, generator-ready RoboChart model from the bare stm
        # (official Xtext parse + vendored robochart2rct.egl). Trace + verification
        # then run against the complete model. Fail-soft: the bare stm is kept on
        # failure (the FDR4 GeneratorRejected check is the backstop).
        self._assemble_complete_rct(output_cfg)
        self.store_json(
            result,
            agent_name=output_cfg["json_agent"],
            file_name=str(self.output_dir / output_cfg["json_file"]),
            tag_name=output_cfg["json_tag"],
        )
        self._verify_and_repair()
        return result

    def _assemble_complete_rct(self, output_cfg):
        """Assemble a complete generator-ready RoboChart model from the LLM's
        behaviour model into result_behaviour_complete.rct (the FDR4 target),
        leaving the LLM model (code_file) UNCHANGED so the evaluation metrics still
        compare the model the LLM produced. Fail-soft on any failure."""
        try:
            import behaviour_assembly
        except Exception:
            return
        code_path = self.output_dir / output_cfg["code_file"]        # LLM behaviour model
        if not code_path.is_file():
            return
        complete_path = self.output_dir / "result_behaviour_complete.rct"
        ok = behaviour_assembly.assemble_complete_rct(code_path, complete_path)
        stream = IOStream.get_default()
        msg = ("✓ Assembled complete RoboChart model into result_behaviour_complete.rct "
               "(interfaces + robotic platform + controller + module)"
               if ok else
               "⚠ RoboChart assembly unavailable — FDR4 will check the bare state machine")
        if stream is not None and hasattr(stream, "send_agent_message"):
            try:
                stream.send_agent_message("system", msg)
            except Exception:
                logger.debug("assembly announce failed", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    BehaviourModelCreation().run()
