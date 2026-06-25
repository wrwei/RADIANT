"""Interactive Web UI for the RADIANT MDE pipeline."""
from __future__ import annotations

import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_malcomp_dir() -> Path:
    """Resolve the MALCOMp project directory.

    Honours the ``MALCOMP_DIR`` environment variable when set; otherwise
    falls back to ``../MALCOMp`` relative to this project's root (the
    expected sibling layout).
    """
    env = os.environ.get("MALCOMP_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (_PROJECT_ROOT.parent / "MALCOMp").resolve()


def get_malcomj_dir() -> Path:
    """Resolve the MALCOMj project directory.

    Honours the ``MALCOMJ_DIR`` environment variable when set; otherwise
    falls back to a sibling of MALCOMp (``MALCOMP_DIR.parent / MALCOMj``).
    """
    env = os.environ.get("MALCOMJ_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (get_malcomp_dir().parent / "MALCOMj").resolve()
