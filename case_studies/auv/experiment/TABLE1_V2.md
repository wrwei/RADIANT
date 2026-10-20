# Table 1 rebuilt under upstream isolation: DeepSeek-V4 (October 2026)

> **Behaviour stage superseded (2026-10-19) — see `BEHAVIOUR_RERUN_2026-10-19.md`.** The FDR and behaviour-F1 cells below were produced before the repair-trigger and assembler fixes; the behaviour stage was re-run under them (cooperating arm: 10/10 FDR-verified, 0 repairs). The other columns are unchanged.

**Why.** The June 2026 sweep behind Table 1 ran a harness in which a downstream
stage could read reference artefacts instead of the run's own earlier outputs
(fixed in `d9c740a`; see `RQ2_V2.md`). This block re-runs the DeepSeek-V4 row with
the corrected harness. QWEN3-max and Claude Sonnet 4.6 were not re-run.

**Protocol.** AUV, all four stages (concept -> notation -> construction -> behaviour),
single-pass and cooperating configurations, 10 runs each, repair budget 5, EOL execution
gate and FDR live, strict mode. `scripts/rebuild_table1.sh`; scored by
`scripts/score_table1.sh`, which re-runs FDR on every behaviour model of both arms.
Provenance: 30/30 downstream input records from the run's own directory. 0 harness
errors, 0 unverified checks.

| | single-pass | cooperating | June single / multi |
|---|---:|---:|---|
| Concept F1 | 0.97 | 0.97 | 0.90 / 0.95 |
| Notation valid (strict Emfatic parser) | 0/10 | 10/10 | 0.50 / 1.00 |
| Notation converts (pipeline gate; accepts a missing `package` header) | 0/10 | 10/10 | |
| Notation-element F1 | 0.90 | 0.86 | 0.93 / 0.91 |
| Construction executes | **10/10** | 10/10 | **0/10** / 10/10 |
| Behaviour F1 (`detail_micro_f1`) | 0.98 | 0.89 | 0.97 / 1.00 |
| FDR verified (deadlock- and divergence-free) | **10/10** | **6/10** | — / 10/10 |
| Trace links emitted | 0 | 10 | |
| Tokens, all stages | 798,134 | 2,791,948 | |

## Reading

1. **The single-pass construction 0/10 does not reproduce** (10/10 here; 20/20 in
   `RQ2_V2.md`). Both arms execute.
2. **Notation validity is the one gap, and it is one defect.** Every single-pass
   notation omits the mandatory `package` declaration; the gates fix it.
3. **The cooperating arm is worse on the behaviour stage, and the cause is visible
   in the attempt logs.** In 6 of 10 cooperating runs the trace agent emitted an empty
   behaviour trace (`{}` entries). That fails `trace_resolved`, which in strict mode
   drives the repair loop. The repair agent is handed a failure it cannot fix by editing
   the state machine, and in 3 of those 6 runs its edits broke a model that had **passed
   FDR as first generated** (duplicate variable declarations after repair in runs 002,
   004, 010; a RoboChart syntax error in run 005, whose first attempt also failed).
   Runs 007 and 009 kept passing FDR through all six attempts. The four runs whose
   trace resolved first time passed FDR in one attempt.

   The single-pass arm has no trace agent and no repair loop: its behaviour models
   pass FDR 10/10 as generated.

   So on this case study, with this model, the behaviour-stage repair loop has
   negative value when triggered by a traceability failure. The structural checks
   (parse, sink states, FDR) should drive repair; a trace failure should mark the
   run's traceability as incomplete, not rewrite a verified model.
4. **Cost.** The cooperating configuration used 3.5x the tokens of single-pass.

## Reproduce

```bash
MODELS=deepseek_v4 ./scripts/rebuild_table1.sh          # generation stages, ~3.5 h
RESUME=1 STAGES=behaviour MODELS=deepseek_v4 ./scripts/rebuild_table1.sh  # licensed shell, ~1.5 h
./scripts/score_table1.sh
```
Per-attempt verdicts and artefacts: `table1_v2/deepseek_v4/multi/run_*/verification_log.json`,
`attempts/behaviour_model_creation/`.
