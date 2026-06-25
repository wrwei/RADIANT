"""Session state with optional disk persistence for chat history and phase statuses."""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionState:
    """Thread-safe state container for a single pipeline session.

    When *persist_path* is given, state is saved to disk after important
    events and reloaded on construction so chat history and phase statuses
    survive server restarts.
    """

    def __init__(self, persist_path: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._phases: dict[str, dict[str, Any]] = {}
        self._messages: list[dict] = []
        self._selected_requirement: str = ""
        self._selected_case_study: str = ""
        self._selected_model: str = ""   # "" => use the config's default_model
        self._agent_mode: str = "multi"  # "multi" | "single"
        self._pipeline_run_id: str = ""
        self._persist_path = persist_path
        if persist_path:
            self._load()

    # ---- Message log --------------------------------------------------------

    def add_message(self, msg: dict) -> None:
        """Append a message to the chat log."""
        with self._lock:
            self._messages.append(msg)

    def get_messages(self) -> list[dict]:
        """Return a copy of all logged messages."""
        with self._lock:
            return list(self._messages)

    def clear_messages(self) -> None:
        """Clear the chat log."""
        with self._lock:
            self._messages.clear()

    # ---- Selected requirement ------------------------------------------------

    def set_selected_requirement(self, path: str) -> None:
        with self._lock:
            self._selected_requirement = path

    def get_selected_requirement(self) -> str:
        with self._lock:
            return self._selected_requirement

    # ---- Selected case study -------------------------------------------------

    def set_selected_case_study(self, path: str) -> None:
        with self._lock:
            self._selected_case_study = path

    def get_selected_case_study(self) -> str:
        with self._lock:
            return self._selected_case_study

    # ---- Run configuration (LLM model + agent mode) -------------------------

    def set_run_config(self, model: str | None = None,
                       agent_mode: str | None = None) -> None:
        """Update the selected LLM model key and/or agent mode for subsequent runs."""
        with self._lock:
            if model is not None:
                self._selected_model = model
            if agent_mode is not None:
                self._agent_mode = agent_mode
        self.save()

    def get_selected_model(self) -> str:
        with self._lock:
            return self._selected_model

    def get_agent_mode(self) -> str:
        with self._lock:
            return self._agent_mode or "multi"

    # ---- Pipeline run archive ----------------------------------------------

    def ensure_pipeline_run_id(self) -> str:
        """Return the current archive run id, creating one if necessary."""
        with self._lock:
            if not self._pipeline_run_id:
                self._pipeline_run_id = f"web_{datetime.now():%Y%m%d_%H%M%S}"
            return self._pipeline_run_id

    def get_pipeline_run_id(self) -> str:
        with self._lock:
            return self._pipeline_run_id

    def start_new_pipeline_run(self) -> str:
        """Create and return a fresh archive run id."""
        with self._lock:
            self._pipeline_run_id = f"web_{datetime.now():%Y%m%d_%H%M%S}"
            return self._pipeline_run_id

    # ---- Phase status -------------------------------------------------------

    def set_phase_status(self, phase: str, status: str) -> None:
        with self._lock:
            self._phases.setdefault(phase, {})["status"] = status

    def get_phase_status(self, phase: str) -> str:
        with self._lock:
            return self._phases.get(phase, {}).get("status", "idle")

    def set_phase_result(self, phase: str, result: Any) -> None:
        with self._lock:
            self._phases.setdefault(phase, {})["result"] = result

    def set_phase_error(self, phase: str, error: str) -> None:
        with self._lock:
            self._phases.setdefault(phase, {})["error"] = error

    def get_phase_statuses(self) -> dict[str, str]:
        """Return {phase_name: status} for all known phases."""
        with self._lock:
            return {
                name: info.get("status", "idle")
                for name, info in self._phases.items()
            }

    def set_phase_verification(self, phase: str, result: dict) -> None:
        with self._lock:
            self._phases.setdefault(phase, {})["verification"] = result
        self.save()

    def get_phase_verifications(self) -> dict[str, dict]:
        """Return {phase_name: {passed, checks}} for phases that have been verified."""
        with self._lock:
            return {
                name: info["verification"]
                for name, info in self._phases.items()
                if "verification" in info
            }

    def to_dict(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {
                name: {"status": info.get("status", "idle")}
                for name, info in self._phases.items()
            }

    def reset(self) -> None:
        """Clear all state (phases + messages) and persist."""
        with self._lock:
            self._phases.clear()
            self._messages.clear()
            self._selected_requirement = ""
            self._pipeline_run_id = ""
        self.save()

    def clear_run_state(self) -> None:
        """Reset per-run state (phase statuses, selected requirement, run id) when
        switching case study, keeping the message log."""
        with self._lock:
            self._phases.clear()
            self._selected_requirement = ""
            self._pipeline_run_id = ""
        self.save()

    # ---- Persistence --------------------------------------------------------

    def save(self) -> None:
        """Write state to disk."""
        if not self._persist_path:
            return
        with self._lock:
            data = {
                "messages": self._messages,
                "phases": {
                    name: {"status": info.get("status", "idle"),
                           **({"verification": info["verification"]}
                              if "verification" in info else {})}
                    for name, info in self._phases.items()
                },
                "selected_requirement": self._selected_requirement,
                "selected_case_study": self._selected_case_study,
                "selected_model": self._selected_model,
                "agent_mode": self._agent_mode,
                "pipeline_run_id": self._pipeline_run_id,
            }
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            logger.debug("Failed to save session state")

    def _load(self) -> None:
        """Load state from disk."""
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))
            self._messages = data.get("messages", [])
            self._selected_requirement = data.get("selected_requirement", "")
            self._selected_case_study = data.get("selected_case_study", "")
            self._selected_model = data.get("selected_model", "")
            self._agent_mode = data.get("agent_mode", "multi")
            self._pipeline_run_id = data.get("pipeline_run_id", "")
            for name, info in data.get("phases", {}).items():
                self._phases[name] = {"status": info.get("status", "idle")}
                if "verification" in info:
                    self._phases[name]["verification"] = info["verification"]
            # Reset any "running" phases (server crashed mid-phase)
            for info in self._phases.values():
                if info.get("status") == "running":
                    info["status"] = "stopped"
        except (json.JSONDecodeError, OSError):
            logger.debug("Failed to load session state")
