"""Compute stage-specific Emfatic/DSML metrics for MALCOMp run outputs."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

try:
    from .metrics import EmfaticQuality, Match, load_aliases, score_files
    from .syntax_checker import EmfaticSyntaxChecker
except ImportError:
    from metrics import EmfaticQuality, Match, load_aliases, score_files
    from syntax_checker import EmfaticSyntaxChecker


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNS_ROOT = REPO_ROOT / "case_studies" / "auv" / "output" / "runs"
DEFAULT_REFERENCE = (
    REPO_ROOT
    / "malcom.evaluation"
    / "reference_models"
    / "auv_independent_expert_20260612"
    / "result_dsml.emf"
)
DEFAULT_ALIASES = Path(__file__).resolve().parent / "aliases_auv.json"
DEFAULT_OUT_DIR = REPO_ROOT / "malcom.evaluation" / "metrics" / "results" / "dsml"


def discover_emfatic_files(runs_root: Path, pattern: str = "*") -> list[Path]:
    files: list[Path] = []
    for run_dir in sorted(runs_root.glob(pattern)):
        if not run_dir.is_dir():
            continue
        path = run_dir / "result_dsml.emf"
        if path.is_file():
            files.append(path)
    return files


def summarise(rows: list[EmfaticQuality]) -> list[dict[str, object]]:
    metrics = [
        "syntax_ok",
        "syntax_error_count",
        "syntax_warning_count",
        "parse_ok",
        "class_precision",
        "class_recall",
        "class_f1",
        "attr_precision",
        "attr_recall",
        "attr_f1",
        "ref_precision",
        "ref_recall",
        "ref_f1",
        "macro_f1",
        "weighted_f1",
        "conditional_weighted_f1",
        "end_to_end_weighted_f1",
    ]
    out: list[dict[str, object]] = []
    for metric in metrics:
        values = [float(value) for row in rows if (value := getattr(row, metric)) is not None]
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


def write_report(path: Path, rows: list[EmfaticQuality], summary: list[dict[str, object]]) -> None:
    lines: list[str] = []
    lines.append("# Emfatic DSML Quality Evaluation")
    lines.append("")
    lines.append("Automated matching uses exact/canonical equality, an auditable alias table, and conservative fuzzy matching for partial matches.")
    lines.append("Syntactic validity is determined by the official Eclipse Emfatic parser. Conditional F1 excludes syntax-invalid outputs; end-to-end F1 assigns them zero.")
    lines.append("")
    lines.append("## Per-run Results")
    lines.append("")
    lines.append("| Run | Syntax | Errors | Warnings | Structural Parse | Class F1 | Attr F1 | Ref F1 | Weighted F1 | End-to-end F1 | Classes P/R | Attrs P/R | Refs P/R | Extra Classes | Missing Classes |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for row in rows:
        lines.append(
            f"| {row.run_id} | {row.syntax_ok:.0f} | {row.syntax_error_count} | {row.syntax_warning_count} | "
            f"{row.parse_ok:.0f} | {row.class_f1:.4f} | {row.attr_f1:.4f} | "
            f"{row.ref_f1:.4f} | {row.weighted_f1:.4f} | {row.end_to_end_weighted_f1:.4f} | "
            f"{row.pred_classes}/{row.ref_classes} | {row.pred_attrs}/{row.ref_attrs} | "
            f"{row.pred_refs}/{row.ref_refs} | {row.extra_classes or '-'} | {row.missing_classes or '-'} |"
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
    parser.add_argument("--aliases", default=str(DEFAULT_ALIASES))
    parser.add_argument("--fuzzy-threshold", type=float, default=0.88)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--java", help="Java executable used for EmfaticHelper")
    parser.add_argument("--emfatic-helper-classpath", help="Explicit classpath for org.sawg.malcomj.EmfaticHelper")
    parser.add_argument("--gradle-user-home", help="Gradle user home used to discover cached Emfatic dependencies")
    args = parser.parse_args(argv)

    runs_root = Path(args.runs_root)
    reference = Path(args.reference)
    out_dir = Path(args.out_dir)
    aliases = load_aliases(Path(args.aliases)) if args.aliases else {"classes": {}, "features": {}, "types": {}}
    files = discover_emfatic_files(runs_root, args.pattern)
    if not files:
        raise SystemExit(f"no result_dsml.emf files under {runs_root}")

    syntax_checker = EmfaticSyntaxChecker(
        REPO_ROOT,
        java=args.java,
        classpath=args.emfatic_helper_classpath,
        gradle_user_home=Path(args.gradle_user_home) if args.gradle_user_home else None,
    )
    reference_syntax = syntax_checker.check(reference)
    if not reference_syntax.syntax_ok:
        raise SystemExit(f"reference Emfatic is syntax-invalid: {reference_syntax.error_summary}")

    rows: list[EmfaticQuality] = []
    match_rows: list[dict[str, object]] = []
    for path in files:
        syntax = syntax_checker.check(path)
        quality, matches = score_files(
            path,
            reference,
            aliases=aliases,
            fuzzy_threshold=args.fuzzy_threshold,
            syntax_ok=syntax.syntax_ok,
            syntax_error_count=syntax.error_count,
            syntax_warning_count=syntax.warning_count,
            syntax_error=syntax.error_summary,
        )
        rows.append(quality)
        for match in matches:
            match_rows.append({
                "run_id": quality.run_id,
                "kind": match.kind,
                "pred": match.pred,
                "ref": match.ref,
                "score": match.score,
                "reason": match.reason,
            })

    row_dicts = [row.as_row() for row in rows]
    summary = summarise(rows)
    write_csv(out_dir / "emfatic_quality_per_run.csv", row_dicts, list(row_dicts[0].keys()))
    write_csv(out_dir / "emfatic_quality_summary.csv", summary, ["metric", "n", "mean", "std", "median", "min", "max"])
    if match_rows:
        write_csv(out_dir / "emfatic_quality_matches.csv", match_rows, ["run_id", "kind", "pred", "ref", "score", "reason"])
    write_report(out_dir / "emfatic_quality_report.md", rows, summary)

    print(f"scored {len(rows)} Emfatic files")
    print(f"report: {out_dir / 'emfatic_quality_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
