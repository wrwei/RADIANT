"""Optional FDR4 refinement check for the behaviour phase.

Generates CSP from a RoboChart .rct via FORGE's standalone RoboChart CSP
generator, tames numeric type ranges to [0..1], and runs FDR4 (refines.exe)
to check deadlock-/divergence-freedom. Fail-soft: when the toolchain is
missing the result is `unverifiable`; an actual refinement violation is a
hard fail. Ports the pure mechanics of FORGE's run_fdr4 (no dashboard
coupling) and invokes FORGE only as an external process for CSP generation.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from verification import Check

logger = logging.getLogger(__name__)


class ToolchainUnavailable(Exception):
    """A required external tool (FORGE generator, gradle, refines) is missing —
    mapped to an `unverifiable` Check, never a hard fail."""


class GeneratorRejected(Exception):
    """The RoboChart CSP generator ran but rejected the model (syntax /
    unresolved-reference ERRORs, no CSP produced) — a real structural defect,
    mapped to a hard-fail Check that the repair agent can act on."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors[:6]))


def _generator_errors(output_text: str) -> list:
    """Extract unique `ERROR:...` messages emitted by the RoboChart CSP
    generator (e.g. "missing '}' at 'and'", "Couldn't resolve reference to
    Interface 'Outputs'")."""
    seen, errs = set(), []
    for ln in (output_text or "").splitlines():
        s = ln.strip()
        idx = s.find("ERROR:")
        if idx != -1:
            msg = s[idx + len("ERROR:"):].strip()
            # Drop the noisy absolute temp-file URI, keep the line/column.
            msg = re.sub(r"file:/\S+\.rct\s*", "", msg).replace("( line", "(line")
            if msg and msg not in seen:
                seen.add(msg)
                errs.append(msg)
    return errs


def _parse_framed_json(raw_output: str) -> list:
    """Parse FDR4 framed_json output (one JSON object per line)."""
    results = []
    for line in (raw_output or "").strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return results


# --- type ranges (port of FORGE csp_corrections.py) --------------------------

DEFAULT_TYPE_RANGES = {
    "nat": "nametype core_nat = {0..1}",
    "int": "nametype core_int = {0..1}",
    "real": "nametype core_real = {0..1}",
    "core_clock_type": "nametype core_clock_type = {0..1}",
    "string": "nametype core_string = {0}",
}
_CSP_NAMES = {
    "nat": "core_nat", "int": "core_int", "real": "core_real",
    "core_clock_type": "core_clock_type", "string": "core_string",
}


def _build_nametype(csp_name: str, lower: int, upper: int) -> str:
    if lower == upper:
        return f"nametype {csp_name} = {{{lower}}}"
    lo = f" {lower}" if lower < 0 else str(lower)   # CSP-M: {-1..1} is a comment
    return f"nametype {csp_name} = {{{lo}..{upper}}}"


def _merge(text: str, overrides: dict) -> str:
    """Replace `-- generate <name>` blocks whose name is in `overrides`."""
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        raw = lines[i]
        m = re.match(r"^-- generate\s+(.+)$", raw.strip())
        if m and m.group(1).strip() in overrides:
            name = m.group(1).strip()
            out.append(raw)
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if re.match(r"^-- generate\s+", s) or re.match(r"^--\s+[A-Z][A-Z_ ]+$", s):
                    break
                i += 1
            out.extend(overrides[name])
            continue
        out.append(raw)
        i += 1
    return "\n".join(out) + "\n"


def _apply_type_range_corrections(csp_gen_dir, type_ranges=None):
    """Rewrite nat/int/real/clock/string blocks in instantiations.csp (and
    timed/instantiations.csp if present) to small [0..1] ranges. Returns the
    list of patched files."""
    overrides = {name: [defn] for name, defn in DEFAULT_TYPE_RANGES.items()}
    for name, cfg in (type_ranges or {}).items():
        if name in _CSP_NAMES:
            overrides[name] = [_build_nametype(_CSP_NAMES[name], cfg["lower"], cfg["upper"])]
    inst = Path(csp_gen_dir) / "instantiations.csp"
    targets = [inst]
    timed = inst.parent / "timed" / "instantiations.csp"
    if timed.exists() and timed != inst:
        targets.append(timed)
    patched = []
    for t in targets:
        if t.exists():
            t.write_text(_merge(t.read_text(encoding="utf-8"), overrides), encoding="utf-8")
            patched.append(t)
    return patched


# --- coreassertions discovery (port of FORGE _discover_fdr4_csp_file) --------

