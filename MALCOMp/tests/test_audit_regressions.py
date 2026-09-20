"""Regressions for the defects found in the source-code audit.

Each test pins a behaviour that was wrong (or silently permissive) before, so a
future change cannot quietly reintroduce it.
"""
import json
import sys
from pathlib import Path

import pytest

MALCOMP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MALCOMP))

import change_impact as CI  # noqa: E402
import trace_locator as T  # noqa: E402
import verification as V  # noqa: E402
from verification import Check, VerificationResult  # noqa: E402


# --- gate semantics: "could not run" must be distinguishable from "verified" --

def _soft():
    return [Check("eol_executes", "structural", ok=False, unverifiable=True,
                  detail="MALCOMj runner not installed"),
            Check("trace_resolved", "traceability", ok=True, unverifiable=False,
                  detail="")]


def test_unrunnable_check_is_not_full_verification():
    r = VerificationResult("model", _soft())
    assert r.passed is True                 # accepted, as designed
    assert r.fully_verified is False        # but NOT verified
    assert [c.name for c in r.unverified] == ["eol_executes"]


def test_strict_mode_rejects_unrunnable_checks():
    r = VerificationResult("model", _soft(), strict=True)
    assert r.passed is False
    assert [c.name for c in r.hard_failures] == ["eol_executes"]


def test_fully_verified_only_when_every_check_ran():
    ok = [Check("a", "structural", True, False, ""),
          Check("b", "traceability", True, False, "")]
    assert VerificationResult("dsml", ok).fully_verified is True
    assert VerificationResult("dsml", []).fully_verified is False


def test_summary_flags_unverified_phases():
    assert "UNVERIFIED" in VerificationResult("model", _soft()).summary()


def test_verify_threads_strict_through_dispatch(tmp_path):
    (tmp_path / "result_model_trace.json").write_text(json.dumps(
        {"model_trace": [{"GID": "R1", "Model_Element": "X",
                          "source": {"resolved": True}}]}), encoding="utf-8")
    assert V.verify("model", tmp_path, malcomj_runner=None).passed is True
    assert V.verify("model", tmp_path, malcomj_runner=None, strict=True).passed is False


# --- locators must match whole identifiers, not substrings -------------------

EOL = ("var auv_module = new M!Module;\n"
       "var ns_rel_dist = new M!Value;\n"
       "var nat = new M!PrimitiveType;\n"
       "var id = new M!Value;\n")


@pytest.mark.parametrize("bogus", ["dist", "rel_dist", "Type", "Primitive"])
def test_eol_locator_rejects_substring_matches(bogus):
    """A short id must not resolve to a longer identifier containing it."""
    assert T.locate_eol_element(EOL, bogus) is None


@pytest.mark.parametrize("eid,line", [("auv_module", 1), ("ns_rel_dist", 2),
                                      ("nat", 3), ("id", 4)])
def test_eol_locator_finds_the_declaration(eid, line):
    assert T.locate_eol_element(EOL, eid) == (line, line)


def test_eol_locator_prefers_declaration_over_earlier_mention():
    text = "auv_module.values.add(depth);\nvar depth = new M!Value;\n"
    assert T.locate_eol_element(text, "depth") == (2, 2)


def test_requirement_locator_rejects_substring_matches():
    text = 'record "ns_rel_dist" (of type "real")'
    assert T.locate_requirement(text, "dist") is None
    assert T.locate_requirement(text, "ns_rel_dist") is not None


# --- change impact: no silent data loss -------------------------------------

def test_requirement_id_collision_is_reported_not_silent(tmp_path, caplog):
    rd = tmp_path / "requirements"
    rd.mkdir()
    (rd / "requirement_architecture.json").write_text(json.dumps({"requirements": [
        {"id": "LRE-Beh6", "description": "first"},
        {"id": "lre_beh_6", "description": "second"},
    ]}), encoding="utf-8")
    with caplog.at_level("WARNING"):
        reqs = CI.load_requirements(tmp_path)
    assert reqs == {"lrebeh6": "first"}          # first wins, deterministically
    assert any("collision" in r.getMessage() for r in caplog.records)


def test_requirements_read_from_the_documented_key(tmp_path):
    rd = tmp_path / "requirements"
    rd.mkdir()
    (rd / "requirement_architecture.json").write_text(json.dumps({
        "tags": ["not", "requirements"],
        "requirements": [{"id": "R1", "description": "real one"}],
    }), encoding="utf-8")
    assert CI.load_requirements(tmp_path) == {"r1": "real one"}


def test_legacy_concept_trace_tag_is_still_read(tmp_path, caplog):
    """Artefacts written before the tag rename must not contribute zero links."""
    (tmp_path / "result_concept_trace.json").write_text(json.dumps({"req": [
        {"GID": "SD1", "Concept": "Module", "Instance": "AUV_Module"},
    ]}), encoding="utf-8")
    with caplog.at_level("WARNING"):
        links = CI.load_links(tmp_path)
    assert [l.phase for l in links] == ["concept"]
    assert any("legacy trace tag" in r.getMessage() for r in caplog.records)


# --- run-directory identity (manifest + arm guard) ---------------------------

def test_manifest_written_and_updated(tmp_path):
    """First stage stamps the manifest; later stages append, not overwrite."""
    import run_evaluation as R

    d = tmp_path / "run_001"
    R.write_or_check_manifest(d, "deepseek_v4", "multi", "concept", Path("config.yaml"))
    R.write_or_check_manifest(d, "deepseek_v4", "multi", "model", Path("config.yaml"))
    m = json.loads((d / "run_manifest.json").read_text())
    assert m["model"] == "deepseek_v4" and m["variant"] == "multi"
    assert m["stages"] == ["concept", "model"]


def test_manifest_refuses_other_arms_run_dir(tmp_path):
    """Recording into a run directory owned by another arm is a hard error.

    A run directory's identity previously lived only in its path, so a sweep
    pointed at the wrong root silently recorded into another experiment's
    data. The manifest guard turns that into SystemExit at the point of use.
    """
    import pytest
    import run_evaluation as R

    d = tmp_path / "run_001"
    R.write_or_check_manifest(d, "deepseek_v4", "multi", "concept", Path("config.yaml"))
    with pytest.raises(SystemExit, match="ARM MISMATCH"):
        R.write_or_check_manifest(d, "deepseek_v4", "single_repair", "concept",
                                  Path("config.yaml"))
