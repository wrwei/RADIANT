import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autogen import ConversableAgent
from base import Base
import trace_locator

logger = logging.getLogger(__name__)


class DSMLCreation(Base):

    def __init__(self, config_path="config.yaml", disabled_agents=None, run_id=None,
                 case_study=None):
        super().__init__(
            "dsml_creation",
            config_path,
            disabled_agents=disabled_agents,
            run_id=run_id,
            case_study=case_study,
        )

        # Load assets
        system_desc = self.load_asset("system_description")
        few_shot_extraction = self.load_asset("few_shot_dsl_extraction")
        few_shot_checker = self.load_asset("few_shot_dsl_checker")
        cot_extraction = self.load_asset("chain_of_thought_extraction")
        cot_checker = self.load_asset("chain_of_thought_checker")
        extracted_terms = self.load_asset("extracted_terms")
        emfatic_rules = self.load_asset("emfatic_rules")

        # DSL Extractor agent
        self.dsl_extractor = self.create_agent(
            name="DSML_Extraction_Agent",
            system_message=(
                "You are an expert in Model Driven Engineering (MDE). "
                'You are experienced in creating "Domain Specific Languages (DSLs)" or "metamodels". '
                "A metamodel contains the abstract syntax to capture the concepts for the system to be developed. "
                "You have extensive experience in creating metamodels using the Ecore modeling language provided by the Eclipse Modeling Framework (EMF). "
                "You are also an expert in creating metamodels using the Emfatic language (a textual syntax for Ecore) to create metamodels. "
                "Your job is to create a metamodel written in Emfatic based on the requirements provided to you in JSON. "
                "The description of the system to be developed is here: " + system_desc +
                "The Concepts and Instances extracted in Phase 2 are here: " + extracted_terms +
                "FAITHFULNESS: examine the requirements carefully and create classes that capture ONLY what the requirements actually describe. Every class, attribute and reference must be traceable to the requirement statements; the Phase-2 Concept model is a guide to help you (not necessarily an exhaustive list — derive a class from the requirements if they clearly call for it even when it is not listed as a Concept). Do NOT hallucinate or invent elements the requirements do not mention — in particular, do not add generic architectural scaffolding (deployment, mission, task, port, connection, coordinator, manager, etc.) that no requirement calls for. "
                "Here are some thinking processes to guide you: " + cot_extraction +
                "Here are some examples of the extracted metamodels based on inputs: " + few_shot_extraction +
                "Consider also the previous inputs from the User. "
                "When building your Emfatic code, incorporate and build upon the code from your previous answers. "
                "You must only include Emfatic code in your responses. "
                "Do not include any other contents that are not provided to you. "
                "Please do not include explanations in your answers. In addition, no markdown is permitted (no ```). "
            ),
            description="A DSL extractor to create metamodels using Emfatic based on the input and responses from the User.",
        )

        # DSL Checker agent
        self.dsl_checker = self.create_agent(
            name="DSML_Checker_Agent",
            system_message=(
                "You are an expert in Model Driven Engineering (MDE). "
                'Specifically, you are experienced in creating "Domain Specific Languages (DSLs)" or "metamodels". '
                "A metamodel contains the abstract syntax to capture the concepts for the system to be developed. "
                "You have extensive experience in creating metamodels using the Ecore modeling language provided by the Eclipse Modeling Framework (EMF). "
                "You are also an expert in using the Emfatic language (a textual syntax for Ecore) to create metamodels. "
                "The description of the system to be developed is here: " + system_desc +
                "A description of the language syntax for Emfatic is here: " + emfatic_rules +
                "Your job is to check whether the metamodel provided to you written in Emfatic is correct. "
                "You should also consult the thinking process in here: " + cot_checker +
                "Here are some examples of the extracted metamodels based on inputs: " + few_shot_checker +
                "FAITHFULNESS — cross-check every class against the requirement statements: each class, attribute and reference must be justified by what the requirements actually say. REMOVE any class the requirements do not support (e.g. invented deployment / mission / task / port / connection scaffolding), and do NOT add ungrounded classes of your own. Use the Phase-2 Concepts and Instances as a guide: " + extracted_terms +
                "You must only include Emfatic code in your responses. "
                "Do not include any other contents that are not provided to you. "
                "Please do not include explanations in your answers. In addition, no markdown is permitted (no ```). "
            ),
            description="A DSML_Checker_Agent to check the syntax of Emfatic code.",
        )

        # DSL Refactorer agent
        self.dsl_refactorer = self.create_agent(
            name="DSML_Refactoring_Agent",
            system_message=(
                'You are an expert in Model Driven Engineering (MDE), and you are working with some experts in creating "Domain Specific Languages (DSLs)" or "metamodels". '
                "DSML_Extraction_Agent has created the DSL using Emfatic based on the inputs from User. "
                "DSML_Checker_Agent has checked the syntax of the Emfatic code. "
                "Your job is to organise and refactor (when necessary) the Emfatic code provided by DSML_Checker_Agent. "
                "When you provide your answer, you need to combine it with your previous answer and update them in one package. "
                # Inheritance / common-parent refactoring (paper §3.7).
                "INHERITANCE & COMMON-ATTRIBUTE REFACTORING: "
                "Inspect the classes generated so far as a whole. When two or more classes share the same attribute(s), reference(s), or operation(s), "
                "elicit an abstract parent class (mark with `abstract`) that contains the common members and have the original classes `extends` it. "
                "When two classes are clearly specialisations of a common concept (e.g. one is a kind of the other in the requirement wording), "
                "introduce an `extends` relationship rather than duplicating members. "
                "Hoist a member to the parent only when it is truly common to all subclasses; otherwise leave it on the specific subclass. "
                "Preserve the original Emfatic semantics: do not rename existing classes or change attribute types when introducing inheritance. "
                "FAITHFULNESS — do NOT use refactoring as a pretext to add classes the requirements do not describe. Introduce an abstract parent ONLY to factor members shared by classes that ALREADY exist, never as a new domain entity. Remove any class not grounded in the requirements (e.g. deployment, mission, task, port, connection, coordinator scaffolding). "
                # Containment / reference disambiguation (preserved from earlier behaviour).
                "CONTAINMENT vs REFERENCE: "
                "Pay attention to containment and non-containment references. "
                'In the requirement, when it says "A contains B" or "A defines B", it often denotes a containment reference. '
                'In the requirement, when it says "A uses B" or "A refers to B", it often denotes a non-containment reference. '
                "Refactor references when necessary by looking at the requirements as a whole. "
                # Output discipline.
                "Your answer needs to be correctly written in Emfatic. "
                "You must include only Emfatic code in your responses. "
                "Do not include any other contents that are not provided to you. "
                "Please do not explain. In addition, no markdown is permitted (no ```)"
            ),
            description="A DSML_Refactoring_Agent to organise and refactor the code from DSML_Checker_Agent (inheritance hoisting + containment-vs-reference disambiguation).",
        )

        # JSON Generator agent for traceability
        self.json_generator = self.create_agent(
            name="Trace_Generation_Agent",
            system_message=(
                "You are an expert in Model Driven Engineering (MDE). "
                "Your job is to generate a traceability JSON element based on the Emfatic code provided by DSML_Refactoring_Agent and the requirement in JSON provided by User. "
                "In the Emfatic code provided to you by DSML_Refactoring_Agent, you shall identify which class, attributes, references and operations are created, based on the requirement JSON provided by User. "
                "Your answer should be in the following JSON format : "
                '{"requirement_gid" : ${the gid of the requirement provided by User}, '
                '"Emfatic_class" : ${the class name provided by DSML_Refactoring_Agent}, '
                '"Emfatic_attributes": ${the "attr"s that the class contains (if not null)}, '
                '"Emfatic_references":${the "ref"s or "val"s that the class contains (if not null)}, '
                '"Emfatic_operations": ${the "op"s that class contains (if not null)} }'
                "If the Emfatic code creates multiple classes, please create a JSON list with multiple JSON entries, like so: [$JSON entry, $JSON entry, ... $JSON entry]."
                " The Output format is JSON only, no markdown permitted (no ```), no explain."
            ),
            description="A Trace_Generation_Agent to generate a JSON element based on the Emfatic code provided by DSML_Refactoring_Agent and the requirement provided by User.",
        )

        # Dedicated repair agent (side agent — not in the roster) used by the
        # verification gate to fix the Emfatic metamodel on a hard failure.
        self._repair_agent = ConversableAgent(
            name="DSML_Repair_Agent",
            llm_config={**self.default_llm_config},
            system_message=(
                "You are an expert in EMF, Ecore and the Emfatic language. "
                "Repair the provided Emfatic metamodel so it satisfies the reported "
                "verification failures (e.g. syntax errors, or a class a trace points to "
                "that is missing). Preserve everything unrelated. "
                "Return the complete corrected Emfatic only — no explanation, no markdown fences."
            ),
            description="Repairs the Emfatic metamodel after a verification failure.",
        )
        self._repair_target = self.stage_config["output"].get("code_file")

        self.init_group_chat()

    def _trace_source_for_entry(self, entry):
        element_id = entry.get("Emfatic_class")
        file_label = self.stage_config["output"].get("code_file", "result_dsml.emf")
        if not element_id:
            return self._build_source(file_label, None)
        span = trace_locator.locate(
            "emfatic", str(element_id), self._read_code_artefact_text())
        return self._build_source(file_label, span)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    DSMLCreation().run()