def _discover_coreassertions(csp_gen_dir):
    """Pick the FDR4 input CSP under <csp-gen>/defs/ by preference tier."""
    defs_dir = Path(csp_gen_dir) / "defs"
    if not defs_dir.is_dir():
        return None
    candidates = sorted(defs_dir.glob("*_coreassertions.csp"))
    if not candidates:
        return None
    for p in candidates:                                  # tier 1: aggregate
        if "_System_Module_coreassertions.csp" in p.name:
            return p
    for p in candidates:                                  # tier 2: controller-only (FORGE naming)
        n = p.name
        if ("Controller_coreassertions.csp" in n and "_Module_" not in n
                and "_Ctrl_" not in n and "_InputEnv_" not in n
                and "_OutputEnv_" not in n):
            return p
    for p in candidates:                                  # tier 2b: controller-only (our EGL naming)
        # The vendored robochart2rct.egl names the controller <Stm>_Ctrl, so the
        # controller-only assertions are <Stm>_Ctrl_coreassertions.csp. Prefer them
        # over the module level, which composes the InputEnv/OutputEnv environment
        # and explodes the state space (see FORGE's discovery rationale).
        if "_Ctrl_coreassertions.csp" in p.name and "_Module_" not in p.name:
            return p
    for p in candidates:                                  # tier 3: module level
        if "_Module_coreassertions.csp" in p.name:
            return p
    if len(candidates) == 1:                              # tier 4: unique
        return candidates[0]
    return None                                           # ambiguous


# --- FDR4 stderr classification (port; environmental errors -> unverifiable) --

def _classify_fdr4_stderr(stderr_text):
    """Return a short headline if stderr is an environmental error (page file /
    RTS / OOM), else None."""
    low = (stderr_text or "").lower()
    if ("virtualalloc" in low and "mem_commit" in low) or "paging file is too small" in low:
        return "FDR4 ran out of address space (Windows page file too small)"
    if "most rts options are disabled" in low:
        return "FDR4 rejected +RTS arguments (refines.exe built with -rtsopts=some)"
    if "out of memory" in low or "getmblocks" in low or "heap exhausted" in low:
        return "FDR4 ran out of memory"
    return None


def _strip_determinism(csp_path: Path) -> Path:
    """Comment out `assert ... :[deterministic]` lines into a *_nodet sibling.
    RoboChart models are non-deterministic by construction; we neither check
    nor report that property. Returns the file to run (nodet if any stripped)."""
    text = csp_path.read_text(encoding="utf-8")
    has_det = any(ln.lstrip().startswith("assert") and ":[deterministic]" in ln
                  for ln in text.splitlines())
    if not has_det:
        return csp_path
    filtered = "\n".join(
        ("-- determinism not verified: " + ln)
        if (ln.lstrip().startswith("assert") and ":[deterministic]" in ln) else ln
        for ln in text.splitlines())
    nodet = csp_path.with_name(csp_path.stem + "_nodet" + csp_path.suffix)
    nodet.write_text(filtered + "\n", encoding="utf-8")
    return nodet


def _process_memory_mb(pid: int) -> float:
    """Best-effort RSS of a process in MB (0.0 on any error)."""
    try:
        if sys.platform == "win32":
            r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                for line in r.stdout.strip().splitlines():
                    parts = line.strip().strip('"').split('","')
                    if len(parts) >= 5:
                        mem = (parts[4].replace('"', '').replace(',', '')
                               .replace(' K', '').replace(' ', ''))
                        return int(mem) / 1024
        elif sys.platform == "linux":
            sf = Path(f"/proc/{pid}/status")
            if sf.exists():
                for line in sf.read_text().splitlines():
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024
        elif sys.platform == "darwin":
            r = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)],
                               capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout.strip():
                return int(r.stdout.strip()) / 1024
    except Exception:
        pass
    return 0.0


# --- refines.exe runner (port of FORGE run_fdr4 mechanics) -------------------

