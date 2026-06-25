"""Pipeline bridge: runs MALCOMp stages in background threads with WebSocket I/O."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

import yaml

from web import get_malcomj_dir, get_malcomp_dir
from web.iostream import WebSocketIOStream
from web.state import SessionState

logger = logging.getLogger(__name__)

# Ensure the MALCOMp root is on sys.path so stage imports work
_MALCOMP_DIR = get_malcomp_dir()
if str(_MALCOMP_DIR) not in sys.path:
    sys.path.insert(0, str(_MALCOMP_DIR))

_MALCOMJ_DIR = get_malcomj_dir()
_GRADLEW = "gradlew.bat" if sys.platform == "win32" else "./gradlew"

# ---------------------------------------------------------------------------
# Pipeline metadata
# ---------------------------------------------------------------------------

STAGE_NAMES = ["concept", "dsml", "model", "behaviour"]

STAGE_REQUIRED_AGENTS = {
    "concept": {"Concept_Extraction_Agent", "Trace_Generation_Agent"},
    "dsml": {"DSML_Extraction_Agent", "DSML_Refactoring_Agent", "Trace_Generation_Agent"},
    "model": {"Model_Creator", "Model_Refactorer", "Trace_Generation_Agent"},
    "behaviour": {"Behaviour_Model_Creation_Agent", "Trace_Generation_Agent"},
}

# Per-phase dedicated repair agent (side agents — not in the roster). Invoked by
# the verification gate to fix the artefact on a hard failure.
STAGE_REPAIR_AGENTS = {
    "concept": "Concept_Repair_Agent",
    "dsml": "DSML_Repair_Agent",
    "model": "EOL_Repairer",
    "behaviour": "Behaviour_Repair_Agent",
}

PIPELINE_STRUCTURE = [
    {
        "id": "phase1_requirements",
        "label": "1 \u2014 Requirement Modelling",
        "type": "manual",
        "tasks": [],
    },
    {
        "id": "phase2_concepts",
        "label": "2 \u2014 Concept Extraction",
        "type": "llm",
        "tasks": ["concept"],
    },
    {
        "id": "phase3_dsml",
        "label": "3 \u2014 DSML Creation",
        "type": "llm",
        "tasks": ["dsml"],
    },
    {
        "id": "phase4_model",
        "label": "4 \u2014 Model Creation",
        "type": "llm",
        "tasks": ["model"],
    },
    {
        "id": "phase5_behaviour",
        "label": "5 \u2014 Behaviour Model Creation (optional)",
        "type": "llm",
        "tasks": ["behaviour"],
    },
    {
        "id": "phase6_management",
        "label": "6 \u2014 Model Management (MALCOMj)",
        "type": "gradle",
        "tasks": [],
        "commands": [
            "buildBifrost",
            "ciaSnapshot",
            "ciaReport",
        ],
    },
]

GRADLE_COMMANDS: dict[str, dict] = {
    "buildBifrost": {"label": "Build Bifrost Traceability Models",
                     "needs": "result_concept_trace.json"},
    "ciaSnapshot": {"label": "Snapshot Traceability Baseline", "kind": "cia"},
    "ciaReport":   {"label": "Change-Impact Report", "kind": "cia"},
}

# Map from stage name to its config key in config.yaml
_STAGE_CONFIG_KEY = {
    "concept": "concept_extraction",
    "dsml": "dsml_creation",
    "model": "emf_model_creation",
    "behaviour": "behaviour_model_creation",
}


def _get_stage_classes() -> dict[str, type]:
    """Stage classes keyed by Layer token, from MALCOMp's LAYERS registry."""
    from pipeline import LAYERS  # MALCOMP_DIR already on sys.path
    return {key: spec.cls for key, spec in LAYERS.items()}


# Per-stage agent rosters derived from the MALCOMp stage classes' AGENT_NAMES
# attribute. Single source of truth — adding/removing a `create_agent(...)`
# call in any stage now requires updating exactly one location (the
# `AGENT_NAMES` tuple on the stage class), and `Base.init_group_chat` will
# raise loudly if the two drift apart.
#
# Resolved lazily via module-level __getattr__ so `import web.bridge` does
# not pay the autogen + dotenv import cost. Consumers keep using
# `from web.bridge import STAGE_AGENTS`; the heavy import only happens on
# first attribute access (e.g. when the first `/api/stages` request arrives).
_STAGE_AGENTS_CACHE: dict[str, list[str]] | None = None


