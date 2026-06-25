"""Single-agent baseline runner.

Reproduces the "Single Agent" configuration reported in paper §6 Table 1:
one direct OpenAI-compatible API call per stage, using the exact system
message that MALCOMp's *primary* agent for that stage was constructed with.

Prompts are loaded directly from `MALCOMp/phases/`, keeping one source of
truth for the pipeline and the single-agent baseline.

Usage:
    python run_single_agent.py                 # all stages, 1 run each
    python run_single_agent.py concept --n-runs 50
    python run_single_agent.py concept dsml model behaviour --n-runs 50

Output layout (under `output_dir/single_runs/`):
    single_<YYYYmmdd_HHMMSS>/
      result_concept_trace.json
      result_dsml.emf
      result_model.eol
      result_behaviour_model.rct
    single_<YYYYmmdd_HHMMSS>_auto2/
      ...

Each round gets its own timestamp-stamped folder (a unique run id), mirroring
the `output/runs/<run_id>/` convention used by the multi-agent pipeline.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline import LAYERS
import token_usage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stage registry for the single-agent baseline, derived from the one true
# LAYERS registry. Each entry carries what the single-call path needs:
#   - cls / config_key      : where to pull the primary system message + config
#   - primary_agent         : the generation agent whose system message we use
#   - output_kind/json_tag  : how to persist the single completion
#   - json_file/code_file   : output filename
# ---------------------------------------------------------------------------

STAGES = {
    key: {
        "cls":           spec.cls,
        "config_key":    spec.config_key,
        "primary_agent": spec.primary_agent.name,
        "output_kind":   spec.output_kind,
        "json_tag":      spec.json_tag,
        "json_file":     spec.json_file,
        "code_filename": spec.code_file,
    }
    for key, spec in LAYERS.items()
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config(config_path: Path) -> dict:
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def select_model(config: dict, key: str | None = None) -> str:
    """Collapse a `models:` map into config['model']. Returns the active key.

    `key` (e.g. from --model) wins, else config['default_model']. A config with a
    bare `model:` block is left untouched.
    """
    if "models" in config:
        key = (key or "").strip() or config.get("default_model")
        if not key:
            raise SystemExit("config defines 'models' but no default_model; pass --model")
        if key not in config["models"]:
            raise SystemExit(f"unknown model {key!r}; available: {sorted(config['models'])}")
        config["model"] = config["models"][key]
        return key
    return (config.get("model") or {}).get("name", "")


def _build_openai_client(config: dict):
    """Build the API client for the configured model.

    OpenAI-compatible providers (OpenAI, DeepSeek, Google's OpenAI endpoint, ...)
    return an OpenAI client; Anthropic returns an Anthropic client. Both are
    consumed by `_complete`, which dispatches on api_type.
    """
    from llm_keys import resolve_api_key
    api_type = config["model"].get("api_type", "openai")
    if api_type == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=resolve_api_key(config["model"]))
    base_url = os.environ.get("OPENAI_API_BASE", config["model"].get("api_base_url", ""))
    return OpenAI(api_key=resolve_api_key(config["model"]), base_url=base_url or None)


def _strip_fences(text: str) -> str:
    """Strip a leading/trailing markdown code fence (```json ... ```), which some
    models (e.g. Claude) wrap output in. Returns text unchanged if no fence."""
    import re
    t = (text or "").strip()
    m = re.match(r"^```[a-zA-Z0-9_+-]*\s*\n?(.*?)\n?```$", t, re.DOTALL)
    return m.group(1).strip() if m else t


def _complete(client, config: dict, system_message: str, user_message: str):
    """One direct completion -> (text, (input_tokens, output_tokens)).

    Dispatches on the model's api_type and omits the temperature parameter when
    the model sets `supports_temperature: false` (reasoning models like GPT-5).
    """
    use_temp = config["model"].get("supports_temperature", True)
    if config["model"].get("api_type", "openai") == "anthropic":
        kwargs = dict(
            model=_model_name(config),
            max_tokens=int(config["model"].get("max_tokens", 8192)),
            system=system_message,
            messages=[{"role": "user", "content": user_message}],
        )
        if use_temp:
            kwargs["temperature"] = _temperature(config)
        msg = client.messages.create(**kwargs)
        parts = [b.text for b in getattr(msg, "content", [])
                 if getattr(b, "type", "") == "text"]
        if not parts:
            raise RuntimeError(f"[{_model_name(config)}] empty Anthropic completion")
        return "".join(parts), token_usage.usage_from_completion(msg, "anthropic")
    # OpenAI-compatible
    kwargs = dict(
        model=_model_name(config),
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
    )
    if use_temp:
        kwargs["temperature"] = _temperature(config)
    if config["model"].get("max_tokens"):
        kwargs["max_tokens"] = int(config["model"]["max_tokens"])
    completion = client.chat.completions.create(**kwargs)
    # DeepSeek occasionally returns 200 OK with choices=None when overloaded.
    choices = getattr(completion, "choices", None) or []
    if not choices:
        fingerprint = getattr(completion, "system_fingerprint", "unknown")
        raise RuntimeError(
            f"[{_model_name(config)}] empty completion (choices is None/empty); "
            f"system_fingerprint={fingerprint}. Likely a transient provider issue; rerun."
        )
    return choices[0].message.content or "", token_usage.usage_from_completion(completion, "openai")


def _primary_system_message(stage_name: str, config_path: Path) -> str:
    """Instantiate the stage just to pull out the primary agent's
    system_message — never runs autogen, never makes an LLM call.
    """
    spec = STAGES[stage_name]
    stage_inst = spec["cls"](config_path=str(config_path))
    primary = spec["primary_agent"]
    for agent in stage_inst.agents:
        if agent.name == primary:
            return agent.system_message
    raise RuntimeError(
        f"primary agent {primary!r} not found in {spec['cls'].__name__} agents "
        f"{[a.name for a in stage_inst.agents]}"
    )


def case_study_dir(config: dict, config_dir: Path) -> Path:
    """Resolve case_studies/<case_study>/ (MALCOMP_CASE_STUDY env wins, then config)."""
    cs = os.environ.get("MALCOMP_CASE_STUDY", "").strip() or config.get("case_study")
    if not cs:
        raise SystemExit("no case study; set --case-study / MALCOMP_CASE_STUDY or config 'case_study'")
    return config_dir / "case_studies" / cs


def _load_requirements(config: dict, stage_name: str, config_dir: Path) -> list[dict]:
    """Load the requirement JSON the stage's config points at.

    Supports the three shapes accepted by MALCOMp's RequirementFeederAgent:
    {"requirements": [...]}, {"req": [...]}, or a bare list.
    """
    spec = STAGES[stage_name]
    stage_cfg = config["stages"][spec["config_key"]]
    req_path = case_study_dir(config, config_dir) / stage_cfg["requirement_file"]
    with req_path.open(encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict):
        if "requirements" in raw:
            return raw["requirements"]
        if "req" in raw:
            return raw["req"]
        raise ValueError(f"{req_path}: unsupported requirement JSON shape (keys={list(raw)})")
    if isinstance(raw, list):
        return raw
    raise ValueError(f"{req_path}: unsupported root type {type(raw).__name__}")


def _model_name(config: dict) -> str:
    return config["model"]["name"]


def _temperature(config: dict) -> float:
    return float(config["model"].get("temperature", 0.5))


# ---------------------------------------------------------------------------
# Per-stage single-agent run
# ---------------------------------------------------------------------------

def run_stage_single_agent(
    stage_name: str,
    config_path: Path,
    output_dir: Path,
    client: OpenAI,
    config: dict,
) -> Path:
    """Run one single-agent pass over all requirements for `stage_name`.

    Returns the path to the produced output file.
    """
    spec = STAGES[stage_name]
    output_dir.mkdir(parents=True, exist_ok=True)

    system_message = _primary_system_message(stage_name, config_path)
    requirements = _load_requirements(config, stage_name, config_path.parent)
    logger.info("[%s] %d requirements, primary=%s", stage_name, len(requirements), spec["primary_agent"])

    # Single-call architecture: feed all requirements at once as the user
    # message (this is what the legacy single_agent notebook does — see
    # `run_term_extraction` in auto_all_single_agent.ipynb).
    user_message = json.dumps(requirements, indent=2)
    raw, _usage = _complete(client, config, system_message, user_message)
    token_usage.record(output_dir, stage_name, _usage[0], _usage[1])

    # Persist
    if spec["output_kind"] == "json":
        # Wrap the raw text in the standard {tag: [...]} envelope so the
        # downstream MALCOMj transformations and the D5 metrics package can
        # consume the file unchanged. Flatten one level of nesting so
        # reasoning models that return list-per-requirement (e.g.
        # deepseek-reasoner emits `[[a,b], [c,d]]`) end up shaped the same
        # as chat models that return a flat list.
        try:
            parsed = json.loads(_strip_fences(raw))
            if isinstance(parsed, list):
                flat: list = []
                for item in parsed:
                    if isinstance(item, list):
                        flat.extend(item)
                    else:
                        flat.append(item)
                payload = flat
            else:
                payload = [parsed]
        except json.JSONDecodeError:
            logger.warning("[%s] response was not valid JSON; storing raw under %r tag",
                           stage_name, spec["json_tag"])
            payload = [{"raw_response": raw}]
        out_path = output_dir / spec["json_file"]
        out_path.write_text(
            json.dumps({spec["json_tag"]: payload}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    else:
        out_path = output_dir / spec["code_filename"]
        out_path.write_text(_strip_fences(raw), encoding="utf-8")

    logger.info("[%s] wrote %s (%d chars)", stage_name, out_path, len(raw))
    return out_path


def _update_manifest(
    run_dir: Path,
    run_id: str,
    config_path: Path,
    config: dict,
    stage_name: str,
    artifact_path: Path,
) -> None:
    """Write/update manifest.json inside the run folder (same shape as multi-agent runs)."""
    spec = STAGES[stage_name]
    stage_config_key = spec["config_key"]
    manifest_path = run_dir / "manifest.json"
    now = datetime.now(timezone.utc).isoformat()

    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
    else:
        manifest = {}

    manifest.setdefault("run_id", run_id)
    manifest.setdefault("variant", "single")
    manifest.setdefault("config_path", str(config_path.resolve()))
    manifest.setdefault("model", config.get("model", {}))
    manifest.setdefault("created_at", now)
    manifest["updated_at"] = now

    stages = manifest.setdefault("stages", {})
    stage_entry = stages.setdefault(
        stage_config_key,
        {"primary_agent": spec["primary_agent"], "artifacts": []},
    )
    stage_entry["primary_agent"] = spec["primary_agent"]

    artifact = {
        "file": artifact_path.name,
        "latest_path": str(artifact_path.resolve()),
        "archived_path": str(artifact_path.resolve()),
        "size": artifact_path.stat().st_size,
        "updated_at": now,
    }
    stage_entry["artifacts"] = [
        item for item in stage_entry.get("artifacts", [])
        if item.get("file") != artifact_path.name
    ]
    stage_entry["artifacts"].append(artifact)
    stage_entry["updated_at"] = now

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("[%s] updated manifest -> %s", stage_name, manifest_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stages", nargs="*", default=list(STAGES.keys()),
                        help=f"stages to run (any of {sorted(STAGES)}); default: all")
    parser.add_argument("--config", default="../config.yaml",
                        help="path to the root MALCOMp YAML config (default: ../config.yaml)")
    parser.add_argument("--output-dir",
                        help="root output dir (default: <config_dir>/output/single_runs)")
    parser.add_argument("--n-runs", type=int, default=1,
                        help="number of repeats (each run gets its own run_NNN/ subdir)")
    parser.add_argument("--model",
                        help="model key from the config's `models:` map (default: its default_model)")
    parser.add_argument("--case-study",
                        help="case study under case_studies/ (default: the config's case_study)")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    if args.case_study:
        os.environ["MALCOMP_CASE_STUDY"] = args.case_study

    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s",
                        datefmt="%H:%M:%S")
    load_dotenv()

    unknown = [s for s in args.stages if s not in STAGES]
    if unknown:
        raise SystemExit(f"Unknown stage(s): {unknown}. Known: {sorted(STAGES)}")

    config_path = Path(args.config).resolve()
    config = _load_config(config_path)
    select_model(config, args.model)
    out_root = Path(args.output_dir) if args.output_dir else (case_study_dir(config, config_path.parent) / "output" / "single_runs")

    client = _build_openai_client(config)

    for run_idx in range(1, args.n_runs + 1):
        # Each round goes into its own timestamp-stamped folder (unique run id).
        # The `_auto<idx>` suffix guarantees uniqueness when several runs land
        # within the same wall-clock second of a single invocation.
        run_id = f"single_{datetime.now():%Y%m%d_%H%M%S}"
        if args.n_runs > 1:
            run_id += f"_auto{run_idx}"
        run_dir = out_root / run_id
        logger.info("==== run %d/%d -> %s ====", run_idx, args.n_runs, run_dir)
        for stage in args.stages:
            out_path = run_stage_single_agent(stage, config_path, run_dir, client, config)
            _update_manifest(run_dir, run_id, config_path, config, stage, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
