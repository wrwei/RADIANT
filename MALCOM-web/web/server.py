"""FastAPI server: REST endpoints + WebSocket for real-time RADIANT pipeline UI."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import json as _json
import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from web import get_malcomp_dir
from web.bridge import (
    PipelineBridge, STAGE_NAMES, STAGE_AGENTS, PIPELINE_STRUCTURE,
    GRADLE_COMMANDS, STAGE_REQUIRED_AGENTS, STAGE_REPAIR_AGENTS, _STAGE_CONFIG_KEY,
)
from web.iostream import WebSocketIOStream
from web.state import SessionState

logger = logging.getLogger(__name__)

MALCOMP_DIR = get_malcomp_dir()
STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_CONFIG = MALCOMP_DIR.parent / "config.yaml"

# Ensure MALCOMp root is importable so PipelineBridge can `from phases import ...`
if str(MALCOMP_DIR) not in sys.path:
    sys.path.insert(0, str(MALCOMP_DIR))

app = FastAPI(title="RADIANT Pipeline UI")

# Serve static assets (CSS, JS)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Module-level persistent session state
_SESSION_FILE = MALCOMP_DIR / "output" / ".session.json"
_state = SessionState(persist_path=_SESSION_FILE)


CASE_STUDIES_ROOT = MALCOMP_DIR.parent / "case_studies"


def _active_config() -> str:
    """Path to the single root config.yaml."""
    return str(DEFAULT_CONFIG)


def _config_dir() -> Path:
    return Path(_active_config()).resolve().parent


def _active_case_study() -> str:
    """The selected case study (session override, else the config's default).
    Read-only: the active study is passed explicitly to the bridge (and thence to
    each stage), so no process-global env var is involved."""
    name = _state.get_selected_case_study()
    if not name or not (CASE_STUDIES_ROOT / name / "requirements").exists():
        try:
            with open(DEFAULT_CONFIG, encoding="utf-8") as f:
                name = (yaml.safe_load(f) or {}).get("case_study", "")
        except Exception:
            name = ""
    return name


def _case_dir() -> Path:
    return CASE_STUDIES_ROOT / _active_case_study()


def _output_dir() -> Path:
    return _case_dir() / "output"


def _assets_dir() -> Path:
    """Root for requirement discovery — the active case study's directory."""
    return _case_dir()


def _case_studies() -> list[dict]:
    """Selectable case studies: each case_studies/<name>/ that provides
    requirements/. config_path carries the case-study name (the selector key)."""
    studies = []
    if CASE_STUDIES_ROOT.exists():
        for d in sorted(CASE_STUDIES_ROOT.iterdir()):
            if d.is_dir() and (d / "requirements").exists():
                studies.append({"name": d.name, "config_path": d.name})
    return studies


# ---------- REST endpoints ------------------------------------------------

def _models_payload() -> dict:
    """LLM models from config.yaml's `models:` map + the session's current selection."""
    with open(_active_config(), encoding="utf-8") as f:
        config = yaml.safe_load(f)
    models_map = config.get("models", {}) or {}
    default_key = config.get("default_model", "") or ""
    models = [{"key": k, "name": (v or {}).get("name", k)} for k, v in models_map.items()]
    selected = _state.get_selected_model() or default_key
    return {
        "models": models,
        "default": default_key,
        "selected": selected,
        "agent_mode": _state.get_agent_mode(),
    }


@app.get("/")
async def index():
    """Serve the main HTML page."""
    return FileResponse(
        str(STATIC_DIR / "index.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/api/config")
async def get_config():
    """Return the current config.yaml."""
    with open(_active_config(), encoding="utf-8") as f:
        return yaml.safe_load(f)


@app.get("/api/case-studies")
async def list_case_studies():
    """The active case study, from the single root config.yaml."""
    return {"case_studies": _case_studies()}


@app.get("/api/models")
async def list_models():
    """Available LLM models and the current model / agent-mode selection."""
    return _models_payload()


@app.get("/api/stages")
async def get_stages():
    """Return stage names and agent rosters."""
    return {"stages": STAGE_NAMES, "agents": STAGE_AGENTS}


@app.get("/api/requirements")
async def list_requirements():
    """List requirement JSON files from the active case study."""
    assets_dir = _assets_dir()
    files = []
    if assets_dir.exists():
        for f in sorted(assets_dir.rglob("requirement_*.json")):
            files.append({
                "path": str(f.relative_to(_config_dir())),
                "name": f.stem,
            })
    return {"files": files}


@app.get("/api/req-files/{path:path}")
async def get_requirement_file_content(path: str):
    """Return content of a requirement JSON file."""
    full = (_config_dir() / path).resolve()
    assets_root = _assets_dir().resolve()
    if not str(full).startswith(str(assets_root)):
        return JSONResponse({"error": "invalid path"}, status_code=400)
    if not full.exists() or not full.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        content = full.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return JSONResponse({"error": "binary file"}, status_code=400)
    return {"path": path, "content": content}


@app.get("/api/files")
async def list_output_files():
    """List files in the output directory."""
    out = _output_dir()
    if not out.exists():
        return {"files": []}
    files = []
    for f in sorted(out.rglob("*")):
        if f.is_file() and not f.name.startswith("."):
            files.append({
                "path": str(f.relative_to(out)).replace("\\", "/"),
                "size": f.stat().st_size,
            })
    return {"files": files}


@app.get("/api/files/{path:path}")
async def get_file_content(path: str):
    """Return content of a specific output file."""
    out = _output_dir()
    full = (out / path).resolve()
    if not str(full).startswith(str(out.resolve())):
        return JSONResponse({"error": "invalid path"}, status_code=400)
    if not full.exists() or not full.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        content = full.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return JSONResponse({"error": "binary file"}, status_code=400)
    return {"path": path, "content": content}


@app.get("/api/task-files/{task}")
async def list_task_files(task: str):
    """Return output files belonging to a specific stage."""
    out = _output_dir()
    files: list[str] = []

    if task in STAGE_NAMES:
        # LLM-based stage — find outputs from config
        config_key = _STAGE_CONFIG_KEY.get(task, task)
        try:
            with open(_active_config(), encoding="utf-8") as f:
                config = yaml.safe_load(f)
            stage_cfg = config.get("stages", {}).get(config_key, {})
            out_cfg = stage_cfg.get("output", {})

            json_file = out_cfg.get("json_file")
            code_file = out_cfg.get("code_file")

            if json_file and (out / json_file).exists():
                files.append(json_file)
            if code_file and (out / code_file).exists():
                files.append(code_file)
        except Exception:
            pass
    elif task in GRADLE_COMMANDS:
        # Gradle command — currently no separate output dir tracking
        pass

    # Fallback: if no specific files found, list all output files
    if not files and out.exists():
        for f in sorted(out.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                files.append(str(f.relative_to(out)).replace("\\", "/"))

    return {"task": task, "files": files}


@app.get("/api/thread")
async def get_thread():
    """The Digital Thread graph for the active case study's current output."""
    import change_impact as ci  # MALCOMp root is on sys.path
    empty = {
        "case_study": _active_case_study(),
        "columns": ["requirement", "concept", "dsml", "model", "behaviour"],
        "nodes": {k: [] for k in ("requirement", "concept", "dsml", "model", "behaviour")},
        "links": [], "impact": {"requirements": [], "elements": []},
        "stats": {"total_links": 0, "by_phase": {}, "coverage": {}},
    }
    out = _output_dir()
    if not out.exists():
        return empty
    try:
        return ci.build_thread(out, _case_dir())
    except Exception:
        logger.exception("build_thread failed")
        return empty


# ---------- WebSocket endpoint --------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Handle real-time communication with the browser."""
    await ws.accept()
    loop = asyncio.get_running_loop()
    config_path = _active_config()
    bridge = PipelineBridge(config_path, _state, case_study=_active_case_study())
    iostream = WebSocketIOStream(ws, loop, state=_state)

    try:
        # Build requirements list
        req_files = []
        assets_dir = _assets_dir()
        if assets_dir.exists():
            for f in sorted(assets_dir.rglob("requirement_*.json")):
                req_files.append({
                    "path": str(f.relative_to(_config_dir())),
                    "name": f.stem,
                })

        # The single root config, presented as one case study.
        case_studies = _case_studies()

        # Check which output files exist (for dependency indicators)
        out = _output_dir()
        existing_outputs = []
        if out.exists():
            for f in out.rglob("*"):
                if f.is_file():
                    existing_outputs.append(
                        str(f.relative_to(out)).replace("\\", "/")
                    )

        # Send initial state
        await ws.send_json({
            "type": "connected",
            "stages": STAGE_NAMES,
            "agents": STAGE_AGENTS,
            "required_agents": {
                stage: sorted(agents)
                for stage, agents in STAGE_REQUIRED_AGENTS.items()
            },
            "pipeline": PIPELINE_STRUCTURE,
            "requirements": req_files,
            "case_studies": case_studies,
            "selected_requirement": _state.get_selected_requirement(),
            "selected_case_study": _active_case_study(),
            "history": _state.get_messages(),
            "phase_statuses": _state.get_phase_statuses(),
            "verifications": _state.get_phase_verifications(),
            "repair_agents": STAGE_REPAIR_AGENTS,
            "gradle_commands": GRADLE_COMMANDS,
            "models_config": _models_payload(),
            "existing_outputs": existing_outputs,
        })

        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "select_requirement":
                path = data.get("path", "")
                _state.set_selected_requirement(path)
                _state.save()

            elif msg_type == "select_case_study":
                # config_path now carries the case-study name (the selector key).
                name = data.get("config_path", "")
                _state.set_selected_case_study(name)
                # New study => clear stale per-run state (selected requirement,
                # phase statuses, run id) so nothing from the old study leaks in.
                _state.clear_run_state()
                # Stop any running phase, then rebind the bridge to the root config
                # with the selected study passed explicitly (no global env var).
                bridge.stop_phase()
                bridge = PipelineBridge(str(DEFAULT_CONFIG), _state, case_study=name)
                # Requirements for the newly selected study.
                new_reqs = []
                new_assets = _assets_dir()
                if new_assets.exists():
                    for f in sorted(new_assets.rglob("requirement_*.json")):
                        new_reqs.append({
                            "path": str(f.relative_to(_config_dir())),
                            "name": f.stem,
                        })
                # Refreshed outputs for the new study (gradle dep gating + archive).
                new_out = _output_dir()
                new_existing = []
                if new_out.exists():
                    for f in new_out.rglob("*"):
                        if f.is_file():
                            new_existing.append(str(f.relative_to(new_out)).replace("\\", "/"))
                await ws.send_json({
                    "type": "case_study_changed",
                    "config_path": name,
                    "requirements": new_reqs,
                    "existing_outputs": new_existing,
                    "phase_statuses": _state.get_phase_statuses(),
                })

            elif msg_type == "set_config":
                _state.set_run_config(
                    model=data.get("model"),
                    agent_mode=data.get("agent_mode"),
                )
                await ws.send_json({
                    "type": "config_changed",
                    "selected_model": _state.get_selected_model(),
                    "agent_mode": _state.get_agent_mode(),
                })

            elif msg_type == "start_phase":
                phase_name = data.get("phase", "")
                requirements = data.get("requirements") or _state.get_selected_requirement() or None
                if phase_name == "behaviour" and requirements:
                    req_name = Path(requirements).name.replace("\\", "/").lower()
                    if req_name != "requirement_behaviour.json":
                        requirements = None
                disabled = data.get("disabled_agents", [])
                feed_mode = data.get("feed_mode", "batch")
                bridge.start_phase(phase_name, iostream, loop,
                                   requirements_override=requirements,
                                   disabled_agents=disabled,
                                   feed_mode=feed_mode,
                                   model=_state.get_selected_model() or None,
                                   agent_mode=_state.get_agent_mode())

            elif msg_type == "start_command":
                command_id = data.get("command", "")
                bridge.start_command(command_id, iostream, loop)

            elif msg_type == "refine":
                phase_name = data.get("phase", "")
                user_message = data.get("message", "")
                bridge.start_refine(phase_name, user_message, iostream, loop)

            elif msg_type == "stop_phase":
                bridge.stop_phase()

            elif msg_type == "clear_dialogue":
                _state.clear_messages()
                _state.save()

            elif msg_type == "user_input":
                iostream.provide_input(data.get("content", ""))

            elif msg_type == "list_files":
                task_filter = data.get("task")
                out = _output_dir()
                files: list[str] = []

                if task_filter and task_filter in STAGE_NAMES:
                    config_key = _STAGE_CONFIG_KEY.get(task_filter, task_filter)
                    try:
                        with open(_active_config(), encoding="utf-8") as cf:
                            cfg = yaml.safe_load(cf)
                        stage_cfg = cfg.get("stages", {}).get(config_key, {})
                        out_cfg = stage_cfg.get("output", {})
                        json_file = out_cfg.get("json_file")
                        code_file = out_cfg.get("code_file")
                        if json_file and (out / json_file).exists():
                            files.append(json_file)
                        if code_file and (out / code_file).exists():
                            files.append(code_file)
                    except Exception:
                        pass
                elif out.exists():
                    for f in sorted(out.rglob("*")):
                        if f.is_file() and not f.name.startswith("."):
                            files.append(
                                str(f.relative_to(out)).replace("\\", "/")
                            )

                await ws.send_json({
                    "type": "file_list",
                    "task": task_filter or "",
                    "files": files,
                })

            elif msg_type == "clear_output":
                task_filter = data.get("task")
                out = _output_dir()
                try:
                    count = 0
                    if task_filter and task_filter in STAGE_NAMES:
                        config_key = _STAGE_CONFIG_KEY.get(task_filter, task_filter)
                        with open(_active_config(), encoding="utf-8") as cf:
                            cfg = yaml.safe_load(cf)
                        stage_cfg = cfg.get("stages", {}).get(config_key, {})
                        out_cfg = stage_cfg.get("output", {})
                        for key in ("json_file", "code_file"):
                            fname = out_cfg.get(key)
                            if fname and (out / fname).exists():
                                (out / fname).unlink()
                                count += 1
                        _state.set_phase_status(task_filter, "idle")
                    else:
                        if out.exists():
                            for f in list(out.rglob("*")):
                                if f.is_file():
                                    f.unlink()
                                    count += 1
                            for d in sorted(out.rglob("*"), reverse=True):
                                if d.is_dir():
                                    try:
                                        d.rmdir()
                                    except OSError:
                                        pass
                        _state.reset()

                    await ws.send_json({
                        "type": "clear_result",
                        "status": "ok",
                        "count": count,
                        "task": task_filter or "",
                    })
                except Exception as exc:
                    logger.exception("Clear output failed")
                    await ws.send_json({
                        "type": "clear_result",
                        "status": "error",
                        "message": str(exc),
                    })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    finally:
        iostream.close()
