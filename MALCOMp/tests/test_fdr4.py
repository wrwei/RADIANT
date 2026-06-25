"""Unit tests for the optional FDR4 behaviour verifier."""
import os
import sys
from pathlib import Path

import pytest

MALCOMP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MALCOMP))


# --- Task 1: framed JSON + exception -----------------------------------------

def test_parse_framed_json_skips_garbage():
    from fdr4 import _parse_framed_json
    raw = '{"results": [{"result": 1}]}\nnot json\n{"results": []}\n'
    frames = _parse_framed_json(raw)
    assert len(frames) == 2
    assert frames[0]["results"][0]["result"] == 1


def test_toolchain_unavailable_is_exception():
    from fdr4 import ToolchainUnavailable
    assert issubclass(ToolchainUnavailable, Exception)


# --- Task 2: type-range corrections ------------------------------------------

def test_apply_type_range_corrections_rewrites_int_and_timed(tmp_path):
    from fdr4 import _apply_type_range_corrections
    csp_gen = tmp_path / "csp-gen"
    (csp_gen / "timed").mkdir(parents=True)
    body = (
        "-- TYPES\n"
        "-- generate int\n"
        "nametype core_int = union({-2..2}, {5})\n"
        "-- generate string\n"
        "nametype core_string = {0..3}\n"
    )
    (csp_gen / "instantiations.csp").write_text(body, encoding="utf-8")
    (csp_gen / "timed" / "instantiations.csp").write_text(body, encoding="utf-8")

    patched = _apply_type_range_corrections(csp_gen, {})

    untimed = (csp_gen / "instantiations.csp").read_text(encoding="utf-8")
    timed = (csp_gen / "timed" / "instantiations.csp").read_text(encoding="utf-8")
    assert "nametype core_int = {0..1}" in untimed
    assert "nametype core_string = {0}" in untimed
    assert "union" not in untimed
    assert "nametype core_int = {0..1}" in timed          # timed patched too
    assert len(patched) == 2


def test_apply_type_range_corrections_honours_override(tmp_path):
    from fdr4 import _apply_type_range_corrections
    csp_gen = tmp_path / "csp-gen"
    csp_gen.mkdir()
    (csp_gen / "instantiations.csp").write_text(
        "-- generate int\nnametype core_int = {0..9}\n", encoding="utf-8")
    _apply_type_range_corrections(csp_gen, {"int": {"lower": 0, "upper": 2}})
    text = (csp_gen / "instantiations.csp").read_text(encoding="utf-8")
    assert "nametype core_int = {0..2}" in text


# --- Task 3: coreassertions discovery ----------------------------------------

def _touch(d: Path, name: str):
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text("-- csp\n", encoding="utf-8")


def test_discover_prefers_system_module(tmp_path):
    from fdr4 import _discover_coreassertions
    defs = tmp_path / "csp-gen" / "defs"
    _touch(defs, "Foo_System_Module_coreassertions.csp")
    _touch(defs, "BarController_coreassertions.csp")
    chosen = _discover_coreassertions(tmp_path / "csp-gen")
    assert chosen.name == "Foo_System_Module_coreassertions.csp"


def test_discover_prefers_controller_only(tmp_path):
    from fdr4 import _discover_coreassertions
    defs = tmp_path / "csp-gen" / "defs"
    _touch(defs, "AuvController_coreassertions.csp")
    _touch(defs, "Auv_Module_coreassertions.csp")
    chosen = _discover_coreassertions(tmp_path / "csp-gen")
    assert chosen.name == "AuvController_coreassertions.csp"


def test_discover_prefers_ctrl_over_module(tmp_path):
    # Our EGL names the controller <Stm>_Ctrl; the controller-only assertions must
    # be preferred over the module level (smaller state space — avoids OOM).
    from fdr4 import _discover_coreassertions
    defs = tmp_path / "csp-gen" / "defs"
    _touch(defs, "LRE_Beh_coreassertions.csp")
    _touch(defs, "LRE_Beh_Ctrl_coreassertions.csp")
    _touch(defs, "LRE_Beh_Module_coreassertions.csp")
    chosen = _discover_coreassertions(tmp_path / "csp-gen")
    assert chosen.name == "LRE_Beh_Ctrl_coreassertions.csp"


def test_discover_unique_fallback(tmp_path):
    from fdr4 import _discover_coreassertions
    defs = tmp_path / "csp-gen" / "defs"
    _touch(defs, "Only_coreassertions.csp")          # single non-tiered file
    assert _discover_coreassertions(tmp_path / "csp-gen").name == "Only_coreassertions.csp"


