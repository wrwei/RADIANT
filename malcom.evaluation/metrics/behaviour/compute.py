"""Compute stage-specific metrics for generated RoboChart state machines."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

try:
    from .metrics import StateMachineScore, score_file
except ImportError:
    from metrics import StateMachineScore, score_file


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNS_ROOT = REPO_ROOT / "case_studies" / "auv" / "output" / "runs"
DEFAULT_REFERENCE = REPO_ROOT / "MALCOMj" / "src" / "main" / "resources" / "examples" / "auv" / "model" / "result_behaviour_model.rct"
DEFAULT_OUT_DIR = REPO_ROOT / "malcom.evaluation" / "metrics" / "results" / "behaviour"
SUMMARY_FIELDS = ["metric", "n", "mean", "std", "median", "min", "max"]


def discover_stm_files(runs_root: Path, pattern: str = "*", latest: int | None = None) -> list[Path]:
    files: list[Path] = []
    for run_dir in sorted(runs_root.glob(pattern)):
        if not run_dir.is_dir():
            continue
        path = run_dir / "result_behaviour_model.rct"
        if path.is_file():
            files.append(path)
    if latest is not None:
        if latest <= 0:
            raise ValueError("--latest must be a positive integer")
        files = files[-latest:]
    return files


def summarise(rows: list[StateMachineScore]) -> list[dict[str, object]]:
    metrics = [
        "syntax_ok",
        "state_f1",
        "initial_f1",
        "transition_id_f1",
        "transition_edge_f1",
        "behavior_micro_f1",
        "variable_f1",
        "constant_f1",
        "function_f1",
        "trigger_f1",
        "condition_f1",
        "action_f1",
        "detail_micro_f1",
        "full_micro_f1",
    ]
    out: list[dict[str, object]] = []
    for metric in metrics:
        values = [float(getattr(row, metric)) for row in rows]
        out.append({
            "metric": metric,
            "n": len(values),
            "mean": round(statistics.fmean(values), 4),
            "std": round(statistics.pstdev(values), 4) if len(values) > 1 else 0.0,
            "median": round(statistics.median(values), 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
        })
    return out


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[StateMachineScore], summary: list[dict[str, object]]) -> None:
    lines: list[str] = []
    lines.append("# State Machine Quality Evaluation")
    lines.append("")
    lines.append("Primary metric: `behavior_micro_f1` over initial nodes, states, and transition edges. Diagnostic metrics cover transition identifiers, variables, constants, functions, triggers, conditions, and actions.")
    lines.append("")
    lines.append("## Per-run Results")
    lines.append("")
    lines.append("| Run | Syntax | States | Transitions | State F1 | Edge F1 | Behavior Micro F1 | Detail Micro F1 | Full Micro F1 | Error |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for row in rows:
        lines.append(
            f"| {row.run_id} | {row.syntax_ok:.0f} | {row.pred_states}/{row.ref_states} | "
            f"{row.pred_transitions}/{row.ref_transitions} | {row.state_f1:.4f} | "
            f"{row.transition_edge_f1:.4f} | {row.behavior_micro_f1:.4f} | "
            f"{row.detail_micro_f1:.4f} | {row.full_micro_f1:.4f} | {row.error or '-'} |"
        )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | n | Mean | Std | Median | Min | Max |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for row in summary:
        lines.append(
            f"| {row['metric']} | {row['n']} | {row['mean']:.4f} | {row['std']:.4f} | "
            f"{row['median']:.4f} | {row['min']:.4f} | {row['max']:.4f} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--reference", default=str(DEFAULT_REFERENCE))
    parser.add_argument("--pattern", default="*")
    parser.add_argument("--latest", type=int, default=None)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args(argv)

    runs_root = Path(args.runs_root)
    reference = Path(args.reference)
    out_dir = Path(args.out_dir)
    files = discover_stm_files(runs_root, args.pattern, args.latest)
    if not files:
        raise SystemExit(f"no result_behaviour_model.rct files under {runs_root} with pattern {args.pattern!r}")
    if not reference.is_file():
        raise SystemExit(f"reference not found: {reference}")

    rows = [score_file(path, reference) for path in files]
    row_dicts = [row.as_row() for row in rows]
    summary = summarise(rows)
    write_csv(out_dir / "state_machine_quality_per_run.csv", row_dicts, list(row_dicts[0].keys()))
    write_csv(out_dir / "state_machine_quality_summary.csv", summary, SUMMARY_FIELDS)
    write_report(out_dir / "state_machine_quality_report.md", rows, summary)

    print(f"scored {len(rows)} state-machine files")
    print(f"per-run: {out_dir / 'state_machine_quality_per_run.csv'}")
    print(f"summary: {out_dir / 'state_machine_quality_summary.csv'}")
    print(f"report:  {out_dir / 'state_machine_quality_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
