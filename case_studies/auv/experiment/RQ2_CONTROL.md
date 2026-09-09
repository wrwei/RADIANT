# RQ2 control experiment — separating iterative repair from role decomposition

**Audit item A7.** The paper's RQ2 compares the full cooperating pipeline against a
single-pass baseline that has neither checking nor repair, so it measures role
decomposition and iterative repair *together*. This is the missing arm.

**Design.** Model: DeepSeek-V4 (`deepseek-v4-pro`). Stage: `model` (the EOL construction
program) — the phase carrying the paper's headline validity jump and 48 of the 62
recorded gate-triggered repairs. n=10 per arm, 30 runs. All arms seeded with an
**identical** concept model and metamodel, so the only difference is generation strategy.
The structural gate (`eol_executes`: does the program run and does the result conform to
its metamodel?) was **live in every arm** — this required building the MALCOMj runner,
without which the check reports UNVERIFIED and the comparison cannot discriminate.

Pass/fail is recomputed from each artefact by
`malcom.evaluation/metrics/rq2_control/analyse.py`, not read from run logs.

## Result

| arm | `eol_executes` | pass rate | runs repaired | total tokens (mean) |
|---|---|---:|---:|---:|
| `single` | 0/10 | 0.00 | 0 | 14,809 |
| `single_repair` | **8/10** | **0.80** | 10 | 47,853 |
| `multi` | 6/10 | 0.60 | 10 | 76,615 |

| contrast | isolates | | Fisher exact |
|---|---|---|---:|
| `single_repair` vs `single` | iterative repair | 8/10 vs 0/10 | **p = 0.0007** |
| `multi` vs `single` | both combined | 6/10 vs 0/10 | **p = 0.0108** |
| `multi` vs `single_repair` | role decomposition | 6/10 vs 8/10 | p = 0.63 |

## What this shows

**The validity gain is attributable to iterative repair, not to role decomposition.**
Adding a gate and repair loop to a single generator moves the pass rate from 0/10 to 8/10
(p = 0.0007). Adding four cooperating agents *on top of* repair changes nothing
detectable — 6/10 vs 8/10, p = 0.63, and the point estimate is lower, not higher.

This is the confound the Discussion currently discloses as a limitation, now measured.
The honest form of the RQ2 claim is: *disciplining generation with a deterministic gate
and a repair loop is what makes construction programs execute; the multi-agent
decomposition is not what produces that gain.*

**Cost makes it sharper.** `single_repair` reached a better outcome for **62% of multi's
tokens** (47,853 vs 76,615). Repair cost 2.0x its own generation budget — real, but
cheaper than decomposition.

## Caveats

1. **One stage, one model, one case study.** This is the `model` phase on the AUV under
   DeepSeek-V4. The paper's other phases may differ; notably the multi-agent arm's value
   may lie in artefacts this gate does not score (trace links — see 3).
2. **`multi` vs `single_repair` is underpowered.** With n=10 per arm, p = 0.63 does not
   establish equivalence, only that no difference is detectable at this sample size. A
   real difference smaller than roughly 40 percentage points would not be visible here.
3. **The arms are not equivalent in output.** The single-agent path writes either a code
   artefact or a trace file, never both, so `trace_resolved` is unsatisfiable in both
   single arms by construction and repair there is driven only by `eol_executes`. The
   multi arm additionally emits a resolved trace model (176 entries in the pilot run),
   which is a genuine capability the pass-rate column does not credit. **This is the
   strongest remaining argument for the multi-agent design and it should be made
   explicitly rather than resting on validity numbers.**
4. **Token accounting differs by arm.** The single arms record repair separately
   (`model_repair`); the multi arm's AutoGen usage summary folds the repair agent into one
   figure. Only the total column is comparable — `multi`'s "repair tokens: 0" is an
   artefact of accounting, not an absence of repair (its log shows 290 repair-agent
   mentions).

## Reproduce

```bash
export DEEPSEEK_API_KEY=...
export JAVA_HOME=/path/to/jdk
export MALCOMJ_RUNNER=$PWD/MALCOMj/build/install/MALCOMj/bin/MALCOMj   # required
python MALCOMp/run_evaluation.py --models deepseek_v4 \
    --variants single single_repair multi --stages model --n-runs 10 \
    --output-root case_studies/auv/output/rq2_10rep
python malcom.evaluation/metrics/rq2_control/analyse.py \
    --root case_studies/auv/output/rq2_10rep/deepseek_v4 --stage model
```

Wall clock: ~3.5 h (bounded by the multi arm at ~22 min/run). Cost: ~US$1.60.

## Failure modes observed

Every failure was a metamodel/program mismatch caught by execution, not a crash:
`single` failed 9/10 on `Property 'robotic_platforms' not found` (the generator inflected
the feature name inconsistently with the metamodel it was given); the two
`single_repair` failures and the four `multi` failures were similar naming and type
mismatches (`'roboticPlatforms'`, `'modules'`, `'module'`, `M!Trace`). This is exactly
the defect class the paper claims execution gating catches — and it does.

## Incidental findings from making the gate runnable

- **`_validate_env` hardcoded `OPENAI_API_KEY`**, so any model declaring its own
  `api_key_env` — including `config.yaml`'s own `deepseek_v4` entry — raised at
  construction despite being fully configured.
- **The MALCOMj runner default was `MALCOMj.bat`**, unrunnable off Windows, so
  `eol_executes` silently degraded to a soft warning on every POSIX machine. Same defect
  class as the FDR path in the original audit. This is why the pilot run's `multi` arm
  showed no repair activity at all.
- **`Base._VERIFY_PHASE` is keyed by pipeline stage names** (`emf_model_creation`) while
  `run_single_agent` uses short keys (`model`), so the control arm's gate lookup silently
  returned `None` and skipped verification entirely.
- **A shipped fixture cannot round-trip.** `fixtures/result_dsml.emf` declares
  `attr PrimitiveType type` where `PrimitiveType` is a `class`; `attr` requires a
  datatype. The Emfatic parser accepts it, so `emfatic_valid` passes, but XMI
  serialisation fails. Unnoticed because nobody could run the execution gate.
