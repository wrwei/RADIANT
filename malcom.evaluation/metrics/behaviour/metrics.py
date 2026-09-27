"""Stage-specific metrics for generated RoboChart-like state-machine text."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


_NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")
_STM_HEADER_RE = re.compile(r"\bstm\s+(?P<name>[A-Za-z_]\w*)\s*\{")
_STATE_RE = re.compile(r"\bstate\s+(?P<name>[A-Za-z_]\w*)\b")
_TRANSITION_HEADER_RE = re.compile(r"\btransition\s+(?P<name>[A-Za-z_]\w*)\s*\{")
_INITIAL_RE = re.compile(r"\binitial\s+(?P<name>[A-Za-z_]\w*)\b")
_USE_RE = re.compile(r"\buses\s+(?P<value>[A-Za-z_][\w]*(?:\s*,\s*[A-Za-z_][\w]*)*)")
_VAR_RE = re.compile(r"\bvar\s+(?P<name>[A-Za-z_]\w*)\s*:\s*(?P<type>[A-Za-z_]\w*)")
_CONST_RE = re.compile(r"\bconst\s+(?P<name>[A-Za-z_]\w*)\s*:\s*(?P<type>[A-Za-z_]\w*)")
_EVENT_RE = re.compile(r"\bevent\s+(?P<name>[A-Za-z_]\w*)\b")
_FUNCTION_RE = re.compile(r"\bfunction\s+(?P<name>[A-Za-z_]\w*)\s*\((?P<params>[^)]*)\)\s*:\s*(?P<ret>[A-Za-z_]\w*)")
_FROM_RE = re.compile(r"\bfrom\s+(?P<value>[A-Za-z_]\w*)\b")
_TO_RE = re.compile(r"\bto\s+(?P<value>[A-Za-z_]\w*)\b")
_TRIGGER_RE = re.compile(r"\btrigger\s+(?P<value>.*?)(?=\bcondition\b|\baction\b|$)", re.S)
_CONDITION_RE = re.compile(r"\bcondition\s+(?P<value>.*?)(?=\btrigger\b|\baction\b|$)", re.S)
_ACTION_RE = re.compile(r"\baction\s+(?P<value>.*?)(?=\btrigger\b|\bcondition\b|$)", re.S)


@dataclass(frozen=True)
class PRF:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int


@dataclass(frozen=True)
class StateMachine:
    syntax_ok: bool
    name: str
    uses: set[str]
    initials: set[str]
    states: set[str]
    transitions: dict[str, dict[str, str]]
    variables: set[tuple[str, str]]
    constants: set[tuple[str, str]]
    events: set[str]
    functions: set[tuple[str, str]]
    diagnostics: str = ""


@dataclass(frozen=True)
class StateMachineScore:
    run_id: str
    syntax_ok: float
    pred_states: int
    ref_states: int
    pred_initials: int
    ref_initials: int
    pred_transitions: int
    ref_transitions: int
    state_f1: float
    initial_f1: float
    transition_id_f1: float
    transition_edge_f1: float
    behavior_micro_f1: float
    variable_f1: float
    constant_f1: float
    function_f1: float
    trigger_f1: float
    condition_f1: float
    action_f1: float
    detail_micro_f1: float
    full_micro_f1: float
    error: str = ""

    def as_row(self) -> dict[str, object]:
        return self.__dict__.copy()


def canonical(value: object) -> str:
    return _NON_ALNUM_RE.sub("", str(value or "").strip().casefold())


def norm_expr(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def clause_value(pattern: re.Pattern[str], body: str) -> str:
    match = pattern.search(body)
    return norm_expr(match.group("value")) if match else ""


def find_matching_brace(text: str, open_idx: int) -> int:
    depth = 1
    for idx in range(open_idx + 1, len(text)):
        char = text[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return idx
    return -1


def strip_fence(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```[A-Za-z0-9_-]*\s*\n(.*)\n```", stripped, re.DOTALL)
    return match.group(1).strip() if match else text


def parse_state_machine_text(text: str) -> StateMachine:
    text = strip_fence(text)
    text = _LINE_COMMENT_RE.sub("", text)
    diagnostics: list[str] = []
    stm_match = _STM_HEADER_RE.search(text)
    if not stm_match:
        return StateMachine(False, "", set(), set(), set(), {}, set(), set(), set(), set(), "no stm block")

    stm_name = stm_match.group("name")
    open_idx = stm_match.end() - 1
    close_idx = find_matching_brace(text, open_idx)
    if close_idx < 0:
        return StateMachine(False, stm_name, set(), set(), set(), {}, set(), set(), set(), set(), "unmatched stm brace")
    body = text[open_idx + 1:close_idx]

    uses: set[str] = set()
    for match in _USE_RE.finditer(body):
        uses.update(canonical(item) for item in match.group("value").split(",") if item.strip())
    initials = {canonical(m.group("name")) for m in _INITIAL_RE.finditer(body)}
    states = {canonical(m.group("name")) for m in _STATE_RE.finditer(body)}
    variables = {(canonical(m.group("name")), canonical(m.group("type"))) for m in _VAR_RE.finditer(body)}
    constants = {(canonical(m.group("name")), canonical(m.group("type"))) for m in _CONST_RE.finditer(body)}
    events = {canonical(m.group("name")) for m in _EVENT_RE.finditer(body)}

    functions = {
        (canonical(m.group("name")), canonical(m.group("ret")))
        for m in _FUNCTION_RE.finditer(text)
    }

    transitions: dict[str, dict[str, str]] = {}
    for match in _TRANSITION_HEADER_RE.finditer(body):
        name = canonical(match.group("name"))
        t_open = match.end() - 1
        t_close = find_matching_brace(body, t_open)
        if t_close < 0:
            diagnostics.append(f"unmatched transition brace: {name}")
            continue
        t_body = body[t_open + 1:t_close]
        transitions[name] = {
            "from": canonical(clause_value(_FROM_RE, t_body)),
            "to": canonical(clause_value(_TO_RE, t_body)),
            "trigger": canonical(clause_value(_TRIGGER_RE, t_body)),
            "condition": canonical(clause_value(_CONDITION_RE, t_body)),
            "action": canonical(clause_value(_ACTION_RE, t_body)),
        }

    known_nodes = initials | states
    for name, trans in transitions.items():
        if not trans["from"] or not trans["to"]:
            diagnostics.append(f"transition {name} missing from/to")
        elif trans["from"] not in known_nodes or trans["to"] not in known_nodes:
            diagnostics.append(f"transition {name} refers to unknown node")
    syntax_ok = not diagnostics and bool(states) and bool(initials) and bool(transitions)
    return StateMachine(
        syntax_ok=syntax_ok,
        name=canonical(stm_name),
        uses=uses,
        initials=initials,
        states=states,
        transitions=transitions,
        variables=variables,
        constants=constants,
        events=events,
        functions=functions,
        diagnostics="; ".join(diagnostics),
    )


def parse_state_machine_file(path: Path) -> StateMachine:
    return parse_state_machine_text(Path(path).read_text(encoding="utf-8"))


def prf_set(pred: set[tuple[str, ...]] | set[str], ref: set[tuple[str, ...]] | set[str]) -> PRF:
    pred_set = set(pred)
    ref_set = set(ref)
    tp = len(pred_set & ref_set)
    fp = len(pred_set - ref_set)
    fn = len(ref_set - pred_set)
    precision = tp / (tp + fp) if (tp + fp) else (1.0 if not ref_set else 0.0)
    recall = tp / (tp + fn) if (tp + fn) else (1.0 if not pred_set else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return PRF(precision, recall, f1, tp, fp, fn)


def prf_counter(pred: Counter[tuple[str, ...]], ref: Counter[tuple[str, ...]]) -> PRF:
    keys = set(pred) | set(ref)
    tp = sum(min(pred[key], ref[key]) for key in keys)
    fp = sum(max(pred[key] - ref[key], 0) for key in keys)
    fn = sum(max(ref[key] - pred[key], 0) for key in keys)
    precision = tp / (tp + fp) if (tp + fp) else (1.0 if not ref else 0.0)
    recall = tp / (tp + fn) if (tp + fn) else (1.0 if not pred else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return PRF(precision, recall, f1, tp, fp, fn)


def facts(sm: StateMachine) -> dict[str, set[tuple[str, ...]]]:
    transition_id = {
        ("transition", name, trans["from"], trans["to"])
        for name, trans in sm.transitions.items()
    }
    transition_edge = Counter(
        ("edge", trans["from"], trans["to"])
        for trans in sm.transitions.values()
    )
    trigger = {
        ("trigger", trans["from"], trans["to"], trans["trigger"])
        for trans in sm.transitions.values()
        if trans["trigger"]
    }
    condition = {
        ("condition", trans["from"], trans["to"], trans["condition"])
        for trans in sm.transitions.values()
        if trans["condition"]
    }
    action = {
        ("action", trans["from"], trans["to"], trans["action"])
        for trans in sm.transitions.values()
        if trans["action"]
    }
    return {
        "states": {("state", state) for state in sm.states},
        "initials": {("initial", initial) for initial in sm.initials},
        "transition_id": transition_id,
        "transition_edge": set(transition_edge.elements()),
        "variables": {("var", name, typ) for name, typ in sm.variables},
        "constants": {("const", name, typ) for name, typ in sm.constants},
        "functions": {("function", name, ret) for name, ret in sm.functions},
        "triggers": trigger,
        "conditions": condition,
        "actions": action,
    }


def score_file(pred_path: Path, ref_path: Path) -> StateMachineScore:
    run_id = Path(pred_path).parent.name
    try:
        pred = parse_state_machine_file(pred_path)
        ref = parse_state_machine_file(ref_path)
        pred_facts = facts(pred)
        ref_facts = facts(ref)

        state = prf_set(pred_facts["states"], ref_facts["states"])
        initial = prf_set(pred_facts["initials"], ref_facts["initials"])
        transition_id = prf_set(pred_facts["transition_id"], ref_facts["transition_id"])
        edge = prf_counter(
            Counter(pred_facts["transition_edge"]),
            Counter(ref_facts["transition_edge"]),
        )
        variable = prf_set(pred_facts["variables"], ref_facts["variables"])
        constant = prf_set(pred_facts["constants"], ref_facts["constants"])
        function = prf_set(pred_facts["functions"], ref_facts["functions"])
        trigger = prf_set(pred_facts["triggers"], ref_facts["triggers"])
        condition = prf_set(pred_facts["conditions"], ref_facts["conditions"])
        action = prf_set(pred_facts["actions"], ref_facts["actions"])

        behavior_pred = set().union(pred_facts["states"], pred_facts["initials"])
        behavior_ref = set().union(ref_facts["states"], ref_facts["initials"])
        behavior_pred_counter = Counter(behavior_pred)
        behavior_ref_counter = Counter(behavior_ref)
        behavior_pred_counter.update(Counter(pred_facts["transition_edge"]))
        behavior_ref_counter.update(Counter(ref_facts["transition_edge"]))
        behavior = prf_counter(behavior_pred_counter, behavior_ref_counter)

        detail_pred = set().union(
            pred_facts["variables"], pred_facts["constants"], pred_facts["functions"],
            pred_facts["triggers"], pred_facts["conditions"], pred_facts["actions"],
        )
        detail_ref = set().union(
            ref_facts["variables"], ref_facts["constants"], ref_facts["functions"],
            ref_facts["triggers"], ref_facts["conditions"], ref_facts["actions"],
        )
        detail = prf_set(detail_pred, detail_ref)
        full = prf_set(set(behavior_pred_counter.elements()) | detail_pred, set(behavior_ref_counter.elements()) | detail_ref)

        return StateMachineScore(
            run_id=run_id,
            syntax_ok=1.0 if pred.syntax_ok else 0.0,
            pred_states=len(pred.states),
            ref_states=len(ref.states),
            pred_initials=len(pred.initials),
            ref_initials=len(ref.initials),
            pred_transitions=len(pred.transitions),
            ref_transitions=len(ref.transitions),
            state_f1=state.f1,
            initial_f1=initial.f1,
            transition_id_f1=transition_id.f1,
            transition_edge_f1=edge.f1,
            behavior_micro_f1=behavior.f1,
            variable_f1=variable.f1,
            constant_f1=constant.f1,
            function_f1=function.f1,
            trigger_f1=trigger.f1,
            condition_f1=condition.f1,
            action_f1=action.f1,
            detail_micro_f1=detail.f1,
            full_micro_f1=full.f1,
            error=pred.diagnostics,
        )
    except Exception as ex:
        return StateMachineScore(
            run_id=run_id,
            syntax_ok=0.0,
            pred_states=0,
            ref_states=0,
            pred_initials=0,
            ref_initials=0,
            pred_transitions=0,
            ref_transitions=0,
            state_f1=0.0,
            initial_f1=0.0,
            transition_id_f1=0.0,
            transition_edge_f1=0.0,
            behavior_micro_f1=0.0,
            variable_f1=0.0,
            constant_f1=0.0,
            function_f1=0.0,
            trigger_f1=0.0,
            condition_f1=0.0,
            action_f1=0.0,
            detail_micro_f1=0.0,
            full_micro_f1=0.0,
            error=str(ex),
        )
