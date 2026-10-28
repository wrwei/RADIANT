# RADIANT — replication data package

Data supporting *Generating engineering model chains from requirements with language model agents
and formal checks* (Communications Engineering submission).
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
| `case_studies/auv/experiment/<model>/<arm>/run_NNN/` | June 2026 accuracy sweep behind Supplementary Table S3 (three models × single/multi × 10) |
| `case_studies/auv/experiment/*.md` | Experiment records: `FINDINGS.md` (June sweep), `RQ2_V2.md`, `TABLE1_V2.md`, `BEHAVIOUR_RERUN_2026-10-19.md` (October, corrected harness), `FDR_VERDICTS.md`, and the superseded September records |
| `case_studies/auv/output/table1_v2/` | Earlier corrected-harness block in Supplementary Table S5 (DeepSeek-V4, single/multi × 10); `table1_v2.csv` is the scored table; `_scores/.../fdr_per_run.json` the per-run FDR verdicts; `run_*/behaviour_v1/` the pre-fix behaviour stage |
| `case_studies/auv/output/rq2_v2_*/` | Corrected-harness comparison blocks (cooperating 40, single-pass 20, repair-equipped 10) |
| `case_studies/sranger/` | Second platform: requirements, system description, archived demo run, and `output/rerun/` (five behaviour-stage October regenerations from unchanged upstream artefacts) with `RERUN_2026-10.md` |
| `reference_models/`, `malcom.evaluation/reference_models/` | Hand-authored expert reference models the accuracy metrics score against |
| `malcom.evaluation/fdr_results.json` | FDR verdicts for the archived AUV behaviour models and the archived SRanger demo |
| `effort_study/` | Effort study: per-participant times and accuracy, background survey (Supplementary Tables S1, S2) |

## Per-run files

A `run_NNN/` directory contains the artefacts produced before that run stopped, including (`result_concept_model.json`,
`result_dsml.emf`, `result_model.eol`, `result_behaviour_model.rct`, and for gated runs
`result_behaviour_complete.rct`), the trace models (`result_*_trace.json`), `tokens.json`,
`run_manifest.json` (model, arm, instrument commit), `upstream_inputs.json` (provenance of
every upstream artefact the stage read — October blocks), `verification_log.json` (every
gate verdict per attempt — October blocks), `stage_status.json` (the pipeline's own accept/reject verdict per phase — 2x2 study) and `attempts/` (the artefact as judged at each
attempt). Every configuration emits concept traces; notation, construction and behaviour traces were requested only in the cooperating configurations. Files for unrun phases are absent.

## Reported item → data

| Paper item | Data |
|---|---|
| Main Table 1 (primary 2x2 comparison) | `case_studies/auv/output/factorial_v2/`; `factorial_summary.csv`; repair configurations' construction/behaviour stages were regenerated with the completed prompt from unchanged concept/notation outputs |
| Main Table 2 (concept traces) | Same forty concept outputs; `submission_records/concept_trace_audit/analysis.json` records per-run scores, source/scorer hashes and separate historical analyses |
| Main Table 3 and abstract (324 probes) | `submission_records/validated_impact/change_impact_validated.json`; eighteen accepted cooperating runs, validated direct seeds TP 280 / FP 0 / FN 44; original expert reference in `malcom.evaluation/reference_models/auv_independent_expert_20260612/result_behaviour.txt` |
| Main requirement verification (29 state machines, 28 completed controller verdicts, one controller timeout) | Filter `block=factorial_v2` in `malcom.evaluation/requirement_properties/results/*per_assertion*.csv`; ten state-machine properties plus a separate module-level M1 check |
| Primary cohort summary and provenance | `submission_records/primary_cohort/summary.json`; source hashes, counts, concept scores, timeout record and staged-rerun qualification |
| Supplementary Table S3 and Figure S1 (June accuracy) | `case_studies/auv/experiment/<model>/<arm>/run_*/`; `case_studies/auv/experiment/FINDINGS.md`; historical upstream-input isolation defect |
| Supplementary Table S4 (June resolvability/coverage) | `case_studies/auv/experiment/<model>/multi/run_*/`; ten June runs per provider |
| Supplementary Table S5 (earlier corrected block) | `case_studies/auv/output/table1_v2/table1_v2.csv`; `case_studies/auv/experiment/TABLE1_V2.md`, `BEHAVIOUR_RERUN_2026-10-19.md` |
| Supplementary Table S6 (supporting change-impact blocks) | `malcom.evaluation/change_impact/`: June 540 injections; earlier corrected 180; primary factorial 324; secondary corrected aggregate 504 |
| Supplementary Figure S2 (archived architectural change example) | June trace models under `case_studies/auv/experiment/`; its 540-injection annotation is historical |
| Supplementary Table S7 (verification across cohorts) | `malcom.evaluation/requirement_properties/`: specification, five mutants, per-assertion verdicts and counterexample; 69 state machines / 68 completed controller verdicts / one timeout across cohorts |
| Supplementary Table S8 (impact-scoring audit) | `submission_records/validated_impact/change_impact_validated.json` compares historical endpoint strings, actual named targets and strict validation; the historical CSV in `malcom.evaluation/change_impact/factorial_v2/` remains unchanged |
| Supplementary Table S9 (impact pilot) | `submission_records/impact_benchmark/`; twelve concrete edits on one archived run; coauthor Haochi Wang accepted all expected sets without amendments |
| Acceptance-rule history and earlier comparisons | `case_studies/auv/output/halt_rule_rescore.json`; `case_studies/auv/experiment/HALT_RULE_2026-10-21.md`, `RQ2_V2.md`; earlier comparison blocks are supporting/superseded |
| June submission recovery | `submission_records/june_2026/`: source, figures and sixty-run inventory at paper commit `351213e`; Qwen single run 008 lacks a behaviour output |
| Separate second-platform study | `case_studies/sranger/output/runs/sranger_deepseek_demo/`; `output/rerun/`; `case_studies/sranger/RERUN_2026-10.md`; five behaviour-stage regenerations |
| Separate effort study; Supplementary Tables S1/S2 | `effort_study/` |
| Supplementary Note 2 (historical costs) | Per-run `tokens.json`; primary factorial token means are main Table 1 |

