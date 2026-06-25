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
import logging
import os
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
    select_model,
)
import token_usage

logger = logging.getLogger(__name__)

# Multi-agent variant: the production stage class registered for each Layer.
MULTI_STAGES = {key: spec.cls for key, spec in LAYERS.items()}

VARIANTS = ("single", "multi")
DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.yaml"


def _list_available_models(config_path: Path) -> list[str]:
    return sorted((_load_config(config_path).get("models") or {}).keys())


def _run_single(stage: str, config_path: Path, run_dir: Path, client, config) -> Path | None:
    if stage not in SINGLE_STAGES:
        logger.warning("stage %s not registered for single-agent variant; skipping", stage)
        return None
    return run_stage_single_agent(stage, config_path, run_dir, client, config)


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
        client = _build_openai_client(config) if "single" in variants else None
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
                    t0 = time.monotonic()
                    try:
                        if variant == "single":
                            out = _run_single(stage, config_path, run_dir, client, config)
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
                        help="single (direct call), multi (full pipeline), or both")
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
