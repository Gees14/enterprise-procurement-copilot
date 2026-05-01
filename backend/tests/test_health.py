import sys
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Heavy optional deps that are not installed in the local test env (available in Docker).
_HEAVY_MOCKS = {
    "sentence_transformers": MagicMock(),
    "chromadb": MagicMock(),
    "google.generativeai": MagicMock(),
}


def get_client():
    # Inject stubs before app.main is imported so module-level imports don't fail.
    with patch.dict(sys.modules, _HEAVY_MOCKS), \
         patch("app.db.database.create_engine") as mock_engine, \
         patch("app.db.database.Base.metadata.create_all"):
        mock_engine.return_value = MagicMock()
        from app.main import app
        return TestClient(app)


def test_health_returns_ok():
    client = get_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "llm_provider" in data
    assert "version" in data
