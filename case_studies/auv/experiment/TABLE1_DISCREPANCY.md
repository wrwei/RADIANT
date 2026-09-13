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
| 2 (shipped) | 3/10 | 3.0 (= 2.0 repairs) |
| 6 (diagnostic) | **8/10** | **4.9** (= 3.9 repairs) |

Fisher exact p = 0.070 on the pass rates (n=10 per arm; the effect is large but at this
sample size not conventionally significant).

The decisive argument is the repair count, and it is an impossibility argument rather
than a match. `FINDINGS.md` records the original sweep's gate-triggered repairs as
**"model/EOL 48"** across 10 multi runs. Counting the recorded attempt artefacts (each
run writes `eol_execution_attempts/candidate_NNN.eol`, so repairs = candidates − 1):

| cap | candidates | **repairs** | runs hitting the cap | executes |
|---|---:|---:|---:|---:|
| 2 (shipped) | 30 | **20** | 10/10 | 3/10 |
| 5 (reconciled) | 42 | **32** | 0/10 | 4/10 |
| 6 (diagnostic) | 49 | **39** | 0/10 | 8/10 |

**Under a ceiling of 2, ten runs can perform at most 20 repairs. The recorded figure is
48. The published run therefore cannot have been produced with the shipped config** —
this is arithmetic, not inference, and it is the load-bearing claim here.

Cap 6 yields 39 repairs, the same regime as the recorded 48 but not identical. No cap-6
run exhausted its budget (the most any run used was 5), so raising the cap further would
not close the residual gap; that difference is attributable to run-to-run variation and
possibly to model drift since May 2026, neither of which this experiment isolates.

*(An earlier version of this note compared 49 candidates against 48 repairs and claimed
they matched. They are different quantities — 49 candidates is 39 repairs — and the
comparison was wrong. The impossibility argument above does not depend on it.)*

## What this means

1. **The paper's 10/10 is not fabricated and the harness is not broken.** Under a
   non-binding budget the multi arm reaches 4/10 and 8/10 in two separate ten-run blocks
   (pooled 12/20 = 0.60), against 3/10 when the budget binds. The published 10/10 sits
   above even the better block, so model drift since May 2026 cannot be excluded — but
   the shipped cap is demonstrably part of the gap.

   **Caution on effect size.** Caps 5 and 6 are *both* non-binding here (maximum repairs
   actually used: 4 and 5), so they impose the same effective budget — yet they returned
   4/10 and 8/10. That spread cannot be a cap effect; it is run-to-run variance, and it
   is large. Treat the binding-vs-non-binding comparison (3/10 vs 12/20, p = 0.25) as
   directional only.
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
budget matched at 5 and run head to head, the arms are statistically indistinguishable:
**multi 4/10 vs `single_repair` 6/10, Fisher p = 0.66.** **The "decomposition adds
nothing" reading is therefore not supported by matched evidence — but neither is any
claim that decomposition helps. The honest statement is that this experiment cannot
separate them at n=10.**

What still holds unambiguously:

* **Repair drives construction validity.** `single` (no repair) is 0/10 under every
  configuration tested. That contrast is unaffected by the cap, since the single arm has
  no repair path at all.
* **Only the multi arm emits trace models** — 10/10 runs, versus 0/10 in both single
  arms. This is independent of repair budget and remains the strongest argument for the
  multi-agent design.

**Resolved by the matched run (`rq2_matched`):** at an identical, non-binding budget of
5 for both arms, multi scores 4/10 and `single_repair` 6/10 (p = 0.66). Decomposition
neither helps nor hurts construction validity detectably. Given the variance measured
above, n=10 per arm is simply too small to resolve a difference at this phase; a
meaningful answer needs roughly 40-50 runs per arm, which is a ~US$40 experiment.

## Recommended fixes

1. **Reconcile `config.yaml` with the published runs** — set the model-stage cap to
   whatever produced the reported figures (6 reproduces the recorded repair count), or
   document the value used. Without this the package contradicts the paper.
2. ~~Re-run the RQ2 comparison at matched budgets~~ **— done (`rq2_matched`): the arms
   are indistinguishable, p = 0.66.** The open question is now statistical power, not
   configuration.
3. **Record the repair budget in Methods.** It is load-bearing — a binding budget of 2
   truncates every run and roughly halves the pass rate — and the paper does not state
   it. State the mean under a non-binding budget (0.6) rather than the best single block
   (0.8), and disclose the variance.

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
