# RADIANT evaluation — findings (DeepSeek-V4)

_Experiment run started 2026-06-18. AUV case study. Single-agent vs Multi-agent, 10 reps each._

> **September 2026 note.** FDR verdicts for the archived runs were regenerated on a
> licensed FDR 4.2.7: 1 of 3 archived behaviour models verifies; the other two do not
> parse as RoboChart in their archived form, so the 10/10 FDR figure below cannot be
> confirmed against the archived text. See `FDR_VERDICTS.md` in this directory.


## Decision: DeepSeek-only

Per the latest direction, **this experiment is DeepSeek-V4 only.** Opus/GPT-5/Gemini
runs are **not** part of it (Opus hit its Anthropic usage limit mid-run and was
intentionally dropped to control cost). The paper's §4.2 four-model lineup is left
as-is pending a decision to narrow to DeepSeek-only or keep the multi-model framing.

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
| Behaviour | behaviour micro-F1 | 1.00 | 1.00 |
| Behaviour | transition-id F1 | 0.688 | 0.673 |
| Model (EOL) | similarity | not scored\* | not scored\* |

\* The model/EOL metric driver fails to import a missing `emfatic` Python module
(tooling gap — needs that package). The EOL artefacts exist and verify-repair ran
on them (below); only the *similarity metric* couldn't compute.

> **Metric/paper mismatch (action item):** the concept driver computes **set-based
> precision/recall/F1** over `{GID, Concept, Instance, Instance_of}` facts — it does
> NOT use S-BERT/cosine. But paper §4.3 + Table 2 describe the concept metric as
> "S-BERT similarity". Reconcile the paper to the real (set-based) metric before
> resubmission. The same likely applies to the other stages' metric descriptions.

**Headline:** multi wins where it matters — concept F1 +0.055, and most strikingly
**Emfatic syntax validity 50% → 100%** (the Checker/Refactorer catch malformed DSML).
Behaviour is ~perfect for both (a reference model is in place). DSML class/attr F1
are comparable (single's are computed over only its 50% syntactically-valid files).

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
