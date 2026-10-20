# RQ2 re-run under upstream isolation (October 2026)

**Why.** Every RQ2 block run after the May 2026 sweep used a harness whose
downstream stages read the golden `case_studies/auv/fixtures/` artefacts instead of
the run's own earlier outputs (fixed in `d9c740a`; see `MALCOMp/tests/
test_upstream_isolation.py`). Those blocks (`rq2_cascade`, `rq2_matched`, `rq2_cap6`,
`rq2_repro`, `rq2_repro2`, `rq2_10rep`) are **superseded** by this record.

**Protocol.** Full cascade concept -> notation -> model, DeepSeek-V4, repair budget 5
for every arm, EOL execution gate live, 70 runs in four blocks
(`scripts/rerun_rq2_blocks.sh`). Every downstream input of every multi run is recorded
in `upstream_inputs.json`: 120 records, 0 from outside the run directory. 0 harness
errors; 0 unverified gate results.

## Result: construction execution

| block | single | single + repair | multi |
|---|---:|---:|---:|
| `rq2_v2_arms` | 10/10 | 10/10 | 8/10 |
| `rq2_v2_repro_b2` | 10/10 | | 10/10 |
| `rq2_v2_repro_b3` | | | 9/10 |
| `rq2_v2_repro_b4` | | | 9/10 |
| **pooled** | **20/20** | **10/10** | **36/40** |

Concept and notation stages: 10/10 in every arm (`rq2_v2_arms`).

Fisher exact: multi 36/40 vs single 20/20, p = 0.29; multi vs single + repair,
p = 0.57. No arm difference is detectable. Against the superseded multi pool (22/40),
p = 0.0009: the leak depressed the cooperating arm's rate. Against Table 1's 10/10,
36/40 is consistent (p = 0.57), so the earlier "drift" explanation is not needed.

## The single-pass 0/10 was produced by the leak, at least after May

In the superseded `rq2_10rep` and `rq2_cascade` single arms, every failing
construction program sets features its own run's notation lacks, and in 20/20 of those
runs every such feature exists in the fixture notation: the program was written
against the fixture (leaked into the prompt) and executed against the run's own
notation. Of the 20 failures, 19 are `Property 'X' not found` and 1 (`rq2_10rep`) is
`Method 'X' not found for: EmfModel`. In this re-run, the single arm's programs
instantiate only their own notation's classes in 20/20 runs; at feature level, 19/20
set only features their own notation declares (1 run in `rq2_v2_arms` sets one that
it lacks, none of which are fixture features). All 20 execute.

## What this does and does not say about Table 1 (May 2026)

The May sweep ran the same harness code (`cb6e5a48:MALCOMp/run_evaluation.py`), so its
downstream stages were exposed to the same fallback. Its failures are only partly
attributable to it:

* **Claude Sonnet 4.6 single, 0/10:** all 10 failing programs use features missing from
  their own notation; in all 10 the missing features appear in a notation produced by a
  multi run of the same sweep. Consistent with contamination through the shared output
  directory, not proven.
* **DeepSeek-V4 single, 0/10:** all 10 use features missing from their own notation,
  but those features are in neither the fixture nor any multi run's notation. The
  source cannot be established from the archived files; it may be a genuine
  single-pass error.

So Table 1's single-vs-multi contrast for construction execution cannot be treated as
clean, and under clean isolation it does not reproduce: the single arm executes
20/20.

## Reproduce

```bash
./scripts/rerun_rq2_blocks.sh        # ~7 h, 7 parallel lanes
python malcom.evaluation/metrics/rq2_control/cascade.py --root case_studies/auv/output/rq2_v2_arms/deepseek_v4
python malcom.evaluation/metrics/rq2_control/analyse.py --root case_studies/auv/output/rq2_v2_repro_b2/deepseek_v4 --stage model
```
