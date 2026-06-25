"""TestClient + SessionState checks for the LLM-model / agent-mode configuration."""
import sys
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parents[2]   # MALCOM-web
sys.path.insert(0, str(WEB_ROOT))


def test_models_endpoint_shape():
    from fastapi.testclient import TestClient
    from web.server import app
    client = TestClient(app)
    resp = client.get("/api/models")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["models"], list) and body["models"], "expected a non-empty models list"
    for m in body["models"]:
        assert "key" in m and "name" in m
    keys = {m["key"] for m in body["models"]}
    assert body["default"] in keys, "default_model must be one of the listed models"
    assert body["selected"] in keys, "selection must resolve to a known model"
    assert body["agent_mode"] in {"single", "multi"}


def test_session_run_config_roundtrip(tmp_path):
    from web.state import SessionState
    persist = tmp_path / "session.json"

    s = SessionState(persist_path=persist)
    assert s.get_agent_mode() == "multi"          # default
    assert s.get_selected_model() == ""           # "" => config default

    s.set_run_config(model="gpt_4o", agent_mode="single")
    assert s.get_selected_model() == "gpt_4o"
    assert s.get_agent_mode() == "single"

    # Partial update keeps the other field.
    s.set_run_config(agent_mode="multi")
    assert s.get_selected_model() == "gpt_4o"
    assert s.get_agent_mode() == "multi"

    # Persisted across a reload.
    s2 = SessionState(persist_path=persist)
    assert s2.get_selected_model() == "gpt_4o"
    assert s2.get_agent_mode() == "multi"
