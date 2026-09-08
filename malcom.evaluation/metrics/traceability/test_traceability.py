"""Tests for the resolvability / coverage driver.

Run: python -m pytest malcom.evaluation/metrics/traceability -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]   # traceability -> metrics -> malcom.evaluation -> repo

# Load this package's metrics module by path: a bare `import metrics` would
# resolve to the sibling `malcom.evaluation/metrics` package instead.
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "traceability_metrics", HERE / "metrics.py")
_mod = importlib.util.module_from_spec(_spec)
sys.modules["traceability_metrics"] = _mod
_spec.loader.exec_module(_mod)
aggregate = _mod.aggregate
canonical_gid = _mod.canonical_gid
load_requirements = _mod.load_requirements
score_run = _mod.score_run

RUNS = REPO / "case_studies" / "auv" / "output" / "runs"
CASE = REPO / "case_studies" / "auv"


def _layer(scores, name):
    return next(s for s in scores if s.layer == name)


# --- unit behaviour on synthetic input --------------------------------------

def _write_run(tmp_path: Path, *, emf=None, eol=None, stm=None,
               dsl_trace=None, model_trace=None, stm_trace=None):
    if emf is not None:
        (tmp_path / "result_DSL.emf").write_text(emf, encoding="utf-8")
    if eol is not None:
        (tmp_path / "result_eol_program.eol").write_text(eol, encoding="utf-8")
    if stm is not None:
        (tmp_path / "STM.txt").write_text(stm, encoding="utf-8")
    if dsl_trace is not None:
        (tmp_path / "result_dsl_extraction.json").write_text(
            json.dumps({"dsl_trace": dsl_trace}), encoding="utf-8")
    if model_trace is not None:
        (tmp_path / "result_model_creation.json").write_text(
            json.dumps({"model_trace": model_trace}), encoding="utf-8")
    if stm_trace is not None:
        (tmp_path / "result_statemachine_extraction.json").write_text(
            json.dumps({"stm_trace": stm_trace}), encoding="utf-8")
    return tmp_path


def test_resolvability_counts_only_targets_that_exist(tmp_path):
    reqs = {"r1": ("desc", "architecture")}
    run = _write_run(
        tmp_path,
        emf="class Module {\n  attr String name;\n}\nclass Sensor { }\n",
        dsl_trace=[{"requirement_gid": "R1", "Emfatic_class": "Module"},
                   {"requirement_gid": "R1", "Emfatic_class": "Sensor"},
                   {"requirement_gid": "R1", "Emfatic_class": "Ghost"}])
    s = _layer(score_run(run, reqs), "notation")
    assert (s.links_emitted, s.links_resolved) == (3, 2)
    assert s.resolvability == pytest.approx(2 / 3)
    assert any("Ghost" in x for x in s.unresolved_examples)


def test_coverage_counts_requirements_with_a_link(tmp_path):
    reqs = {f"r{i}": ("d", "architecture") for i in range(1, 5)}
    run = _write_run(
        tmp_path,
        eol="var a = new M!Module;\nvar b = new M!Sensor;\n",
        model_trace=[{"requirement_gid": "R1", "Model_Element_id": "a"},
                     {"requirement_gid": "R2", "Model_Element_id": "b"}])
    s = _layer(score_run(run, reqs), "model")
    assert (s.requirements_covered, s.requirements_total) == (2, 4)
    assert s.coverage == pytest.approx(0.5)


def test_coverage_is_independent_of_resolution(tmp_path):
    """A requirement with an emitted-but-unresolved link still counts as
    covered; `effective_coverage` is the stricter reading."""
    reqs = {"r1": ("d", "architecture"), "r2": ("d", "architecture")}
    run = _write_run(
        tmp_path,
        eol="var a = new M!Module;\n",
        model_trace=[{"requirement_gid": "R1", "Model_Element_id": "a"},
                     {"requirement_gid": "R2", "Model_Element_id": "ghost"}])
    s = _layer(score_run(run, reqs), "model")
    assert s.coverage == pytest.approx(1.0)
    assert s.effective_coverage == pytest.approx(0.5)
    assert s.resolvability == pytest.approx(0.5)


def test_concept_typename_links_reported_separately(tmp_path):
    """The concept layer's type-name fallback must not be pooled with links
    that name a specific instance."""
    reqs = {"r1": ('should contain a Robotic Platform named "AUV_Platform"',
                   "architecture")}
    (tmp_path / "result_term_extraction.json").write_text(json.dumps({
        "term_trace": [
            {"GID": "R1", "Instance": "AUV_Platform", "Concept": "RoboticPlatform"},
            {"GID": "R1", "Concept": "RoboticPlatform"},   # type-name fallback
        ]}), encoding="utf-8")
    s = _layer(score_run(tmp_path, reqs), "concept")
    assert (s.instance_emitted, s.instance_resolved) == (1, 1)
    assert s.instance_resolvability == pytest.approx(1.0)
    assert (s.typename_emitted, s.typename_resolved) == (1, 0)
    assert s.resolvability == pytest.approx(0.5)   # pooled, for reference


def test_missing_artefact_yields_no_links(tmp_path):
    reqs = {"r1": ("d", "architecture")}
    run = _write_run(tmp_path, dsl_trace=[
        {"requirement_gid": "R1", "Emfatic_class": "Module"}])
    s = _layer(score_run(run, reqs), "notation")
    assert s.links_emitted == 0 and s.resolvability is None


def test_empty_layer_excluded_from_coverage_average(tmp_path):
    """A failed phase (trace file present, no links) must not enter the
    coverage mean as a zero."""
    reqs = {"r1": ("d", "behaviour"), "r2": ("d", "behaviour")}
    good = _write_run(tmp_path / "good", stm="transition t0 { }\n",
                      stm_trace=[{"requirement_gid": "R1", "transition": "t0"}]) \
        if (tmp_path / "good").mkdir() is None else None
    bad = tmp_path / "bad"
    bad.mkdir()
    _write_run(bad, stm="", stm_trace=[{}, {}])
    summary = aggregate([score_run(good, reqs), score_run(bad, reqs)])
    beh = next(r for r in summary if r["layer"] == "behaviour")
    assert beh["runs"] == 1 and beh["runs_empty"] == 1
    assert beh["coverage_mean"] == pytest.approx(0.5)   # not 0.25


def test_canonical_gid_matches_pipeline_convention():
    assert canonical_gid("LRE-Beh6") == canonical_gid("lre_beh_6") == "lrebeh6"


# --- reproduction of the reported figures -----------------------------------

@pytest.mark.skipif(not (RUNS / "web_20260530_182240_auto1").is_dir(),
                    reason="requires the archived AUV runs")
class TestReportedFigures:
    """The driver must reproduce Table 2 of the paper from the shipped runs."""

    @pytest.fixture(scope="class")
    @classmethod
    def summary(cls):
        reqs = load_requirements(CASE)
        runs = sorted(p for p in RUNS.iterdir() if p.is_dir())
        return aggregate([score_run(r, reqs) for r in runs])

    def test_architectural_resolvability_is_one(self, summary):
        for layer in ("concept", "notation", "model"):
            row = next(r for r in summary if r["layer"] == layer)
            assert row["instance_resolvability"] == pytest.approx(1.0), layer

    def test_behaviour_resolvability_is_one(self, summary):
        row = next(r for r in summary if r["layer"] == "behaviour")
        assert row["resolvability"] == pytest.approx(1.0)

    def test_architectural_coverage_at_least_098(self, summary):
        for layer in ("concept", "notation", "model"):
            row = next(r for r in summary if r["layer"] == layer)
            assert row["coverage_mean"] >= 0.98, layer

    def test_behaviour_coverage_is_067(self, summary):
        row = next(r for r in summary if r["layer"] == "behaviour")
        assert row["coverage_mean"] == pytest.approx(2 / 3, abs=5e-3)
