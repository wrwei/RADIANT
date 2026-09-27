# RQ2 reproduction attempt — the published 10/10 does not reproduce

**Question.** Table 1 reports DeepSeek-V4 multi "construction executes" = 10/10, the
paper's headline RQ2 cell. Does it reproduce under the paper's own protocol?

**Protocol.** Exactly as the paper describes the published sweep: multi-agent
configuration, full cascade (each run generates its own concept model, metamodel and
construction program), DeepSeek-V4, ten repetitions, repair budget 5 (the reconciled
value; non-binding — no run used more than 4 repairs before passing or stalling), EOL
execution gate live via the built MALCOMj runner. One run aborted on a transient harness
error (`'NoneType' object has no attribute 'model'` — an API response object arrived
malformed during generation) and was re-run rather than scored.

## Result

**5/10 construction programs execute.** Against the published 10/10: Fisher exact
**p = 0.033**.

Pooling every non-binding full-cascade multi block run this session:

| block | cap | executes |
|---|---|---:|
| `rq2_matched` | 5 | 4/10 |
| `rq2_cap6` | 6 | 8/10 |
| `rq2_repro` | 5 | 5/10 |
| `rq2_repro2` (September 27) | 5 | 5/10 |
| **pooled** | non-binding | **22/40 = 0.55** |

Pooled against the published figure: Fisher **p = 0.009**. If the true per-run pass
probability were 0.55, the chance of observing 10/10 in a ten-run block is **0.0025**.
(`rq2_repro2` is the first block recorded under the run-manifest guard: every run
directory carries its arm identity, stamped at instrument commit `1467adf`.)
(For contrast, the binding shipped cap of 2 gives 3/10 — that part is config, fixed in
`d92e6d5`.)

Repair activity in this run: 36 repairs across 10 runs (mean 3.6), against the original
sweep's recorded 48 (mean 4.8) — same regime, still short of the recorded intensity.

## Reading

Today's `deepseek-v4-pro`, through the shipped pipeline with the corrected config,
produces a construction program that executes in roughly **half to two-thirds** of runs,
not all of them. The published 10/10 is now statistically inconsistent with current model
behaviour, not just unluckily unmatched. Since the harness reproduces the paper's
`single` baseline exactly (0/10, three times over) and the recorded repair counts confirm
the original sweep ran with a higher budget than shipped, the remaining explanations are:

1. **Model drift behind a stable name.** The published runs date from May 2026. Hosted
   models change; nothing pins the served snapshot. This is the most likely cause and
   cannot be excluded or confirmed from here.
2. **Configuration differences beyond the cap** (prompts, temperature handling, feed
   mode) between the published runs and the shipped tree. The recorded 48-repair figure
   is consistent with the cap-6 regime, so the budget alone does not close the gap.
3. **Selection.** FINDINGS.md records one sweep; if earlier or partial sweeps existed,
   the published block may be the better of several. No evidence for or against this in
   the repository.

## What the paper should do

The safest fix is also the honest one: report the construction-executes cell as measured
**now**, with dispersion, rather than defending a point figure that no longer reproduces:
"under a non-binding repair budget, 22/40 runs (55%; blocks of 4, 8, 5, 5 of 10)" — and
date the runs, name the model snapshot as unpinnable, and keep 0/10 for the single-pass
baseline, which reproduces perfectly. The Fisher test against the single baseline remains
decisive at pooled rates (22/40 vs 0/20, p = 9.4e-06), so **the paper's qualitative claim
survives: gated multi-agent generation makes construction programs execute where a single
pass never does.** What does not survive is the 10/10 point estimate and the
p = 1.1x10^-5 attached to it.

## Reproduce

```bash
export DEEPSEEK_API_KEY=... JAVA_HOME=... 
export MALCOMJ_RUNNER=$PWD/MALCOMj/build/install/MALCOMj/bin/MALCOMj
python MALCOMp/run_evaluation.py --models deepseek_v4 --variants multi \
    --stages concept dsml model --n-runs 10 \
    --output-root case_studies/auv/output/rq2_repro
```
~7 h wall clock, ~US$3.
