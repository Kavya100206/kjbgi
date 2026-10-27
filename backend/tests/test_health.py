"""Test for /api/health endpoint — T0.2 smoke test."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert body["timestamp"].endswith("Z") or "+" in body["timestamp"]


def test_meta_returns_snapshot_info() -> None:
    resp = client.get("/api/meta")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["actuals_rows_loaded"] == 1536
    assert body["forecasts_rows_loaded"] == 19856
    assert "ingested_at" in body
    assert "window" in body
