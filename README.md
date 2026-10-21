# RADIANT — replication data package

Data supporting *Model-driven discipline for multi-agent language models: verified,
traceable system models from requirements* (Communications Engineering submission).
This repository holds **data only**: inputs, every generated artefact, trace models,
verification verdicts, and experiment records. The RADIANT source code (pipeline,
model-management tooling, prompts, evaluation drivers, hand-written model transformations) is **not publicly released**;
it is available from the corresponding author upon reasonable request, and to editors
and referees for peer review.

> History note. Until 2026-10-20 this repository also carried the source code. On
> withdrawing the code from public release the history was replaced by this single
> data-only commit. Every data file carried over is byte-identical to the previously
> published copy, with four exceptions: the experiment records `RQ2_CASCADE.md`,
> `RQ2_CONTROL.md`, `RQ2_REPRODUCTION.md` and `TABLE1_DISCREPANCY.md` are the current
> versions, each carrying a "superseded" note at the top that points to `RQ2_V2.md`
> (their measurements are unchanged). The October 2026 blocks listed below are new.

## Layout

| Path | Contents |
|---|---|
| `case_studies/auv/requirements/` | The AUV requirement model (architecture + behaviour JSON), the single hand-authored input |
| `case_studies/auv/system_description/` | Natural-language system description |
| `case_studies/auv/model/`, `case_studies/auv/metamodel/` | The authors' hand-authored AUV Eclipse project (domain metamodel in Emfatic/Ecore, requirement and system models, Sirius representation) used as the baseline the generated artefacts are compared with in the running example |
| `case_studies/auv/fixtures/` | The reference pipeline run used as the running example (concept model, Emfatic notation, EOL construction program, trace models) |
| `case_studies/auv/output/runs/` | Archived May/June 2026 pipeline runs, incl. the three behaviour models whose FDR verdicts are in `malcom.evaluation/fdr_results.json` |
| `case_studies/auv/experiment/<model>/<arm>/run_NNN/` | June 2026 accuracy sweep behind Table 1 (three models × single/multi × 10) |
| `case_studies/auv/experiment/*.md` | Experiment records: `FINDINGS.md` (June sweep), `RQ2_V2.md`, `TABLE1_V2.md`, `BEHAVIOUR_RERUN_2026-10-19.md` (October, corrected harness), `FDR_VERDICTS.md`, and the superseded September records |
| `case_studies/auv/output/table1_v2/` | Table 1 corrected-harness rows (DeepSeek-V4, single/multi × 10, all four phases); `table1_v2.csv` is the scored table; `_scores/.../fdr_per_run.json` the per-run FDR verdicts; `run_*/behaviour_v1/` the pre-fix behaviour stage |
| `case_studies/auv/output/rq2_v2_*/` | Corrected-harness comparison blocks (cooperating 40, single-pass 20, repair-equipped 10) |
| `case_studies/sranger/` | Second platform: requirements, system description, archived demo run, and `output/rerun/` (five end-to-end October runs) with `RERUN_2026-10.md` |
| `reference_models/`, `malcom.evaluation/reference_models/` | Hand-authored expert reference models the accuracy metrics score against |
| `malcom.evaluation/fdr_results.json` | FDR verdicts for the archived AUV behaviour models and the archived SRanger demo |
| `effort_study/` | Effort study: per-participant times and accuracy, background survey (Supplementary Tables S1, S2) |

## Per-run files

Each `run_NNN/` directory contains the generated artefacts (`result_concept_model.json`,
`result_dsml.emf`, `result_model.eol`, `result_behaviour_model.rct`, and for gated runs
`result_behaviour_complete.rct`), the trace models (`result_*_trace.json`), `tokens.json`,
`run_manifest.json` (model, arm, instrument commit), `upstream_inputs.json` (provenance of
every upstream artefact the stage read — October blocks), `verification_log.json` (every
gate verdict per attempt — October blocks) and `attempts/` (the artefact as judged at each
attempt).

## Reported item → data

| Paper item | Data |
|---|---|
| Table 1, June rows | `case_studies/auv/experiment/<model>/<arm>/run_*/` ; summary in `experiment/FINDINGS.md` |
| Table 1, † rows (DeepSeek-V4, corrected harness) | `case_studies/auv/output/table1_v2/table1_v2.csv` ; `experiment/TABLE1_V2.md`, `BEHAVIOUR_RERUN_2026-10-19.md` |
| Table 2 (resolvability, coverage) | trace models in `case_studies/auv/output/runs/web_20260530_*/` (three archived runs) |
| Results: controlled comparison (40/20/10) | `case_studies/auv/output/rq2_v2_arms/`, `rq2_v2_repro_b*/` ; `experiment/RQ2_V2.md` |
| Acceptance rule (rejected artefact ends the run); single-pass 1/20 | `case_studies/auv/output/halt_rule_rescore.json` ; `experiment/HALT_RULE_2026-10-21.md` |
| Results: FDR verification | `verification_log.json` per run; `table1_v2/_scores/*/fdr_per_run.json`; `malcom.evaluation/fdr_results.json` |
| Results: second platform | `case_studies/sranger/output/runs/sranger_deepseek_demo/` (archived, deadlock) ; `output/rerun/` (five re-runs) ; `RERUN_2026-10.md` |
| Results: effort study; Supp. Tables S1–S2 | `effort_study/` |
| Supp. Note 2 (tokens, cost) | `tokens.json` in every run directory |

The per-stage evaluation drivers that compute each metric from these files are part of the
source code and are available on request with it. Every metric is a deterministic function
of the files above.
