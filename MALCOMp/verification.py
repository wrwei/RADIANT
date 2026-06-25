"""Deterministic per-phase artefact verification (structural + traceability).

Pure functions: an artefact (and an optional MALCOMj runner) -> VerificationResult.
A check whose tool is unavailable is `unverifiable` (soft warning, not a hard fail).
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Check:
    name: str
    kind: str            # "structural" | "traceability"
    ok: bool
    unverifiable: bool
    detail: str


@dataclass(frozen=True)
class VerificationResult:
    phase: str
    checks: list[Check] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.ok or c.unverifiable for c in self.checks)

    @property
    def hard_failures(self) -> list[Check]:
        return [c for c in self.checks if not c.ok and not c.unverifiable]

    def summary(self) -> str:
        marks = []
        for c in self.checks:
            mark = "OK" if c.ok else ("warn" if c.unverifiable else "FAIL")
            marks.append(f"[{mark}] {c.name}" + (f" — {c.detail}" if c.detail else ""))
        return "\n".join(marks)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def trace_resolution_check(trace_path: Path, tag: str) -> Check:
    """Traceability: every entry under `tag` has source.resolved == true."""
    if not trace_path.is_file():
        return Check("trace_resolved", "traceability", False, False,
                     f"missing trace file {trace_path.name}")
    try:
        entries = _read_json(trace_path).get(tag, [])
    except json.JSONDecodeError as ex:
        return Check("trace_resolved", "traceability", False, False, f"invalid JSON: {ex}")
    if not entries:
        return Check("trace_resolved", "traceability", False, False, "trace is empty")
    unresolved = [e for e in entries
                  if isinstance(e, dict) and not (e.get("source") or {}).get("resolved")]
    if unresolved:
        gids = ", ".join(str(e.get("GID") or e.get("requirement_gid") or "?") for e in unresolved[:8])
        return Check("trace_resolved", "traceability", False, False,
                     f"{len(unresolved)} unresolved trace entries (e.g. {gids})")
    return Check("trace_resolved", "traceability", True, False, f"{len(entries)} entries resolved")


def _concept_coverage(trace_path: Path, model_path: Path, requirement_data):
    """Concept extraction must actually cover the requirements. Catches the
    intermittent failure where the model comes back empty / placeholder / severely
    partial, so the repair loop re-extracts (the failure is stochastic — 8/10 runs
    succeed — so a re-roll recovers it). Soft (None) when there is nothing to check."""
    req_ids = [str(r.get("id") or r.get("name")) for r in (requirement_data or [])
               if isinstance(r, dict) and (r.get("id") or r.get("name"))]
    if not req_ids:
        return None, "no requirement GIDs to check"
    if not trace_path.is_file() or not model_path.is_file():
        return None, "missing concept trace/model"
    try:
        entries = _read_json(trace_path).get("term_trace", [])
        n_concepts = len(_read_json(model_path).get("concepts", []))
    except json.JSONDecodeError as ex:
        return None, f"unparseable concept JSON: {ex}"
    covered = {str(e.get("GID")) for e in entries if isinstance(e, dict) and e.get("GID")}
    hit = [g for g in req_ids if g in covered]
    missing = [g for g in req_ids if g not in covered]
    if n_concepts == 0 or len(hit) < len(req_ids) * 0.5:
        return False, (
            f"concept extraction is incomplete ({n_concepts} concepts, "
            f"{len(hit)}/{len(req_ids)} requirement GIDs covered). Re-extract the Concepts "
            f"and Instances so EVERY requirement GID is covered; missing GIDs: "
            + ", ".join(missing[:15])
        )
    return True, f"{len(hit)}/{len(req_ids)} requirement GIDs covered"


def verify_concept(output_dir: Path, *, requirement_data=None, **_) -> VerificationResult:
    checks: list[Check] = []
    trace = output_dir / "result_concept_trace.json"
    model = output_dir / "result_concept_model.json"
    # structural: both JSONs parse; trace entries have GID + Concept/Instance
    try:
        entries = _read_json(trace).get("term_trace", []) if trace.is_file() else None
        _read_json(model) if model.is_file() else None
        if entries is None or not model.is_file():
            checks.append(Check("artefacts_present", "structural", False, False,
                                "missing concept trace or model JSON"))
        else:
            bad = [e for e in entries if not (isinstance(e, dict) and e.get("GID")
                   and (e.get("Concept") or e.get("Instance")))]
            checks.append(Check("schema", "structural", not bad, False,
                                "" if not bad else f"{len(bad)} entries missing GID/Concept/Instance"))
    except json.JSONDecodeError as ex:
        checks.append(Check("json_valid", "structural", False, False, f"invalid JSON: {ex}"))
    checks.append(trace_resolution_check(trace, "term_trace"))
    ok_c, detail_c = _concept_coverage(trace, model, requirement_data)
    checks.append(Check("concept_coverage", "structural", bool(ok_c), ok_c is None, detail_c))
    return VerificationResult("concept", checks)


# --- structural helpers (reuse existing parsers; all fail-soft) ---------------

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _behaviour_parse(rct_path: Path):
    """Return (ok: bool|None, detail). None == unverifiable."""
    try:
        import sys
        sys_path = str(_REPO_ROOT / "malcom.evaluation" / "metrics" / "behaviour")
        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)
        from metrics import parse_state_machine_file  # type: ignore
    except Exception as ex:  # parser unavailable
        return None, f"RoboChart parser unavailable: {ex}"
    try:
        # Structural validity = the hand-rolled parser accepts the file without
        # raising. (Avoid depending on the parsed object's attribute names.)
        parse_state_machine_file(rct_path)
        return True, "RoboChart parsed"
    except Exception as ex:
        return False, f"RoboChart parse failed: {ex}"


def _emfatic_syntax_ok(emf_path: Path):
    """Official Emfatic parser (the shipped MALCOMj EmfaticHelper). Returns
    (ok: bool|None, detail); None == unverifiable (MALCOMj not built / no Java)."""
    try:
        import sys
        sys_path = str(_REPO_ROOT / "malcom.evaluation" / "metrics" / "dsml")
        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)
        from syntax_checker import EmfaticSyntaxChecker  # type: ignore
        result = EmfaticSyntaxChecker(_REPO_ROOT).check(emf_path)
    except Exception as ex:
        return None, f"EmfaticHelper unavailable (build MALCOMj): {ex}"
    if result.syntax_ok:
        return True, f"emfatic syntax ok ({result.warning_count} warnings)"
    return False, f"emfatic syntax errors: {result.error_summary}"


def _emfatic_converts(emf_path: Path):
    """Structural check: the pipeline's own Emfatic->Ecore conversion succeeds.

    Uses the SAME parser the pipeline uses downstream (convert_emfatic_to_ecore),
    not the official Emfatic parser: the pipeline deliberately emits package-less,
    class-only Emfatic, which the strict standalone parser rejects. Pure Python —
    no Java/classpath, so this is a real check (rarely unverifiable)."""
    if not emf_path.is_file():
        return False, f"missing {emf_path.name}"
    try:
        from eol_execution import convert_emfatic_to_ecore
    except Exception as ex:
        return None, f"emfatic converter unavailable: {ex}"
    try:
        convert_emfatic_to_ecore(emf_path, emf_path.parent / (emf_path.stem + ".verify.ecore"))
        return True, "emfatic converts to ecore"
    except Exception as ex:
        return False, f"emfatic conversion failed: {ex}"


def _eol_executes(output_dir: Path, malcomj_runner):
    """Return (ok: bool|None, detail). None == unverifiable (no runner)."""
    if malcomj_runner is None or not Path(malcomj_runner).exists():
        return None, "MALCOMj runner not installed"
    try:
        from eol_execution import convert_emfatic_to_ecore, execute_eol
        emf = output_dir / "result_dsml.emf"
        eol = output_dir / "result_model.eol"
        if not emf.is_file() or not eol.is_file():
            return False, "missing result_dsml.emf or result_model.eol"
        ecore = output_dir / "result_dsml.verify.ecore"
        convert_emfatic_to_ecore(emf, ecore)
        res = execute_eol(
            runner=Path(malcomj_runner), eol_path=eol, ecore_path=ecore,
            attempt_model_path=output_dir / "result.verify.model",
            accepted_model_path=output_dir / "result.verify.accepted.model",
            timeout_seconds=60,
        )
        return (True, "EOL executed; model conforms") if res.ok else (False, res.error_summary)
    except Exception as ex:
        return None, f"EOL execution could not run: {ex}"


def verify_dsml(output_dir: Path, **_) -> VerificationResult:
    emf = output_dir / "result_dsml.emf"
    # Prefer the shipped official Emfatic parser; fall back to the pipeline's own
    # converter (pure Python) when MALCOMj isn't built, so it's never a soft warn.
    ok, detail = _emfatic_syntax_ok(emf)
    if ok is None:
        ok, detail = _emfatic_converts(emf)
    structural = Check("emfatic_valid", "structural", bool(ok), ok is None, detail)
    return VerificationResult("dsml", [
        structural, trace_resolution_check(output_dir / "result_dsml_trace.json", "dsl_trace")])


def verify_model(output_dir: Path, *, malcomj_runner=None, **_) -> VerificationResult:
    ok, detail = _eol_executes(output_dir, malcomj_runner)
    structural = Check("eol_executes", "structural", bool(ok), ok is None, detail)
    return VerificationResult("model", [
        structural, trace_resolution_check(output_dir / "result_model_trace.json", "model_trace")])


# --- behaviour completeness (requirement transitions vs generated machine) ----
# The boolean abstraction (mandated for FDR) can make two distinct requirement
# transitions look identical and get silently merged, dropping a transition.
# Prompts alone don't prevent this, so we check it structurally and repair.
_REQ_TRANSITION_RE = re.compile(r"transition\s+from\s+(\w+)\s+to\s+(\w+)", re.IGNORECASE)
_RCT_TRANSITION_RE = re.compile(r"transition\s+\w+\s*\{([^}]*)\}", re.DOTALL)
_RCT_INITIAL_RE = re.compile(r"\binitial\s+(\w+)")


def _expected_transition_counts(requirement_data) -> Counter:
    """Per (source,target) count of transitions the requirements describe, parsed
    from the behaviour requirement descriptions ('... transition from X to Y ...').
    The initial transition (phrased 'shall be in <state>') is not counted."""
    counts: Counter = Counter()
    for req in requirement_data or []:
        desc = (req.get("description") if isinstance(req, dict) else str(req)) or ""
        for m in _REQ_TRANSITION_RE.finditer(desc):
            counts[(m.group(1).lower(), m.group(2).lower())] += 1
    return counts


def _actual_transition_counts(rct_text: str) -> Counter:
    """Per (source,target) count of non-initial transitions in a generated .rct."""
    initials = {m.lower() for m in _RCT_INITIAL_RE.findall(rct_text)}
    counts: Counter = Counter()
    for m in _RCT_TRANSITION_RE.finditer(rct_text):
        body = m.group(1)
        fm = re.search(r"\bfrom\s+(\w+)", body)
        tm = re.search(r"\bto\s+(\w+)", body)
        if fm and tm and fm.group(1).lower() not in initials:
            counts[(fm.group(1).lower(), tm.group(1).lower())] += 1
    return counts


def _requirements_for_pair(requirement_data, src: str, tgt: str):
    """The requirement (id, description) pairs that specify a src->tgt transition."""
    out = []
    for req in requirement_data or []:
        desc = (req.get("description") if isinstance(req, dict) else str(req)) or ""
        for m in _REQ_TRANSITION_RE.finditer(desc):
            if m.group(1).lower() == src and m.group(2).lower() == tgt:
                gid = (req.get("id") or req.get("name") or "?") if isinstance(req, dict) else "?"
                out.append((gid, " ".join(desc.split())))
                break
    return out


def _behaviour_completeness(rct_path: Path, requirement_data):
    """Compare requirement-specified transition counts against the generated
    machine. Returns (None, ...) when there is nothing to check (so it is a soft
    warning), (False, detail) when transitions are missing, else (True, ...).

    The failure detail lists the actual requirement statements for each deficient
    state pair, so the repair agent knows exactly which transitions to add (a bare
    count was not enough for it to recover the dropped transition)."""
    expected = _expected_transition_counts(requirement_data)
    if not expected:
        return None, "no requirement transitions to check"
    if not rct_path.is_file():
        return None, f"missing {rct_path.name}"
    actual = _actual_transition_counts(rct_path.read_text(encoding="utf-8"))
    blocks = []
    for (src, tgt), exp in sorted(expected.items()):
        have = actual.get((src, tgt), 0)
        if have < exp:
            reqs = _requirements_for_pair(requirement_data, src, tgt)
            listed = "".join(f"\n    [{gid}] {desc}" for gid, desc in reqs)
            blocks.append(
                f"{src}->{tgt}: requirements specify {exp}, model has {have}. "
                f"The {exp} required transitions are:{listed}"
            )
    if blocks:
        return False, (
            "incomplete state machine — every requirement transition below MUST be its "
            "own transition block with its OWN distinct boolean guard variable; do NOT "
            "merge two of them into one. Add the missing ones:\n" + "\n".join(blocks)
        )
    return True, f"all {sum(expected.values())} requirement transitions present"


def verify_behaviour(output_dir: Path, *, requirement_data=None, fdr4_config=None, **_) -> VerificationResult:
    # The LLM's behaviour model (compared by the metrics) is parse-checked; the
    # assembled generator-ready model (result_behaviour_complete.rct) is what FDR4
    # verifies. The complete model falls back to the LLM model when assembly was
    # skipped (toolchain absent / FDR4 disabled).
    checks: list[Check] = []
    ok, detail = _behaviour_parse(output_dir / "result_behaviour_model.rct")
    checks.append(Check("robochart_parses", "structural", bool(ok), ok is None, detail))
    ok_c, detail_c = _behaviour_completeness(
        output_dir / "result_behaviour_model.rct", requirement_data)
    checks.append(Check("behaviour_completeness", "structural", bool(ok_c), ok_c is None, detail_c))
    if fdr4_config and fdr4_config.get("enabled"):
        complete = output_dir / "result_behaviour_complete.rct"
        target = complete if complete.is_file() else output_dir / "result_behaviour_model.rct"
        try:
            from fdr4 import run_fdr4_check
            checks.append(run_fdr4_check(target, config=fdr4_config))
        except Exception as ex:  # importing/calling must never crash the gate
            checks.append(Check("fdr4_refinement", "structural", False, True,
                                f"FDR4 check unavailable: {ex}"))
    checks.append(trace_resolution_check(
        output_dir / "result_behaviour_trace.json", "stm_trace"))
    return VerificationResult("behaviour", checks)


_VERIFIERS = {
    "concept": verify_concept,
    "dsml": verify_dsml,
    "model": verify_model,
    "behaviour": verify_behaviour,
}


def verify(phase_key: str, output_dir: Path, *, malcomj_runner=None,
           requirement_data=None, fdr4_config=None) -> VerificationResult:
    try:
        fn = _VERIFIERS[phase_key]
    except KeyError:
        raise ValueError(f"unknown phase {phase_key!r}")
    return fn(output_dir, malcomj_runner=malcomj_runner,
              requirement_data=requirement_data, fdr4_config=fdr4_config)
