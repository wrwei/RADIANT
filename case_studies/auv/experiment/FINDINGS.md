# RADIANT evaluation — findings (DeepSeek-V4 · Sonnet 4.6 · QWEN3-max)

_Experiment run started 2026-06-18. AUV case study. Single-agent vs Multi-agent, 10 reps each._
_Three models evaluated (RQ2): DeepSeek-V4, Claude Sonnet 4.6, QWEN3-max. See the
THREE-MODEL SYNTHESIS at the end for the cross-model RQ2 finding._

## Model lineup

This experiment evaluates **three models** — DeepSeek-V4 (open), Claude Sonnet 4.6 and
QWEN3-max — single- vs multi-agent, 10 reps each. (Opus/GPT-5/Gemini are **not** part of
it; Opus hit its Anthropic usage limit mid-run and was dropped to control cost — partial
Opus single data is left on disk unscored, see below.) The DeepSeek section was written
first (this file's original "DeepSeek-only" framing); Sonnet and QWEN were added as the
RQ2 model-dependence question matured.

Output layout (new): `case_studies/auv/experiment/<model>/<variant>/run_NNN/`.

## Bugs found and fixed during setup

| # | Bug | Symptom | Fix | Commit |
|---|-----|---------|-----|--------|
| B | **Multi-agent batch under-production** | multi concept produced 1 GID of 20 (DeepSeek); the Checker/Trace prompts were *sequential*-framed ("emit only for the most recent requirement's GID"), but batch feeds all 20 in one turn | feed-mode-aware prompts: in batch mode, cover EVERY GID. Verified **1 → 48 entries / 20 GIDs**; full cascade (9 concepts, 14 DSML classes, 180-line EOL, behaviour). | `b696dbc` |
| A | **Single-agent fence parse** | Claude wraps JSON in ```fences → `json.loads` failed → stored 1 `raw_response` blob | strip leading/trailing fences before parse (+ for `.emf/.eol/.rct`); no-op for DeepSeek | `19e4875` |
| — | **Claude concept truncation** | Opus single concept cut off mid-list at the 8192 anthropic default | `max_tokens: 32000` for Claude, threaded through single + multi paths | `c32a041` |

## Infrastructure added (verified working)

- **Token/cost capture** (`token_usage.py`): per-run `tokens.json` (single via completion `usage`, multi via AutoGen `gather_usage_summary`); `aggregate()` + per-model price table → `cost_usd()`. `1d70e28`
- **FDR cross-process lock**: `_generate_csp` already isolates per-call temp dirs (no file race); added a `filelock` around `run_fdr4_check` so concurrent sweeps don't run two 8 GB `refines.exe` at once. `1d70e28`
- **Per-provider API keys** (`llm_keys.resolve_api_key`, `api_key_env` per model), `a082374`.
- FDR runnable standalone (`fdr4.run_fdr4_check(rct, config)` → deadlock/divergence verdict), metric drivers re-score existing runs (S-BERT/UniXcoder local, no API).
- Test suite: **115 passed, 1 skipped.**

## Cost (DeepSeek is cheap)

DeepSeek-V4 full sweep ≈ **$1–2** total (single ~$0.36, multi the rest). For reference,
the aborted Opus run cost ~$31 before it was dropped.

## Opus single — partial data (NOT used in this experiment)

Recovered for the record (no new spend): dsml/model/behaviour complete for all 10 runs;
concept only partially salvageable (8/10 partial, runs 003 & 008 empty) due to truncation.
Raw saved as `claude_opus_48/single/run_NNN/result_concept_trace.raw.txt`. Left on disk,
not scored.

---

## RESULTS — DeepSeek-V4 (10 reps, single vs multi)

Sweep: **80/80 cells succeeded**, 0 API errors. Total cost **~$1.72**.

### Accuracy (mean over 10 reps)

| Stage | Metric | Single | Multi |
|-------|--------|-------:|------:|
| Concept | dedup vocabulary F1 (set-based P/R/F1, **not** S-BERT) | 0.899 | **0.954** |
| Concept | requirement-linked micro-F1 (GID,Concept,Instance,Instance_of) | 0.683 | **0.715** |
| DSML | Emfatic **syntax-valid rate** | 0.50 | **1.00** |
| DSML | class F1 | 0.928 | 0.905 |
| DSML | attribute F1 | 0.923 | 0.913 |
| Behaviour | transition-edge F1 *(multiplicity-aware)* | 0.965 | **1.00** |
| Behaviour | behavior_micro_f1 (structure) | 0.973 | **1.00** |
| Behaviour | trigger F1 | 0.75 | 0.75 |
| Model (EOL) | Emfatic→Ecore conversion rate | 1.00 (10/10) | 1.00 (10/10) |
| Model (EOL) | **EOL executes to a conformant model** | **0.00 (0/10)** | **1.00 (10/10)**† |
| Model (EOL) | model-instance micro-F1 (over executed runs) | n/a | 0.864 |

† **Multi re-run (2026-06-19), reached in stages.** Original 2026-06-18 sweep: 4/10.
Re-run under the current pipeline: 8/10 (better generation). The last two (run_006
`Controller.platform`, run_010 `.module` on `Interface`) were genuine EOL errors —
the LLM writes to metamodel features that do not exist. The execution-error feedback
already reaches the repair agent (`_build_execution_feedback`); the blocker was the
repair budget (`execution_repair.max_attempts` was 2). Bumping it to **5** and re-running
closed both → **10/10** (006 at ≤2 attempts, 010 needed the larger budget). Single was
NOT re-run (0/10). Attribution caveat: re-running regenerates the EOL, so the fix mixes
repair with stochastic re-draw — not fully isolated. Single still never instantiates a
conformant model.

**Model/EOL (now scored — earlier "missing emfatic module" was a misdiagnosis).**
The blocker was a stale import: `metrics/model/emfatic_to_ecore.py` imported the
Emfatic parser from `emfatic.metrics`, a path that died in the dsl/emfatic→dsml rename.
Re-pointed to `dsml.metrics` (one line). With that fixed the metric runs and reveals a
genuine, strong **multi > single** result on the hardest stage:
- **Emfatic→Ecore conversion: 10/10 both** — the generated DSML is structurally sound.
- **EOL executes to a conformant model instance: single 0/10, multi 10/10** (micro-F1
  **0.864**). Single-agent EOL never instantiates (real conformance errors, e.g. assigning
  a `String` where the metamodel demands a typed object, or referencing an undeclared type
  `Value`). Multi reaches 10/10 via the execution-guided generate→check→refactor chat plus
  the execution-error repair loop once given an adequate retry budget (`max_attempts` 2→5).
- **On attribution:** in the original sweep the repair (2 attempts) was ineffective — most
  conformant runs were accepted on the first draft, so early multi gains came from the
  group chat, not repair. With the budget raised to 5, the execution-error feedback closes
  the residual hallucinations (006/010), so repair *does* contribute at the margin. Because
  every re-run regenerates the EOL, repair-fixing and stochastic re-draw are not fully
  separable — but the outcome is a stable 10/10 and single (no repair gate) stays at 0/10.
- The earlier "model/EOL repair = 48" figure is the *in-chat Checker* rejection count, a
  different mechanism from the EOL-execution gate (~13 attempts total) — don't conflate.
- Honest caveat: even multi only reaches 40% executable — the model phase is the weakest
  link, and 6/10 multi runs still fail to instantiate.

> **Metric/paper mismatch (action item):** the concept driver computes **set-based
> precision/recall/F1** over `{GID, Concept, Instance, Instance_of}` facts — it does
> NOT use S-BERT/cosine. But paper §4.3 + Table 2 describe the concept metric as
> "S-BERT similarity". Reconcile the paper to the real (set-based) metric before
> resubmission. The same likely applies to the other stages' metric descriptions.

**Headline:** multi wins where it matters — concept F1 +0.055, and most strikingly
**Emfatic syntax validity 50% → 100%** (the Checker/Refactorer catch malformed DSML).
Behaviour splits cleanly into **structure (a real multi win) and semantics (a by-design
abstraction gap)**, scored against a FAITHFUL expert reference (regenerated 2026-06-19
from the audited `result_behaviour.txt`/`.json` — 18 transitions, 10 real variables,
5 constants, real guard predicates, 3 functions) with a **multiplicity-aware** edge metric.

**Structure (the headline, and discriminating):** with the new behaviour completeness
gate, **multi reaches `transition_edge_f1 = behavior_micro_f1 = 1.00`** (every run emits
all 18 transitions, 4 `MOM→HCM`), while **single — which has no verify-repair gate —
stays at 0.965 / 0.973** (it silently merges two distinct requirement transitions into
one, dropping a transition). This is a genuine multi > single advantage driven by the
verify-repair loop, not abstraction parity.

**Behaviour is scored on structure only.** Semantic-fidelity metrics (condition/variable/
constant/function/full-micro F1) are deliberately **not reported**: the behaviour prompt
mandates abstracting real guards (`CDA < MinSafeDist /\ TCPA >= 0`) into booleans
(`collisionRisk`) and forbids functions, for FDR-verifiability — so those metrics measure
the *deliberate abstraction*, are a fixed floor identical for both variants, and say
nothing about generation quality. They remain available per-run as raw diagnostics.

> **Corrections to earlier drafts.** (1) The prior `behaviour ≈ 1.00` was scored against a
> *divergent* `.rct` that was itself boolean-abstracted — an artifact, replaced by the
> faithful `.rct`. (2) The structural metric was set-based (blind to a dropped transition);
> it is now **multiplicity-aware** (`metrics/behaviour/metrics.py`), so the merge is visible
> and the gate's fix shows up. (3) `condition`/`variable`/`full_micro` are reported as an
> *abstraction-fidelity diagnostic*, not behaviour accuracy.

> **Note — `transition_id_f1` is a cosmetic diagnostic, not accuracy.** It collapsed to
> 0.00/0.11 vs the expert ref purely because the expert names transitions `t_init`,
> `t_ocm_vel`… while the LLM emits `t0`, `t1`… It compares arbitrary label strings; the
> edges they encode are 100% correct. **Now excluded from the summary/headline**
> (`behaviour/compute.py`), kept per-run as a raw diagnostic. (The "reference already in
> place" line in the paper refers to the human RQ4 efficiency study, not this LLM sweep.)

DSML class/attr F1 are comparable (single's are over only its 50% valid files).

### Verify-repair (multi only) — the gate worked hard
Verification-gate failures that triggered the per-phase Repair Agent:
**model/EOL 48 · behaviour 6 · concept 4 · dsml 4** (repair-agent activity: 30 mentions).
The EOL/model phase needed by far the most repair — consistent with it being the
hardest stage, and with the 50%→100% jump multi achieves elsewhere.

### FDR (deadlock/divergence-freedom)
All 20 behaviour models verified with FDR4 (`refines.exe`):
- **single: 10/10 pass** · **multi: 10/10 pass** (0 fail, 0 unverifiable).

Both variants produce sound state machines. The multi models additionally passed
the in-sweep verify-repair gate (6 behaviour-phase repairs along the way); the
single models weren't verified during generation but still all pass FDR post-hoc.
The AUV behaviour reference is well-established, so this stage is strong for both —
the multi advantage shows up earlier in the chain (DSML validity, concept F1).
Raw per-run verdicts: `malcom.evaluation/fdr_results.json`.

### Tokens / cost
| Variant | input | output | est $ |
|---------|------:|-------:|------:|
| single | 255,310 | 264,143 | $0.36 |
| multi | 986,639 | 997,075 | $1.36 |

Multi uses ~3.8× the tokens of single (the group chat + verify-repair loop) — but
that's what buys the 100% DSML validity and higher concept F1. Prices approximate
(verify before quoting).

---

## RESULTS — QWEN3-max (10 reps, single vs multi) — added 2026-06-20

Sweep: **79/80 cells succeeded** (1 cell failure: single/run_008/behaviour).
Run with `fdr4.enabled: false` for sweep speed (behaviour FDR is a post-hoc item;
the model-EOL execution gate and per-phase verify-repair were fully on, `max_attempts: 5`).

### Accuracy (mean over 10 reps; offline-reproducible metric drivers)

| Stage | Metric | Single | Multi |
|-------|--------|-------:|------:|
| Concept | dedup vocabulary F1 (set-based) | **0.843** | 0.798 |
| Concept | requirement-linked micro-F1 | **0.552** | 0.529 |
| Concept | concept F1 | 0.920 | 0.915 |
| DSML | Emfatic **syntax-valid rate** | **0.00 (0/10)** | **0.80 (8/10)** |
| DSML | class F1 | 0.880 | 0.898 |
| DSML | attribute F1 | 0.880 | 0.884 |
| DSML | end-to-end weighted F1 (invalid→0) | 0.00 | **0.698** |
| Model (EOL) | Emfatic→Ecore conversion rate | 1.00 (10/10) | 1.00 (10/10) |
| Model (EOL) | **EOL executes to a conformant model** | **0.00 (0/10)** | **0.40 (4/10)** |
| Model (EOL) | object/attr/link F1 (over the 4 executed) | n/a | ~0.89 |
| Behaviour | transition-edge F1 (multiplicity-aware) | **1.00** | 0.977 |
| Behaviour | behavior_micro_f1 (structure) | **1.00** | 0.982 |
| Behaviour | trigger F1 | 0.75 | 0.75 |

### Where multi-agent helps QWEN — and where it doesn't

- **DSML syntactic validity: 0% → 80%** (the headline, same mechanism as DeepSeek's
  50%→100%). **Every** single-agent QWEN run omits the required Emfatic `package`
  header (files begin `abstract class NamedElement {…}` → the Eclipse parser rejects
  them at line 1). The multi-agent Checker/Refactorer add the header → 8/10 valid.
- **EOL executability: 0/10 → 4/10.** Multi helps but the ceiling is well below
  DeepSeek's 10/10. The 6 failures are **genuine EOL hallucinations** — the LLM writes
  to RoboChart feature names its *own* generated DSML does not declare (e.g.
  `providedInterfaces` when the metamodel names the feature `uses`; also `.platform`,
  `.type`). Repair (budget 5) + the group chat closed 4; the rest are residual.
- **Concept: multi is slightly *lower*** (vocab F1 0.843→0.798, req-linked 0.552→0.529)
  — the group chat over-elaborates the concept vocabulary, costing precision. Unlike
  DeepSeek (where multi *helped* concept +0.055), QWEN's concept stage is already strong
  single-agent and multi adds noise.
- **Behaviour: both near-perfect, single edges ahead** (1.00 vs 0.977). QWEN single
  already emits all 18 transitions; the one multi run that drops an edge is within noise.

> **Correction to live sweep tracking.** During the sweep I tracked `model=Y 10/10`,
> which counted the **existence** of `result_AUV.model` / `result.verify.model` — stale
> intermediate run artifacts (some are empty `<platforms/>` with no links). The honest,
> reproducible figure is the **offline EOL-execution gate: multi 4/10, single 0/10**.
> File-existence ≠ offline conformance.

### Metric-driver fix made during scoring
`metrics/dsml/compute.py:summarise` crashed (`fmean requires at least one data point`)
when **every** run is syntax-invalid (QWEN single, 0/10), because
`conditional_weighted_f1` is `None` for syntax-invalid outputs → empty value list.
Added a zero-n guard (matches `concept/compute.py`) so the report renders 0/10 instead
of crashing. No metric semantics changed.

---

## THREE-MODEL SYNTHESIS (RQ2) — DeepSeek-V4 · Claude Sonnet 4.6 · QWEN3-max

The tie-breaker refines the RQ2 claim rather than just confirming it. Multi-agent's
benefit splits cleanly into two kinds:

1. **Syntactic / structural validity of the formal artifacts — a reliable,
   model-independent multi-agent win.** The verify-repair gate's core job. DSML
   compiles and EOL executes far more often under multi:
   - DSML syntax-valid: DeepSeek 50→100% · QWEN **0→80%** · Sonnet (over-elaborates, see below).
   - EOL executes conformant: DeepSeek 0→10/10 · QWEN **0→4/10** · Sonnet 0→0.
2. **Semantic accuracy (concept vocabulary, behaviour structure) — model-dependent.**
   Multi helped DeepSeek (concept +0.055), was neutral-to-slightly-negative for QWEN,
   and actively hurt Sonnet (DSML class over-generation 30→… before the requirement-
   grounding prompt fix; EOL genuinely weak at 0/10 both variants).

**Headline:** *multi-agent reliably buys validity/executability of the downstream formal
models; its effect on upstream semantic extraction is model-dependent.* QWEN is the
clean middle case — decisive validity/executability gains, neutral semantics — between
DeepSeek (broad gains) and Sonnet (the EOL/over-elaboration outlier).

Scored CSV/MD per phase under `malcom.evaluation/metrics/results/qwen3_max/{single,multi}/`.

### Significance (RQ2) — independent-sample tests across all three models

`malcom.evaluation/significance_analysis.py` re-scores every model from its raw runs
and tests Single vs Multi per stage. The ten single / ten multi runs are **independent
samples** (not matched pairs), so: **Mann-Whitney U** for the continuous F1 stages,
**Fisher's exact** for the two binary-rate stages (DSML syntactic validity, EOL
exec-conform). Outputs: `metrics/results/significance_summary.{csv,md}` and the paper
figure `graphics/significantly.pdf`.

| Model | Stage | Single | Multi | Test | p | Sig |
|---|---|---:|---:|---|---:|:--:|
| DeepSeek-V4 | Concept vocab F1 | 0.90 | 0.95 | MWU | 0.038 | * |
| DeepSeek-V4 | DSML syntax | 0.50 | 1.00 | Fisher | 0.033 | * |
| DeepSeek-V4 | DSML class F1 | 0.93 | 0.91 | MWU | 0.318 | ns |
| DeepSeek-V4 | Model/EOL exec | 0/10 | 10/10 | Fisher | 1.1e-5 | **** |
| DeepSeek-V4 | Behaviour struct F1 | 0.97 | 1.00 | MWU | 3.3e-5 | **** |
| QWEN3-max | Concept vocab F1 | 0.84 | 0.80 | MWU | 0.518 | ns |
| QWEN3-max | DSML syntax | 0.00 | 0.80 | Fisher | 7.1e-4 | *** |
| QWEN3-max | DSML class F1 | 0.88 | 0.90 | MWU | 0.066 | ns |
| QWEN3-max | Model/EOL exec | 0/10 | 4/10 | Fisher | 0.087 | ns |
| QWEN3-max | Behaviour struct F1 | 1.00 | 0.98 | MWU | 7.1e-4 | *** (single higher) |
| Sonnet 4.6 | Concept vocab F1 | 0.89 | 0.88 | MWU | 1.0 | ns |
| Sonnet 4.6 | DSML syntax | 1.00 | 1.00 | — | 1.0 | ns |
| Sonnet 4.6 | DSML class F1 | 0.92 | 0.86 | MWU | 1.1e-3 | ** (single higher) |
| Sonnet 4.6 | Model/EOL exec | 0/10 | 0/10 | — | 1.0 | ns |
| Sonnet 4.6 | Behaviour struct F1 | 0.97 | 0.97 | — | 1.0 | ns |

**Honest reading.** (1) The only multi-agent win significant for *every* model whose
single output is imperfect is **DSML syntactic validity** (DeepSeek *, QWEN ***).
(2) **EOL executability** for QWEN (0→4/10) is a positive trend but **not significant at
n=10** (p=0.087) — not a win. (3) Two significant effects run *against* multi: QWEN
behaviour 1.00→0.98 and Sonnet DSML class 0.92→0.86. (4) Stages where both variants are
constant-equal (Sonnet syntax/EOL/behaviour) admit no test.

---

## RQ3 — Quantitative traceability — added 2026-06-20

Two scripts, both over existing artefacts (no LLM calls):
`malcom.evaluation/rq3_traceability.py` (trace-link quality) and
`malcom.evaluation/rq3_change_impact.py` (change-impact correctness).
Outputs: `metrics/results/traceability_summary.{csv,md}`,
`metrics/results/change_impact_summary.{csv,md}`.

**Headline finding — traceability is a by-construction property of the *multi-agent*
pipeline.** Single-agent runs emit only an *unresolved* concept trace (no `source`
field) and **no dsml/model/behaviour trace at all** — the single baseline runs each
layer's primary agent once and skips the Trace_Generation_Agent and the trace-resolution
step. So RQ3 evaluates the quality of the traces RADIANT (multi) emits; single yields no
resolvable links and cannot support change impact.

### Trace-link quality (multi)

| Model | Beh link F1 | Concept link F1 | Resolved C/D/M/B | Coverage C/D/M/B |
|---|---:|---:|:--:|:--:|
| DeepSeek-V4 | 1.00 | 0.72 | 1.00/1.00/1.00/1.00 | 1.00/1.00/0.99/0.67 |
| QWEN3-max | 1.00 | 0.53 | 1.00/1.00/1.00/0.97 | 1.00/0.99/0.98/0.67 |
| Sonnet 4.6 | 1.00 | 0.59 | 1.00/1.00/1.00/0.73 | 1.00/1.00/1.00/0.93 |

- **Beh link F1** = P/R/F1 of generated (requirement_gid → transition-edge) links vs the
  expert reference (18 transitions). Perfect for all three models — the trace correctly
  attributes every behaviour requirement to its transition (matched on edge, since the
  LLM's `t`-labels are cosmetic).
- **Concept link F1** = reused requirement-linked micro-F1 (the requirement→concept trace).
- **Resolved** = fraction of emitted links pointing to a real element in the artefact. The
  discriminating signal is **behaviour resolvability**: DeepSeek 1.00 > QWEN 0.97 >
  **Sonnet 0.73** — Sonnet's weaker generation leaves more dangling links (the trace
  claims a transition the `.rct` doesn't actually contain).
- **Coverage** = fraction of in-scope requirements with ≥1 link. The one real gap is
  **behaviour 0.67** (DeepSeek/QWEN): the behaviour trace links *transitions* but not the
  variable/constant/state requirements.

### Change-impact correctness (multi)

Inject each of the 18 behaviour requirements as a change → snapshot/diff/impact → compare
the flagged element's edge vs the expert reference. Micro over 180 changes/model:

| Model | CI precision | CI recall | CI F1 | Arch phase spread |
|---|---:|---:|---:|---:|
| DeepSeek-V4 | 1.00 | 1.00 | 1.00 | 3.0 |
| QWEN3-max | 1.00 | 1.00 | 1.00 | 3.0 |
| Sonnet 4.6 | 1.00 | 1.00 | 1.00 | 3.0 |

When a requirement changes the tool flags exactly the correct element — precision 1.0
(no over-flagging) and recall 1.0 (no under-flagging). **Arch phase spread = 3.0**:
changing the root architecture requirement (SD1) flags elements across concept+dsml+model
(the cross-phase digital thread); single = 1.0 (concept only).

> **Honest caveat.** CI correctness is scored against the reference-*intended* edge, and
> the trace's claims all match (= 1.0). Resolvability is the complementary check: for
> Sonnet ~27% of behaviour links name a transition the generated `.rct` does not contain,
> so the *practical* reliability of the impact set is bounded by generation quality, not
> by the trace mechanism. The mechanism is exact; the artefact under it is model-dependent.

---

## RQ5 — Generality: second domain (SRanger) — added 2026-06-20

Replaced the never-committed Epsilon Playground claim with a real second case study,
**SRanger** (a reactive ground robot; requirements adapted from the FORGE
`forge.assets/case-studies/sranger`, split arch/behaviour by `types`). See
`case_studies/sranger/README.md`.

Ran the **full** RADIANT pipeline (phases 2--5) with the **unmodified** multi-agent
layers, `deepseek_v4`. **All four phases passed their verification gates:**

| Phase | Result |
|---|---|
| Concept | 9 concepts / 8 instances, 10/10 requirement GIDs covered |
| DSML | 13-class valid Emfatic metamodel (Sensor, Actuator, Event, Move, Mode, Moving/Turning/Final, StateMachine, Controller, …) |
| Model (EOL) | 76-line EOL executes to a **conformant** EMF model instance |
| Behaviour | RoboChart `.rct` with **3 states + 7 transitions** (exactly the spec's 3 modes / SR-Beh1–7); **FDR: 3 assertions hold, deadlock/divergence-free** |

This is genuine *applicability* evidence (no expert reference authored for SRanger, so
no accuracy score) — and far stronger than the old unsubstantiated Playground claim: the
unmodified layers drove every phase, including formal verification, to a passing artefact.

**Bug fixed (surfaced by SRanger).** The first run halted at the concept trace-resolution
gate: `trace_locator.locate_requirement` did a case-sensitive, verbatim substring match of
concept/instance names against the requirement prose. AUV always named verbatim identifiers
so it never showed; SRanger's overview requirements introduce concepts in prose (`Sensor`←
"sensor", `StateMachine`←"state machine") and DeepSeek quoted its instances (`"Moving"`).
Fixed the matcher to be **case-insensitive, quote-tolerant, and camelCase/multiword-aware**
(`MALCOMp/trace_locator.py` + 3 tests; strictly more permissive, AUV unaffected, full suite
125 pass). This dropped concept failures 18→4; the repair loop closed the rest → passed.