def __getattr__(name: str):
    if name == "STAGE_AGENTS":
        global _STAGE_AGENTS_CACHE
        if _STAGE_AGENTS_CACHE is None:
            from pipeline import LAYERS
            _STAGE_AGENTS_CACHE = {
                key: list(spec.agent_names) for key, spec in LAYERS.items()
            }
        return _STAGE_AGENTS_CACHE
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class PipelineBridge:
    """Manages running pipeline stages in background threads."""

    def __init__(self, config_path: str, state: SessionState,
                 case_study: str | None = None) -> None:
        self.config_path = config_path
        self.state = state
        # Active case study for this bridge (per-connection): explicit arg wins,
        # else the session selection, else the config default. Passed to every
        # stage construction so MALCOMP_CASE_STUDY (a process-global env) is not
        # needed in the web.
        self.case_study = case_study or self._resolve_case_study()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._current_phase: str | None = None
        self._iostream: WebSocketIOStream | None = None
        # Cache stage instances so agents retain conversation context
        self._phase_cache: dict[str, Any] = {}

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @staticmethod
    def _predecessor(phase_name: str) -> str | None:
        """The phase that must verify before `phase_name` may run (pipeline order)."""
        if phase_name in STAGE_NAMES:
            i = STAGE_NAMES.index(phase_name)
            if i > 0:
                return STAGE_NAMES[i - 1]
        return None

    def _gate_blocker(self, phase_name: str) -> str | None:
        """Return the predecessor blocking `phase_name` (it failed verification),
        or None if the phase may proceed."""
        pred = self._predecessor(phase_name)
        if pred is not None and self.state.get_phase_status(pred) == "failed":
            return pred
        return None

    # ---- LLM-based stages (Phases 2-5) -----------------------------------

    def start_phase(self, phase_name: str, iostream: WebSocketIOStream,
                    loop: asyncio.AbstractEventLoop, *,
                    requirements_override: str | None = None,
                    disabled_agents: list[str] | None = None,
                    feed_mode: str = "batch",
                    model: str | None = None,
                    agent_mode: str = "multi") -> None:
        """Launch an LLM pipeline stage in a background thread."""
        if self.is_running:
            iostream.notify_phase_event(
                "error", message="A stage is already running",
            )
            return

        if phase_name not in STAGE_NAMES:
            iostream.notify_phase_event(
                "error", message=f"Unknown stage: {phase_name}",
            )
            return

        # Verification gate: do not start a phase whose predecessor failed
        # verification this session (lenient — a predecessor that was never run
        # is allowed, so standalone runs against existing/golden artefacts work).
        blocker = self._gate_blocker(phase_name)
        if blocker is not None:
            iostream.notify_phase_event(
                "error",
                message=(f"Phase '{blocker}' did not pass verification — fix it "
                         f"before running '{phase_name}'."),
            )
            return

        # Build effective config path (apply requirements / model override if given)
        effective_config = self.config_path
        if requirements_override or model:
            effective_config = self._make_override_config(
                phase_name,
                requirements_override,
                model,
            )

        self._stop_event.clear()
        self._current_phase = phase_name
        self._iostream = iostream
        iostream.phase_name = phase_name
        iostream.reopen()  # revive the stream if a prior run was stopped
        iostream._flush_buffer()
        iostream._current_sender = ""
        if phase_name == "concept":
            run_id = self.state.start_new_pipeline_run()
        else:
            run_id = self.state.ensure_pipeline_run_id()
        self.state.save()
        self.state.set_phase_status(phase_name, "running")

        self._thread = threading.Thread(
            target=self._run_phase,
            args=(phase_name, iostream, loop, effective_config,
                  disabled_agents or [], run_id, feed_mode, agent_mode),
            daemon=True,
        )
        self._thread.start()

    def _run_phase(self, phase_name: str, iostream: WebSocketIOStream,
                   loop: asyncio.AbstractEventLoop,
                   config_path: str | None = None,
                   disabled_agents: list[str] | None = None,
                   run_id: str | None = None,
                   feed_mode: str = "batch",
                   agent_mode: str = "multi") -> None:
        """Execute a single LLM stage (runs in a background thread)."""
        from autogen.io import IOStream

        effective_config = config_path or self.config_path
        tmp_config = effective_config if effective_config != self.config_path else None
        disabled = set(disabled_agents or [])
        disabled -= STAGE_REQUIRED_AGENTS.get(phase_name, set())

        status = "completed"
        try:
            with IOStream.set_default(iostream):
                stages = _get_stage_classes()
                cls = stages[phase_name]
                # Pass disabled_agents through to the stage constructor
                # rather than mutating .agents post-hoc — the new Base API
                # skips the create_agent calls entirely and the AGENT_NAMES
                # consistency check accounts for the disabled set.
                stage = cls(
                    config_path=effective_config,
                    disabled_agents=disabled,
                    run_id=run_id,
                    case_study=self.case_study,
                )
                # Per-run requirement feeding mode (sequential | batch).
                stage.feed_mode = feed_mode or "sequential"

                # Patch output_cfg if the configured json/code agent was disabled.
                if disabled:
                    output_cfg = stage.stage_config.get("output", {})
                    json_agent = output_cfg.get("json_agent", "")
                    if json_agent and json_agent in disabled:
                        output_cfg.pop("json_agent", None)
                        logger.info(
                            "json_agent %s disabled — skipping trace JSON",
                            json_agent,
                        )
                    code_agent = output_cfg.get("code_agent", "")
                    if code_agent and code_agent in disabled:
                        # Pick a fallback code-emitting agent from those still
                        # enabled, excluding the configured json_agent (whose
                        # output is structured trace JSON, not code). The old
                        # filter used `"Json" not in a.name` — substring match
                        # against the literal "Json", which silently missed
                        # the new Trace_Generator agent (D2, no "Json"
                        # substring) and would have selected it as a code
                        # source in any future term-stage code-agent setup.
                        configured_json = (
                            stage.stage_config.get("output", {}).get("json_agent")
                        )
                        candidates = [
                            a.name for a in stage.agents
                            if a.name != configured_json
                        ]
                        if candidates:
                            output_cfg["code_agent"] = candidates[-1]
                            logger.info(
                                "code_agent %s disabled — falling back to %s",
                                code_agent, candidates[-1],
                            )
                        else:
                            output_cfg.pop("code_agent", None)
                            logger.warning(
                                "code_agent %s disabled and no fallback "
                                "candidate available — skipping code artefact",
                                code_agent,
                            )

                if agent_mode == "single":
                    # Faithful Single-Agent baseline (paper §4): one direct LLM
                    # call with the primary agent's system message, written into
                    # the stage's output dir, then verified (no repair loop).
                    self._generate_single_agent(
                        phase_name, stage, effective_config, iostream)
                    stage._run_verification()
                    result = None
                else:
                    result = stage.run()
                stage.archive_configured_outputs()
                iostream.finalize()

                # Verification gate: a phase that ran but failed verification is
                # marked 'failed', which blocks the next phase (see _gate_blocker).
                vr = getattr(stage, "verification_result", None)
                if vr is not None:
                    payload = {
                        "passed": vr.passed,
                        "checks": [
                            {"name": c.name, "kind": c.kind, "ok": c.ok,
                             "unverifiable": c.unverifiable, "detail": c.detail}
                            for c in vr.checks
                        ],
                    }
                    self.state.set_phase_verification(phase_name, payload)
                    iostream.notify_phase_event("verification", **payload)
                    if not vr.passed:
                        status = "failed"
                        logger.info("Phase %s failed verification:\n%s",
                                    phase_name, vr.summary())

                self.state.set_phase_result(phase_name, result)
                self._phase_cache[phase_name] = stage

        except Exception as e:
            iostream.finalize()
            if self._stop_event.is_set():
                logger.info("Stage %s was stopped by user", phase_name)
                status = "stopped"
            else:
                logger.exception("Stage %s raised an exception", phase_name)
                status = "failed"
                self.state.set_phase_error(phase_name, str(e))
        finally:
            self._current_phase = None
            self._iostream = None
            if tmp_config:
                try:
                    os.unlink(tmp_config)
                except OSError:
                    pass

        # Only notify if stop_phase() hasn't already done so
        if not self._stop_event.is_set():
            self.state.set_phase_status(phase_name, status)
            iostream.notify_phase_event("phase_complete", status=status,
                                        phase=phase_name)

    def _generate_single_agent(self, phase_name: str, stage,
                               effective_config: str,
                               iostream: WebSocketIOStream) -> None:
        """Faithful Single-Agent baseline (paper §4): one direct LLM call using
        the stage's primary-agent system message, written into the stage's output
        dir so the normal verification + archive path can consume it unchanged."""
        import run_single_agent as sa

        cfg_path = Path(effective_config)
        config = sa._load_config(cfg_path)
        config["case_study"] = self.case_study   # pin the active study for req lookup
        sa.select_model(config)                  # honours default_model (set by override)
        client = sa._build_openai_client(config)

        spec = sa.STAGES.get(phase_name, {})
        primary = spec.get("primary_agent", "Single_Agent")
        model_name = (config.get("model") or {}).get("name", "?")
        if hasattr(iostream, "send_agent_message"):
            try:
                iostream.send_agent_message(
                    "system",
                    f"Single-agent mode — one {primary} call on {model_name}.")
            except Exception:
                logger.debug("single-agent announce failed", exc_info=True)

        out_path = sa.run_stage_single_agent(
            phase_name, cfg_path, stage.output_dir, client, config)

        try:
            content = Path(out_path).read_text(encoding="utf-8")
        except OSError:
            content = f"(wrote {Path(out_path).name})"
        if hasattr(iostream, "send_agent_message"):
            try:
                iostream.send_agent_message(primary, content)
            except Exception:
                logger.debug("single-agent output emit failed", exc_info=True)

    def _make_override_config(self, phase_name: str,
                              requirements_file: str | None = None,
                              model: str | None = None) -> str:
        """Write a temp config.yaml applying the requirements and/or model override.

        When the temp config is loaded from Temp, Base resolves all paths
        relative to Temp and would break. So we resolve assets_dir, output_dir
        and requirement_file against the original config directory and write
        absolute paths into the temp config; Base then uses them as-is.
        """
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        config_dir = Path(self.config_path).resolve().parent

        # Pin absolute roots so Base resolves correctly when this temp config is
        # loaded from the system Temp dir (where it can't derive case_dir/prompts).
        case_study = self.case_study
        config["_case_dir"] = str((config_dir / "case_studies" / case_study).resolve())
        config["_prompts_dir"] = str((config_dir / config.get("prompts_dir", "prompts")).resolve())
        # Pin the active case study so the single-agent runner (which resolves
        # requirements via config['case_study']) uses the right one.
        config["case_study"] = case_study

        # Model override: Base and the single-agent runner both honour default_model.
        if model:
            config["default_model"] = model

        if requirements_file:
            req_path = Path(requirements_file)
            if not req_path.is_absolute():
                req_path = (config_dir / req_path).resolve()
            requirement_file_resolved = str(req_path)

            stage_key = _STAGE_CONFIG_KEY.get(phase_name)
            if stage_key:
                stage_cfg = config.get("stages", {}).get(stage_key, {})
                if "requirement_file" in stage_cfg:
                    stage_cfg["requirement_file"] = requirement_file_resolved

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8",
        )
        yaml.safe_dump(config, tmp)
        tmp.close()
        return tmp.name

    # ---- Gradle-based commands (Phase 6) ----------------------------------

    def start_command(self, command_id: str, iostream: WebSocketIOStream,
                      loop: asyncio.AbstractEventLoop) -> None:
        """Launch a MALCOMj Gradle task in a background thread."""
        if self.is_running:
            iostream.notify_phase_event(
                "error", message="A stage is already running",
            )
            return

        if command_id not in GRADLE_COMMANDS:
            iostream.notify_phase_event(
                "error", message=f"Unknown command: {command_id}",
            )
            return

        # Check dependency
        cmd_cfg = GRADLE_COMMANDS[command_id]
        needs = cmd_cfg.get("needs")
        if needs:
            output_dir = self._get_output_dir()
            if output_dir and not (output_dir / needs).exists():
                iostream.notify_phase_event(
                    "error",
                    message=f"Prerequisite missing: {needs}. Run the corresponding stage first.",
                )
                return

        self._stop_event.clear()
        self._current_phase = command_id
        self._iostream = iostream
        iostream.phase_name = command_id
        iostream.reopen()  # revive the stream if a prior run was stopped
        iostream._flush_buffer()
        iostream._current_sender = ""
        self.state.set_phase_status(command_id, "running")

        self._thread = threading.Thread(
            target=self._run_command,
            args=(command_id, iostream, loop),
            daemon=True,
        )
        self._thread.start()

    # Patterns for Gradle noise lines that should be suppressed
    _GRADLE_NOISE = re.compile(
        r"^("
        r"(> Task |:)\S+"
        r"|Downloading\s+http"
        r"|Download\s+http"
        r"|\s*$"
        r"|[\[\]]{1,2}"
        r"|BUILD SUCCESSFUL in"
        r"|[0-9]+ actionable task"
        r"|> Configure project"
        r"|Picked up JAVA_TOOL_OPTIONS"
        r"|WARNING:.*--args"
        r")",
        re.IGNORECASE,
    )

    def _run_command(self, command_id: str, iostream: WebSocketIOStream,
                     loop: asyncio.AbstractEventLoop) -> None:
        """Run a MALCOMj transformation task and stream output to the WebSocket."""
        cmd_cfg = GRADLE_COMMANDS[command_id]
        label = cmd_cfg["label"]

        # Change-impact commands run the MALCOMp change_impact facility in-process
        # (Python, not a Gradle task) and stream their report to the dialogue.
        if cmd_cfg.get("kind") == "cia":
            self._run_cia(command_id, label, iostream)
            return

        # Copy prerequisite JSON files from MALCOMp output to MALCOMj model dir
        self._copy_outputs_to_malcomj()

        commands = self._malcomj_commands(command_id)

        def _sys(text):
            iostream._flush_buffer()
            iostream._current_sender = ""
            iostream._send_json({
                "type": "agent_message",
                "phase": iostream.phase_name,
                "agent": "system",
                "content": text,
            })

        status = "completed"
        try:
            _sys(f"{label} starting...")
            error_lines = []
            returncode = 0
            for cmd in commands:
                logger.info("Running command: %s", " ".join(cmd))
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(_MALCOMJ_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                assert proc.stdout is not None
                for line in proc.stdout:
                    if self._stop_event.is_set():
                        proc.terminate()
                        break
                    stripped = line.rstrip("\n")
                    logger.debug("[%s] %s", command_id, stripped)

                    if any(kw in stripped.lower() for kw in
                           ("error", "exception", "failed", "fatal", "caused by")):
                        error_lines.append(stripped)

                    clean = stripped.strip()
                    if clean and not self._GRADLE_NOISE.match(clean):
                        iostream.print(clean, flush=True)

                proc.wait(timeout=30)
                returncode = proc.returncode
                if self._stop_event.is_set() or returncode != 0:
                    break

            if self._stop_event.is_set():
                status = "stopped"
                _sys(f"{label} stopped by user.")
            elif returncode != 0:
                status = "failed"
                error_summary = "\n".join(error_lines[:10])
                msg = f"{label} failed with exit code {returncode}."
                if error_summary:
                    msg += "\n" + error_summary
                _sys(msg)
            else:
                _sys(f"{label} completed successfully.")

        except Exception as e:
            if self._stop_event.is_set():
                status = "stopped"
            else:
                logger.exception("Command %s raised an exception", command_id)
                status = "failed"
                iostream.print(f"[{label}] Error: {e}", flush=True)
                self.state.set_phase_error(command_id, str(e))
        finally:
            self._current_phase = None
            self._iostream = None

        # Only notify if stop_phase() hasn't already done so
        if not self._stop_event.is_set():
            self.state.set_phase_status(command_id, status)
            iostream.notify_phase_event("phase_complete", status=status,
                                        phase=command_id)

    def _run_cia(self, command_id: str, label: str,
                 iostream: WebSocketIOStream) -> None:
        """Run change-impact analysis in-process and stream the result.

        ciaSnapshot captures a per-requirement baseline; ciaReport diffs the current
        requirements against it and lists the impacted model elements (across phases)
        with their verified source spans."""
        def _sys(text: str) -> None:
            iostream._flush_buffer()
            iostream._current_sender = ""
            iostream._send_json({
                "type": "agent_message", "phase": iostream.phase_name,
                "agent": "system", "content": text,
            })

        status = "completed"
        try:
            import change_impact as ci  # MALCOMp root is on sys.path
            output_dir = self._get_output_dir()
            if output_dir is None:
                raise RuntimeError("could not resolve the case-study output directory")
            case_dir = output_dir.parent
            requirements = ci.load_requirements(case_dir)
            links = ci.load_links(output_dir)
            baseline_path = output_dir / "cia_baseline.json"

            if command_id == "ciaSnapshot":
                output_dir.mkdir(parents=True, exist_ok=True)
                snap = ci.snapshot(requirements, links, created=None)
                baseline_path.write_text(__import__("json").dumps(snap, indent=2),
                                         encoding="utf-8")
                _sys(f"✓ Baseline captured: {len(requirements)} requirements, "
                     f"{len(links)} trace links → cia_baseline.json")
            else:  # ciaReport
                if not baseline_path.is_file():
                    _sys("No baseline found — run \"Snapshot Traceability Baseline\" first.")
                else:
                    import json as _json
                    baseline = _json.loads(baseline_path.read_text(encoding="utf-8"))
                    report = ci.impact(ci.diff(baseline, requirements),
                                       ci.build_graph(links), requirements)
                    (output_dir / "cia_report.json").write_text(
                        _json.dumps(report, indent=2), encoding="utf-8")
                    _sys(ci.format_report(report))
        except Exception as e:  # noqa: BLE001
            logger.exception("Change-impact command %s failed", command_id)
            status = "failed"
            _sys(f"[{label}] Error: {e}")
            self.state.set_phase_error(command_id, str(e))
        finally:
            self._current_phase = None
            self._iostream = None
        if not self._stop_event.is_set():
            self.state.set_phase_status(command_id, status)
            iostream.notify_phase_event("phase_complete", status=status, phase=command_id)

    def _malcomj_commands(self, command_id: str) -> list[list[str]]:
        gradlew = _MALCOMJ_DIR / _GRADLEW
        if gradlew.exists():
            return [[str(gradlew), command_id]]

        auv = _MALCOMJ_DIR / "src" / "main" / "resources" / "examples" / "auv"
        core = _MALCOMJ_DIR / "src" / "main" / "resources" / "metamodel"
        runner = self._ensure_malcomj_runner()

        def transform(script: str, *model_args: str) -> list[str]:
            return [str(runner), "--script", str(auv / "transformation" / script), *model_args]

        tasks: dict[str, list[list[str]]] = {
            "runAuvEmfCreation": [transform(
                "auv_emf_creation.eol",
                "--emf", f"M={auv / 'model' / 'AUV.model'};{auv / 'metamodel' / 'auv.ecore'};readOnLoad=false,storeOnDisposal=true",
            )],
            "runAuvValidation": [transform(
                "auv_validation.evl",
                "--emf", f"M={auv / 'model' / 'AUV.model'};{auv / 'metamodel' / 'auv.ecore'}",
            )],
            "runEmf2Robochart": [transform(
                "emf2robochart.egl",
                "--emf", f"M={auv / 'model' / 'AUV.model'};{auv / 'metamodel' / 'auv.ecore'}",
            )],
            "runReq2Concept": [transform(
                "req2concept_traceability.eol",
                "--emf", f"S={auv / 'model' / 'AUV.requirement'};{core / 'base.ecore'},{core / 'requirement.ecore'}",
                "--emf", f"T={auv / 'model' / 'example.terminology'};{core / 'base.ecore'},{core / 'terminology.ecore'};readOnLoad=false,storeOnDisposal=true",
                "--emf", f"B={auv / 'model' / 'req2concept.bifrost'};{core / 'bifrost.ecore'};readOnLoad=false,storeOnDisposal=true",
                "--json", f"J={auv / 'model' / 'result_concept_trace.json'}",
            )],
            "runReq2Ecore": [transform(
                "req2ecore_traceability.eol",
                "--emf", f"S={auv / 'model' / 'AUV.requirement'};{core / 'base.ecore'},{core / 'requirement.ecore'}",
                "--emf", f"T={auv / 'metamodel' / 'auv.ecore'};meta:http://www.eclipse.org/emf/2002/Ecore",
                "--emf", f"B={auv / 'model' / 'req2DSL.bifrost'};{core / 'bifrost.ecore'};readOnLoad=false,storeOnDisposal=true",
                "--json", f"J={auv / 'model' / 'result_dsml_trace.json'}",
            )],
            "runReq2EmfModel": [transform(
                "req2emf_model_traceability.eol",
                "--emf", f"S={auv / 'model' / 'AUV.requirement'};{core / 'base.ecore'},{core / 'requirement.ecore'}",
                "--emf", f"T={auv / 'model' / 'AUV.model'};{core / 'base.ecore'},{auv / 'metamodel' / 'auv.ecore'}",
                "--emf", f"B={auv / 'model' / 'req2model.bifrost'};{core / 'bifrost.ecore'};readOnLoad=false,storeOnDisposal=true",
                "--json", f"J={auv / 'model' / 'result_model_trace.json'}",
            )],
        }

        # runReq2StateMachine first parses the RoboChart text into AUV.robochart,
        # then runs the traceability transform against it.
        statemachine_cmds = [
            self._robochart_parse_command(
                auv / "model" / "result_behaviour_model.rct",
                auv / "model" / "AUV.robochart",
                auv / "metamodel" / "robochart.ecore",
            ),
            transform(
                "req2state_machine_traceability.eol",
                "--emf", f"S={auv / 'model' / 'AUV.requirement'};{core / 'base.ecore'},{core / 'requirement.ecore'}",
                "--emf", f"T={auv / 'model' / 'AUV.robochart'};{auv / 'metamodel' / 'robochart.ecore'}",
                "--emf", f"B={auv / 'model' / 'req2statemachine.bifrost'};{core / 'bifrost.ecore'};readOnLoad=false,storeOnDisposal=true",
                "--json", f"J={auv / 'model' / 'result_behaviour_trace.json'}",
            ),
        ]

        if command_id == "runReq2StateMachine":
            return statemachine_cmds

        # buildBifrost: create the EMF model instance + parse RoboChart text
        # (prerequisites), then run all four requirement->element traceability
        # transforms, in dependency order.
        if command_id == "buildBifrost":
            return [
                *tasks["runAuvEmfCreation"],
                *tasks["runReq2Concept"],
                *tasks["runReq2Ecore"],
                *tasks["runReq2EmfModel"],
                *statemachine_cmds,
            ]

        if command_id not in tasks:
            raise ValueError(f"Unsupported MALCOMj command without Gradle: {command_id}")
        return tasks[command_id]

    def _ensure_malcomj_runner(self) -> Path:
        runner = _MALCOMJ_DIR / "build" / "install" / "MALCOMj" / "bin" / (
            "MALCOMj.bat" if sys.platform == "win32" else "MALCOMj"
        )
        if runner.exists():
            return runner

        dist = _MALCOMJ_DIR / "build" / "distributions" / "MALCOMj.zip"
        if not dist.exists():
            raise FileNotFoundError(
                f"No {_GRADLEW} and no built MALCOMj distribution found at {dist}"
            )
        shutil.unpack_archive(str(dist), str(_MALCOMJ_DIR / "build" / "install"))
        if not runner.exists():
            raise FileNotFoundError(f"MALCOMj runner not found after unpacking {dist}")
        return runner

    def _robochart_parse_command(self, input_file: Path, output_file: Path,
                                 metamodel: Path) -> list[str]:
        classes = _MALCOMJ_DIR / "build" / "manual-classes"
        parser_class = classes / "org" / "sawg" / "malcomj" / "RoboChartTextParser.class"
        libs = _MALCOMJ_DIR / "build" / "install" / "MALCOMj" / "lib" / "*"
        if not parser_class.exists():
            classes.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    "javac",
                    "-encoding", "UTF-8",
                    "-cp", str(libs),
                    "-d", str(classes),
                    str(_MALCOMJ_DIR / "src" / "main" / "java" / "org" / "sawg" / "malcomj" / "RoboChartTextParser.java"),
                ],
                cwd=str(_MALCOMJ_DIR),
                check=True,
            )
        cp = f"{classes}{os.pathsep}{libs}"
        return [
            "java", "-cp", cp, "org.sawg.malcomj.RoboChartTextParser",
            "--input", str(input_file),
            "--output", str(output_file),
            "--metamodel", str(metamodel),
        ]

    def _copy_outputs_to_malcomj(self) -> None:
        """Copy MALCOMp output JSON/rct files to the case study's model directory,
        where MALCOMj's transformation tasks read them."""
        output_dir = self._get_output_dir()
        if not output_dir:
            return

        # MALCOMj reads case-study models from case_studies/<study>/model/,
        # the sibling of the MALCOMp output/ directory.
        target_dir = output_dir.parent / "model"
        if not target_dir.exists():
            return

        # JSON traces consumed by Bifrost transformations, plus result_behaviour_model.rct which
        # the runRobochartParse Gradle task parses into AUV.robochart before
        # runReq2StateMachine consumes it.
        output_files = [
            "result_concept_trace.json",
            "result_dsml_trace.json",
            "result_model_trace.json",
            "result_behaviour_trace.json",
            "result_behaviour_model.rct",
        ]
        for name in output_files:
            src = output_dir / name
            if src.exists():
                shutil.copy2(src, target_dir / name)
                logger.info("Copied %s to %s", src, target_dir / name)

    # ---- Stop ---------------------------------------------------------------

    def stop_phase(self) -> None:
        """Request the running phase to stop."""
        if not self.is_running:
            return

        phase_name = self._current_phase
        iostream = self._iostream

        self._stop_event.set()
        if iostream:
            iostream.close()

        # Detach the thread so new phases can start immediately
        self._thread = None
        self._current_phase = None
        self._iostream = None

        if iostream and phase_name:
            self.state.set_phase_status(phase_name, "stopped")
            iostream.notify_phase_event("phase_complete", status="stopped",
                                        phase=phase_name)

    # ---- Refine mode --------------------------------------------------------

    def start_refine(self, phase_name: str, user_message: str,
                     iostream: WebSocketIOStream,
                     loop: asyncio.AbstractEventLoop) -> None:
        """Launch a refine run: re-run a stage with user instructions."""
        if self.is_running:
            iostream.notify_phase_event(
                "error", message="A stage is already running",
            )
            return

        if phase_name not in STAGE_NAMES:
            iostream.notify_phase_event(
                "error", message=f"Unknown stage: {phase_name}",
            )
            return

        self._stop_event.clear()
        self._current_phase = phase_name
        self._iostream = iostream
        iostream.phase_name = phase_name
        iostream.reopen()  # revive the stream if a prior run was stopped
        iostream._flush_buffer()
        iostream._current_sender = ""
        self.state.set_phase_status(phase_name, "running")

        self._thread = threading.Thread(
            target=self._run_refine,
            args=(phase_name, user_message, iostream, loop),
            daemon=True,
        )
        self._thread.start()

    def _run_refine(self, phase_name: str, user_message: str,
                    iostream: WebSocketIOStream,
                    loop: asyncio.AbstractEventLoop) -> None:
        """Execute a refine run in a background thread."""
        from autogen.io import IOStream

        cached_stage = self._phase_cache.get(phase_name)
        status = "completed"
        try:
            with IOStream.set_default(iostream):
                if cached_stage:
                    result = cached_stage.run(
                        message=f"REFINEMENT REQUEST:\n{user_message}",
                    )
                    iostream.finalize()
                    stage = cached_stage
                else:
                    # No cache — re-create stage with refinement message
                    stages = _get_stage_classes()
                    cls = stages[phase_name]
                    stage = cls(
                        config_path=self.config_path,
                        run_id=self.state.ensure_pipeline_run_id(),
                        case_study=self.case_study,
                    )
                    result = stage.run(
                        message=f"REFINEMENT REQUEST:\n{user_message}",
                    )
                    iostream.finalize()

                self.state.set_phase_result(phase_name, result)
                self._phase_cache[phase_name] = stage

        except Exception as e:
            iostream.finalize()
            if self._stop_event.is_set():
                status = "stopped"
            else:
                logger.exception("Refine %s raised an exception", phase_name)
                status = "failed"
                self.state.set_phase_error(phase_name, str(e))
        finally:
            self._current_phase = None
            self._iostream = None

        if not self._stop_event.is_set():
            self.state.set_phase_status(phase_name, status)
            iostream.notify_phase_event("phase_complete", status=status,
                                        phase=phase_name)

    # ---- Helpers ------------------------------------------------------------

    def _get_output_dir(self) -> Path | None:
        """Get the output directory from the active config."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            config_dir = Path(self.config_path).resolve().parent
            return config_dir / "case_studies" / self.case_study / "output"
        except Exception:
            return None

    @staticmethod
    def _resolve_case_study(self) -> str:
        """Active case study for this bridge: session selection, else config
        default. Read once at construction into self.case_study; no env var."""
        sel = self.state.get_selected_case_study()
        if sel:
            return sel
        try:
            with open(self.config_path, encoding="utf-8") as f:
                return (yaml.safe_load(f) or {}).get("case_study") or "auv"
        except Exception:
            return "auv"
