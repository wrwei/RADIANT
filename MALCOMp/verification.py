"""Deterministic per-phase artefact verification (structural + traceability).

Pure functions: an artefact (and an optional MALCOMj runner) -> VerificationResult.
A check whose tool is unavailable is `unverifiable` (soft warning, not a hard fail).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, replace
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
    """The outcome of one phase's gate.

    A phase has THREE distinguishable outcomes, and callers that report
    verification status must not collapse them:

    * ``passed`` and no ``unverified`` checks — every check ran and succeeded.
      This is the only state in which the artefact has actually been verified.
    * ``passed`` with a non-empty ``unverified`` — the artefact was accepted
      because the checks that did run succeeded, but one or more checks could
      not run at all (external tool absent). Nothing was proved about those
      properties. Use ``fully_verified`` to test for this.
    * not ``passed`` — a check ran and failed; ``hard_failures`` drives repair.

    ``strict=True`` promotes unrunnable checks to failures, so a run can be
    configured to refuse to accept an artefact whose checks never executed.
    """

    phase: str
    checks: list[Check] = field(default_factory=list)
    strict: bool = False

    @property
    def passed(self) -> bool:
        if self.strict:
            return all(c.ok for c in self.checks)
        return all(c.ok or c.unverifiable for c in self.checks)

    @property
    def hard_failures(self) -> list[Check]:
        if self.strict:
            return [c for c in self.checks if not c.ok]
        return [c for c in self.checks if not c.ok and not c.unverifiable]

    @property
    def unverified(self) -> list[Check]:
        """Checks that could not run (external tool absent). Non-empty means
        the phase was accepted without those properties being established."""
        return [c for c in self.checks if c.unverifiable]

    @property
    def fully_verified(self) -> bool:
        """True only when every check actually ran and succeeded."""
        return bool(self.checks) and all(c.ok for c in self.checks)

    def summary(self) -> str:
        marks = []
        for c in self.checks:
            mark = "OK" if c.ok else ("UNVERIFIED" if c.unverifiable else "FAIL")
            marks.append(f"[{mark}] {c.name}" + (f" — {c.detail}" if c.detail else ""))
        if self.unverified and not self.strict:
            marks.append(
                f"NOTE: {len(self.unverified)} check(s) could not run; this phase was "
                "accepted WITHOUT verifying those properties "
                "(set verification.strict=true to refuse such artefacts).")
        return "\n".join(marks)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _entries_under_tag(data, tag: str, legacy=(), fname: str = "") -> list:
    """Entries under `tag`, falling back to a `legacy` tag with a warning (the
    concept phase emitted "req" before the tag was renamed "term_trace")."""
    if not isinstance(data, dict):
        return []
    if isinstance(data.get(tag), list):
        return data[tag]
    for old in legacy:
        if isinstance(data.get(old), list):
            logger.warning("%s uses the legacy trace tag %r (current: %r) — "
                           "regenerate this artefact.", fname, old, tag)
            return data[old]
    return []


def trace_resolution_check(trace_path: Path, tag: str, legacy=()) -> Check:
    """Traceability: every entry under `tag` has source.resolved == true."""
    if not trace_path.is_file():
        return Check("trace_resolved", "traceability", False, False,
                     f"missing trace file {trace_path.name}")
    try:
        entries = _entries_under_tag(_read_json(trace_path), tag, legacy,
                                     trace_path.name)
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


def verify_concept(output_dir: Path, **_) -> VerificationResult:
    checks: list[Check] = []
    trace = output_dir / "result_concept_trace.json"
    model = output_dir / "result_concept_model.json"
    # structural: both JSONs parse; trace entries have GID + Concept/Instance
    try:
        entries = (_entries_under_tag(_read_json(trace), "term_trace", ("req",),
                                      trace.name) if trace.is_file() else None)
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
    checks.append(trace_resolution_check(trace, "term_trace", legacy=("req",)))
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


def verify_behaviour(output_dir: Path, *, fdr4_config=None, **_) -> VerificationResult:
    # The LLM's behaviour model (compared by the metrics) is parse-checked; the
    # assembled generator-ready model (result_behaviour_complete.rct) is what FDR4
    # verifies. The complete model falls back to the LLM model when assembly was
    # skipped (toolchain absent / FDR4 disabled).
    checks: list[Check] = []
    ok, detail = _behaviour_parse(output_dir / "result_behaviour_model.rct")
    checks.append(Check("robochart_parses", "structural", bool(ok), ok is None, detail))
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
           requirement_data=None, fdr4_config=None,
           strict: bool = False) -> VerificationResult:
    """Run `phase_key`'s gate over `output_dir`.

    `strict=True` refuses artefacts whose checks could not run (external tool
    absent) instead of accepting them with a warning; see VerificationResult.
    Unrunnable checks are always logged at WARNING so a run on an incomplete
    toolchain cannot look silently clean.
    """
    try:
        fn = _VERIFIERS[phase_key]
    except KeyError:
        raise ValueError(f"unknown phase {phase_key!r}")
    result = fn(output_dir, malcomj_runner=malcomj_runner,
                requirement_data=requirement_data, fdr4_config=fdr4_config)
    if strict:
        result = replace(result, strict=True)
    if result.unverified:
        logger.warning(
            "phase %s: %d check(s) could not run (%s). The phase is %s; the "
            "corresponding properties were NOT verified.",
            result.phase, len(result.unverified),
            "; ".join(f"{c.name}: {c.detail}" for c in result.unverified),
            "REJECTED (strict)" if strict else "accepted anyway",
        )
    return result
