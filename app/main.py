from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.core import Store, evaluate_observation, simulate


class RunIn(BaseModel):
    job: str = Field(min_length=1, max_length=120)
    status: Literal["success", "failed"] = "success"
    duration: float = Field(ge=0)
    rows_in: int = Field(ge=0)
    rows_out: int = Field(ge=0)
    null_rate: float = Field(ge=0, le=1)
    duplicate_rate: float = Field(ge=0, le=1)
    schema: dict[str, str]
    created: float | None = None


store = Store()
app = FastAPI(
    title="ETL Observability Dashboard",
    version="3.0.0",
    description="Production-style run-level observability API for ETL pipelines with quality, drift, latency, and failure detection.",
)
static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static), name="static")


def require_ingestion_key(x_api_key: str | None) -> None:
    if settings.ingestion_api_key and x_api_key != settings.ingestion_api_key:
        raise HTTPException(status_code=401, detail="invalid ingestion API key")


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(static / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "etl-observability-dashboard", "version": "3.0.0"}


@app.get("/ready")
def ready() -> dict[str, str]:
    if not store.ping():
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ready", "database": "ok"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    values = store.metrics()
    lines = [
        "# HELP etl_runs_total Total ETL runs ingested.",
        "# TYPE etl_runs_total counter",
        f"etl_runs_total {values['runs_total']}",
        "# HELP etl_runs_failed_total Total failed ETL runs.",
        "# TYPE etl_runs_failed_total counter",
        f"etl_runs_failed_total {values['runs_failed_total']}",
        "# HELP etl_alerts_total Total observability alerts generated.",
        "# TYPE etl_alerts_total counter",
        f"etl_alerts_total {values['alerts_total']}",
        "# HELP etl_run_duration_seconds_avg Average ETL run duration in seconds.",
        "# TYPE etl_run_duration_seconds_avg gauge",
        f"etl_run_duration_seconds_avg {values['run_duration_seconds_avg']}",
    ]
    return "\n".join(lines) + "\n"


@app.get("/api/config")
def public_config() -> dict[str, float]:
    return {
        "null_rate_threshold": settings.null_rate_threshold,
        "duplicate_rate_threshold": settings.duplicate_rate_threshold,
        "row_delta_threshold": settings.row_delta_threshold,
        "slow_run_seconds": settings.slow_run_seconds,
    }


@app.get("/api/summary")
def summary(window: int = Query(100, ge=1, le=1000)):
    return store.summary(window)


@app.get("/api/runs")
def runs(limit: int = Query(200, ge=1, le=1000)):
    return store.rows("runs", limit)


@app.get("/api/jobs/{job}/runs")
def job_runs(job: str, limit: int = Query(100, ge=1, le=1000)):
    return store.job_runs(job, limit)


@app.get("/api/alerts")
def alerts(limit: int = Query(200, ge=1, le=1000)):
    return store.rows("alerts", limit)


@app.post("/api/runs", status_code=201)
def ingest_run(payload: RunIn, x_api_key: str | None = Header(default=None)):
    require_ingestion_key(x_api_key)
    return evaluate_observation(store, **payload.model_dump())


@app.post("/api/simulate")
def seed(
    count: int = Query(36, ge=1, le=500),
    seed: int = 7,
    x_api_key: str | None = Header(default=None),
):
    require_ingestion_key(x_api_key)
    simulate(store, count=count, seed=seed)
    return {"created": count, "seed": seed}


# Backwards-compatible aliases for the original demo API.
@app.get("/runs", include_in_schema=False)
def legacy_runs():
    return store.rows("runs")


@app.get("/alerts", include_in_schema=False)
def legacy_alerts():
    return store.rows("alerts")


@app.post("/simulate", include_in_schema=False)
def legacy_seed(count: int = 24):
    simulate(store, count=count)
    return {"created": count}
