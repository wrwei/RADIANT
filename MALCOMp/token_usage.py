"""Per-run LLM token-usage capture + cost aggregation for evaluation sweeps.

Each generation writes/updates a ``tokens.json`` in its run directory:

    {"<stage>": {"input_tokens": N, "output_tokens": M}, ...}

- single-agent: usage comes from the OpenAI/Anthropic completion's ``usage``.
- multi-agent : usage comes from AutoGen's ``gather_usage_summary(agents)``.

``aggregate()`` sums these across a sweep; ``cost_usd()`` applies a per-model
price table to turn tokens into dollars.
"""
from __future__ import annotations

import json
from pathlib import Path

# Approximate USD per 1M tokens, (input, output), keyed by the model's API name.
# VERIFY against current provider pricing before quoting in the paper.
PRICES: dict[str, tuple[float, float]] = {
    "deepseek-chat":   (0.27, 1.10),
    "deepseek-v4-pro": (0.27, 1.10),
    "claude-opus-4-8": (15.0, 75.0),
    "gpt-5":           (1.25, 10.0),
    "gemini-2.5-pro":  (1.25, 10.0),
}


def record(run_dir, stage: str, input_tokens, output_tokens) -> None:
    """Accumulate token usage for a stage into ``run_dir/tokens.json``."""
    p = Path(run_dir) / "tokens.json"
    data: dict = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    cur = data.get(stage, {"input_tokens": 0, "output_tokens": 0})
    cur["input_tokens"] = int(cur.get("input_tokens", 0)) + int(input_tokens or 0)
    cur["output_tokens"] = int(cur.get("output_tokens", 0)) + int(output_tokens or 0)
    data[stage] = cur
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def usage_from_completion(completion, api_type: str) -> tuple[int, int]:
    """(input, output) tokens from a single OpenAI/Anthropic completion object."""
    u = getattr(completion, "usage", None)
    if u is None:
        return 0, 0
    if api_type == "anthropic":
        return (int(getattr(u, "input_tokens", 0) or 0),
                int(getattr(u, "output_tokens", 0) or 0))
    return (int(getattr(u, "prompt_tokens", 0) or 0),
            int(getattr(u, "completion_tokens", 0) or 0))


def usage_from_agents(agents) -> tuple[int, int]:
    """(input, output) tokens summed across an AutoGen multi-agent group chat."""
    try:
        from autogen import gather_usage_summary
        summ = gather_usage_summary(list(agents)) or {}
    except Exception:
        return 0, 0
    block = summ.get("usage_including_cached_inference", {}) or {}
    in_tok = out_tok = 0
    for _k, v in block.items():
        if isinstance(v, dict):
            in_tok += int(v.get("prompt_tokens", 0) or 0)
            out_tok += int(v.get("completion_tokens", 0) or 0)
    return in_tok, out_tok


def cost_usd(input_tokens: int, output_tokens: int, model_name: str) -> float | None:
    """Dollar cost for the given tokens, or None if the model isn't priced."""
    price = PRICES.get(model_name)
    if price is None:
        return None
    pin, pout = price
    return (input_tokens / 1_000_000) * pin + (output_tokens / 1_000_000) * pout


def aggregate(output_root) -> dict[tuple[str, str], dict]:
    """Sum every ``tokens.json`` under a sweep root.

    Returns {(variant, model_key): {input_tokens, output_tokens, runs}} for paths
    shaped ``<root>/<model_key>/<variant>/run_NNN/tokens.json``.
    """
    output_root = Path(output_root)
    out: dict[tuple[str, str], dict] = {}
    for tok in output_root.rglob("tokens.json"):
        rel = tok.relative_to(output_root).parts
        if len(rel) < 4:
            continue
        model_key, variant = rel[0], rel[1]
        try:
            data = json.loads(tok.read_text(encoding="utf-8"))
        except Exception:
            continue
        agg = out.setdefault((variant, model_key),
                             {"input_tokens": 0, "output_tokens": 0, "runs": 0})
        agg["runs"] += 1
        for _stage, u in data.items():
            agg["input_tokens"] += int(u.get("input_tokens", 0))
            agg["output_tokens"] += int(u.get("output_tokens", 0))
    return out
