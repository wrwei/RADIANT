"""Compute trace-link resolvability and requirement coverage for run outputs.

Example:
    cd /path/to/REMEDIATE
    python malcom.evaluation/metrics/traceability/compute.py

The default input root is case_studies/auv/output/runs; pass --runs-root to
score a different sweep layout (e.g. case_studies/auv/experiment/<model>/multi)
and --case-dir to point at the requirement set the runs were generated from.

Outputs (under metrics/results/traceability/ by default):
    traceability_per_run.csv   one row per run per layer
    traceability_summary.csv   link-weighted totals per layer
    traceability_report.md     the same, plus unresolved-link examples

No API key and no network access are needed: resolution is textual, using the
pipeline's own locators.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

try:
    from .metrics import (ARCHITECTURAL_LAYERS, LAYERS, aggregate,
                          load_requirements, score_run)
except ImportError:  # run as a script, from anywhere
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from metrics import (ARCHITECTURAL_LAYERS, LAYERS, aggregate,
                         load_requirements, score_run)


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNS_ROOT = REPO_ROOT / "case_studies" / "auv" / "output" / "runs"
DEFAULT_CASE_DIR = REPO_ROOT / "case_studies" / "auv"
DEFAULT_OUT_DIR = (REPO_ROOT / "malcom.evaluation" / "metrics" / "results"
                   / "traceability")

SUMMARY_FIELDS = ["layer", "runs", "runs_empty", "links_emitted", "links_resolved",
                  "resolvability", "instance_emitted", "instance_resolvability",
                  "typename_emitted", "typename_resolvability",
                  "coverage_mean", "coverage_min", "coverage_max",
                  "effective_coverage_mean", "recorded_agreement"]


def discover_runs(runs_root: Path, pattern: str = "*",
                  latest: int | None = None,
                  exclude_regex: str | None = None) -> list[Path]:
    """Run directories under `runs_root` holding at least one trace file."""
    trace_names = {n for spec in LAYERS for n in spec["trace"]}
    runs: list[Path] = []
    for run_dir in sorted(runs_root.glob(pattern)):
        if not run_dir.is_dir():
            continue
        if exclude_regex and re.search(exclude_regex, run_dir.name, re.IGNORECASE):
            continue
        if any((run_dir / n).is_file() for n in trace_names):
            runs.append(run_dir)
    if latest is not None:
        if latest <= 0:
            raise ValueError("--latest must be a positive integer")
        runs = runs[-latest:]
    return runs


def _fmt(v, nd=4):
    return "" if v is None else f"{v:.{nd}f}"


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def write_markdown(path: Path, runs: list[Path], per_run: list[dict],
                   summary: list[dict], scores_by_run) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Trace-link resolvability and requirement coverage",
        "",
        "*Resolvability* is the fraction of emitted links whose target element",
        "exists in the generated artefact; *coverage* is the fraction of",
        "requirements with at least one emitted link. The two are independent:",
        "`effective_coverage` (in the CSVs) is the stricter reading that counts",
        "only requirements whose link also resolves. Resolution uses the",
        "pipeline's own locators (`MALCOMp/trace_locator.py`), so these figures",
        "measure the same property the pipeline stamps as `source.resolved`.",
        "",
        f"Runs scored: **{len(runs)}**",
        "",
        "## Summary (link-weighted across runs)",
        "",
        "| Layer | Runs | Links | Resolved | Resolvability | Resolvability"
        " (named elements) | Coverage (mean) | Coverage (min-max) |"
        " Agreement with recorded `source.resolved` |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary:
        rng = ("" if r["coverage_min"] is None
               else f"{r['coverage_min']:.2f}-{r['coverage_max']:.2f}")
        inst = _fmt(r["instance_resolvability"])
        if r["typename_emitted"]:
            inst += f" ({r['instance_emitted']} links)"
        lines.append(
            f"| {r['layer']} | {r['runs']} | {r['links_emitted']} | "
            f"{r['links_resolved']} | {_fmt(r['resolvability'])} | "
            f"{inst or 'n/a'} | "
            f"{_fmt(r['coverage_mean'])} | {rng} | "
            f"{_fmt(r['recorded_agreement']) or 'n/a'} |")
    tn = next((r for r in summary if r["layer"] == "concept"), None)
    if tn and tn["typename_emitted"]:
        lines += [
            "",
            f"The concept layer emitted {tn['typename_emitted']} links naming a "
            f"metamodel **type** rather than a specific instance "
            f"(resolvability {_fmt(tn['typename_resolvability'], 3)}). A type "
            "name is normally written as prose in the requirement "
            '("Robotic Platform" for `RoboticPlatform`), so it does not resolve '
            "by identifier match. The *named elements* column excludes these; "
            "it is the figure comparable to the other layers.",
        ]

    lines += ["", "## Per run", "",
              "| Run | Layer | Links | Resolvability | Coverage | Artefact |",
              "|---|---|---:|---:|---:|---|"]
    for run, scores in zip(runs, scores_by_run):
        for s in scores:
            if not s.links_emitted and not s.trace_file:
                continue
            lines.append(
                f"| {run.name} | {s.layer} | {s.links_emitted} | "
                f"{_fmt(s.resolvability)} | {_fmt(s.coverage)} | "
                f"{s.artefact or '(missing)'} |")

    unresolved = [(run.name, s) for run, scores in zip(runs, scores_by_run)
                  for s in scores if s.unresolved_examples]
    if unresolved:
        lines += ["", "## Unresolved links (examples)", "",
                  "Each entry is `requirement:element` — a link whose target",
                  "was not found in the artefact.", ""]
        for name, s in unresolved[:40]:
            lines.append(f"- **{name}** / {s.layer}: "
                         + ", ".join(f"`{x}`" for x in s.unresolved_examples))

    empties = [(run.name, s.layer) for run, scores in zip(runs, scores_by_run)
               for s in scores if s.trace_file and not s.links_emitted]
    legacy = {s.legacy_tag for scores in scores_by_run for s in scores if s.legacy_tag}
    if legacy or empties:
        lines += ["", "## Warnings", ""]
    for name, layer in empties:
        lines.append(f"- **{name}** / {layer}: a trace file exists but emitted "
                     "no links (failed phase). Excluded from the coverage "
                     "average; see `runs_empty` in the summary.")
    if legacy:
        pass
        for tag in sorted(legacy):
            lines.append(f"- Trace files using the legacy tag `{tag}` were read; "
                         "those artefacts predate the current pipeline and "
                         "should be regenerated.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    ap.add_argument("--case-dir", default=str(DEFAULT_CASE_DIR),
                    help="case study holding requirements/ (for coverage)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--pattern", default="*", help="glob over run directories")
    ap.add_argument("--latest", type=int, default=None,
                    help="score only the N most recent runs")
    ap.add_argument("--exclude-regex", default=None)
    args = ap.parse_args(argv)

    runs_root = Path(args.runs_root)
    case_dir = Path(args.case_dir)
    out_dir = Path(args.out_dir)

    runs = discover_runs(runs_root, args.pattern, args.latest, args.exclude_regex)
    if not runs:
        raise SystemExit(f"no run directories with trace files under {runs_root}")
    requirements = load_requirements(case_dir)
    if not requirements:
        raise SystemExit(f"no requirements found under {case_dir / 'requirements'}")

    scores_by_run = [score_run(r, requirements) for r in runs]
    per_run_rows = [dict(run=run.name, **s.as_row())
                    for run, scores in zip(runs, scores_by_run) for s in scores]
    summary = aggregate(scores_by_run)

    write_csv(out_dir / "traceability_per_run.csv", per_run_rows,
              ["run"] + list(scores_by_run[0][0].as_row().keys()))
    write_csv(out_dir / "traceability_summary.csv", summary, SUMMARY_FIELDS)
    write_markdown(out_dir / "traceability_report.md", runs, per_run_rows,
                   summary, scores_by_run)

    print(f"scored {len(runs)} runs, {len(requirements)} requirements")
    for r in summary:
        extra = ""
        if r["typename_emitted"]:
            extra = (f"  [named elements only:"
                     f" {_fmt(r['instance_resolvability'], 3)}]")
        print(f"  {r['layer']:24} resolvability={_fmt(r['resolvability'], 3) or 'n/a':>6}"
              f"  coverage={_fmt(r['coverage_mean'], 3) or 'n/a':>6}"
              f"  ({r['links_resolved']}/{r['links_emitted']} links){extra}")
    print(f"per-run:  {out_dir / 'traceability_per_run.csv'}")
    print(f"summary:  {out_dir / 'traceability_summary.csv'}")
    print(f"report:   {out_dir / 'traceability_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
