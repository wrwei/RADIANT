"""Tests for token_usage record / aggregate / cost."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # MALCOMp
import token_usage


def test_record_accumulates_per_stage(tmp_path):
    token_usage.record(tmp_path, "concept", 100, 50)
    token_usage.record(tmp_path, "concept", 10, 5)      # same stage accumulates
    token_usage.record(tmp_path, "dsml", 200, 80)
    data = json.loads((tmp_path / "tokens.json").read_text())
    assert data["concept"] == {"input_tokens": 110, "output_tokens": 55}
    assert data["dsml"] == {"input_tokens": 200, "output_tokens": 80}


def test_usage_from_completion_openai_and_anthropic():
    oai = type("C", (), {"usage": type("U", (), {"prompt_tokens": 9, "completion_tokens": 4})()})()
    assert token_usage.usage_from_completion(oai, "openai") == (9, 4)
    ant = type("M", (), {"usage": type("U", (), {"input_tokens": 3, "output_tokens": 7})()})()
    assert token_usage.usage_from_completion(ant, "anthropic") == (3, 7)


def test_cost_uses_price_table():
    # claude-opus-4-8 = (15, 75) per 1M
    c = token_usage.cost_usd(1_000_000, 1_000_000, "claude-opus-4-8")
    assert abs(c - (15.0 + 75.0)) < 1e-6
    assert token_usage.cost_usd(1, 1, "unknown-model") is None


def test_aggregate_sums_runs(tmp_path):
    for variant in ("single", "multi"):
        for run in (1, 2):
            d = tmp_path / "deepseek_v4" / variant / f"run_{run:03d}"
            d.mkdir(parents=True)
            token_usage.record(d, "concept", 100, 50)
    agg = token_usage.aggregate(tmp_path)
    assert agg[("single", "deepseek_v4")] == {"input_tokens": 200, "output_tokens": 100, "runs": 2}
    assert agg[("multi", "deepseek_v4")]["runs"] == 2
