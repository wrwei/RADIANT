"""The `single_repair` control arm: single generating call + gate + repair.

The plain single-agent variant has no checking and no repair, so comparing it
against the full pipeline measures role decomposition and iterative repair
together. This variant adds only the gate and the repair loop, so the two
factors can be separated. These tests drive it with a stub client — no API key
and no network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

MALCOMP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MALCOMP))

import run_evaluation as R  # noqa: E402
import run_single_agent as S  # noqa: E402

CONFIG = MALCOMP.parent / "config.yaml"


def test_variant_is_registered_and_dispatched():
    assert "single_repair" in R.VARIANTS
    assert callable(R._run_single_repair)


def test_signature_matches_the_plain_runner():
    import inspect
    assert (list(inspect.signature(S.run_stage_single_agent_with_repair).parameters)
            == list(inspect.signature(S.run_stage_single_agent).parameters))


def test_phase_mapping_is_shared_with_the_pipeline():
    """The repair arm must gate the same stages the multi-agent path gates."""
    from base import Base
    assert set(Base._VERIFY_PHASE) >= {"dsml_creation", "emf_model_creation"}


class _StubClient:
    """Returns queued payloads in order, recording every prompt it saw."""

    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.prompts = []


@pytest.fixture
def stubbed(monkeypatch, tmp_path):
    """Patch generation and completion so the loop runs without a network."""
    state = {"prompts": [], "written": []}

    def fake_generate(stage_name, config_path, output_dir, client, config):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        p = Path(output_dir) / "result_dsml.emf"
        p.write_text(client.payloads.pop(0), encoding="utf-8")
        state["written"].append(p.read_text(encoding="utf-8"))
        return p

    def fake_complete(client, config, system_message, user_message):
        state["prompts"].append(user_message)
        return client.payloads.pop(0), (10, 20)

    monkeypatch.setattr(S, "run_stage_single_agent", fake_generate)
    monkeypatch.setattr(S, "_complete", fake_complete)
    monkeypatch.setattr(S.token_usage, "record", lambda *a, **k: None)
    return state


def _trace(tmp_path, resolved=True):
    (tmp_path / "result_dsml_trace.json").write_text(json.dumps({"dsl_trace": [
        {"requirement_gid": "R1", "Emfatic_class": "Module",
         "source": {"resolved": resolved}}]}), encoding="utf-8")


def test_repair_loop_fixes_a_failing_artefact(stubbed, tmp_path):
    """A first artefact that fails the gate is repaired and re-verified."""
    _trace(tmp_path)
    broken = "package p; class Module {"          # unbalanced brace
    fixed = "package p;\nclass Module {\n}\n"
    client = _StubClient([broken, fixed])
    cfg = {"verification": {"enabled": True, "max_repair_attempts": 2}}

    S.run_stage_single_agent_with_repair("dsml_creation", CONFIG, tmp_path,
                                         client, cfg)

    assert len(stubbed["prompts"]) == 1, "expected exactly one repair call"
    prompt = stubbed["prompts"][0]
    assert "failed verification" in prompt
    assert broken in prompt, "the failing artefact must be shown to the repairer"
    assert (tmp_path / "result_dsml.emf").read_text().strip() == fixed.strip()


def test_no_repair_when_the_gate_passes(stubbed, tmp_path):
    _trace(tmp_path)
    good = "package p;\nclass Module {\n}\n"
    client = _StubClient([good])
    cfg = {"verification": {"enabled": True, "max_repair_attempts": 2}}

    S.run_stage_single_agent_with_repair("dsml_creation", CONFIG, tmp_path,
                                         client, cfg)

    assert stubbed["prompts"] == [], "a passing artefact must not be repaired"


def test_repair_attempts_are_capped(stubbed, tmp_path):
    """A model that never fixes the artefact must not loop forever."""
    _trace(tmp_path)
    broken = ["package p; class A {", "package p; class B {",
              "package p; class C {", "package p; class D {"]
    client = _StubClient(broken)
    cfg = {"verification": {"enabled": True, "max_repair_attempts": 2}}

    S.run_stage_single_agent_with_repair("dsml_creation", CONFIG, tmp_path,
                                         client, cfg)

    assert len(stubbed["prompts"]) == 2, "must stop at max_repair_attempts"


def test_identical_reply_stops_the_loop(stubbed, tmp_path):
    """If the repairer returns the artefact unchanged, stop rather than spend
    another call on the same input."""
    _trace(tmp_path)
    broken = "package p; class A {"
    client = _StubClient([broken, broken, broken])
    cfg = {"verification": {"enabled": True, "max_repair_attempts": 3}}

    S.run_stage_single_agent_with_repair("dsml_creation", CONFIG, tmp_path,
                                         client, cfg)

    assert len(stubbed["prompts"]) == 1


def test_verification_disabled_skips_the_loop(stubbed, tmp_path):
    _trace(tmp_path)
    client = _StubClient(["package p; class A {"])
    cfg = {"verification": {"enabled": False}}

    S.run_stage_single_agent_with_repair("dsml_creation", CONFIG, tmp_path,
                                         client, cfg)

    assert stubbed["prompts"] == []
