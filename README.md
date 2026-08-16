# ETL Observability Dashboard

A production-style portfolio project for monitoring ETL pipeline reliability. It captures run telemetry, evaluates data quality and schema drift, persists run/alert history, exposes a FastAPI ingestion API, and renders an auto-refreshing operations dashboard.

`ETL job → telemetry ingestion → quality + drift evaluation → SQLite → FastAPI → live dashboard`

## What it monitors

- Pipeline success/failure state
- Runtime trends and p95 duration
- Input/output row volumes
- Null-rate and duplicate-rate quality checks
- Row-count anomaly detection against recent job history
- Schema additions, removals, and type changes
- Alert history across failures, quality breaches, and schema drift
- Per-job health summaries

## Run locally

```bash
docker compose up --build
```

Open `http://localhost:8000`.

The dashboard refreshes automatically every 10 seconds. Click **Generate demo telemetry** to populate realistic sample runs, or send telemetry from a real ETL job through the API.

## Ingest a real ETL run

```bash
curl -X POST http://localhost:8000/api/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "job": "orders_etl",
    "status": "success",
    "duration": 42.7,
    "rows_in": 10500,
    "rows_out": 10220,
    "null_rate": 0.012,
    "duplicate_rate": 0.003,
    "schema": {"id": "int", "value": "float", "source": "string"}
  }'
```

You can wire this endpoint into Airflow, AWS Glue, dbt orchestration, Spark jobs, cron-based pipelines, or any ETL system that can make an HTTP request after a run.

## API

- `GET /health` — service health
- `GET /api/summary` — dashboard KPIs and per-job health
- `GET /api/runs` — recent pipeline runs
- `GET /api/alerts` — recent alerts
- `POST /api/runs` — ingest real pipeline telemetry
- `POST /api/simulate` — generate demo telemetry
- `GET /docs` — interactive OpenAPI documentation

## Quality model

Default thresholds:

- null rate: `<= 8%`
- duplicate rate: `<= 4%`
- output row deviation from recent job average: `<= 35%`

These values are deliberately simple and visible for a portfolio implementation. In a production deployment, thresholds should be configurable per dataset/job and may incorporate seasonality or SLA windows.

## Tests and CI

```bash
pip install -r requirements.txt
pytest -q
```

GitHub Actions automatically runs the test suite and builds the Docker image on pull requests and updates to `main`.

## Architecture

- **FastAPI** for telemetry ingestion and metrics APIs
- **SQLite** for lightweight persistent run and alert history
- **Plotly** for interactive runtime visualization
- **Docker / Compose** for repeatable deployment
- **GitHub Actions** for automated validation

## Production extensions

Natural next steps are PostgreSQL/TimescaleDB storage, authentication, webhook/Slack alert delivery, OpenTelemetry ingestion, per-job configurable thresholds, Airflow/Glue adapters, and Prometheus-compatible metrics.

MIT licensed. Built as a data engineering / observability portfolio project.
