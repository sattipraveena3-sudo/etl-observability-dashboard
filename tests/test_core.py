from app.core import Store, check_quality, detect_schema_drift, evaluate_observation, simulate


def test_drift():
    assert detect_schema_drift({"id": "int"}, {"id": "string", "new": "float"}) == {
        "added": ["new"],
        "removed": [],
        "changed": ["id"],
    }


def test_quality():
    q = check_quality(100, 90, 10, 0, 100)
    assert "null_rate" in q.breached


def test_alerts(tmp_path):
    store = Store(tmp_path / "x.db")
    simulate(store, 15)
    assert store.rows("runs")
    assert store.rows("alerts")


def test_ingested_run_detects_failure_quality_and_schema_drift(tmp_path):
    store = Store(tmp_path / "observability.db")
    evaluate_observation(
        store,
        job="orders",
        status="success",
        duration=10,
        rows_in=100,
        rows_out=100,
        null_rate=0.0,
        duplicate_rate=0.0,
        schema={"id": "int"},
    )
    result = evaluate_observation(
        store,
        job="orders",
        status="failed",
        duration=25,
        rows_in=100,
        rows_out=50,
        null_rate=0.10,
        duplicate_rate=0.05,
        schema={"id": "string", "country": "string"},
    )
    assert "job execution failed" in result["alerts"]
    assert "null_rate" in result["quality"]["breached"]
    assert result["schema_drift"]["changed"] == ["id"]
    assert result["schema_drift"]["added"] == ["country"]


def test_summary(tmp_path):
    store = Store(tmp_path / "summary.db")
    simulate(store, 12)
    summary = store.summary()
    assert summary["total_runs"] == 12
    assert 0 <= summary["success_rate"] <= 1
    assert summary["avg_duration"] > 0
    assert summary["p95_duration"] > 0
    assert len(summary["jobs"]) == 3
