# SRanger case study (RQ5 generality)

A small reactive ground robot: drives forward, turns in place on detecting an
obstacle, and stops on an `endTask` event. Forward IR distance sensor,
differential-drive actuator, three-mode controller (Moving / Turning / Final).

## Provenance

The requirement model and system description are adapted from an independently
authored case study used in a separate code-generation study (FORGE,
`forge.assets/case-studies/sranger`). The single source `requirement_all.json`
(23 requirements) was split into RADIANT's two requirement files **by the `types`
field** (no wording changed):

- `requirements/requirement_architecture.json` (10): structural / data-model
  requirements (`architecture`, `data_type`, `constants`, `event`, `actuator`,
  `function`, `variable`) — consumed by phases 2--4 (Concept, DSML, Model).
- `requirements/requirement_behaviour.json` (13): state-machine requirements
  (`state`, `guard_predicate`, `transition`, `constraint`) — consumed by phase 5.

## RQ5 demonstration run

`output/runs/sranger_deepseek_demo/` is a full RADIANT pipeline run with the
**unmodified** multi-agent layers (model: `deepseek_v4`):

    cd MALCOMp
    python run.py concept dsml model behaviour --case-study sranger --model deepseek_v4

All four phases passed their verification gates: 9-concept model (full coverage),
13-class valid Emfatic metamodel, an EOL that executes to a conformant EMF model,
and a 3-state / 7-transition RoboChart behaviour model that FDR verifies
deadlock- and divergence-free. See `case_studies/auv/experiment/FINDINGS.md`.
