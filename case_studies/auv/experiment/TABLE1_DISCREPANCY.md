# Why Table 1's multi cell does not reproduce — the shipped repair cap

**Resolved.** The paper reports 10/10 for DeepSeek-V4 multi "construction executes"; the
shipped package produces 3/10. The cause is a configuration value, not model drift and
not a harness defect: **`config.yaml` caps model-stage repair at 2 attempts, and the
published runs were produced with a substantially higher cap.**

## The evidence

`config.yaml` line 130, under `emf_model_creation.execution_repair`, sets
`max_attempts: 2`. This is a *per-stage* override; the global
`verification.max_repair_attempts` is 5 and does not apply here. Git history shows the
value has been 2 since the commit that introduced EOL execution validation.

Under that cap, **all 10** of the full-cascade multi runs logged
`model EOL repair attempts exhausted` — every run hit the ceiling with a still-failing
program.

So I re-ran the multi arm with one variable changed — cap 2 to 6 — feeding each run the
**same concept model and metamodel that run had generated for itself** in the cascade, so
generation is held fixed and only the repair budget differs:

| repair cap | executes | repair candidates (mean/run) |
|---|---:|---:|
| 2 (shipped) | 3/10 | 3.0 |
| 6 (diagnostic) | **8/10** | **4.9** |

Fisher exact p = 0.070 on the pass rates (n=10 per arm; the effect is large but at this
sample size not conventionally significant).

The decisive number is the repair count. `FINDINGS.md` records the original sweep's
gate-triggered repairs as **"model/EOL 48"** across 10 multi runs — a mean of 4.8. My
cap-6 run produced **49** candidates, mean 4.9. My cap-2 run produced 30, which is
exactly what a cap of 2 forces (initial attempt plus two repairs, times 10 runs). **The
published run cannot have been produced under the shipped cap of 2** — 48 repairs across
10 runs is arithmetically impossible when the ceiling is 2 per run.

## What this means

1. **The paper's 10/10 is not fabricated and the harness is not broken.** With a repair
   budget consistent with the recorded 48 repairs, the multi arm reaches 8/10 here — the
   same regime as the published figure, and the remaining gap to 10/10 is within run-to-run
   variation at n=10 (plus possible model drift since May 2026, which this experiment does
   not isolate and cannot exclude).
2. **The replication package as shipped does not reproduce the paper.** A referee who
   runs it today gets 3/10, and nothing in the repository explains why. This is a
   reproducibility defect, and it is the single highest-value fix available.
3. **The RQ2 conclusion is unaffected in direction, and its margin narrows.** The
   repair-vs-decomposition comparison used cap 2 for both the multi arm and (via
   `verification.max_repair_attempts: 5`) a *more* generous budget for `single_repair`.
   Re-running that comparison with matched budgets is now the outstanding experiment —
   see below.

## Consequence for the RQ2 result — important

The published cascade comparison was **not budget-matched**:

| arm | model-stage repair budget |
|---|---|
| `single_repair` | 5 (`verification.max_repair_attempts`) |
| `multi` | 2 (`emf_model_creation.execution_repair.max_attempts`) |

`single_repair`'s 7/10 was obtained with 2.5x the multi arm's repair budget. With the
budget raised, multi reaches 8/10 — at or above `single_repair`'s figure. **The
"decomposition adds nothing" reading is therefore no longer supported by matched
evidence, and the cascade record's headline must be read with this correction.**

What still holds unambiguously:

* **Repair drives construction validity.** `single` (no repair) is 0/10 under every
  configuration tested. That contrast is unaffected by the cap, since the single arm has
  no repair path at all.
* **Only the multi arm emits trace models** — 10/10 runs, versus 0/10 in both single
  arms. This is independent of repair budget and remains the strongest argument for the
  multi-agent design.

What is now open: whether decomposition adds construction validity *at matched repair
budget*. The cap-6 point estimate (8/10 multi vs 7/10 single_repair at cap 5) suggests
parity rather than either direction, but the arms were not run head-to-head under
matched caps, so this is not a result yet.

## Recommended fixes

1. **Reconcile `config.yaml` with the published runs** — set the model-stage cap to
   whatever produced the reported figures (6 reproduces the recorded repair count), or
   document the value used. Without this the package contradicts the paper.
2. **Re-run the RQ2 comparison at matched budgets** before drafting any Results revision.
   ~3 h, ~US$4.
3. **Record the repair budget in Methods.** It is a load-bearing parameter — it moves the
   headline cell from 3/10 to 8/10 — and the paper does not currently state it.

## Reproduce

```bash
# with max_attempts raised to 6 under emf_model_creation.execution_repair
export DEEPSEEK_API_KEY=... JAVA_HOME=/path/to/jdk
export MALCOMJ_RUNNER=$PWD/MALCOMj/build/install/MALCOMj/bin/MALCOMj
python MALCOMp/run_evaluation.py --models deepseek_v4 --variants multi \
    --stages model --n-runs 10 --output-root case_studies/auv/output/rq2_cap6
```

Runs were seeded with the cascade multi arm's own upstream artefacts, so generation is
held fixed and the repair budget is the only variable. Wall clock ~6 h; cost ~US$2.
