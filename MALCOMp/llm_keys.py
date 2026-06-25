"""Per-model API-key resolution for multi-provider runs / sweeps.

Each model entry in config.yaml's `models:` map may carry an optional
`api_key_env` naming the environment variable that holds its key (e.g.
DEEPSEEK_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY). This lets a single
sweep span providers that each require their own key.

Resolution falls back to OPENAI_API_KEY so existing single-provider setups
(which only set OPENAI_API_KEY) keep working unchanged.
"""
from __future__ import annotations

import os


def resolve_api_key(model_cfg: dict | None) -> str:
    """Return the API key for a model entry.

    Reads the env var named by the model's optional ``api_key_env`` (default
    ``OPENAI_API_KEY``), falling back to ``OPENAI_API_KEY``. Raises if neither
    is set.
    """
    key_env = (model_cfg or {}).get("api_key_env", "OPENAI_API_KEY")
    api_key = os.environ.get(key_env) or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            f"no API key found: set {key_env} (or OPENAI_API_KEY) in your "
            "environment / .env"
        )
    return api_key
