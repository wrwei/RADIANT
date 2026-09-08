# Traceability Metrics

Input: each phase's trace file in a run directory
(`result_term_extraction.json`, `result_dsl_extraction.json`,
`result_model_creation.json`, `result_statemachine_extraction.json`) plus the
generated artefact each layer's links point into. No reference model is needed:
these metrics are properties of the run's own artefacts.

Metrics:
- **resolvability** — fraction of emitted links whose target element exists in
  the generated artefact
- **resolvability (named elements)** — the same, excluding the concept layer's
  type-name fallback (see below)
- **coverage** — fraction of in-scope requirements with at least one emitted link
- **effective coverage** — the stricter reading: requirements whose link also
  resolves
- **agreement with `source.resolved`** — where a trace entry carries a recorded
  verdict, whether recomputation agrees. A disagreement means the artefact and
  its trace file have drifted apart.

Resolution reuses `MALCOMp/trace_locator.py`, the same locators the pipeline
uses to stamp `source.resolved` during generation, so the driver measures the
property the pipeline claims rather than a re-implementation of it. Each layer
resolves against a different artefact: concept links into the requirement text,
notation into the Emfatic metamodel, model into the EOL program, behaviour into
the RoboChart state machine.

Two definitional points worth knowing before quoting a number:

- **Coverage is scoped per layer.** Behavioural requirements are only expected
  to be linked by the behaviour layer, architectural ones by the other three, so
  each layer's denominator is its own requirement set. Pooling them would
  understate every layer.
- **The concept layer has two kinds of link.** Most name a specific instance the
  requirement introduces (`AUV_Platform`), which appears verbatim in the
  requirement text. Where a requirement introduces no instance, the trace falls
  back to the metamodel *type* (`RoboticPlatform`), which requirements normally
  write as prose ("Robotic Platform") — so it does not resolve by identifier
  match. These are counted and reported separately; the *named elements* figure
  is the one comparable across layers.

A run whose layer emitted no links (a failed phase) is excluded from the
coverage average and counted under `runs_empty`, so a failure is not averaged in
as poor coverage.

Files:
- `metrics.py`: per-layer specs, resolution, and aggregation
- `compute.py`: batch scoring, CSV and Markdown report generation
- `test_traceability.py`: unit tests plus reproduction of the reported figures

Run:

```bash
python malcom.evaluation/metrics/traceability/compute.py
```

Outputs land in `metrics/results/traceability/`. To score a sweep laid out per
model and variant:

```bash
python malcom.evaluation/metrics/traceability/compute.py \
    --runs-root case_studies/auv/experiment/deepseek_v4/multi
```

## Reproduced figures (archived AUV runs)

| Layer | Resolvability | Coverage |
|---|---:|---:|
| concept (named elements) | 1.00 | 1.00 |
| notation | 1.00 | 1.00 |
| model | 1.00 | 1.00 |
| behaviour | 1.00 | 0.67 |

Behaviour coverage of 0.67 is 18 of 27 behavioural requirements: the layer links
transition requirements but not the state, variable and constant requirements.
