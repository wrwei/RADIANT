"""Launch the RADIANT Pipeline Web UI.

Usage:
    cd MALCOM-web
    python -m web

Configuration (optional environment variables):
    MALCOMP_DIR — path to the MALCOMp project (default: ../MALCOMp)
    MALCOMJ_DIR — path to the MALCOMj project (default: ../MALCOMj)
"""
import uvicorn

uvicorn.run("web.server:app", host="0.0.0.0", port=8000, reload=True)
