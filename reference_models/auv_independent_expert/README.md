# AUV Independent Expert Reference

This directory is the audited independent expert reference for the AUV case
study. It was produced by reasoning over the requirements, the MALCOMp
extraction rules, Emfatic/Ecore semantics, EOL, and the supplied RoboChart
grammar. No configured MALCOMp LLM stage or `config.yaml` was invoked.

## Pipeline Boundary

1. `requirement_architecture.json` drives term extraction, DSL extraction, and
   architecture model creation.
2. `requirement_behaviour.json`, together with the architecture context, drives
   state-machine extraction.
3. The resulting chain is:

   `requirements -> result_concept_extraction.json -> result_dsml.emf/.ecore ->`
   `result_eol_program.eol -> result_AUV.model -> result_behaviour.txt`

## Artifacts

| Stage | Artifacts |
|---|---|
| Term extraction | `result_concept_extraction.json` |
| DSL extraction | `result_dsml.emf`, `result_dsml.ecore`, `result_dsml_extraction.json` |
| Model creation | `result_eol_program.eol`, `result_AUV.model`, `result_model_creation.json` |
| State machine | `result_behaviour.txt`, `result_behaviour_extraction.json`, `reference_traceability.json` |
| Audit | `AUDIT.md`, `reference_manifest.json` |

## Architecture Model

The metamodel has 13 EClasses. `Component` factors the interface references of
`RoboticPlatform` and `Controller`; `Type` generalises `PrimitiveType` and
`CompositeType`. The instance contains 47 objects: one module, five primitive
types, three composite types, four interfaces, one robotic platform, three
controllers, three functions, and their contained values, events, and
parameters.

## Expert Interpretations

1. Term extraction preserves the source spelling `Intpus`. Model creation
   normalises it to `Inputs`, because SD3, SD4, and all behaviour references use
   `Inputs`. Each Concept is emitted only on its first occurrence, while every
   quoted Instance occurrence is traced to its own GID.
2. Event and function parameters that have no name in the requirements remain
   unnamed in `result_AUV.model`. EOL variable names such as `advVelParam` are
   program-local identifiers, not domain names.
3. LRE-Beh4 uses `hvel` for the undeclared `vel`, and uses `odist` for general
   obstacle distance.
4. LRE-Beh11 is interpreted according to its stated vertical semantics, using
   `vvel` and `vdist` instead of the inconsistent `hvel` and `hdist` tokens.
5. LRE-Beh13 normalises `StaticObsHorzDist` to the declared
   `StaticObsHorizDist`.

`result_behaviour.txt` contains the required upstream type, record, interface, and event
declarations, followed by exactly one state machine. This satisfies the
state-machine prompt rule that every triggered event must be defined in the
generated DSL text.

See `AUDIT.md` for the validation scope and limitations. The reference is
suitable as a gold model under these documented interpretations; it is not a
claim that the ambiguous source requirements have a unique interpretation.
