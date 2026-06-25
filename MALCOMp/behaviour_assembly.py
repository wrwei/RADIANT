"""Assemble a complete, generator-ready RoboChart `.rct` from a bare `stm`.

Pipeline (all in MALCOMj): the LLM-produced bare state machine is normalised for
common syntax slips, then MALCOMj's `RoboChartAssembler` parses it via the official
RoboChart Xtext setup and runs the vendored `robochart2rct.egl` to synthesise the
interfaces / robotic platform / controller / module around it.

Run as a Gradle task (`roboChartAssemble`) rather than the install-dist runner: the
vendored RoboChart bundle and MALCOMj's maven Epsilon deps both carry Eclipse/EMF
runtime jars, and a flat `java -cp` classpath mixes their signers; Gradle's resolved
classpath loads consistently.

Fail-soft: every failure path returns False and leaves the bare stm in place, so the
behaviour phase still produces an artefact (the FDR4 `GeneratorRejected` check is the
backstop that reports an unassembled/invalid model).
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MALCOMJ_DIR = _REPO_ROOT / "MALCOMj"
_EGL = _MALCOMJ_DIR / "src" / "main" / "resources" / "transformations" / "robochart2rct.egl"


# RoboChart primitive types (lowercase) — never need a synthesised declaration.
_PRIMITIVE_TYPES = {"int", "nat", "real", "boolean", "string", "natural"}


def normalise_stm(text: str) -> str:
    """Fix the common LLM RoboChart slips before parsing: boolean operators, stray
    `uses`/`requires` clauses, and undeclared domain types.

    - `and`/`or` -> RoboChart conjunction `/\\` / disjunction `\\/`.
    - drop `uses ... requires ...` lines (the EGL synthesises those interfaces).
    - inject an `enumeration` declaration for every referenced-but-undeclared
      capitalised type (e.g. `var c : Obstacle`), so the model parses with concrete,
      FDR-enumerable domain types instead of unresolved proxies that crash the EGL.
    """
    # Remove uninterpreted function declarations (`function f ( p : T ) : R { }`):
    # they are not FDR-verifiable and crash the generator's type resolution.
    text = re.sub(r"(?m)^[ \t]*function\s+\w+\s*\([^)]*\)\s*:\s*\w+\s*\{\s*\}[ \t]*\r?\n?",
                  "", text)
    # Rewrite the matching function CALLS into opaque guard variables so the guard
    # structure survives: `odist(cdyn)` -> `odist_cdyn`, `move(lv, a)` -> `move_lv_a`.
    def _call_to_var(m):
        fn, args = m.group(1), m.group(2)
        san = re.sub(r"[^0-9A-Za-z]+", "_", args.strip()).strip("_")
        return f"{fn}_{san}" if san else fn
    text = re.sub(r"\b([A-Za-z]\w*)\s*\(\s*([^()]*?)\s*\)", _call_to_var, text)

    # Strip event data payloads so events are plain synchronisations (untyped
    # events can't carry data): `advVel ! 1` / `advVel ! x` -> `advVel`, and
    # `reqVel ? x` -> `reqVel`. The `!(?!=)` lookahead avoids the `!=` operator.
    text = re.sub(r"(\b\w+)\s*!(?!=)\s*[^\n;}]+", r"\1", text)
    text = re.sub(r"(\b\w+)\s*\?\s*\w+", r"\1", text)
    # Make event declarations untyped to match the synchronisation usage above:
    # `event reqVel : real` -> `event reqVel`.
    text = re.sub(r"(\bevent\s+\w+)\s*:\s*\w+", r"\1", text)

    # Strip C-style trailing semicolons from var/const/event/clock declarations
    # (the LLM sometimes adds them; RoboChart declarations don't use ';').
    text = re.sub(r"(?m)^([ \t]*(?:var|const|event|clock)\b[^\n;]*?)\s*;[ \t]*$", r"\1", text)

    # Boolean operators (lambda replacements avoid re.sub backslash-escaping).
    text = re.sub(r"\band\b", lambda _m: "/\\", text)
    text = re.sub(r"\bor\b", lambda _m: "\\/", text)
    # Drop a leading `uses ... requires ...` interface line inside the stm head.
    text = re.sub(r"^\s*uses\s+\w+(\s+requires\s+\w+)*\s*$", "", text, flags=re.MULTILINE)
    # Synthesise enumerations for undeclared capitalised types.
    declared = set(re.findall(r"\b(?:type|datatype|enumeration|record)\s+(\w+)", text))
    referenced = set(re.findall(r":\s*([A-Z]\w*)", text))
    missing = sorted(t for t in referenced - declared if t not in _PRIMITIVE_TYPES)
    if missing:
        decls = "\n".join(f"enumeration {t} {{ {t}_v0 {t}_v1 }}" for t in missing)
        text = decls + "\n\n" + text

    # Declare any event used as a trigger or a synchronisation action/entry but
    # not declared (the LLM often omits the `event` declarations). Without this
    # the parser cannot resolve the event and the EGL emits empty triggers.
    used_events = set(re.findall(r"\btrigger\s+(\w+)", text))
    # entry/during/exit/action sync sends: a bare identifier followed by a
    # statement terminator (`}`, `;`, newline, end) — excludes assignments
    # (`action v = 1`) and operation calls (`action f(...)`), and `skip`.
    for m in re.finditer(r"\b(?:entry|during|exit|action)\s+(\w+)(?=\s*(?:[}\n;]|\Z))", text):
        if m.group(1) != "skip":
            used_events.add(m.group(1))
    declared_events = set(re.findall(r"\bevent\s+(\w+)", text))
    missing_events = sorted(used_events - declared_events)
    if missing_events:
        ev_decls = "\n".join(f"\tevent {e}" for e in missing_events)
        text = re.sub(r"(\bstm\s+\w+\s*\{)", r"\1\n" + ev_decls, text, count=1)
    return text


def _run_assembler(bare: Path, egl: Path, out: Path) -> bool:
    """Invoke the MALCOMj `roboChartAssemble` Gradle task. Returns True iff the
    task succeeds and the output file is produced."""
    gradle = shutil.which("gradle") or "gradle"
    cmd = [
        gradle, "-p", str(_MALCOMJ_DIR), "roboChartAssemble",
        f"-Pinput={bare.resolve()}", f"-Pegl={egl.resolve()}", f"-Poutput={out.resolve()}",
        "-x", "test", "--console=plain", "-q",
    ]
    res = subprocess.run(cmd, cwd=str(_MALCOMJ_DIR), capture_output=True,
                         text=True, timeout=600, env=os.environ.copy())
    if res.returncode != 0 or not out.is_file():
        logger.warning("roboChartAssemble failed (rc=%s): %s",
                       res.returncode, (res.stderr or res.stdout or "")[:500])
        return False
    return True


def assemble_complete_rct(model_rct: Path, out_rct: Path) -> bool:
    """Assemble a complete, generator-ready RoboChart model from the LLM's
    behaviour model (`model_rct`, left UNCHANGED) into `out_rct`.

    `model_rct` is the canonical behaviour artefact (compared by the evaluation
    metrics), so it is never mutated — the FDR-friendly normalisation is applied
    to a copy that feeds the assembler. Returns True on success. Fail-soft: on a
    missing toolchain or assembly failure it writes the normalised model to
    `out_rct` (so a best-effort artefact still exists for FDR4) and returns False."""
    model_rct = Path(model_rct)
    out_rct = Path(out_rct)
    try:
        normalised = normalise_stm(model_rct.read_text(encoding="utf-8"))
    except OSError:
        return False

    def _fallback():
        try:
            out_rct.write_text(normalised, encoding="utf-8")
        except OSError:
            pass

    if not _MALCOMJ_DIR.is_dir() or shutil.which("gradle") is None:
        logger.warning("RoboChartAssembler: gradle/MALCOMj unavailable; using bare stm")
        _fallback()
        return False
    norm_path = out_rct.with_name(out_rct.stem + ".normalised.rct")
    try:
        norm_path.write_text(normalised, encoding="utf-8")
        if _run_assembler(norm_path, _EGL, out_rct):
            return True
    except Exception as ex:
        logger.warning("RoboChartAssembler failed: %s", ex)
    _fallback()
    return False
