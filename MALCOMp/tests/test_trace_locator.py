"""Unit tests for the deterministic trace locators."""
import sys
from pathlib import Path

MALCOMP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MALCOMP))

from trace_locator import (  # noqa: E402
    locate, locate_requirement, locate_emfatic_class,
    locate_eol_element, locate_robochart_block,
)

FIXTURES = MALCOMP.parent / "case_studies" / "auv" / "fixtures"


def test_requirement_char_span():
    text = 'The system uses a Sensor named "S1".'
    span = locate_requirement(text, "S1")
    assert span is not None
    start, end = span
    assert text[start:end] == "S1"


def test_requirement_absent_returns_none():
    assert locate_requirement("no match here", "Zzz") is None


def test_requirement_case_insensitive():
    # A capitalised Concept name ("Sensor") must resolve to the lowercase noun in
    # the prose ("sensor"): concept names are often the capitalised form of a word
    # in the requirement text. Without this, overview requirements that introduce
    # concepts (rather than naming concrete instances) leave the trace unresolved.
    text = "The robot carries a single IR distance sensor mounted facing forward."
    span = locate_requirement(text, "Sensor")
    assert span is not None
    start, end = span
    assert text[start:end].lower() == "sensor"


def test_requirement_strips_surrounding_quotes():
    # Extractors sometimes quote instance names ("Moving"); the quotes are not in
    # the prose and must not block resolution.
    text = "At start-up the controller is in Moving."
    span = locate_requirement(text, '"Moving"')
    assert span is not None
    start, end = span
    assert text[start:end] == "Moving"


def test_requirement_camelcase_matches_multiword():
    # A camelCase concept ("StateMachine") resolves to the spaced phrase in prose.
    text = "the controller is a single state machine that selects transitions"
    span = locate_requirement(text, "StateMachine")
    assert span is not None
    start, end = span
    assert text[start:end].lower() == "state machine"


def test_emfatic_class_block_span():
    text = (
        "abstract class NamedElement {\n"
        "    attr String name;\n"
        "}\n"
        "class Module extends NamedElement {\n"
        "    val Platform[*] platforms;\n"
        "}\n"
    )
    span = locate_emfatic_class(text, "Module")
    assert span == (4, 6)  # 1-based: 'class Module' line .. its closing brace


def test_emfatic_class_against_fixture():
    emf = (FIXTURES / "result_dsml.emf").read_text(encoding="utf-8")
    import re
    m = re.search(r"(?m)^\s*(?:abstract\s+)?class\s+(\w+)", emf)
    assert m, "fixture has at least one class"
    name = m.group(1)
    span = locate_emfatic_class(emf, name)
    assert span is not None
    line_start, line_end = span
    assert line_start <= line_end
    assert name in emf.splitlines()[line_start - 1]


def test_eol_element_line():
    text = "{\nvar a_module = new M!Module;\na_module.name = \"A_Module\";\n}\n"
    assert locate_eol_element(text, "a_module") == (2, 2)
    assert locate_eol_element(text, "A_Module") == (3, 3)
    assert locate_eol_element(text, "missing") is None


def test_robochart_transition_block_span():
    text = (
        "stm S {\n"
        "  state Move { }\n"
        "  transition t0 {\n"
        "    from i0\n"
        "    to Move\n"
        "  }\n"
        "}\n"
    )
    assert locate_robochart_block(text, "t0") == (3, 6)
    assert locate_robochart_block(text, "Move") == (2, 2)
    assert locate_robochart_block(text, "t99") is None


def test_locate_dispatch():
    assert locate("requirement", "S1", 'x "S1" y') is not None
    assert locate("eol", "a_module", "var a_module = new M!Module;") == (1, 1)
    import pytest
    with pytest.raises(ValueError):
        locate("nonsense", "x", "y")
