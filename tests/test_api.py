from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingest_and_summary():
    payload = {
        "job": "inventory_etl",
        "status": "success",
        "duration": 14.2,
        "rows_in": 1000,
        "rows_out": 990,
        "null_rate": 0.01,
        "duplicate_rate": 0.005,
        "schema": {"id": "int", "sku": "string"},
    }
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["run"]["job"] == "inventory_etl"

    summary = client.get("/api/summary").json()
    assert summary["total_runs"] >= 1


def test_simulate_endpoint():
    response = client.post("/api/simulate?count=3&seed=11")
    assert response.status_code == 200
    assert response.json() == {"created": 3, "seed": 11}
