"""Evaluate model creation against each run's generated DSL metamodel.

For each run, this script:
1. converts `result_dsml.emf` to a generated `.ecore`;
2. executes the same run's `result_model.eol` against that `.ecore`;
3. scores the resulting `.model` against the expert `AUV.model` using
   alias-aware object/attribute/link facts.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
import sys
from pathlib import Path

try:
    from .emfatic_to_ecore import convert_file
    from .metrics import ModelScore, load_aliases, score_generated
except ImportError:
    from emfatic_to_ecore import convert_file
    from metrics import ModelScore, load_aliases, score_generated


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNS_ROOT = REPO_ROOT / "case_studies" / "auv" / "output" / "runs"
DEFAULT_REFERENCE = (
    REPO_ROOT
    / "malcom.evaluation"
    / "reference_models"
    / "auv_independent_expert_20260612"
    / "result_AUV.model"
)
DEFAULT_ALIASES = Path(__file__).resolve().parent / "aliases_auv.json"
DEFAULT_OUT_DIR = REPO_ROOT / "malcom.evaluation" / "metrics" / "results" / "model"

SUMMARY_FIELDS = ["metric", "n", "mean", "std", "median", "min", "max"]


def find_default_runner() -> Path:
    candidates = [
        REPO_ROOT / "MALCOMj" / "build" / "install" / "MALCOMj" / "bin" / "MALCOMj.bat",
        REPO_ROOT / ".codex-run" / "malcomj-runner" / "bin" / "MALCOMj.bat",
        REPO_ROOT / "MALCOMj" / "build" / "scripts" / "MALCOMj.bat",
    ]
    for runner in candidates:
        try:
            distribution_jar = runner.parent.parent / "lib" / "MALCOMj.jar"
            if runner.is_file() and distribution_jar.is_file():
                return runner
        except OSError:
            continue
    return candidates[0]


DEFAULT_RUNNER = find_default_runner()


def discover_run_dirs(runs_root: Path, pattern: str = "*", latest: int | None = None) -> list[Path]:
    run_dirs = [
        path for path in sorted(runs_root.glob(pattern))
        if path.is_dir() and (path / "result_dsml.emf").is_file() and (path / "result_model.eol").is_file()
    ]
    if latest is not None:
        if latest <= 0:
            raise ValueError("--latest must be a positive integer")
        run_dirs = run_dirs[-latest:]
    return run_dirs


def short_error(text: str, limit: int = 220) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("Exception") or "Property '" in line or "Parse errors" in line:
            return line[:limit]
    return (lines[-1] if lines else "")[:limit]


def _emf_runtime_spec(model_path: Path, metamodel: Path) -> str:
    """Build --emf spec with absolute forward-slash paths (Windows-safe)."""
    model = model_path.resolve().as_posix()
    meta = metamodel.resolve().as_posix()
    return f"M={model};{meta};readOnLoad=false,storeOnDisposal=true"


def execute_eol(runner: Path, eol_path: Path, model_path: Path, metamodel: Path) -> subprocess.CompletedProcess[str]:
    distribution_jar = runner.parent.parent / "lib" / "MALCOMj.jar"
    if not runner.is_file() or not distribution_jar.is_file():
        raise FileNotFoundError(
            f"invalid MALCOMj distribution: expected {runner} and {distribution_jar}"
        )
    model_path.parent.mkdir(parents=True, exist_ok=True)
    spec = _emf_runtime_spec(model_path, metamodel)
    return subprocess.run(
        [str(runner), "--script", str(eol_path), "--emf", spec],
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )


def empty_score(run_id: str, source_kind: str, error: str) -> ModelScore:
    return ModelScore(
        run_id=run_id,
        source_kind=source_kind,
        parse_ok=0.0,
        pred_object_facts=0,
        ref_object_facts=0,
        pred_attribute_facts=0,
        ref_attribute_facts=0,
        pred_link_facts=0,
        ref_link_facts=0,
        object_precision=0.0,
        object_recall=0.0,
        object_f1=0.0,
        attribute_precision=0.0,
        attribute_recall=0.0,
        attribute_f1=0.0,
        link_precision=0.0,
        link_recall=0.0,
        link_f1=0.0,
        micro_precision=0.0,
        micro_recall=0.0,
        micro_f1=0.0,
        macro_f1=0.0,
        error=error,
    )


def summarise(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    metrics = [
        "ecore_ok",
        "execution_ok",
        "model_exists",
        "object_f1",
        "attribute_f1",
        "link_f1",
        "micro_f1",
        "macro_f1",
        "end_to_end_micro_f1",
        "end_to_end_macro_f1",
    ]
    out: list[dict[str, object]] = []
    for metric in metrics:
        values = [float(row[metric]) for row in rows]
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


def write_report(path: Path, rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    lines: list[str] = []
    lines.append("# AUV Model Instance Evaluation Using Generated DSLs")
    lines.append("")
    lines.append("Each run's `result_dsml.emf` is converted to `.ecore`; the same run's EOL program is executed against that generated metamodel; the resulting `.model` is scored against the expert reference model with alias-aware facts.")
    lines.append("")
    lines.append("## Per-run Results")
    lines.append("")
    lines.append("| Run | Ecore | Exec | Model | Object F1 | Attribute F1 | Link F1 | Micro F1 | E2E Micro F1 | Error |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for row in rows:
        lines.append(
            f"| {row['run_id']} | {row['ecore_ok']:.0f} | {row['execution_ok']:.0f} | {row['model_exists']:.0f} | "
            f"{row['object_f1']:.4f} | {row['attribute_f1']:.4f} | {row['link_f1']:.4f} | "
            f"{row['micro_f1']:.4f} | {row['end_to_end_micro_f1']:.4f} | {row['error'] or '-'} |"
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


def score_run(run_dir: Path, runner: Path, reference: Path, aliases: dict[str, dict[str, str]], out_dir: Path) -> dict[str, object]:
    run_id = run_dir.name
    emf_path = run_dir / "result_dsml.emf"
    eol_path = run_dir / "result_model.eol"

    # Always rebuild and execute from this run's generated Emfatic and EOL.
    run_out = out_dir / "generated_artifacts" / run_id
    ecore_path = run_out / "generated.ecore"
    model_path = run_out / "AUV.model"

    ecore_ok = False
    try:
        convert_file(emf_path, ecore_path)
        ecore_ok = True
    except Exception as ex:
        score = empty_score(run_id, "generated_dsl_model_xml", f"emfatic_to_ecore: {ex}")
        result = None

    if ecore_ok:
        result = execute_eol(runner, eol_path, model_path, ecore_path)
        execution_ok = result.returncode == 0 and model_path.is_file()
        error = "" if execution_ok else short_error(result.stderr + "\n" + result.stdout)
        score = score_generated(model_path, reference, aliases, source_kind="generated_dsl_model_xml") if execution_ok else empty_score(run_id, "generated_dsl_model_xml", error)
    else:
        execution_ok = False
        error = score.error

    model_exists = model_path.is_file()
    row = score.as_row()
    row.update({
        "run_id": run_id,
        "ecore_ok": 1.0 if ecore_ok else 0.0,
        "execution_ok": 1.0 if execution_ok else 0.0,
        "model_exists": 1.0 if model_exists else 0.0,
        "exit_code": result.returncode if result is not None else "",
        "emf_path": str(emf_path),
        "ecore_path": str(ecore_path),
        "model_path": str(model_path),
        "end_to_end_micro_f1": score.micro_f1 if execution_ok else 0.0,
        "end_to_end_macro_f1": score.macro_f1 if execution_ok else 0.0,
        "error": error or score.error,
    })
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--reference", default=str(DEFAULT_REFERENCE))
    parser.add_argument("--runner", default=str(DEFAULT_RUNNER))
    parser.add_argument("--pattern", default="*")
    parser.add_argument("--latest", type=int, default=None)
    parser.add_argument("--aliases", default=str(DEFAULT_ALIASES))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args(argv)

    runs_root = Path(args.runs_root)
    reference = Path(args.reference)
    runner = Path(args.runner)
    out_dir = Path(args.out_dir)
    aliases = load_aliases(Path(args.aliases)) if args.aliases else {"classes": {}, "features": {}, "values": {}}

    for required in [reference, runner]:
        if not required.exists():
            raise SystemExit(f"required file not found: {required}")
    run_dirs = discover_run_dirs(runs_root, args.pattern, args.latest)
    if not run_dirs:
        raise SystemExit(f"no runs with result_dsml.emf and result_model.eol under {runs_root}")

    rows = [score_run(run_dir, runner, reference, aliases, out_dir) for run_dir in run_dirs]
    summary = summarise(rows)
    fieldnames = [
        "run_id", "ecore_ok", "execution_ok", "model_exists", "exit_code", "source_kind",
        "parse_ok", "object_precision", "object_recall", "object_f1",
        "attribute_precision", "attribute_recall", "attribute_f1",
        "link_precision", "link_recall", "link_f1",
        "micro_precision", "micro_recall", "micro_f1", "macro_f1",
        "end_to_end_micro_f1", "end_to_end_macro_f1",
        "pred_object_facts", "ref_object_facts", "pred_attribute_facts", "ref_attribute_facts",
        "pred_link_facts", "ref_link_facts", "emf_path", "ecore_path", "model_path", "error",
    ]
    write_csv(out_dir / "model_instance_generated_dsl_quality_per_run.csv", rows, fieldnames)
    write_csv(out_dir / "model_instance_generated_dsl_quality_summary.csv", summary, SUMMARY_FIELDS)
    write_report(out_dir / "model_instance_generated_dsl_quality_report.md", rows, summary)

    print(f"scored {len(rows)} runs using generated DSLs")
    print(f"ecore conversions: {sum(float(row['ecore_ok']) for row in rows):.0f}/{len(rows)}")
    print(f"execution successes: {sum(float(row['execution_ok']) for row in rows):.0f}/{len(rows)}")
    print(f"per-run: {out_dir / 'model_instance_generated_dsl_quality_per_run.csv'}")
    print(f"summary: {out_dir / 'model_instance_generated_dsl_quality_summary.csv'}")
    print(f"report:  {out_dir / 'model_instance_generated_dsl_quality_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