def test_discover_none_when_no_defs(tmp_path):
    from fdr4 import _discover_coreassertions
    # missing csp-gen dir, and an empty defs dir, both yield None
    assert _discover_coreassertions(tmp_path / "missing") is None
    (tmp_path / "csp-gen" / "defs").mkdir(parents=True)
    assert _discover_coreassertions(tmp_path / "csp-gen") is None


# --- Task 4: stderr classify + determinism strip -----------------------------

def test_classify_stderr_pagefile_and_clean():
    from fdr4 import _classify_fdr4_stderr
    assert _classify_fdr4_stderr("The paging file is too small for this operation")
    assert "memory" in _classify_fdr4_stderr("out of memory: heap exhausted").lower()
    assert _classify_fdr4_stderr("Checking assertion... done") is None
    assert _classify_fdr4_stderr("") is None


def test_strip_determinism_writes_nodet(tmp_path):
    from fdr4 import _strip_determinism
    csp = tmp_path / "X_coreassertions.csp"
    csp.write_text(
        "assert P :[deadlock free]\n"
        "assert P :[deterministic]\n"
        "assert P :[divergence free]\n", encoding="utf-8")
    out = _strip_determinism(csp)
    assert out.name == "X_coreassertions_nodet.csp"
    text = out.read_text(encoding="utf-8")
    assert "-- determinism not verified" in text
    assert "assert P :[deadlock free]" in text          # untouched
    assert not any(ln.lstrip().startswith("assert") and ":[deterministic]" in ln
                   for ln in text.splitlines())


def test_strip_determinism_noop_returns_original(tmp_path):
    from fdr4 import _strip_determinism
    csp = tmp_path / "Y_coreassertions.csp"
    csp.write_text("assert P :[deadlock free]\n", encoding="utf-8")
    assert _strip_determinism(csp) == csp


# --- Task 5: refines runner --------------------------------------------------

class _FakeProc:
    def __init__(self, stdout="", stderr=""):
        self._stdout, self._stderr = stdout, stderr
        self.pid = 4321
        self._done = False

    def poll(self):
        return 0 if self._done else None

    def communicate(self, timeout=None):
        self._done = True
        return self._stdout, self._stderr

    def kill(self):
        self._done = True


def test_run_refines_all_pass(monkeypatch):
    import fdr4
    frame = ('{"results": [{"assertion_string": "A :[deadlock free]", "result": 1},'
             '{"assertion_string": "A :[divergence free]", "result": 1}]}')
    monkeypatch.setattr(fdr4.shutil, "which", lambda _: "refines")
    monkeypatch.setattr(fdr4.subprocess, "Popen",
                        lambda *a, **k: _FakeProc(stdout=frame + "\n"))
    res = fdr4._run_refines(Path("x.csp"), "refines")
    assert len(res["passed"]) == 2
    assert res["failed"] == [] and res["env_error"] is None


def test_run_refines_failure_with_counterexample(monkeypatch):
    import fdr4
    # realistic FDR4 framed_json: nested implementation_behaviour.trace of event
    # ids, plus a frame-level event_map mapping id -> qualified name.
    frame = ('{"event_map": {"4": "M_Module::go.in"}, "results": ['
             '{"assertion_string": "P_M :[deadlock free]", "result": 0,'
             '"counterexamples": [{"type": "deadlock",'
             '"implementation_behaviour": {"trace": [4]}}]}]}')
    monkeypatch.setattr(fdr4.shutil, "which", lambda _: "refines")
    monkeypatch.setattr(fdr4.subprocess, "Popen",
                        lambda *a, **k: _FakeProc(stdout=frame + "\n"))
    res = fdr4._run_refines(Path("x.csp"), "refines")
    assert len(res["failed"]) == 1
    assert res["counterexamples"][0] == ("P_M :[deadlock free]", "deadlock after trace: go")


def test_clean_event_and_format_counterexample():
    import fdr4
    assert fdr4._clean_event("M_Module::ctrl_ref0::go.in") == "go"
    assert fdr4._clean_event("advVel.out") == "advVel"
    a = {"counterexamples": [{"type": "deadlock",
                             "implementation_behaviour": {"trace": [4, 5]}}]}
    s = fdr4._format_counterexample(a, {"4": "M::reqMove.in", "5": "M::tick.in"})
    assert s == "deadlock after trace: reqMove -> tick"
    # empty trace -> reachable-from-initial phrasing
    a2 = {"counterexamples": [{"type": "divergence", "implementation_behaviour": {"trace": []}}]}
    assert "initial" in fdr4._format_counterexample(a2, {})


