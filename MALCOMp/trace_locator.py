"""Deterministic source locators for requirement->element traceability.

Given an artefact's text and the canonical id of an element, return where that
element lives: a character span for requirement text, a 1-based line span for
code artefacts. Pure functions, no I/O, so each adapter is unit-testable.
"""
import re

__all__ = [
    "locate", "locate_requirement", "locate_emfatic_class",
    "locate_eol_element", "locate_robochart_block",
]


def _line_of_offset(text: str, offset: int) -> int:
    """1-based line number containing character `offset`."""
    return text.count("\n", 0, offset) + 1


def _block_span(text: str, header_start: int) -> tuple[int, int]:
    """1-based (line_start, line_end) from a `... {` header to its matching `}`.

    `header_start` is the char index where the declaration begins. If no brace
    follows, returns a single-line span on the header line.
    """
    line_start = _line_of_offset(text, header_start)
    brace = text.find("{", header_start)
    if brace == -1:
        return line_start, line_start
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return line_start, _line_of_offset(text, i)
    return line_start, _line_of_offset(text, len(text) - 1)


def _word_search(text: str, element_id: str):
    """First whole-identifier occurrence of `element_id`, or None.

    A bare ``str.find`` matches inside longer identifiers ("dist" inside
    "ns_rel_dist", "Type" inside "PrimitiveType"), silently yielding a trace
    span that points at a *different* element. Requiring identifier boundaries
    means an element that is not present simply does not resolve — which the
    trace machinery already represents faithfully as ``resolved: False`` —
    rather than resolving to the wrong place.
    """
    if not element_id:
        return None
    m = re.search(rf"(?<![0-9A-Za-z_]){re.escape(element_id)}(?![0-9A-Za-z_])", text)
    return (m.start(), m.end()) if m else None


def locate_requirement(text: str, element_id: str) -> tuple[int, int] | None:
    """Char span (start, end) of element_id within a requirement description."""
    span = _word_search(text, element_id)
    return span if span else None


def locate_emfatic_class(text: str, element_id: str) -> tuple[int, int] | None:
    """Line span of `class <id>` (optionally `abstract class`) in Emfatic."""
    if not element_id:
        return None
    m = re.search(rf"(?m)^[ \t]*(?:abstract\s+)?class\s+{re.escape(element_id)}\b", text)
    return _block_span(text, m.start()) if m else None


def locate_eol_element(text: str, element_id: str) -> tuple[int, int] | None:
    """Line of `element_id` in an EOL program.

    Prefers the element's declaration (``var <id> = ...``) over any earlier
    mention, and matches on identifier boundaries so a short id cannot resolve
    to a longer identifier that contains it.
    """
    if not element_id:
        return None
    decl = re.search(
        rf"(?m)^[ \t]*var\s+{re.escape(element_id)}(?![0-9A-Za-z_])", text)
    if decl:
        line = _line_of_offset(text, decl.start())
        return line, line
    span = _word_search(text, element_id)
    if not span:
        return None
    line = _line_of_offset(text, span[0])
    return line, line


def locate_robochart_block(text: str, element_id: str) -> tuple[int, int] | None:
    """Line span of `transition <id> { ... }` or `state <id> { ... }`."""
    if not element_id:
        return None
    m = re.search(rf"(?m)^[ \t]*(?:transition|state)\s+{re.escape(element_id)}\b", text)
    return _block_span(text, m.start()) if m else None


_ADAPTERS = {
    "requirement": locate_requirement,
    "emfatic": locate_emfatic_class,
    "eol": locate_eol_element,
    "robochart": locate_robochart_block,
}


def locate(kind: str, element_id: str, text: str) -> tuple[int, int] | None:
    """Dispatch to the adapter for `kind`. Returns (start, end): char offsets
    for 'requirement', 1-based line numbers otherwise; or None if not found."""
    try:
        adapter = _ADAPTERS[kind]
    except KeyError:
        raise ValueError(f"unknown locator kind {kind!r}")
    return adapter(text, element_id)
