"""Compute term-extraction metrics for MALCOMp run outputs.

Example:
    cd E:/REMEDIATE
    python compute.py

The default input root is case_studies/auv/output/runs and the default
reference is reference_models/auv_independent_expert_20260612/result_concept_extraction.json.
"""

from __future__ import annotations

import argparse
import csv
import re
import statistics
import sys
from pathlib import Path

try:
    from .metrics import TermMetrics, load_aliases, score_file
except ImportError:
    from metrics import TermMetrics, load_aliases, score_file


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNS_ROOT = REPO_ROOT / "case_studies" / "auv" / "output" / "runs"
DEFAULT_REFERENCE = (
    REPO_ROOT
    / "malcom.evaluation"
    / "reference_models"
    / "auv_independent_expert_20260612"
    / "result_concept_extraction.json"
)
DEFAULT_ALIASES = Path(__file__).resolve().parent / "aliases_auv.json"
DEFAULT_OUT_DIR = REPO_ROOT / "malcom.evaluation" / "metrics" / "results" / "concept"


SUMMARY_FIELDS = [
    "metric",
    "n",
    "mean",
    "std",
    "median",
    "min",
    "max",
]


def discover_term_files(
    runs_root: Path,
    pattern: str = "*",
    latest: int | None = None,
    exclude_regex: str | None = None,
) -> list[Path]:
    files: list[Path] = []
    for run_dir in sorted(runs_root.glob(pattern)):
        if not run_dir.is_dir():
            continue
        if exclude_regex and re.search(exclude_regex, run_dir.name, re.IGNORECASE):
            continue
        path = run_dir / "result_concept_trace.json"
        if path.is_file():
            files.append(path)
    if latest is not None:
        if latest <= 0:
            raise ValueError("--latest must be a positive integer")
        files = files[-latest:]
    return files


def summarise(rows: list[TermMetrics]) -> list[dict[str, object]]:
    metrics = {
        "valid_json": "valid_json",
        "schema_valid": "schema_valid",
        "valid_entry_ratio": "valid_entry_ratio",
        "duplicate_rate": "duplicate_rate",
        "dedup_vocabulary_precision": "dedup_vocabulary_precision",
        "dedup_vocabulary_recall": "dedup_vocabulary_recall",
        "dedup_vocabulary_f1": "dedup_vocabulary_f1",
        "requirement_linked_micro_precision": "requirement_linked_micro_precision",
        "requirement_linked_micro_recall": "requirement_linked_micro_recall",
        "requirement_linked_micro_f1": "requirement_linked_micro_f1",
        "requirement_linked_macro_f1": "requirement_linked_macro_f1",
        "requirement_linked_exact_match_rate": "requirement_linked_exact_match_rate",
        "requirement_linked_hallucination_rate": "requirement_linked_hallucination_rate",
        "requirement_linked_omission_rate": "requirement_linked_omission_rate",
        "concept_precision": "concept_precision",
        "concept_recall": "concept_recall",
        "concept_f1": "concept_f1",
        "instance_precision": "instance_precision",
        "instance_recall": "instance_recall",
        "instance_f1": "instance_f1",
        "typed_instance_precision": "typed_instance_precision",
        "typed_instance_recall": "typed_instance_recall",
        "typed_instance_f1": "typed_instance_f1",
        "instance_type_precision": "instance_type_precision",
        "instance_type_recall": "instance_type_recall",
        "instance_type_f1": "instance_type_f1",
        "term_structural_precision": "tuple_precision",
        "term_structural_recall": "tuple_recall",
        "term_structural_f1": "tuple_f1",
        "field_gid_f1": "field_gid_f1",
        "field_concept_f1": "field_concept_f1",
        "field_instance_f1": "field_instance_f1",
        "field_instance_of_f1": "field_instance_of_f1",
        "term_field_f1": "field_macro_f1",
        "term_alias_precision": "alias_precision",
        "term_alias_recall": "alias_recall",
        "term_alias_f1": "alias_f1",
        "dedup_term_structural_precision": "dedup_tuple_precision",
        "dedup_term_structural_recall": "dedup_tuple_recall",
        "dedup_term_structural_f1": "dedup_tuple_f1",
        "dedup_term_field_f1": "dedup_field_macro_f1",
        "dedup_term_alias_precision": "dedup_alias_precision",
        "dedup_term_alias_recall": "dedup_alias_recall",
        "dedup_term_alias_f1": "dedup_alias_f1",
    }
    out: list[dict[str, object]] = []
    for metric, attribute in metrics.items():
        values = [float(getattr(row, attribute)) for row in rows]
        if not values:
            continue
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


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, per_run: list[TermMetrics], summary: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Term Extraction Evaluation")
    lines.append("")
    lines.append("Primary metric: deduplicated vocabulary micro F1. Key secondary metrics cover requirement linkage, per-GID performance, exact-set matches, and typed relations.")
    lines.append("")
    lines.append("## Per-run Results")
    lines.append("")
    lines.append("| Run | Vocabulary F1 | Linked Micro F1 | Per-GID Macro F1 | Exact GID Rate | Typed Instance F1 | Instance-Type F1 | Hallucination | Omission |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in per_run:
        lines.append(
            f"| {row.run_id} | {row.dedup_vocabulary_f1:.4f} | "
            f"{row.requirement_linked_micro_f1:.4f} | {row.requirement_linked_macro_f1:.4f} | "
            f"{row.requirement_linked_exact_match_rate:.4f} | {row.typed_instance_f1:.4f} | "
            f"{row.instance_type_f1:.4f} | {row.requirement_linked_hallucination_rate:.4f} | "
            f"{row.requirement_linked_omission_rate:.4f} |"
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
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--reference", default=str(DEFAULT_REFERENCE))
    parser.add_argument("--pattern", default="*", help="run directory glob, e.g. 'web_*_auto*'")
    parser.add_argument("--exclude-regex", default=None, help="case-insensitive run-directory exclusion regex")
    parser.add_argument("--latest", type=int, default=None, help="score only the latest N run directories by name")
    parser.add_argument("--aliases", default=str(DEFAULT_ALIASES), help="auditable alias-table JSON")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args(argv)

    runs_root = Path(args.runs_root)
    reference = Path(args.reference)
    out_dir = Path(args.out_dir)
    aliases = load_aliases(Path(args.aliases)) if args.aliases else {}

    files = discover_term_files(runs_root, args.pattern, args.latest, args.exclude_regex)
    if not files:
        raise SystemExit(f"no result_concept_trace.json files under {runs_root} with pattern {args.pattern!r}")
    if not reference.is_file():
        raise SystemExit(f"reference not found: {reference}")

    per_run = [score_file(path, reference, aliases=aliases) for path in files]
    summary = summarise(per_run)

    per_run_rows = [row.as_row() for row in per_run]
    per_run_fields = list(per_run_rows[0].keys())
    write_csv(out_dir / "term_extraction_per_run.csv", per_run_rows, per_run_fields)
    write_csv(out_dir / "term_extraction_summary.csv", summary, SUMMARY_FIELDS)
    write_markdown(out_dir / "term_extraction_report.md", per_run, summary)

    print(f"scored {len(per_run)} runs")
    print(f"per-run:  {out_dir / 'term_extraction_per_run.csv'}")
    print(f"summary:  {out_dir / 'term_extraction_summary.csv'}")
    print(f"report:   {out_dir / 'term_extraction_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