def _run_refines(csp_path: Path, fdr4_path: str, *, memory_limit_mb: int = 8192,
                 timeout: int = 600) -> dict:
    """Run `refines.exe --format framed_json <csp>`. Returns a dict with keys
    assertions/passed/failed/inconclusive/errors/counterexamples/env_error.
    `env_error` is a non-None string for environmental failures (timeout,
    memory, page file). Raises ToolchainUnavailable if refines is not found."""
    resolved = shutil.which(fdr4_path) or (
        fdr4_path if fdr4_path and Path(fdr4_path).exists() else "")
    if not resolved:
        raise ToolchainUnavailable(f"refines not found: {fdr4_path!r}")

    empty = {"assertions": [], "passed": [], "failed": [], "inconclusive": [],
             "errors": [], "counterexamples": [], "env_error": None}

    cmd = [resolved, "--format", "framed_json", str(csp_path)]
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace", env=env)

    killed = threading.Event()

    def monitor():
        while proc.poll() is None:
            if _process_memory_mb(proc.pid) > memory_limit_mb:
                killed.set()
                proc.kill()
                return
            time.sleep(1)

    mt = threading.Thread(target=monitor, daemon=True)
    mt.start()
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return {**empty, "env_error": f"FDR4 timed out after {timeout}s"}
    mt.join(timeout=2)
    if killed.is_set():
        return {**empty, "env_error": f"FDR4 exceeded memory limit {memory_limit_mb} MB"}

    frames = _parse_framed_json(out)
    if not frames and err:
        cls = _classify_fdr4_stderr(err)
        if cls:
            return {**empty, "env_error": cls}

    assertions, errors, counterexamples = [], [], []
    for f in frames:
        if isinstance(f.get("errors"), list):
            errors += [{"error": e} for e in f["errors"] if e]
        if "error" in f:
            errors.append(f)
        # event_map is frame-local: event id (in the counterexample trace) -> name.
        event_map = {str(k): str(v) for k, v in (f.get("event_map") or {}).items()}
        for a in f.get("results", []):
            assertions.append(a)
            if a.get("result") in (0, False):
                ce_str = _format_counterexample(a, event_map)
                if ce_str:
                    counterexamples.append((a.get("assertion_string", "?"), ce_str))
    passed = [a for a in assertions if a.get("result") in (1, True)]
    failed = [a for a in assertions if a.get("result") in (0, False)]
    inconclusive = [a for a in assertions if a not in passed and a not in failed]
    return {"assertions": assertions, "passed": passed, "failed": failed,
            "inconclusive": inconclusive, "errors": errors,
            "counterexamples": counterexamples, "env_error": None}


def _clean_event(name: str) -> str:
    """`M_Module::ctrl_ref0::go.in` -> `go` (drop CSP path prefix + .in/.out)."""
    short = name.rsplit("::", 1)[-1]
    return re.sub(r"\.(in|out)$", "", short)


def _format_counterexample(assertion: dict, event_map: dict) -> str:
    """Human-readable counterexample for a failed assertion: the event trace that
    reaches the deadlock/divergence, with event ids mapped to RoboChart names."""
    parts = []
    for ce in assertion.get("counterexamples", []):
        kind = ce.get("type", "violation")
        beh = ce.get("implementation_behaviour") or {}
        trace_ids = beh.get("trace") or ce.get("trace") or []
        names = [_clean_event(event_map.get(str(t), str(t))) for t in trace_ids]
        if names:
            parts.append(f"{kind} after trace: " + " -> ".join(names))
        else:
            parts.append(f"{kind} reachable from the initial state")
    return "; ".join(parts)


# --- CSP generation (vendored RoboChart generator, isolated classpath) -------

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Serialise the FDR step across processes: concurrent sweeps must not run two
# ~8 GB refines instances at once or contend for the toolchain. filelock uses
# OS locks that release automatically when the holding process exits.
import filelock as _filelock
import tempfile as _tempfile
_FDR_LOCK = _filelock.FileLock(str(Path(_tempfile.gettempdir()) / "remediate_fdr4.lock"))
_DEFAULT_GEN_DIR = _REPO_ROOT / "MALCOMj" / "lib" / "robochart"


