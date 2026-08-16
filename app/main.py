from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

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
    version="2.0.0",
    description="Run-level observability API for ETL pipelines with quality, drift, and failure detection.",
)
static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static), name="static")


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(static / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "etl-observability-dashboard"}


@app.get("/api/summary")
def summary(window: int = Query(100, ge=1, le=1000)):
    return store.summary(window)


@app.get("/api/runs")
def runs(limit: int = Query(200, ge=1, le=1000)):
    return store.rows("runs", limit)


@app.get("/api/alerts")
def alerts(limit: int = Query(200, ge=1, le=1000)):
    return store.rows("alerts", limit)


@app.post("/api/runs", status_code=201)
def ingest_run(payload: RunIn):
    return evaluate_observation(store, **payload.model_dump())


@app.post("/api/simulate")
def seed(count: int = Query(36, ge=1, le=500), seed: int = 7):
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
