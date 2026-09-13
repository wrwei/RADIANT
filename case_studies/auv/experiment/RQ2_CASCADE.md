# RQ2 full-cascade experiment — repair vs decomposition, each arm end to end

**Audit item A7, second experiment.** The first control (fixed-input, `RQ2_CONTROL.md`)
seeded every arm with the same metamodel, which isolated the model stage but withheld
from the multi-agent arm the upstream artefact it would normally generate itself. That
made its decomposition contrast unfair. This run removes the seeding: **each arm runs the
cascade end to end and generates its own concept model, metamodel and construction
program.**

**Design.** DeepSeek-V4 (`deepseek-v4-pro`), AUV case study, 10 repetitions per arm,
3 arms x 3 stages x 10 reps = 90 stage-runs, 0 errors. The behaviour stage is excluded:
its gate is FDR refinement checking and the `refines` binary is unavailable here, so it
would score UNVERIFIED in every arm. All gates were live, including the EOL execution
gate (MALCOMj built for this purpose).

Pass/fail is recomputed from each artefact by
`malcom.evaluation/metrics/rq2_control/cascade.py`, not read from run logs.

## Result

| arm | concept | notation | **model executes** | tokens (mean) |
|---|---:|---:|---:|---:|
| `single` | 10/10 | 10/10 | **0/10** | 61,116 |
| `single_repair` | 10/10 | 10/10 | **7/10** | 249,243 |
| `multi` | 10/10 | 10/10 | **3/10** | 242,506 |

| contrast | isolates | | Fisher exact |
|---|---|---|---:|
| `single_repair` vs `single` | iterative repair | 7/10 vs 0/10 | **p = 0.0031** |
| `multi` vs `single_repair` | role decomposition | 3/10 vs 7/10 | p = 0.18 |
| `multi` vs `single` | both combined | 3/10 vs 0/10 | p = 0.21 |

> **CORRECTION (see `TABLE1_DISCREPANCY.md`).** The arms in this run were **not
> budget-matched**: `single_repair` used the global `verification.max_repair_attempts: 5`,
> while `multi` was capped at 2 by the per-stage
> `emf_model_creation.execution_repair.max_attempts`. All 10 multi runs exhausted that
> cap. Raising it to 6 — generation held fixed — moves multi from 3/10 to **8/10**, at or
> above `single_repair`'s 7/10. **The "decomposition adds nothing" reading below is
> therefore not supported by matched evidence and should not be cited.** What survives
> unaffected: `single` is 0/10 under every configuration (it has no repair path), and only
> the multi arm emits trace models (10/10 vs 0/10). A budget-matched re-run is the
> outstanding experiment.

## What this shows

**The fixed-input finding survives the fair test.** Seeding was not what disadvantaged
the multi arm: given the chance to generate its own upstream artefacts, it still does not
beat a single generator with a repair loop. Iterative repair remains the only contrast
that reaches significance (p = 0.0031); decomposition does not (p = 0.18), and its point
estimate is again lower, not higher.

**The upstream stages do not discriminate at all.** Concept extraction and notation
generation are 10/10 in every arm. Whatever the cooperating configuration contributes, it
is not upstream validity on this case study — which was the alternative explanation the
fixed-input design could not rule out. It is now ruled out.

**But the pass-rate column is the wrong scorecard for the multi arm, and this matters
more than the p-values.** Trace artefacts, counted separately:

| arm | runs emitting notation traces | runs emitting model traces |
|---|---:|---:|
| `single` | 0/10 | 0/10 |
| `single_repair` | 0/10 | 0/10 |
| `multi` | **10/10** | **10/10** |

Only the multi-agent configuration produces the trace models the paper's change-impact
analysis depends on — reliably, in every run. The single arms emit none, by construction.
**That, not construction-program validity, is what the multi-agent design buys**, and the
paper should rest its RQ2 argument there.

The two are causally linked: 2 of the multi arm's 7 model-stage failures reference a
`Trace` type that its own generated metamodel does not declare. Emitting traceability is
what makes its construction programs harder to execute. That is a real engineering
tension worth stating plainly rather than a defect to hide.

## Discrepancy with the paper's Table 1 — unresolved

| cell | paper | this run |
|---|---|---|
| DeepSeek single, construction executes | 0/10 | 0/10 (replicates) |
| DeepSeek multi, construction executes | **10/10** | **3/10** |
| DeepSeek single, notation valid | 5/10 | 10/10 |

The `single` construction cell replicates exactly, which is good evidence the harness
reproduces published behaviour. **The multi cell does not, and I cannot currently explain
the gap.** Candidate causes not yet eliminated: the published runs date from May 2026 and
`deepseek-v4-pro` may have changed behind the same name; the published configuration may
differ from the one in `config.yaml`; or the published runs may have executed with a
different repair-attempt budget. **This must be resolved before the paper's Table 1 is
defended in review** — a referee who runs the package today will see 3/10.

The notation-validity row differs for a separate, understood reason (below).

## Notation validity: two checkers, opposite verdicts

Scoring notation with the **official Emfatic parser** gives 0/10; the **pipeline's own
converter** gives 10/10 — on identical artefacts. The pipeline deliberately emits
package-less, class-only Emfatic, which the strict standalone parser rejects by design
(this is documented in `verification._emfatic_converts`). The converter is the correct
checker: its verdict governs whether the artefact is usable downstream, and every
artefact it accepts does convert and execute.

This is a live trap. `verify_dsml` prefers the official parser **whenever MALCOMj is
built** — so building the toolchain, which is required to run the execution gate at all,
silently flips notation scoring to 0/10 and makes the generator look collapsed. The
cascade driver pins the converter explicitly with this reasoning in a comment.

Neither figure matches the published 5/10, which remains unexplained.

## Caveats

1. **One model, one case study, three stages.** DeepSeek-V4 on the AUV, behaviour stage
   excluded for want of FDR.
2. **`multi` vs `single_repair` is underpowered.** At n=10, p = 0.18 does not establish
   equivalence; a true difference below roughly 45 percentage points would be invisible.
   The direction is consistent across both experiments, which is suggestive, not
   conclusive.
3. **Cost is not comparable to the paper's efficiency claims.** Both repair-equipped arms
   spend roughly 4x the single arm's tokens (249k and 243k vs 61k). Verified generation
   is not cheap; the paper's efficiency argument is about human effort, not tokens, and
   these figures should not be conflated with it.

## Reproduce

```bash
export DEEPSEEK_API_KEY=...
export JAVA_HOME=/path/to/jdk
export MALCOMJ_RUNNER=$PWD/MALCOMj/build/install/MALCOMj/bin/MALCOMj
for v in single single_repair multi; do
  python MALCOMp/run_evaluation.py --models deepseek_v4 --variants $v \
      --stages concept dsml model --n-runs 10 \
      --output-root case_studies/auv/output/rq2_cascade &
done; wait
python malcom.evaluation/metrics/rq2_control/cascade.py \
    --root case_studies/auv/output/rq2_cascade/deepseek_v4
```

Wall clock: ~14 h with the three arms in parallel (multi is the long pole at ~45 min per
cascade). Cost: ~US$5.

## Code change required to run this

The single-agent variants previously wrote only a trace file at the concept stage, not
`result_concept_model.json`, which phases 3-5 load as a prompt asset — so they could not
cascade at all. That artefact is a *deterministic* deduplication of the trace entries
with no model call, so deriving it for the single arms imports no multi-agent advantage
into the baseline; it gives the baseline the same mechanical derivation. The helper calls
`ConceptExtraction._store_concept_model` itself rather than reimplementing the dedup, so
the two paths cannot drift.
