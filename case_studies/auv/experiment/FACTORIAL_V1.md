# 2x2 study: {single generator, cooperating agents} x {no repair, gate-driven repair}

DeepSeek-V4, AUV, all four phases, 10 runs per arm, strict mode, repair budget 5,
in-chat execution repair off, acceptance rule (a rejected artefact ends the run).
Harness audited before the run (PRE_RUN_AUDIT_2026-10-21.md); smoke test in
`output/factorial_smoke/`. Data: `output/factorial_v1/`; summary
`output/factorial_v1/factorial_summary.csv` (scripts/score_factorial.py).

## Phase acceptance (runs whose artefact the pipeline accepted)

| | single | single + repair | agents | agents + repair |
|---|---:|---:|---:|---:|
| concept | 10/10 | 10/10 | 10/10 | 10/10 |
| notation | 1/10 | 10/10 | 9/10 | 10/10 |
| construction | 1/10 | 10/10 | 9/10 | 8/10 |
| behaviour, FDR certified (6 assertions) | 1/10 | 10/10 | 9/10 | 8/10 |
| notation valid at attempt 0 (before any repair) | 1/10 | 0/10 | 9/10 | 9/10 |
| repairs used (notation / construction) | - | 10 / 0 | - | 3 / 15 |
| trace models, notation + construction | 0/10 | 0/10 | 9/10 | 10/10 |
| tokens per run | 50k | 85k | 273k | 264k |

Fisher exact, end-to-end certified:
- decomposition without repair: 9/10 vs 1/10, p = 0.0011
- repair with a single generator: 10/10 vs 1/10, p = 0.0001
- decomposition with repair: 8/10 vs 10/10, p = 0.47
- repair with cooperating agents: 8/10 vs 9/10, p = 1.0
- notation valid at attempt 0, agents (pooled) vs single generator (pooled): 18/20 vs 1/20, p = 5.8e-8

## Reading

Either mechanism alone takes end-to-end certification from 1/10 to 9-10/10; combining
them adds nothing (the interaction is substitutive). Agents produce valid artefacts
before any tool feedback (18/20 notations at attempt 0, against 1/20); gate-driven
repair reaches the same end point from invalid first drafts, at about a third of the
agents' tokens. The agents uniquely produce the trace models (19/20 vs 0/20).

Agents lower notation-element F1 (pooled 0.81 vs 0.91, Mann-Whitney p = 0.0007; with
repair 0.80 vs 0.91, p = 0.002; without 0.82 vs 0.90, p = 0.13). Concept F1 (0.96-0.97)
and behaviour F1 (0.98) do not differ.

## Failures

- single (9/10): notation without a `package` declaration; run stopped.
- agents, no repair (run_001): notation syntax error (`datatype` at line 3); run stopped.
- agents + repair (run_002, run_005): construction program instantiates classes absent
  from the run's own notation (run_002's notation lacked the type classes at attempt 0;
  its 3 notation repairs fixed syntax only). Five construction repairs renamed types
  but cannot add classes to the upstream notation, so the program was rejected.
  Not repair damage: both programs failed at attempt 0.

## Why the cooperating arm's construction repair underperformed (analysis, 2026-10-21)

The gap is confined to the construction phase of `multi`: 7/10 programs executed at
attempt 0 (single + repair 10/10, agents without repair 9/9), and repair fixed 1 of the
3 failures in 15 calls. Two causes:

1. **Repair without the metamodel (defect, shared by both repair arms).** The gate-driven
   repair prompt held only the failing program and the error; the EOL repairer is
   instructed to "use the exact class and feature names declared in the current Emfatic
   metamodel", but the metamodel was not in the prompt (the in-chat execution loop, off
   in this study, did include it). The repairer guessed and oscillated: run_005
   Interface <-> InterfaceType for five attempts (the notation declares neither, only
   InterfaceUser); run_002 PrimitiveType <-> Type; run_003 cycled roboticPlatform /
   roboticPlatforms / platforms and landed on a working name at attempt 5. The "unchanged
   reply" stop rule cannot catch an A -> B -> A cycle, so each spent the full budget.
   single + repair never needed construction repair, so the defect never showed there.
2. **Occasional first-draft mismatch in the cooperating chat.** 2 of 19 cooperating
   first-draft programs instantiate classes absent from the run's own notation (0/10
   single + repair). The stored program is the refactorer's output, and the refactorer's
   prompt contains neither the notation nor the vocabulary; the checker is told to work
   through the whole concept vocabulary. Plausible contributors; not established, since
   the chat transcripts are not stored.

8/10 vs 10/10 is not significant (p = 0.47).

**Fix** (`stage_io.build_repair_prompt`, used by both repair arms): the repair prompt now
carries the upstream notation (construction and behaviour phases), the EOL repair
knowledge (construction), and the earlier attempts' errors; a repair that returns an
earlier attempt stops the loop (`stage_io.is_cycle`). Tests: `test_arm_parity.py`.
Not changed: the cooperating agents' generation prompts (cause 2) -- that is a change to
the system under study, left for a decision.

**Re-run:** `scripts/prepare_repair_rerun.py` builds `output/factorial_v2/` with the two
repair arms' concept and notation phases kept as generated and construction + behaviour
removed; the no-repair arms are copied unchanged.

## factorial_v2: repair arms re-run from construction with the repaired prompt (2026-10-21)

`output/factorial_v2/`: concept and notation phases of the two repair arms carried over
from v1 unchanged; construction and behaviour regenerated. No-repair arms unchanged.

| | single | single + repair | agents | agents + repair |
|---|---:|---:|---:|---:|
| construction accepted | 1/10 | 10/10 | 9/10 | 9/10 (v1: 8/10) |
| FDR certified | 1/10 | 10/10 | 9/10 | 9/10 (v1: 8/10) |
| construction repairs used | - | 0 | - | 7 (v1: 15) |

With the notation in the repair prompt, run_002 was fixed in 2 repairs (v1: 5 failed).
All four factor contrasts on certification are now p = 1.0 or as before; decomposition
with repair: 9/10 vs 10/10, p = 1.0.

**run_005 is a pipeline defect, not a model failure.** Its notation declares
`class ~Interface` -- Emfatic's `~` escapes the keyword, so the class IS named
`Interface`, and the official parser accepted the notation. The pipeline's
Emfatic-to-Ecore converter (`eol_execution.py`) did not accept the escape and dropped the
class and both references to it, so the run's correct first-draft program
(`new M!Interface`) failed with "Type 'M!Interface' not found". The repairer, now shown
the notation, copied the escape into EOL (`M!~Interface`), which is not EOL syntax. With
the converter fixed (tests: `test_converter_accepts_emfatic_keyword_escape`), the attempt-0
program executes and conforms; no other stored program's verdict changes (checked over
factorial_v1, v2 and table1_v2). The `~` escape appears in exactly one generated notation
across all these studies (this run, both versions).

Honest reading of the agents + repair cell: 10/10 programs would have executed under a
correct converter, 9 of them at attempt 0.