def _generate_csp(rct_path, robochart_gen_dir, *, timeout: int = 600) -> Path:
    """Stage the .rct into a temp RoboChart project and run the vendored official
    RoboChart CSP generator with an *isolated* classpath (only the RoboChart jars
    — no Epsilon, so no Eclipse-jar signer conflict and no Gradle). Returns the
    csp-gen/ dir. Raises ToolchainUnavailable / GeneratorRejected."""
    gen_dir = Path(robochart_gen_dir) if robochart_gen_dir else _DEFAULT_GEN_DIR
    # Resolve repo-relative config paths against the repo root (the generator runs
    # with cwd set to the temp project, so the classpath must be absolute).
    if not gen_dir.is_absolute():
        gen_dir = _REPO_ROOT / gen_dir
    gen_dir = gen_dir.resolve()
    if not gen_dir.is_dir() or not any(gen_dir.glob("*.jar")):
        raise ToolchainUnavailable(f"RoboChart generator jars not found in {gen_dir}")
    java = shutil.which("java") or "java"
    rct = Path(rct_path)
    if not rct.is_file():
        raise ToolchainUnavailable(f"missing .rct: {rct_path}")

    import tempfile
    proj = Path(tempfile.mkdtemp(prefix="remediate_fdr4_"))
    shutil.copy(rct, proj / rct.name)
    # Official generator Main args: <iteratedComp> <assertionComp> <projectDir>.
    cmd = [java, "-cp", str(gen_dir / "*"),
           "circus.robocalc.robochart.generator.csp.Main", "true", "true", str(proj)]
    try:
        result = subprocess.run(cmd, cwd=str(proj), capture_output=True,
                                text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as ex:
        raise ToolchainUnavailable(f"RoboChart CSP generator failed to run: {ex}")
    csp_gen = proj / "csp-gen"
    has_csp = csp_gen.is_dir() and any(csp_gen.rglob("*.csp"))
    if not has_csp:
        # The generator ran but produced no CSP. If it logged ERROR lines, the
        # model is malformed (syntax / unresolved refs) -> hard fail + repair.
        # Otherwise treat as an environmental/toolchain issue -> unverifiable.
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        errs = _generator_errors(combined)
        if errs:
            raise GeneratorRejected(errs)
        raise ToolchainUnavailable("roboChartCspGen produced no csp-gen/ output")
    return csp_gen


# --- public entry point ------------------------------------------------------

def run_fdr4_check(rct_path, *, config: dict) -> Check:
    """Cross-process-serialised wrapper around the FDR check.

    Holds a file lock for the duration so concurrent sweeps run FDR one at a
    time. Falls back to running without the lock if the wait is excessive
    (a hung holder is bounded by FDR's own timeout)."""
    wait = int(config.get("timeout", 600)) * 2 + 60
    try:
        with _FDR_LOCK.acquire(timeout=wait):
            return _do_fdr4_check(rct_path, config=config)
    except _filelock.Timeout:
        logger.warning("FDR lock wait exceeded %ss; proceeding without it", wait)
        return _do_fdr4_check(rct_path, config=config)


def _do_fdr4_check(rct_path, *, config: dict) -> Check:
    """rct -> CSP -> [0..1] -> coreassertions -> FDR4 -> Check('fdr4_refinement')."""
    name = "fdr4_refinement"
    try:
        csp_gen = _generate_csp(rct_path, config.get("robochart_gen_dir", ""),
                                timeout=int(config.get("timeout", 600)))
        _apply_type_range_corrections(csp_gen, config.get("type_ranges") or {})
        coreassertions = _discover_coreassertions(csp_gen)
        if coreassertions is None:
            return Check(name, "structural", False, True,
                         "generator produced no *_coreassertions.csp")
        # Determinism is not verified by default — RoboChart models are
        # non-deterministic by construction (concurrent transition choices, hidden
        # internal events), so the property is neither meaningful nor wanted here.
        # Strip the generator's :[deterministic] assertions unless explicitly asked.
        if config.get("check_determinism", False):
            to_run = coreassertions
        else:
            to_run = _strip_determinism(coreassertions)
        res = _run_refines(to_run, config.get("fdr4_path", "refines"),
                           memory_limit_mb=int(config.get("memory_limit_mb", 8192)),
                           timeout=int(config.get("timeout", 600)))
    except GeneratorRejected as ex:
        n = len(ex.errors)
        detail = (f"RoboChart generator rejected the model ({n} error(s)): "
                  + "; ".join(ex.errors[:6]))
        return Check(name, "structural", False, False, detail)   # hard fail -> repair
    except ToolchainUnavailable as ex:
        return Check(name, "structural", False, True, f"FDR4 toolchain unavailable: {ex}")
    except Exception as ex:                      # never crash the pipeline
        logger.warning("FDR4 check errored", exc_info=True)
        return Check(name, "structural", False, True, f"FDR4 check could not run: {ex}")

    if res.get("env_error"):
        return Check(name, "structural", False, True, res["env_error"])

    failed, inconclusive, errors = res["failed"], res["inconclusive"], res["errors"]
    if failed or inconclusive or errors:
        parts = []
        ces = dict(res.get("counterexamples", []))
        for a in failed:
            s = a.get("assertion_string", "?")
            parts.append(f"FAIL {s}" + (f" [{ces[s]}]" if s in ces else ""))
        if inconclusive:
            parts.append(f"{len(inconclusive)} inconclusive")
        if errors:
            parts.append(f"{len(errors)} error(s): "
                         + "; ".join(str(e.get('error', '?')) for e in errors[:3]))
        return Check(name, "structural", False, False, "; ".join(parts))

    n = len(res["passed"])
    if n == 0:
        # No assertion ran at all. Every generated coreassertions file contains
        # deadlock/divergence assertions, so an empty result set means refines
        # produced no verdicts (unlicensed copy prompting for a licence key,
        # wrapper script, truncated output) — NOT that the model verified.
        # Reporting this as a pass was a vacuous-pass hole: the gate went green
        # with no property checked.
        return Check(name, "structural", False, True,
                     "refines returned no assertion results (unlicensed or "
                     "misconfigured FDR?) — nothing was verified")
    return Check(name, "structural", True, False,
                 f"{n} assertion(s) hold (deadlock/divergence-free)")
