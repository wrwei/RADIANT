"""Unit tests for per-model API-key resolution."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # MALCOMp
from llm_keys import resolve_api_key


def test_uses_named_env_var(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "dk")
    monkeypatch.setenv("OPENAI_API_KEY", "ok")
    assert resolve_api_key({"api_key_env": "DEEPSEEK_API_KEY"}) == "dk"


def test_falls_back_to_openai_when_named_missing(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "ok")
    assert resolve_api_key({"api_key_env": "DEEPSEEK_API_KEY"}) == "ok"


def test_default_is_openai_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "ok")
    assert resolve_api_key({}) == "ok"
    assert resolve_api_key(None) == "ok"


def test_missing_everything_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        resolve_api_key({"api_key_env": "OPENROUTER_API_KEY"})
