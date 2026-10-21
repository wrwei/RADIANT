# Pre-run audit of the 2x2 study harness (2026-10-21)

Audited before running `scripts/run_factorial.sh`: every place where the four arms
(single, single_repair, multi_no_repair, multi) could differ in anything other than
the two factors (agents; gate-driven repair).

| # | Defect | Effect if run as-was | Fix |
|---|---|---|---|
| 1 | Single arms never assembled the behaviour model; their gate ran FDR on the bare state machine | 3 assertions for single arms, 6 for multi | Assembly is a shared derivation (`stage_io.derive_after_change`) run by every arm |
| 2 | Single-repair trigger was `hard_failures` (incl. trace failures); multi used `repairable_failures` | different repair policies across the agent factor | single uses `repairable_failures` |
| 3 | Single-repair used a generic repair prompt; multi used phase-specialised repair agents | repair factor not identical across the agent factor | single uses the phase's own repair-agent system message |
| 4 | Concept model not re-derived after a concept repair (both arms) | later phases read a stale concept model | re-derived after every repair, both arms |
| 5 | Multi behaviour repair rewrote the assembled copy; parse/structure checks and F1 read the bare model | a bare-model defect could never be repaired (-> rejection); multi F1 scored pre-repair model | both arms repair the state machine; assembly re-derived after each repair |
| 6 | Assembly failure (or no `gradle` on PATH) silently wrote the bare model under the assembled name | FDR on 3 assertions, unrecorded | gate path has no fallback; `behaviour_assembles` check; FDR not run on the bare model in its place |
| 7 | A crashed stage did not end the run; later stages then fell back to golden fixtures | reference-answer leak | crash recorded in `stage_status.json` and ends the run; sweeps run with `MALCOMP_NO_FIXTURES=1` |
| 8 | Single arms recorded no per-attempt log and no upstream provenance | no attempt-0 validity, no leak check for single arms | shared `stage_io.log_attempt` / `record_upstream_inputs` |
| 9 | Log printed "gate FAILED" for accepted artefacts with only trace failures | misleading logs | message reports accepted/rejected separately from trace checks |
| 10 | Scorer counted runs that never reached behaviour as "FDR no verdict"; F1 mixed accepted and rejected artefacts | misreported cells | fixed; F1 reported over accepted and over all produced |

Checked and found consistent: temperature (0.0) and model/endpoint in both code paths;
gate invocation (same `verify()`, strict, runner, FDR config); zero-budget loop in
`multi_no_repair` (outer budget 0, in-chat execution repair off); RESUME counting;
per-run directories (no shared writable state across lanes).

Verification: 193 tests pass (`test_arm_parity.py`, `test_stage_rejection.py` new);
the stored DeepSeek behaviour models of both arms assemble 10/10 through the new gate
path; a real sweep of the single arms through all four phases with a replay stub
(real gates, MALCOMj execution, assembly, halting, scoring) behaves as specified.

Not verified here: the two cooperating arms end to end (they need the live model),
and FDR (needs the licence). Run the smoke test in the script header first.
