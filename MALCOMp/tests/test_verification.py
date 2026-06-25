"""Unit tests for the per-phase artefact verifiers."""
import json
import sys
from pathlib import Path

MALCOMP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MALCOMP))

from verification import (  # noqa: E402
    Check, VerificationResult, trace_resolution_check, verify_concept,
    _behaviour_completeness, _expected_transition_counts, verify_behaviour,
    _concept_coverage,
)


_CONCEPT_REQS = [{"id": f"R{i}"} for i in range(1, 21)]  # 20 requirement GIDs


def _write_concept(tmp_path, trace_entries, n_concepts):
    import json as _j
    (tmp_path / "result_concept_trace.json").write_text(
        _j.dumps({"term_trace": trace_entries}), encoding="utf-8")
    (tmp_path / "result_concept_model.json").write_text(
        _j.dumps({"concepts": [{"name": f"C{i}"} for i in range(n_concepts)], "instances": []}),
        encoding="utf-8")
    return tmp_path / "result_concept_trace.json", tmp_path / "result_concept_model.json"


def test_concept_coverage_flags_empty_placeholder(tmp_path):
    tr, mo = _write_concept(tmp_path, [{"GID": "T-001", "Concept": "Placeholder"}], 0)
    ok, detail = _concept_coverage(tr, mo, _CONCEPT_REQS)
    assert ok is False and "0 concepts" in detail


def test_concept_coverage_passes_full(tmp_path):
    entries = [{"GID": f"R{i}", "Concept": "C", "Instance": "x"} for i in range(1, 21)]
    tr, mo = _write_concept(tmp_path, entries, 9)
    ok, _ = _concept_coverage(tr, mo, _CONCEPT_REQS)
    assert ok is True


def test_concept_coverage_soft_when_no_requirements(tmp_path):
    tr, mo = _write_concept(tmp_path, [], 0)
    ok, _ = _concept_coverage(tr, mo, [])
    assert ok is None


def test_verify_concept_coverage_is_hard_failure(tmp_path):
    _write_concept(tmp_path, [{"GID": "T-001", "Concept": "Placeholder",
                               "source": {"resolved": True}}], 0)
    r = verify_concept(tmp_path, requirement_data=_CONCEPT_REQS)
    assert "concept_coverage" in {c.name for c in r.hard_failures}


_REQS = [
    {"id": "B1", "description": "On start up, the LRE shall be in the OCM mode."},
    {"id": "B2", "description": "The LRE shall transition from MOM to HCM, if A."},
    {"id": "B3", "description": "The LRE shall transition from MOM to HCM, if B."},
    {"id": "B4", "description": "The LRE shall transition from HCM to OCM if reqOCM."},
]
# requirements describe 2x MOM->HCM and 1x HCM->OCM (initial B1 not counted)

_COMPLETE_RCT = """
stm M {
  initial i0
  state OCM { } state MOM { } state HCM { }
  transition t0 { from i0 to OCM }
  transition t1 { from MOM to HCM condition a }
  transition t2 { from MOM to HCM condition b }
  transition t3 { from HCM to OCM trigger reqOCM }
}
"""
_MERGED_RCT = _COMPLETE_RCT.replace("  transition t2 { from MOM to HCM condition b }\n", "")


def test_expected_transition_counts_ignores_initial():
    exp = _expected_transition_counts(_REQS)
    assert exp[("mom", "hcm")] == 2
    assert exp[("hcm", "ocm")] == 1
    assert ("i0", "ocm") not in exp  # the initial requirement isn't counted


def test_behaviour_completeness_detects_merge(tmp_path):
    rct = tmp_path / "result_behaviour_model.rct"
    rct.write_text(_MERGED_RCT, encoding="utf-8")
    ok, detail = _behaviour_completeness(rct, _REQS)
    assert ok is False
    assert "mom->hcm" in detail and "specify 2, model has 1" in detail


def test_behaviour_completeness_passes_when_complete(tmp_path):
    rct = tmp_path / "result_behaviour_model.rct"
    rct.write_text(_COMPLETE_RCT, encoding="utf-8")
    ok, _ = _behaviour_completeness(rct, _REQS)
    assert ok is True


def test_behaviour_completeness_soft_when_no_requirements(tmp_path):
    rct = tmp_path / "result_behaviour_model.rct"
    rct.write_text(_COMPLETE_RCT, encoding="utf-8")
    ok, _ = _behaviour_completeness(rct, [])      # nothing to check -> soft
    assert ok is None


def test_verify_behaviour_completeness_is_hard_failure(tmp_path):
    (tmp_path / "result_behaviour_model.rct").write_text(_MERGED_RCT, encoding="utf-8")
    r = verify_behaviour(tmp_path, requirement_data=_REQS)
    assert "behaviour_completeness" in {c.name for c in r.hard_failures}


def test_result_passed_and_hard_failures():
    r = VerificationResult("dsml", [
        Check("a", "structural", ok=True, unverifiable=False, detail=""),
        Check("b", "structural", ok=False, unverifiable=True, detail="tool missing"),
    ])
    assert r.passed is True                      # unverifiable counts as soft-pass
    assert r.hard_failures == []
    r2 = VerificationResult("dsml", [Check("a", "structural", False, False, "boom")])
    assert r2.passed is False
    assert [c.name for c in r2.hard_failures] == ["a"]


