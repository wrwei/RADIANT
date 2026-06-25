"""Unified entry point for the MALCOMp pipeline."""
import argparse
import logging
import sys
import os
from datetime import datetime

# Ensure the MALCOMp directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import LAYERS

STAGES = {key: spec.cls for key, spec in LAYERS.items()}


def gate_ok(result) -> bool:
    """True if the phase may unlock the next one (no result == not gated)."""
    return result is None or result.passed


def main():
    parser = argparse.ArgumentParser(
        description="MALCOMp — Multi-Agent LLM pipeline for Model-Driven Engineering"
    )
    parser.add_argument(
        "stages",
        nargs="*",
        default=list(STAGES.keys()),
        choices=list(STAGES.keys()),
        help="Pipeline stages to run (default: all in order)",
    )
    parser.add_argument(
        "--config",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.yaml"),
        help="Path to the root config.yaml (default: ../config.yaml)",
    )
    parser.add_argument(
        "--model",
        default="",
        help="Model key from the config's `models:` map (default: its default_model).",
    )
    parser.add_argument(
        "--case-study",
        default="",
        help="Case study under case_studies/ to run (default: the config's case_study).",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of times to repeat term extraction (only applies to 'term' stage)",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Archive run id. Defaults to timestamped pipeline_<YYYYmmdd_HHMMSS>.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.model:
        os.environ["MALCOMP_MODEL"] = args.model
    if args.case_study:
        os.environ["MALCOMP_CASE_STUDY"] = args.case_study

    run_id = args.run_id or f"pipeline_{datetime.now():%Y%m%d_%H%M%S}"
    os.environ["MALCOMP_RUN_ID"] = run_id
    logging.info("Archiving artefacts under output/runs/%s", run_id)

    for stage_name in args.stages:
        logging.info("Running stage: %s", stage_name)
        spec = LAYERS[stage_name]
        stage = spec.cls(config_path=args.config, run_id=run_id)

        if spec.repeatable and args.repeat > 1:
            stage.run_multiple(args.repeat)
        else:
            stage.run()
        stage.archive_configured_outputs()

        if not gate_ok(getattr(stage, "verification_result", None)):
            r = stage.verification_result
            print(
                f"\nPhase '{stage_name}' verification FAILED — stopping before the "
                f"next phase:\n{r.summary()}",
                file=sys.stderr,
            )
            raise SystemExit(2)

        logging.info("Completed stage: %s", stage_name)


if __name__ == "__main__":
    main()
