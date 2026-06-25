"""TestClient checks for the /api/thread endpoint."""
import sys
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parents[2]   # MALCOM-web
sys.path.insert(0, str(WEB_ROOT))


def test_thread_endpoint_returns_graph_shape():
    from fastapi.testclient import TestClient
    from web.server import app
    client = TestClient(app)
    resp = client.get("/api/thread")
    assert resp.status_code == 200
    g = resp.json()
    assert g["columns"] == ["requirement", "concept", "dsml", "model", "behaviour"]
    assert set(g["nodes"]) == {"requirement", "concept", "dsml", "model", "behaviour"}
    assert "links" in g and "stats" in g and "impact" in g
    assert "total_links" in g["stats"]
