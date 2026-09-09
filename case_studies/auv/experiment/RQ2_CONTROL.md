# RQ2 control experiment — separating iterative repair from role decomposition

**Audit item A7.** The paper's RQ2 compares the full cooperating pipeline against a
single-pass baseline that has neither checking nor repair, so it measures role
decomposition and iterative repair *together*. This is the missing arm.

**Design.** Model: DeepSeek-V4 (`deepseek-v4-pro`). Stage: `model` (the EOL construction
program) — the phase carrying the paper's headline validity jump and 48 of the 62
recorded gate-triggered repairs. n=10 per arm, 30 runs. All arms seeded with an
**identical** concept model and metamodel — which isolates the model stage but also
withholds from the multi arm the upstream artefact it would normally generate itself
(caveat 1).
The structural gate (`eol_executes`: does the program run and does the result conform to
its metamodel?) was **live in every arm** — this required building the MALCOMj runner,
without which the check reports UNVERIFIED and the comparison cannot discriminate.

Pass/fail is recomputed from each artefact by
`malcom.evaluation/metrics/rq2_control/analyse.py`, not read from run logs.

## Result

| arm | `eol_executes` | pass rate | runs with recorded repair | total tokens (mean) |
|---|---|---:|---:|---:|
| `single` | 0/10 | 0.00 | 0 (no repair path) | 14,809 |
| `single_repair` | **8/10** | **0.80** | 10 | 47,853 |
| `multi` | 6/10 | 0.60 | not separable — see caveat 5 | 76,615 |

The repair column counts runs with a separately recorded `<stage>_repair` token entry.
The multi arm has none: its AutoGen usage summary folds the repair agent into one
figure, so **no per-run repair count is derivable for it** from the recorded data. Its
repair loop did run — the sweep log shows repair-agent activity throughout — but the
number of runs that invoked it is not recoverable, and is left unstated rather than
inferred.

| contrast | isolates | | Fisher exact |
|---|---|---|---:|
| `single_repair` vs `single` | iterative repair | 8/10 vs 0/10 | **p = 0.0007** |
| `multi` vs `single` | both combined | 6/10 vs 0/10 | **p = 0.0108** |
| `multi` vs `single_repair` | role decomposition | 6/10 vs 8/10 | p = 0.63 |

## What this shows

**Iterative repair, applied to a fixed input, is sufficient to produce the validity
gain.** Adding a gate and repair loop to a single generator moves the pass rate from
0/10 to 8/10 (p = 0.0007), with no change of architecture. The `single` arm's 0/10
exactly replicates the paper's own Table 1 figure for this cell, which is a useful check
that the harness reproduces the published behaviour.

**The decomposition contrast, however, is not a clean test — see caveat 1.** All three
arms were seeded with the *same* metamodel, and that metamodel came from a single-agent
run. In the paper's full-cascade design the cooperating pipeline generates its own
metamodel and its notation phase is precisely where cooperation helps most (Table 1:
notation validity 5/10 single vs 10/10 multi for this model). By holding the input fixed
I isolated the model stage but denied the multi arm the better upstream artefact it would
normally produce — which is very likely why it scores 6/10 here against 10/10 in the
paper.

So the defensible reading is narrower than "decomposition adds nothing":

* **Supported.** At the model stage, from an identical fixed input, gate-plus-repair
  accounts for the whole of the observed validity gain; the multi-agent configuration
  adds nothing detectable *on top of repair at that stage*.
* **Not supported by this experiment.** That decomposition contributes nothing
  end-to-end. Its contribution may be largely *upstream* — a better metamodel entering
  the model phase — which this design deliberately removes. Testing that needs a
  full-cascade run of all three arms.

**Cost makes it sharper.** `single_repair` reached a better outcome for **62% of multi's
tokens** (47,853 vs 76,615). Repair cost 2.0x its own generation budget — real, but
cheaper than decomposition.

## Caveats

1. **Fixed upstream input — this is the important one.** Every arm received the same
   concept model and the same metamodel, and that metamodel was produced by a
   single-agent run. This is what makes the *repair* contrast clean (identical input,
   one variable changed) and what makes the *decomposition* contrast unfair to `multi`:
   in the real pipeline its notation phase would have generated a gate-passing metamodel
   first, and Table 1 shows that is exactly where cooperation pays (5/10 vs 10/10
   notation validity for this model). The paper's 10/10 for multi construction is a
   full-cascade figure; my 6/10 is a fixed-input figure. **They are not comparable, and
   the 6/10 must not be quoted against the paper's 10/10.** A full-cascade run of all
   three arms is the missing experiment.

2. **One stage, one model, one case study.** This is the `model` phase on the AUV under
   DeepSeek-V4. The paper's other phases may differ; notably the multi-agent arm's value
   may lie in artefacts this gate does not score (trace links — see below).
3. **`multi` vs `single_repair` is underpowered.** With n=10 per arm, p = 0.63 does not
   establish equivalence, only that no difference is detectable at this sample size. A
   real difference smaller than roughly 40 percentage points would not be visible here.
4. **The arms are not equivalent in output.** The single-agent path writes either a code
   artefact or a trace file, never both, so `trace_resolved` is unsatisfiable in both
   single arms by construction and repair there is driven only by `eol_executes`. The
   multi arm additionally emits a resolved trace model (176 entries in the pilot run),
   which is a genuine capability the pass-rate column does not credit. **This is the
   strongest remaining argument for the multi-agent design and it should be made
   explicitly rather than resting on validity numbers.**
5. **Token accounting differs by arm.** The single arms record repair separately
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
