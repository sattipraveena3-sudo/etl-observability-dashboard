from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_and_readiness():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["version"] == "3.0.0"

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "database": "ok"}


def test_ingest_summary_and_job_drilldown():
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
    assert any(job["job"] == "inventory_etl" for job in summary["jobs"])

    job_runs = client.get("/api/jobs/inventory_etl/runs").json()
    assert job_runs
    assert all(run["job"] == "inventory_etl" for run in job_runs)


def test_simulate_endpoint():
    response = client.post("/api/simulate?count=3&seed=11")
    assert response.status_code == 200
    assert response.json() == {"created": 3, "seed": 11}


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "etl_runs_total" in response.text
    assert "etl_runs_failed_total" in response.text
    assert "etl_alerts_total" in response.text


def test_public_config_does_not_expose_secret():
    response = client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    assert "slow_run_seconds" in body
    assert "ingestion_api_key" not in body
