"""Unit tests for the behaviour-phase RoboChart assembly (normalise + assemble)."""
import sys
from pathlib import Path

MALCOMP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MALCOMP))


# --- normaliser (B2) ---------------------------------------------------------

def test_normalise_fixes_operators_and_strips_uses():
    import behaviour_assembly as ba
    raw = "stm M {\n\tuses Intpus requires Outputs\n\tcondition a < 1 and b > 2 or not c\n}"
    fixed = ba.normalise_stm(raw)
    assert "/\\" in fixed and "\\/" in fixed          # and/or rewritten
    assert " and " not in fixed and " or " not in fixed
    assert "uses Intpus" not in fixed                  # stray uses/requires stripped


def test_normalise_keeps_not_and_identifiers():
    import behaviour_assembly as ba
    fixed = ba.normalise_stm("condition not c /\\ android > 1")
    assert "not c" in fixed                             # 'not' is valid RoboChart, kept
    assert "android" in fixed                           # word-boundary: 'and' in 'android' untouched


def test_normalise_injects_undeclared_types():
    import behaviour_assembly as ba
    fixed = ba.normalise_stm("stm M {\n\tvar c : Obstacle\n\tvar b : boolean\n}")
    assert "enumeration Obstacle {" in fixed            # undeclared capitalised type synthesised
    assert "enumeration boolean" not in fixed           # primitives untouched


def test_normalise_strips_functions_and_rewrites_calls():
    import behaviour_assembly as ba
    src = ("stm M {\n\tcondition odist(cdyn) > 7 /\\ hdist(cstc) < 3\n}\n"
           "function odist ( p : Obstacle ) : real { }\n"
           "function hdist ( p : Obstacle ) : real { }\n")
    fixed = ba.normalise_stm(src)
    assert "function" not in fixed                      # declarations removed
    assert "odist(" not in fixed and "odist_cdyn" in fixed   # call -> variable
    assert "hdist_cstc" in fixed


def test_normalise_strips_event_payloads_and_types():
    import behaviour_assembly as ba
    src = ("stm M {\n\tevent advVel : real\n\tstate S { entry advVel ! 1 }\n"
           "\ttransition t1 { from S to S trigger reqVel ? x action advVel ! x }\n}")
    fixed = ba.normalise_stm(src)
    assert "advVel ! " not in fixed and "reqVel ? " not in fixed   # payloads stripped
    assert "event advVel\n" in fixed or "event advVel " in fixed   # event type stripped
    assert "advVel" in fixed                            # the event itself survives


def test_normalise_keeps_not_equal_operator():
    import behaviour_assembly as ba
    fixed = ba.normalise_stm("condition a != b")
    assert "!=" in fixed                                # `!=` not mistaken for an output `!`


def test_normalise_strips_declaration_semicolons():
    import behaviour_assembly as ba
    src = ("stm M {\n\tvar cobs : Close;\n\tconst Lim : real;\n\tevent tick;\n"
           "\ttransition t1 { from S to S trigger tick }\n}")
    fixed = ba.normalise_stm(src)
    assert "var cobs : Close" in fixed and "Close;" not in fixed
    assert "const Lim : real" in fixed and "real;" not in fixed
    assert "event tick" in fixed and "tick;" not in fixed


def test_normalise_injects_undeclared_events():
    import behaviour_assembly as ba
    src = ("stm M {\n"
           "\tstate S { entry moved }\n"
           "\ttransition t1 { from S to S trigger reqMove action advVel }\n}")
    fixed = ba.normalise_stm(src)
    assert "event reqMove" in fixed     # trigger event declared
    assert "event advVel" in fixed      # action (sync send) event declared
    assert "event moved" in fixed       # entry event declared
    assert "event skip" not in fixed    # 'skip' is not an event


def test_normalise_skips_already_declared_events():
    import behaviour_assembly as ba
    src = "stm M {\n\tevent tick\n\ttransition t1 { from S to S trigger tick }\n}"
    fixed = ba.normalise_stm(src)
    assert fixed.count("event tick") == 1   # not duplicated


def test_normalise_skips_already_declared_types():
    import behaviour_assembly as ba
    src = "enumeration Mode { a b }\nstm M {\n\tvar m : Mode\n}"
    fixed = ba.normalise_stm(src)
    assert fixed.count("enumeration Mode") == 1         # not duplicated


# --- assemble (B1) -----------------------------------------------------------

def test_assemble_uses_normalised_copy_and_leaves_model_unchanged(monkeypatch, tmp_path):
    import behaviour_assembly as ba
    seen = {}

    def fake_run(norm, egl, out):
        seen["norm_text"] = Path(norm).read_text(encoding="utf-8")
        Path(out).write_text("module M { }", encoding="utf-8")
        return True

    monkeypatch.setattr(ba, "_run_assembler", fake_run)
    monkeypatch.setattr(ba.shutil, "which", lambda _: "gradle")  # pretend gradle present
    model = tmp_path / "result_behaviour_model.rct"
    model.write_text("stm M {\n\tcondition x < 1 and y > 2\n}", encoding="utf-8")
    out = tmp_path / "result_behaviour_complete.rct"

    ok = ba.assemble_complete_rct(model, out)
    assert ok
    assert out.read_text(encoding="utf-8").startswith("module")
    # the LLM model is NOT mutated (metrics fidelity) ...
    assert " and " in model.read_text(encoding="utf-8")
    assert "/\\" not in model.read_text(encoding="utf-8")
    # ... but the assembler saw a normalised copy
    assert "/\\" in seen["norm_text"]


def test_assemble_failsoft_writes_normalised_fallback_when_gradle_absent(monkeypatch, tmp_path):
    import behaviour_assembly as ba
    monkeypatch.setattr(ba.shutil, "which", lambda _: None)   # gradle not on PATH
    model = tmp_path / "result_behaviour_model.rct"
    model.write_text("stm M {\n\tcondition a and b\n}", encoding="utf-8")
    out = tmp_path / "result_behaviour_complete.rct"
    assert ba.assemble_complete_rct(model, out) is False
    # fallback: a normalised artefact is still written so FDR4 has something to check
    assert out.is_file() and "/\\" in out.read_text(encoding="utf-8")
    # the model itself is untouched
    assert " and " in model.read_text(encoding="utf-8")


def test_assemble_failsoft_when_runner_fails(monkeypatch, tmp_path):
    import behaviour_assembly as ba
    monkeypatch.setattr(ba.shutil, "which", lambda _: "gradle")
    monkeypatch.setattr(ba, "_run_assembler", lambda *a: False)
    model = tmp_path / "result_behaviour_model.rct"
    model.write_text("stm M { }", encoding="utf-8")
    out = tmp_path / "result_behaviour_complete.rct"
    assert ba.assemble_complete_rct(model, out) is False
    assert out.is_file()   # fallback written