def test_run_refines_env_error(monkeypatch):
    import fdr4
    monkeypatch.setattr(fdr4.shutil, "which", lambda _: "refines")
    monkeypatch.setattr(fdr4.subprocess, "Popen",
                        lambda *a, **k: _FakeProc(stdout="", stderr="paging file is too small"))
    res = fdr4._run_refines(Path("x.csp"), "refines")
    assert res["env_error"] and "page file" in res["env_error"].lower()


def test_run_refines_missing_tool_raises(monkeypatch):
    import fdr4
    monkeypatch.setattr(fdr4.shutil, "which", lambda _: None)
    with pytest.raises(fdr4.ToolchainUnavailable):
        fdr4._run_refines(Path("x.csp"), "nope")


# --- Task 6: orchestration ---------------------------------------------------

def _ok_rct(tmp_path):
    rct = tmp_path / "result_behaviour_model.rct"
    rct.write_text("module M { }", encoding="utf-8")
    return rct


def test_run_fdr4_check_pass(monkeypatch, tmp_path):
    import fdr4
    rct = _ok_rct(tmp_path)
    monkeypatch.setattr(fdr4, "_generate_csp", lambda *a, **k: tmp_path / "csp-gen")
    monkeypatch.setattr(fdr4, "_apply_type_range_corrections", lambda *a, **k: [])
    monkeypatch.setattr(fdr4, "_discover_coreassertions", lambda *a: tmp_path / "X_coreassertions.csp")
    (tmp_path / "X_coreassertions.csp").write_text("assert P :[deadlock free]\n", encoding="utf-8")
    monkeypatch.setattr(fdr4, "_run_refines", lambda *a, **k: {
        "passed": [{"result": 1}], "failed": [], "inconclusive": [], "errors": [],
        "counterexamples": [], "env_error": None, "assertions": [{"result": 1}]})
    c = fdr4.run_fdr4_check(rct, config={"enabled": True})
    assert c.name == "fdr4_refinement" and c.ok and not c.unverifiable


def test_run_fdr4_check_violation_is_hard_fail(monkeypatch, tmp_path):
    import fdr4
    rct = _ok_rct(tmp_path)
    monkeypatch.setattr(fdr4, "_generate_csp", lambda *a, **k: tmp_path / "csp-gen")
    monkeypatch.setattr(fdr4, "_apply_type_range_corrections", lambda *a, **k: [])
    monkeypatch.setattr(fdr4, "_discover_coreassertions", lambda *a: tmp_path / "X_coreassertions.csp")
    (tmp_path / "X_coreassertions.csp").write_text("assert P :[deadlock free]\n", encoding="utf-8")
    monkeypatch.setattr(fdr4, "_run_refines", lambda *a, **k: {
        "passed": [], "failed": [{"assertion_string": "P :[deadlock free]"}],
        "inconclusive": [], "errors": [], "counterexamples": [("P :[deadlock free]", "e1 -> e2")],
        "env_error": None, "assertions": [{"assertion_string": "P :[deadlock free]"}]})
    c = fdr4.run_fdr4_check(rct, config={"enabled": True})
    assert not c.ok and not c.unverifiable
    assert "deadlock free" in c.detail and "e1 -> e2" in c.detail


def test_run_fdr4_check_toolchain_absent_is_unverifiable(monkeypatch, tmp_path):
    import fdr4
    rct = _ok_rct(tmp_path)

    def _boom(*a, **k):
        raise fdr4.ToolchainUnavailable("forge_transformations_dir not found")
    monkeypatch.setattr(fdr4, "_generate_csp", _boom)
    c = fdr4.run_fdr4_check(rct, config={"enabled": True})
    assert c.unverifiable and not c.ok


def test_generator_errors_extracts_and_dedups():
    from fdr4 import _generator_errors
    out = (
        "Loaded: foo.rct\n"
        "gradlew.bat : ERROR:missing '}' at 'and'\n"
        "ERROR:Couldn't resolve reference to Interface 'Outputs'.\n"
        "ERROR:Couldn't resolve reference to Interface 'Outputs'.\n"   # dup
        "BUILD SUCCESSFUL\n"
    )
    errs = _generator_errors(out)
    assert errs == ["missing '}' at 'and'",
                    "Couldn't resolve reference to Interface 'Outputs'."]


