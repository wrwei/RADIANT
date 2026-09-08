# RQ2 control experiment — separating iterative repair from role decomposition

**Audit item A7.** The paper's RQ2 compares the full cooperating pipeline against a
single-pass baseline with no checking and no repair, so it measures role decomposition
and iterative repair *together*. This adds the missing arm.

Model: DeepSeek-V4 (`deepseek-v4-pro`). Stage: `model` (EOL construction program) — the
phase carrying the paper's headline 0/10 -> 10/10 validity jump and 48 of the 62 recorded
gate-triggered repairs. n=1 per arm.

All three arms were seeded with an **identical** concept model and metamodel, so the only
difference is the generation strategy.

## Result

| arm | `eol_executes` | generation tokens | repair tokens | outcome |
|---|---|---:|---:|---|
| `single` | FAIL | 15,438 | 0 | `Property 'robotic_platforms' not found` |
| `single_repair` | **PASS** | 14,972 | 58,392 | EOL executed; model conforms |
| `multi` | FAIL | 77,086 | 0 | `Property 'types' not found` |

The repair loop ran 4 attempts against real execution failures, terminating when the
repairer stopped changing the artefact.

## What this shows

**Iterative repair, not role decomposition, is what makes the construction program
execute — at least at n=1 on this stage.** The single generator plus a repair loop
reached a conforming model; the four-agent configuration without a working execution gate
did not. That is the confound the Discussion discloses, now measured rather than assumed:
`single_repair` vs `single` isolates repair, and `multi` vs `single_repair` isolates
decomposition.

Cost profile: repair consumed ~3.9x its own generation budget (58,392 vs 14,972), and the
repair-equipped single arm used **73,364 tokens total against multi's 77,086** — within
5% for a *better* verified outcome.

## Caveats — read before citing

1. **n=1 per arm.** The paper's own figures are 10 repetitions. This establishes the
   experiment runs and produces a discriminating signal; it does not establish an effect
   size. Re-run with `--n-runs 10` before putting a number in the paper.
2. **The `multi` arm ran without a live execution gate.** Its repair agent never fired
   because `eol_executes` reported UNVERIFIED at the time (the runner default was a
   Windows `.bat`; fixed since). A fair `multi` arm must be re-run with `MALCOMJ_RUNNER`
   set — its result here is a lower bound, and the headline comparison above is
   provisional until it is.
3. **`trace_resolved` is unsatisfiable in both single arms** by construction: the
   single-agent path writes either a code artefact or a trace, never both. Repair is
   therefore driven only by `eol_executes` in these arms, and the inapplicable check is
   logged, not silently passed.

## Reproduce

```bash
export DEEPSEEK_API_KEY=...            # your key
export MALCOMJ_RUNNER=/path/to/MALCOMj # required, or eol_executes is UNVERIFIED
python MALCOMp/run_evaluation.py --models deepseek_v4 \
    --variants single single_repair multi --stages model --n-runs 10 \
    --output-root <dir>
```

## Incidental findings from making this runnable

- **`_validate_env` hardcoded `OPENAI_API_KEY`**, so any model declaring its own
  `api_key_env` — including the DeepSeek entry in `config.yaml` — failed at construction
  despite being fully configured. `llm_keys.resolve_api_key` already handled this; the
  validator ignored it.
- **The MALCOMj runner default was `MALCOMj.bat`**, unrunnable off Windows, so
  `eol_executes` silently degraded to a soft warning on every non-Windows machine — the
  same defect class as the FDR path found in the original audit.
- **A shipped fixture cannot round-trip.** With the gate genuinely running,
  `fixtures/result_dsml.emf` fails XMI serialisation: it declares
  `attr PrimitiveType type` where `PrimitiveType` is a `class`, and `attr` requires a
  datatype. The Emfatic parser accepts it, so `emfatic_valid` passes — this is precisely
  the defect class the paper claims execution gating catches, and it went unnoticed
  because nobody could run the gate.