def test_trace_resolution_check(tmp_path):
    good = tmp_path / "g.json"
    good.write_text(json.dumps({"t": [
        {"GID": "X", "source": {"resolved": True}},
        {"GID": "Y", "source": {"resolved": True}},
    ]}), encoding="utf-8")
    c = trace_resolution_check(good, "t")
    assert c.ok and c.kind == "traceability"
    bad = tmp_path / "b.json"
    bad.write_text(json.dumps({"t": [
        {"GID": "X", "source": {"resolved": True}},
        {"GID": "Y", "source": {"resolved": False}},
    ]}), encoding="utf-8")
    c2 = trace_resolution_check(bad, "t")
    assert not c2.ok and "1" in c2.detail        # 1 unresolved reported


def test_behaviour_structural_via_parser(tmp_path):
    from verification import verify_behaviour
    (tmp_path / "result_behaviour_model.rct").write_text(
        "stm S { state Move { } transition t0 { from i0 to Move } }", encoding="utf-8")
    (tmp_path / "result_behaviour_trace.json").write_text(
        '{"stm_trace": [{"requirement_gid":"R1","transition":"t0","source":{"resolved":true}}]}',
        encoding="utf-8")
    r = verify_behaviour(tmp_path)
    assert r.passed, r.summary()


def test_dsml_structural(tmp_path):
    from verification import verify_dsml
    # Well-formed Emfatic (with the required package decl) -> valid -> passes.
    (tmp_path / "result_dsml.emf").write_text(
        "package p;\n\nclass A {\n    attr String name;\n}\n", encoding="utf-8")
    (tmp_path / "result_dsml_trace.json").write_text(
        '{"dsl_trace": [{"requirement_gid":"R1","Emfatic_class":"A","source":{"resolved":true}}]}',
        encoding="utf-8")
    assert verify_dsml(tmp_path).passed
    # Garbage Emfatic -> structural is a hard FAIL (via EmfaticHelper or the
    # pure-Python converter fallback — whichever is available).
    (tmp_path / "result_dsml.emf").write_text("not emfatic at all", encoding="utf-8")
    r = verify_dsml(tmp_path)
    assert not r.passed
    assert any(c.name == "emfatic_valid" and not c.ok and not c.unverifiable
               for c in r.checks)


def test_dispatch(tmp_path):
    from verification import verify
    (tmp_path / "result_concept_trace.json").write_text(
        '{"term_trace":[{"GID":"X","Concept":"C","source":{"resolved":true}}]}', encoding="utf-8")
    (tmp_path / "result_concept_model.json").write_text('{"concepts":[],"instances":[]}', encoding="utf-8")
    assert verify("concept", tmp_path).passed
    import pytest
    with pytest.raises(ValueError):
        verify("nope", tmp_path)


def test_behaviour_fdr4_disabled_omits_check(tmp_path):
    from verification import verify_behaviour
    (tmp_path / "result_behaviour_model.rct").write_text(
        "stm S { state Move { } transition t0 { from i0 to Move } }", encoding="utf-8")
    (tmp_path / "result_behaviour_trace.json").write_text(
        '{"stm_trace": [{"requirement_gid":"R1","transition":"t0","source":{"resolved":true}}]}',
        encoding="utf-8")
    # no fdr4_config -> no fdr4_refinement check (back-compat)
    r = verify_behaviour(tmp_path)
    assert not any(c.name == "fdr4_refinement" for c in r.checks)
    # enabled:false -> still omitted
    r2 = verify_behaviour(tmp_path, fdr4_config={"enabled": False})
    assert not any(c.name == "fdr4_refinement" for c in r2.checks)


def test_behaviour_fdr4_enabled_adds_check(tmp_path, monkeypatch):
    import verification
    from verification import Check
    (tmp_path / "result_behaviour_model.rct").write_text(
        "stm S { state Move { } transition t0 { from i0 to Move } }", encoding="utf-8")
    (tmp_path / "result_behaviour_trace.json").write_text(
        '{"stm_trace": [{"requirement_gid":"R1","transition":"t0","source":{"resolved":true}}]}',
        encoding="utf-8")
    import fdr4
    monkeypatch.setattr(
        fdr4, "run_fdr4_check",
        lambda rct, config: Check("fdr4_refinement", "structural", True, False, "2 assertions hold"))
    r = verification.verify_behaviour(tmp_path, fdr4_config={"enabled": True})
    assert any(c.name == "fdr4_refinement" and c.ok for c in r.checks)


def test_verify_dispatch_threads_fdr4_config(tmp_path, monkeypatch):
    import verification
    from verification import Check
    (tmp_path / "result_behaviour_model.rct").write_text(
        "stm S { state Move { } transition t0 { from i0 to Move } }", encoding="utf-8")
    (tmp_path / "result_behaviour_trace.json").write_text(
        '{"stm_trace": [{"requirement_gid":"R1","transition":"t0","source":{"resolved":true}}]}',
        encoding="utf-8")
    import fdr4
    seen = {}

    def _fake(rct, config):
        seen.update(config)
        return Check("fdr4_refinement", "structural", True, False, "ok")
    monkeypatch.setattr(fdr4, "run_fdr4_check", _fake)
    verification.verify("behaviour", tmp_path, fdr4_config={"enabled": True, "marker": 7})
    assert seen.get("marker") == 7


def test_verify_concept(tmp_path):
    (tmp_path / "result_concept_trace.json").write_text(json.dumps({"term_trace": [
        {"GID": "SD1", "Concept": "Module", "Instance": "M", "source": {"resolved": True}},
    ]}), encoding="utf-8")
    (tmp_path / "result_concept_model.json").write_text(json.dumps({"concepts": [], "instances": []}), encoding="utf-8")
    r = verify_concept(tmp_path)
    assert r.passed
    # break it: invalid JSON
    (tmp_path / "result_concept_model.json").write_text("{not json", encoding="utf-8")
    assert not verify_concept(tmp_path).passed
