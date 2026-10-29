# Archived-controller integration repair — 28 October 2026

This is a separate, deterministic repair of the integration of 29 archived
primary-cohort models, plus five pre-existing seeded faults. It uses no LLM calls.
The forty-run experiment and its original native-controller verdicts are unchanged.

Two implementation changes define the repaired variant:

1. The robotic platform provides read-only state interfaces, so the module has
   actual environmental input channels instead of permanently frozen hazard flags.
2. The explicit `atomic` input policy replaces parent receipt followed by child
   delivery with one CSP synchronization shared by both memories and the child.
   A request cannot interleave before the corresponding input reaches its guard.

The second change is a **new untimed CSP integration policy**. Native RoboChart
uses hierarchical propagation by design; its original counterexamples remain valid.
Opening a corrected `.rct` in stock RoboTool without the atomic adapter retains
native propagation semantics. The repaired verification results apply to the
recorded generated CSP policy, not to an unmodified native translation or physical
hardware. The supported integration has one controller, one state machine,
read-only shared inputs and no operations; the audited inputs are four Booleans.

The archived state-machine text is unchanged. The only `.rct` source edit is the
platform provider clause. The independent requirement specification is byte-identical
to `malcom.evaluation/requirement_properties/lre_requirements.csp.tmpl`, SHA-256
`e615b63ef74d64deaee8c4fe42fd0a99f4fe94a9906acfa63e9e67c0c76d1d7f`.
At module scope its update ports are bound to `set_x` rather than controller
`set_EXT_x`; the predicates and permitted behaviour are unchanged.

## Results

- All 29 repaired models pass all ten properties (R1–R4, S1–S3, V1–V3) at
  state-machine, controller and module scope: 870 passing property evaluations.
- Every module can accept `reqMOM`, `reqHCM` and `endTask`; reachability is tested,
  rather than inferred from a deadlock-freedom pass.
- Diagnostic M1 asserts that the module cannot accept `reqMOM`. It is false for
  all repaired models, as intended. A true M1 was evidence of the old frozen-input
  limitation; it is not a required behavioural property that should pass.
- All five seeded faults are detected at all three scopes (15 detections), using
  their pre-existing target-property lists. A faulty guard still fails after repair.
- These are repeated checks of existing models after an implementation change,
  not new generations, independent engineering cases or a new factorial experiment.

## Files and reproduction

`results.json` binds every original and corrected model hash, implementation and
specification hashes, generated-CSP transformation hashes, assertions and verdicts.
`summary.json` records completeness. `models/` contains 34 derived `.rct` artefacts;
`raw/` retains all 102 original framed-JSON FDR outputs. These are generated/model
data, with no pipeline implementation source included.

With the matching private source and licensed FDR 4.2.7:

```sh
python scripts/check_controller_integration.py --data-root /path/to/RADIANT \
  --out-dir /path/to/new-derived-evaluation --timeout 180
```

Original native controller counterexamples remain under
`malcom.evaluation/requirement_properties/results/raw/ctrl/`. The primary cohort's
original pass/fail counts, accepted-run selection, trace scores and frozen impact
benchmark have not been overwritten.

## Coauthor review — 29 October 2026

Haochi Wang reviewed five frozen integration decisions. He agreed with platform
input ownership (I02), the scoped synchronous integration (I03), the evidence
limits (I04) and proposed reporting (I05). He marked the immediate-update
interpretation (I01) **uncertain**: LRE-Beh4 specifies neither input sampling nor
delivery timing, so he could not confirm that it matches the intended controller
design. Immediate propagation remains an explicit assumption of the revised
analysis; the four agreements do not resolve that design-intent question.

`reviews/haochi-2026-10-29.json` preserves his original export byte-for-byte.
`review_status.json` validates the packet hash, revisions and five complete
decisions, and retains the I01 note verbatim. This is completed coauthor review
with an open architectural question, not independent external validation.
No models, input policy, oracle or formal results changed in response.