The main quantitative protocol is the existing forty-run DeepSeek factorial cohort.
Older corrected and June cohorts are not pooled into its primary estimates.
The new JSON records are deterministic reanalyses of stored data; no model calls
were made. The upstream audit verifies all 187 matching logical-run inputs; seventy
recorded paths retain first-pass directory names with byte-identical primary-cohort copies. Original raw artefacts and recorded experimental outcomes are unchanged.

## Validated impact audit

The separate records in `submission_records/validated_impact/` reanalyse the same
eighteen accepted cooperating runs and 324 requirement-text probes. The historical
scorer trusted endpoint strings in trace JSON (TP/FP/FN 302/0/22). Reading the actual
named transitions gives 280/4/44; rejecting inconsistent endpoint claims gives
280/0/44 (precision 1.000, recall 0.864, F1 0.927). Eighteen previously credited
links name nonexistent transitions and four give inconsistent endpoints. The
original cohort summary and historical scores remain unchanged; the strict audit
supersedes them when assessing actual trace targets. It does not establish correct
guards, triggers or actions, and does not fill missing links from the reference.

`dependency_closure_audit.json` records structural reach and diagnostics for these
runs under the revised implementation, with input and implementation hashes.
The new analyser validates direct targets, freezes the graph in a baseline and
computes exact reachability with explanatory paths. Its bounded extractors cover
explicit dependencies in concept JSON, Emfatic, static EOL construction declarations
and RoboChart. Exactness is relative to that graph; semantic completeness and
empirical closure accuracy are not established by this audit. No model calls were
made. The source implementation remains in the private code repository.

The per-stage evaluation drivers that compute each metric from these files are part of the
source code and are available on request with it. Every metric is a deterministic function
of the files above.

## Impact pilot and coauthor review

`submission_records/impact_benchmark/` contains frozen draft labels, their hash,
a reviewer worksheet without predictions, and results for twelve local edits on
`factorial_v2/deepseek_v4/multi/run_001`. Expected review sets were drafted from
source by the implementation assistant. Coauthor Haochi Wang accepted all twelve
affected/unaffected sets on 28 October 2026, with no amendments or notes. His
original export is preserved byte-for-byte in
`submission_records/impact_benchmark/reviews/haochi-2026-10-28.json`;
`review_status.json` records the matching benchmark hash and complete case identities.
The form's exported status remains `draft_review_record`; all twelve explicit
case decisions are `accept`. The original specification, worksheet and results
retain their pre-review metadata, and no labels or scores changed. This is
coauthor review, not independent external ground truth. Archived requirement links recover 27 of 64
case-element targets with 18 extra candidates; supplying the intended element
seeds recovers 64 with 11 extra candidates. The latter bypasses trace discovery
and is not end-to-end accuracy. All scores are limited to the case's specified
file; repeated cases share elements. Inputs and historical results are unchanged.

## Legacy nine-run traceability reports

`malcom.evaluation/metrics/results/traceability/` preserves the existing textual
resolvability and coverage analysis of nine May/June archived runs. It uses the
historical permissive locators and is separate from the primary forty-run
factorial cohort and the strict target-validation audit. The original CSVs and
report are retained without changing their measurements.
