"""Score a FULL-CASCADE RQ2 run: every arm generates its own upstream artefacts.

The fixed-input experiment (analyse.py) seeded all arms with the same metamodel,
which isolates one stage but withholds from the multi arm the better upstream
artefact it would normally produce. This scores a cascade instead, per stage, so
an upstream advantage shows up where it happens rather than being inferred.

Reported per arm and stage:

  gate_pass   the stage's own structural check (notation parses / program
              executes), recomputed from the artefact
  reached     runs that produced this stage's artefact at all — a run whose
              upstream stage failed may still proceed, so this separates
              "did not get here" from "got here and failed"

Usage:
    export MALCOMJ_RUNNER=.../MALCOMj/build/install/MALCOMj/bin/MALCOMj
    python malcom.evaluation/metrics/rq2_control/cascade.py \
        --root case_studies/auv/output/rq2_cascade/deepseek_v4
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "MALCOMp"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import verification as V  # noqa: E402
from analyse import STRUCTURAL, fisher_exact_2x2  # noqa: E402

ARMS = ("single", "single_repair", "multi")
# stage -> the artefact whose presence means the run reached that stage
ARTEFACT = {
    "concept": ("result_concept_trace.json", "result_term_extraction.json"),
    "dsml": ("result_dsml.emf", "result_DSL.emf"),
    "model": ("result_model.eol", "result_eol_program.eol"),
}
# Three of the pipeline's four generation stages. The behaviour stage is
# excluded: its structural gate is FDR refinement checking, and the `refines`
# binary is not available here, so it would score UNVERIFIED in every arm and
# contribute nothing to the comparison. Add "behaviour" here when running on a
# machine with FDR installed.
STAGES = ("concept", "dsml", "model")


def _present(run_dir: Path, stage: str) -> bool:
    return any((run_dir / n).is_file() for n in ARTEFACT[stage])


def score(root: Path, runner: str | None) -> tuple[list[dict], list[dict]]:
    per_run, summary = [], []
    for arm in ARMS:
        runs = sorted((root / arm).glob("run_*"))
        for d in runs:
            row = {"arm": arm, "run": d.name}
            tok = {}
            tp = d / "tokens.json"
            if tp.is_file():
                try:
                    tok = json.loads(tp.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass
            row["total_tokens"] = sum(
                int(v.get("input_tokens", 0)) + int(v.get("output_tokens", 0))
                for v in tok.values() if isinstance(v, dict))
            for stage in STAGES:
                reached = _present(d, stage)
                row[f"{stage}_reached"] = reached
                if not reached:
                    row[f"{stage}_pass"] = False
                    continue
                if stage == "dsml":
                    # verify_dsml prefers the OFFICIAL Emfatic parser when
                    # MALCOMj is built, but the pipeline deliberately emits
                    # package-less, class-only Emfatic, which that parser
                    # rejects (0/10 here) even though every artefact converts
                    # to Ecore and executes downstream (10/10). Scoring with
                    # the strict parser would report a generation failure that
                    # is really a notation-dialect mismatch, so use the
                    # pipeline's own converter — the check whose verdict
                    # actually governs whether the artefact is usable.
                    ok, _ = V._emfatic_converts(d / "result_dsml.emf")
                    row[f"{stage}_pass"] = bool(ok)
                else:
                    res = V.verify(stage, d, malcomj_runner=runner)
                    key = STRUCTURAL[stage]
                    c = next((x for x in res.checks if x.name == key), None)
                    row[f"{stage}_pass"] = bool(c and c.ok)
            per_run.append(row)

        rows = [r for r in per_run if r["arm"] == arm]
        if not rows:
            continue
        s = {"arm": arm, "n": len(rows)}
        for stage in STAGES:
            s[f"{stage}_reached"] = sum(r[f"{stage}_reached"] for r in rows)
            s[f"{stage}_pass"] = sum(r[f"{stage}_pass"] for r in rows)
        s["total_tokens_mean"] = (
            sum(r["total_tokens"] for r in rows) / len(rows))
        summary.append(s)
    return per_run, summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    ap.add_argument("--runner", default=os.environ.get("MALCOMJ_RUNNER"))
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args(argv)
    if args.runner is None:
        print("WARNING: no MALCOMj runner; the model-stage check cannot run.",
              file=sys.stderr)

    root = Path(args.root).resolve()
    per_run, summary = score(root, args.runner)
    if not per_run:
        raise SystemExit(f"no run directories under {root}")

    out = Path(args.out_dir) if args.out_dir else \
        REPO / "malcom.evaluation" / "metrics" / "results" / "rq2_control"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "cascade_per_run.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per_run[0]))
        w.writeheader()
        w.writerows(per_run)
    with (out / "cascade_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)

    hdr = f"{'arm':16}{'n':>4}"
    for stage in STAGES:
        hdr += f"{stage + ' pass':>16}"
    hdr += f"{'tokens':>10}"
    print("full cascade — each arm generates its own upstream artefacts")
    print(hdr)
    for s in summary:
        line = f"{s['arm']:16}{s['n']:>4}"
        for stage in STAGES:
            cell = f"{s[f'{stage}_pass']}/{s[f'{stage}_reached']}"
            line += f"{cell:>16}"
        line += f"{s['total_tokens_mean']:>10,.0f}"
        print(line)
    print("  (pass/reached — 'reached' counts runs that produced the artefact)")

    print()
    for stage in STAGES:
        print(f"  {stage}:")
        for hi, lo, what in (("single_repair", "single", "repair"),
                             ("multi", "single_repair", "decomposition"),
                             ("multi", "single", "both")):
            sh = next((x for x in summary if x["arm"] == hi), None)
            sl = next((x for x in summary if x["arm"] == lo), None)
            if not sh or not sl:
                continue
            a, b = sh[f"{stage}_pass"], sh["n"] - sh[f"{stage}_pass"]
            c, d = sl[f"{stage}_pass"], sl["n"] - sl[f"{stage}_pass"]
            p = fisher_exact_2x2(a, b, c, d)
            print(f"    {hi:14} vs {lo:14} ({what:14}) "
                  f"{a}/{sh['n']} vs {c}/{sl['n']}  p={p:.4f}")
    print(f"\nwrote {out}/cascade_per_run.csv, cascade_summary.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
