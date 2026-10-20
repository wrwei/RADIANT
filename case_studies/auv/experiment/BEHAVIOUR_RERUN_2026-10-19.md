# Behaviour stage re-run under the 2026-10-19 fixes

**Why.** TABLE1_V2.md and sranger/RERUN_2026-10.md recorded two defects in the
behaviour stage: trace-resolution failures drove the repair agent to rewrite models
that had already passed FDR (breaking three of them, plus SRanger run 4, with an `initial X`/`state X`
name clash), and the assembler dropped the state machine's own `var`/`const`
declarations (every SRanger first attempt failed the CSP generator for this; the
first record blamed the LLM). Fixes, commit `b1ca947`..`bf118fe`: repair driven by
structural failures only and stopping when they pass; structure gate rejects a
state/pseudostate name clash; assembler keeps machine declarations and values;
`final` nodes emitted as `final`; template refreshed from FORGE_Dev `2014d0b`.

**Protocol.** `scripts/rerun_behaviour_stage.sh`: ONLY the behaviour stage of the
existing runs was regenerated, from each run's own (unchanged) concept, notation
and construction artefacts. The pre-fix behaviour artefacts and verdicts are under
`run_*/behaviour_v1/`. Same model (DeepSeek-V4), same budget (5 repairs), strict
mode, FDR live. Run 2026-10-19 20:xx–21:29 from the author's licensed shell.

## Table 1, DeepSeek-V4 (`case_studies/auv/output/table1_v2`)

| | Single-pass | Cooperating | v1 cooperating (pre-fix) |
|---|---:|---:|---:|
| Behaviour F1 | 0.98 | **0.99** | 0.89 |
| FDR verified | 10/10 † | **10/10** | 6/10 |
| Repairs used | – | **0 in 10 runs** | 5 in 6 runs |

Per run, cooperating arm: every first-attempt model passed FDR (10/10). In v1,
9/10 first attempts passed (run 005's was rejected by the CSP generator), six runs
were then rewritten because the trace check failed, and three of them (002, 004,
010) went from FDR-verified to FDR-rejected. With the trigger fixed the loop never ran.
Behaviour F1 per run: single 0.97–1.00, multi 0.97–1.00; the v1 mean of 0.89 was
the repair damage, not a generation difference.

† Re-scored 2026-10-20 07:48 with both arms judged on the assembled model (6
assertions: deadlock- and divergence-freedom of machine, controller and module):
single 10/10, cooperating 10/10 (`_scores/deepseek_v4/*/fdr_per_run.json`). The
21:30 scoring had judged the single arm on the bare `stm` (3 assertions).

## SRanger (`case_studies/sranger/output/rerun`)

| Run | v1 (pre-fix) | v2 (re-run) | first attempt | repairs |
|---|---|---|---|---|
| 1 | verified after 1 repair | **verified, 0 repairs** | 6 assertions hold | 0 |
| 2 | verified after 1 repair | **verified, 0 repairs** | 6 assertions hold | 0 |
| 3 | verified after 1 repair | FAILED | 3 inconclusive | 5 (two produced unparseable models) |
| 4 | verified then broken (5 repairs) | **verified after 2 repairs** | 6 inconclusive | 2 |
| 5 | verified after 1 repair | FAILED | 3 inconclusive; trace empty | 5 |

3/5 verified (v1: 4/5), but the two sets are not comparable run-for-run: each v2
run generated a fresh behaviour model, so run 3/5 drawing an "inconclusive" model
is a new draw, not a regression of the v1 model. Structure check passed every
first-attempt model (5/5; v1 flagged the demo's sink `Final`), and with the
assembler fix the CSP generator accepted every first attempt (v1: 0/5).

**New finding: "inconclusive" FDR verdicts.** Three first attempts (3, 4, 5)
returned assertions with no verdict -- FDR neither passed nor failed them. The
pipeline reported only "3 inconclusive", which (a) is not a counterexample and
gives the repair agent nothing to act on, and (b) was treated as a hard failure
that drove repair. Run 3 spent five repairs on it, two producing syntax the
generator rejects. Run 4 "fixed" it on attempt 2 by **retyping every real-valued
state variable as boolean** (`lastLinearVelocity : real` -> `boolean`,
`moveVel`/`turnVel` assignments -> `true`/`false`); that model verifies but no
longer carries the velocities the requirements specify. The inconclusive models
have 3–4 real-typed state variables where the verified ones have 1–2
(`core_real` is instantiated as {-2..2}), which is the working hypothesis; the raw
FDR output was not retained so the cause is not established. Changes made
(commit after this record): the FDR check now names each undecided assertion
with whatever FDR said about it, persists the full parsed result beside the
model (`*.fdr4_result.json`), and an inconclusive-only verdict is reported as
*unverifiable* (fails a strict gate, is recorded as unverified) rather than as a
defect the repair agent should act on. The next run will show the cause.

**Run 5** also had an empty trace from the trace agent (as in v1 Table 1 runs);
under the fixed trigger that no longer drove repair -- the five repairs were all
for the inconclusive FDR verdict.

## What this means for the paper

- Cooperating arm, AUV: 10/10 FDR-verified with zero repairs is the clean Table 1
  cell. The earlier 6/10 was the pipeline's repair loop damaging verified models,
  now fixed; the paper should report the mechanism (RESULTS "what repair does")
  rather than the number alone.
- Decomposition vs single pass: behaviour F1 0.99 vs 0.98, FDR 10/10 vs 10/10. The arms remain indistinguishable on this stage; the cooperating
  arm's distinguishing output is still the trace model (10 vs 0).
- SRanger: 3/5 verified end-to-end from requirements on the second platform, with
  the deadlock of the archived model not recurring, and an open FDR-inconclusive
  class to be diagnosed on the next run.

## Reproduce
```bash
./scripts/rerun_behaviour_stage.sh        # licensed shell; archives behaviour_v1/, re-runs, scores
./scripts/score_table1.sh                 # re-score (single arm now judged on the assembled model)
```
