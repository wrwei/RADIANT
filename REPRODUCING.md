# Reproducing the reported results

Every number in the paper is produced by a driver in this repository from the
artefacts in this repository. This file maps each reported item to the command
that regenerates it.

## Install

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r MALCOMp/requirements.txt
```

The AutoGen dependency is pinned to `ag2>=0.9,<1.0`. This matters: the
`pyautogen` distribution no longer provides the `autogen` module the pipeline
imports, so an unpinned install fails at import. See the comment in
`MALCOMp/requirements.txt`.

Two gates invoke external tools:

- **model execution** needs the MALCOMj runner:
  `cd MALCOMj && gradle installDist -PjavaVersion=21` (JDK 21). If gradle's
  lock service is unavailable, `MALCOMj/README.md` documents a direct
  `javac`/`java -cp` route. Point the pipeline at it with `MALCOMJ_RUNNER=` or
  `malcomj_runner:` in `config.yaml`.
- **behaviour refinement** needs FDR 4.2.7 (`refines`) on `PATH`, or set
  `verification.fdr4.fdr4_path` in `config.yaml`.

A check whose tool is unavailable is recorded as **unverified**, not failed,
and the phase is accepted with `fully_verified=False`. Set
`verification.strict: true` in `config.yaml` to reject those phases instead;
the reported results were produced with every check runnable.

## Reported item -> command

| Paper item | Command |
|---|---|
| Table 2, trace resolvability and coverage | `python malcom.evaluation/metrics/traceability/compute.py` |
| Table 2, behaviour coverage 0.67 | same driver; `traceability_report.md` breaks it down per layer |
| Figure 3, change-impact set | `python -m MALCOMp.change_impact` over `case_studies/auv/fixtures` |
| RQ2 control (matched budget) | `python malcom.evaluation/metrics/rq2_control/analyse.py --root case_studies/auv/output/rq2_matched/deepseek_v4 --stage model` |
| RQ2 full cascade | `python malcom.evaluation/metrics/rq2_control/cascade.py --root case_studies/auv/output/rq2_cascade/deepseek_v4` |
| Reproduction blocks (4, 8, 5, 5 of 10) | `analyse.py --root case_studies/auv/output/{rq2_matched,rq2_cap6,rq2_repro,rq2_repro2}/deepseek_v4 --stage model` |
| FDR verdicts | `./scripts/run_fdr_verdicts.sh` -> `malcom.evaluation/fdr_results.json` |
| Supplementary Note 2, tokens and cost | `tokens.json` in each published run directory |

## Experiment records

`case_studies/auv/experiment/` holds the protocol and result of each
experiment, including what did **not** reproduce:

- `FINDINGS.md` — the May 2026 sweep that Table 1 reports
- `RQ2_CONTROL.md` — repair vs decomposition, fixed upstream inputs
- `RQ2_CASCADE.md` — the same contrast with each arm generating its own inputs
- `RQ2_REPRODUCTION.md` — why Table 1's DeepSeek-V4 construction cell does not
  reproduce, and the four-block pooled rate that replaces it
- `TABLE1_DISCREPANCY.md` — the repair-budget parameter behind that gap
- `FDR_VERDICTS.md` — 1 of 3 archived behaviour models verifies; why the other
  two cannot be checked in their archived form

## Published run outputs

`case_studies/auv/output/runs/` holds the three archived May 2026 runs.
`case_studies/auv/output/rq2_*/` hold the September 2026 blocks, reduced to the
files the drivers read: the scored artefact, the token ledger, the arm manifest
(`run_manifest.json`, which records which model and configuration owns each run
directory), and the per-attempt repair candidates. Full run trees are not
published; re-running a sweep regenerates them.

## Tests

```bash
cd MALCOMp && python -m pytest tests -q
```

Tests that need a prior pipeline run, or FDR, skip themselves with a message
naming the prerequisite. CI (`.github/workflows/tests.yml`) runs the suite and
an import check without an API key.
