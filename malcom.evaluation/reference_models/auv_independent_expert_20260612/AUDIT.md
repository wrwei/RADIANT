# AUV Reference Audit

Audit date: 2026-06-12

## Verdict

The artifact chain is internally coherent and suitable as the independent
expert reference, subject to the documented requirement normalisations below.
The architecture chain is executable and deterministic. The state machine has
complete requirement coverage and is structurally parseable, but it has not
been validated by a full Xtext linker or a behavioural model checker.

## Stage Results

### Term extraction

- 83 trace entries cover all 20 architecture requirement GIDs.
- The nine Concepts are emitted exactly once, at their first occurrence. Every
  unique quoted Instance occurrence is retained, including the repeated
  `AUV_Module` references in later requirements.
- Every `Requirement` field is byte-for-byte equal to the corresponding source
  requirement description.
- Concept descriptions are `null` because the source does not explicitly
  define generic concept meanings. Non-null instance descriptions contain only
  wording supplied by the corresponding requirement.
- The source token `Intpus` is preserved in this stage. Its later normalisation
  to `Inputs` is explicit rather than hidden.
- Referenced type instances (`real`, `nat`, `SVec`, and `Obstacle`) are retained
  because the term-extraction few-shot rule explicitly treats quoted input and
  return types as instances.
- `Parameter` is not extracted as an independent concept: the supplied event
  few-shot mentions parameters but extracts only `Interface` and `Event`.
- No Concept is rediscovered in a later requirement; later entries set
  `Concept` to `null` and retain the established `Instance_of` relationship.

### Emfatic and Ecore

- The official Eclipse Emfatic compiler reports no syntax errors or warnings.
- The generated Ecore loads as package
  `http://www.sawg.org/malcom/reference/auv/independent` and contains 13
  EClasses.
- Containment is used for module-owned elements, values, events, and
  parameters. Interface usage and type references are non-containment links.
- `result_dsml_extraction.json` contains 66 prompt-schema trace entries. Every
  traced class, attribute, and reference exists in the generated Ecore.

### EOL and AUV model

- The EOL parser reports no parse problems.
- Executing `result_eol_program.eol` against `result_dsml.ecore` recreates
  `result_AUV.model` exactly, including the same SHA-256 digest.
- The model contains 47 objects and satisfies all 20 architecture requirements.
- All type and interface references resolve to objects contained by the module.
- The five parameters that are unnamed by the requirements remain unnamed in
  the EMF model.
- `result_model_creation.json` contains 122 prompt-schema trace entries. Every
  entry maps to an actual EOL object creation, assignment, or reference update.

### State machine

- All 41 behaviour requirements are represented in
  `reference_traceability.json`.
- All 18 transition requirements map exactly to transitions `t1` through
  `t18`.
- The MALCOMj RoboChart text parser extracts one initial node, four states, and
  18 transitions (5 nodes total).
- Every type, interface, event, and function referenced by `result_behaviour.txt` is present
  in the architecture model.
- `result_behaviour.txt` explicitly declares the required types, records, interfaces, and
  all eight used events before defining the single `LRE_Beh` state machine.
- Separate `uses Inputs` and `uses Outputs` clauses follow the supplied Xtext
  grammar, which repeats `uses` rather than accepting a comma-separated list.

## Documented Interpretations

- `Intpus` is a source typo and becomes `Inputs` after term extraction.
- LRE-Beh4's undeclared `vel` is interpreted as horizontal velocity `hvel`.
- LRE-Beh11's prose says vertical while its tokens say `hvel`/`hdist`; vertical
  semantics (`vvel`/`vdist`) are used.
- LRE-Beh13's `StaticObsHorzDist` is interpreted as the declared
  `StaticObsHorizDist`.
- Requirements omit architecture parameter names, so those model elements are
  left unnamed. The local function parameter `o` in `result_behaviour.txt` follows the exact
  function-declaration example supplied by the state-machine prompt.

## Validation Limit

`RoboChartTextParser` intentionally validates only the machine name, nodes, and
transition endpoints. It does not parse or link variables, constants, events,
functions, guards, triggers, or actions. Therefore the correct claim is
"structurally parsed and manually semantically audited", not "fully Xtext
validated". No FDR/CSP refinement or reachability analysis was performed.