def test_run_fdr4_check_generator_rejected_is_hard_fail(monkeypatch, tmp_path):
    import fdr4
    rct = _ok_rct(tmp_path)

    def _reject(*a, **k):
        raise fdr4.GeneratorRejected(
            ["missing '}' at 'and'", "Couldn't resolve reference to Interface 'Outputs'"])
    monkeypatch.setattr(fdr4, "_generate_csp", _reject)
    c = fdr4.run_fdr4_check(rct, config={"enabled": True})
    assert not c.ok and not c.unverifiable           # hard fail -> triggers repair
    assert "rejected the model" in c.detail
    assert "and" in c.detail and "Outputs" in c.detail


def test_determinism_stripped_by_default(monkeypatch, tmp_path):
    """By default the :[deterministic] assertions are stripped before refines;
    with check_determinism:true they are kept."""
    import fdr4
    rct = _ok_rct(tmp_path)
    monkeypatch.setattr(fdr4, "_generate_csp", lambda *a, **k: tmp_path / "csp-gen")
    monkeypatch.setattr(fdr4, "_apply_type_range_corrections", lambda *a, **k: [])
    ca = tmp_path / "X_coreassertions.csp"
    ca.write_text("assert P :[deadlock-free]\nassert P :[deterministic]\n"
                  "assert P :[divergence-free]\n", encoding="utf-8")
    monkeypatch.setattr(fdr4, "_discover_coreassertions", lambda *a: ca)
    seen = {}

    def _capture(csp_path, *a, **k):
        seen["text"] = Path(csp_path).read_text(encoding="utf-8")
        return {"passed": [{"result": 1}], "failed": [], "inconclusive": [],
                "errors": [], "counterexamples": [], "env_error": None, "assertions": []}
    monkeypatch.setattr(fdr4, "_run_refines", _capture)

    fdr4.run_fdr4_check(rct, config={"enabled": True})        # default
    assert not any(ln.lstrip().startswith("assert") and ":[deterministic]" in ln
                   for ln in seen["text"].splitlines())

    fdr4.run_fdr4_check(rct, config={"enabled": True, "check_determinism": True})
    assert any(ln.lstrip().startswith("assert") and ":[deterministic]" in ln
               for ln in seen["text"].splitlines())


def test_generate_csp_missing_gen_dir_raises(tmp_path):
    import fdr4
    rct = tmp_path / "x.rct"
    rct.write_text("stm M { }", encoding="utf-8")
    with pytest.raises(fdr4.ToolchainUnavailable):
        fdr4._generate_csp(rct, str(tmp_path / "no_such_jars"), timeout=5)


def test_run_fdr4_check_no_coreassertions_is_unverifiable(monkeypatch, tmp_path):
    import fdr4
    rct = _ok_rct(tmp_path)
    monkeypatch.setattr(fdr4, "_generate_csp", lambda *a, **k: tmp_path / "csp-gen")
    monkeypatch.setattr(fdr4, "_apply_type_range_corrections", lambda *a, **k: [])
    monkeypatch.setattr(fdr4, "_discover_coreassertions", lambda *a: None)
    c = fdr4.run_fdr4_check(rct, config={"enabled": True})
    assert c.unverifiable and not c.ok


# --- Task 9: opt-in real-toolchain integration -------------------------------

@pytest.mark.skipif(
    not (os.environ.get("FDR4_PATH") and os.environ.get("FORGE_DIR")),
    reason="set FDR4_PATH and FORGE_DIR to run the real FDR4 toolchain")
def test_run_fdr4_check_real_toolchain(tmp_path):
    """End-to-end against the real FORGE generator + refines.exe.

    A minimal well-formed RoboChart should not be a hard fail (either it
    verifies, or the result is unverifiable for an environmental reason)."""
    import fdr4
    rct = tmp_path / "result_behaviour_model.rct"
    rct.write_text(
        "module Mod {\n"
        "  stm Machine {\n"
        "    initial i0\n"
        "    state S {}\n"
        "    transition t0 { from i0 to S }\n"
        "  }\n"
        "}\n", encoding="utf-8")
    config = {
        "enabled": True,
        "forge_transformations_dir": os.environ["FORGE_DIR"],
        "fdr4_path": os.environ["FDR4_PATH"],
        "memory_limit_mb": 8192,
        "timeout": 600,
    }
    c = fdr4.run_fdr4_check(rct, config=config)
    assert c.name == "fdr4_refinement"
    assert c.ok or c.unverifiable, c.detail
