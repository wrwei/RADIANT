"""Cross-model + cross-variant evaluation sweep for the MALCOMp pipeline.

Drives the Cartesian product reported in the paper's RQ1/RQ2:

    {model in config.yaml `models:` map} x {variant in {single, multi}}
    x {run in 1..N} x {stage in pipeline.LAYERS}

- `multi`  : instantiate the productised stage class (pipeline.LAYERS) and call
             .run() -- the full Multi-Agent LLM layer, the production code path.
- `single` : delegate to run_single_agent.run_stage_single_agent -- one direct
             OpenAI-compatible call per stage using that stage's *primary* agent
             system message (the Single-Agent baseline).

Output layout (under <output_root>):

    <variant>/result/<model>/run_<NNN>/result_concept_trace.json
                                       result_dsml.emf
                                       result_model.eol
                                       result_behaviour_model.rct

This matches what the deterministic metric drivers under
malcom.evaluation/metrics/ expect, so the metrics can score per-model
results without modification.

Usage:
    cd MALCOMp
    python run_evaluation.py --models gpt_4o deepseek_v3 \\
        --variants single multi --n-runs 50 \\
        --output-root ../malcom.evaluation/sweep

NOTE: this harness launches the sweep; it does NOT compute metrics. After a
sweep, run the per-stage drivers in malcom.evaluation/metrics/.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline import LAYERS
from run_single_agent import (
    STAGES as SINGLE_STAGES,
    _build_openai_client,
    _load_config,
    run_stage_single_agent,
    run_stage_single_agent_with_repair,
    select_model,
)
import token_usage

logger = logging.getLogger(__name__)

# Multi-agent variant: the production stage class registered for each Layer.
MULTI_STAGES = {key: spec.cls for key, spec in LAYERS.items()}

# single        one direct call per phase, no checking, no repair
# single_repair one direct call per phase PLUS the deterministic gate and the
#               same repair loop the multi-agent phases use — the control arm
#               that separates iterative repair from role decomposition
# multi         the full cooperating-agent pipeline
VARIANTS = ("single", "single_repair", "multi")
DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.yaml"


def _list_available_models(config_path: Path) -> list[str]:
    return sorted((_load_config(config_path).get("models") or {}).keys())


def _run_single(stage: str, config_path: Path, run_dir: Path, client, config) -> Path | None:
    if stage not in SINGLE_STAGES:
        logger.warning("stage %s not registered for single-agent variant; skipping", stage)
        return None
    return run_stage_single_agent(stage, config_path, run_dir, client, config)


def _run_single_repair(stage: str, config_path: Path, run_dir: Path, client,
                       config) -> Path | None:
    if stage not in SINGLE_STAGES:
        logger.warning("stage %s not registered for single-agent variant; skipping", stage)
        return None
    return run_stage_single_agent_with_repair(stage, config_path, run_dir,
                                              client, config)


def _run_multi(stage: str, config_path: Path, run_dir: Path, run_label: str) -> Path | None:
    if stage not in MULTI_STAGES:
        logger.warning("stage %s not registered for multi-agent variant; skipping", stage)
        return None
    run_dir.mkdir(parents=True, exist_ok=True)
    inst = MULTI_STAGES[stage](config_path=str(config_path), run_id=run_label)
    # Redirect the stage's artefacts into this run's directory.
    inst.output_dir = run_dir
    inst.run()
    in_tok, out_tok = token_usage.usage_from_agents(getattr(inst, "agents", []))
    token_usage.record(run_dir, stage, in_tok, out_tok)
    output_cfg = inst.stage_config.get("output", {})
    name = output_cfg.get("code_file") or output_cfg.get("json_file")
    return run_dir / name if name else None


def _instrument_commit() -> str | None:
    """The repo's HEAD commit, or None outside a git checkout."""
    try:
        out = subprocess.run(
            ["git", "-C", str(Path(__file__).resolve().parents[1]),
             "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def write_or_check_manifest(run_dir: Path, model: str, variant: str,
                            stage: str, config_path: Path) -> None:
    """Stamp the run directory with the arm that owns it; refuse a mismatch.

    A run directory's identity (which model, which variant) previously existed
    only in its PATH, so a sweep pointed at the wrong root — or a scoring pass
    over mixed directories — recorded or scored the wrong arm silently. The
    manifest makes the run directory self-describing, and this guard turns the
    silent wrong-arm write into a hard error. (Same failure class as a
    prompt-driven runner defaulting to another experiment's worktree: the
    capability to isolate arms is worthless if nothing checks it at the point
    of use.)
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    mf = run_dir / "run_manifest.json"
    if mf.is_file():
        try:
            m = json.loads(mf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as ex:
            raise SystemExit(f"unreadable run manifest {mf}: {ex}")
        owner = (m.get("model"), m.get("variant"))
        if owner != (model, variant):
            raise SystemExit(
                f"ARM MISMATCH: {run_dir} is owned by model={owner[0]!r} "
                f"variant={owner[1]!r} but this sweep is model={model!r} "
                f"variant={variant!r}. Refusing to record into another arm's "
                f"run directory — use a fresh --output-root or run number.")
    else:
        m = {
            "model": model,
            "variant": variant,
            "config": str(config_path),
            "instrument_commit": _instrument_commit(),
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "stages": [],
        }
    if stage not in m["stages"]:
        m["stages"].append(stage)
    mf.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")


def run_sweep(
    models: list[str],
    variants: list[str],
    stages: list[str],
    n_runs: int,
    output_root: Path,
    config_path: Path = DEFAULT_CONFIG,
    start_run: int = 1,
    fail_fast: bool = False,
) -> dict[tuple[str, str, int, str], Path | None]:
    """Run the Cartesian product. Returns {(model, variant, run, stage): path|None}.

    Each model is selected from the single root config's `models:` map via the
    MALCOMP_MODEL env var (read by the multi-agent stages) and select_model (for
    the single-agent variant). Failures are logged and the sweep continues
    (set fail_fast=True to stop).
    """
    results: dict[tuple[str, str, int, str], Path | None] = {}
    for model in models:
        os.environ["MALCOMP_MODEL"] = model
        config = _load_config(config_path)
        select_model(config, model)
        needs_client = any(v in ("single", "single_repair") for v in variants)
        client = _build_openai_client(config) if needs_client else None
        logger.info("==== model %s ====", model)
        for variant in variants:
            if variant not in VARIANTS:
                raise SystemExit(f"Unknown variant {variant!r}. Known: {VARIANTS}")
            variant_root = output_root / model / variant
            for run_idx in range(start_run, start_run + n_runs):
                run_dir = variant_root / f"run_{run_idx:03d}"
                run_label = f"{model}_{variant}_run_{run_idx:03d}"
                for stage in stages:
                    key = (model, variant, run_idx, stage)
                    write_or_check_manifest(run_dir, model, variant, stage,
                                            config_path)
                    t0 = time.monotonic()
                    try:
                        if variant == "single":
                            out = _run_single(stage, config_path, run_dir, client, config)
                        elif variant == "single_repair":
                            out = _run_single_repair(stage, config_path, run_dir,
                                                     client, config)
                        else:
                            out = _run_multi(stage, config_path, run_dir, run_label)
                        results[key] = out
                        logger.info("[%s/%s/run_%03d/%s] OK %.1fs -> %s",
                                    model, variant, run_idx, stage, time.monotonic() - t0, out)
                    except Exception as ex:  # noqa: BLE001 - sweep resilience
                        results[key] = None
                        logger.exception("[%s/%s/run_%03d/%s] FAILED after %.1fs: %s",
                                         model, variant, run_idx, stage, time.monotonic() - t0, ex)
                        if fail_fast:
                            raise
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--models", nargs="+", default=None,
                        help="model keys from the config's models: map (default: all of them)")
    parser.add_argument("--variants", nargs="+", default=["multi"], choices=list(VARIANTS),
                        help="single (direct call, no checking), single_repair "
                             "(direct call + gate + repair loop), multi (full "
                             "cooperating pipeline); any combination")
    parser.add_argument("--stages", nargs="+", default=list(LAYERS.keys()),
                        help=f"stages to run (any of {sorted(LAYERS)}); default: all")
    parser.add_argument("--n-runs", type=int, default=50, help="runs per (model, variant)")
    parser.add_argument("--start-run", type=int, default=1, help="run index to start from (resume)")
    parser.add_argument("--output-root", required=True,
                        help="root under which <variant>/result/<model>/run_NNN/ is created")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG),
                        help="path to the root config.yaml (holds the models: map)")
    parser.add_argument("--case-study", default=None,
                        help="case study under case_studies/ (default: the config's case_study)")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    if args.case_study:
        os.environ["MALCOMP_CASE_STUDY"] = args.case_study

    logging.basicConfig(level=args.log_level,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s",
                        datefmt="%H:%M:%S")
    load_dotenv()

    config_path = Path(args.config).resolve()
    models = args.models or _list_available_models(config_path)
    if not models:
        raise SystemExit(f"no models found in {config_path} (expected a models: map)")

    results = run_sweep(
        models=models,
        variants=args.variants,
        stages=args.stages,
        n_runs=args.n_runs,
        output_root=Path(args.output_root).resolve(),
        config_path=config_path,
        start_run=args.start_run,
        fail_fast=args.fail_fast,
    )
    n_ok = sum(1 for v in results.values() if v is not None)
    logger.info("done: %d/%d cells succeeded", n_ok, len(results))
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
