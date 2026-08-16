# ETL Observability Dashboard

A complete, runnable ETL reliability and observability project. It accepts telemetry from real pipelines, detects failures, slow runs, data-quality breaches and schema drift, persists history, exposes operational APIs/metrics, and presents a live auto-refreshing dashboard.

`ETL job → telemetry API → quality/drift/SLA evaluation → SQLite → FastAPI → dashboard + metrics`

## Features

- Real ETL run ingestion over REST
- Pipeline success/failure monitoring
- Runtime trend, average and p95 duration metrics
- Slow-run alerting
- Input/output row-volume monitoring
- Null-rate and duplicate-rate checks
- Historical row-count anomaly detection
- Schema additions/removals/type-change detection
- Persistent run and alert history
- Per-job health summaries and run drilldowns
- Prometheus-compatible `/metrics` endpoint
- Liveness `/health` and readiness `/ready` probes
- Optional API-key protection for ingestion
- Configurable thresholds through environment variables
- Responsive Plotly operations dashboard
- Automatic dashboard refresh every 10 seconds
- Realistic demo telemetry generator
- Docker and Docker Compose startup
- Unit/API integration tests
- GitHub Actions test, image-build and running-container smoke checks
- Interactive OpenAPI docs at `/docs`

## Fastest start

Requirements: Docker + Docker Compose.

```bash
git clone https://github.com/sattipraveena3-sudo/etl-observability-dashboard.git
cd etl-observability-dashboard
docker compose up --build
```

Open `http://localhost:8000`, then click **Generate demo telemetry**.

Useful endpoints:

- Dashboard: `http://localhost:8000/`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Readiness: `http://localhost:8000/ready`
- Metrics: `http://localhost:8000/metrics`

## Local Python development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make test
make run
```

In another terminal:

```bash
make seed
make smoke
```

## Send telemetry from a real ETL job

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

This can be called from Airflow, AWS Glue, Spark, dbt orchestration, Dagster, Prefect, cron jobs, CI pipelines, or any ETL runner capable of an HTTP request.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Liveness probe |
| GET | `/ready` | Database readiness probe |
| GET | `/metrics` | Prometheus-style service metrics |
| GET | `/api/config` | Public alert thresholds |
| GET | `/api/summary` | KPIs and per-job health |
| GET | `/api/runs` | Recent runs |
| GET | `/api/jobs/{job}/runs` | Run history for one job |
| GET | `/api/alerts` | Recent alert stream |
| POST | `/api/runs` | Ingest pipeline telemetry |
| POST | `/api/simulate` | Generate realistic demo telemetry |
| GET | `/docs` | Swagger/OpenAPI interface |

## Configuration

Copy the example settings if you want custom values:

```bash
cp .env.example .env
```

Available settings:

| Variable | Default | Meaning |
|---|---:|---|
| `DATABASE_PATH` | `data/metrics.db` | SQLite database location |
| `NULL_RATE_THRESHOLD` | `0.08` | Maximum null fraction |
| `DUPLICATE_RATE_THRESHOLD` | `0.04` | Maximum duplicate fraction |
| `ROW_DELTA_THRESHOLD` | `0.35` | Maximum deviation from recent output average |
| `SLOW_RUN_SECONDS` | `120` | Runtime threshold for slow-run alerts |
| `INGESTION_API_KEY` | empty | Optional key required by write endpoints |

When `INGESTION_API_KEY` is set, send it as `X-API-Key` when posting telemetry.

## Observability logic

For every submitted run the service compares the event with recent history for that job. It records the run, checks status and duration, calculates row-volume deviation, evaluates null/duplicate thresholds, compares the current schema with the previous schema, and writes alerts for any detected anomaly.

The demo generator deliberately creates healthy runs plus failures, slow executions, quality violations and schema changes so every major UI state can be exercised locally.

## Architecture

- **FastAPI** — ingestion, query and operational APIs
- **SQLite** — zero-setup persistent telemetry and alert storage
- **Plotly** — interactive runtime visualization
- **Vanilla HTML/CSS/JS** — lightweight dashboard with no frontend build step
- **Docker / Compose** — repeatable local or server startup
- **GitHub Actions** — Python compile check, pytest, container build and live smoke test

SQLite is intentional here: the repository stays completely runnable with one command and no external service dependencies. For larger deployments, the `Store` boundary can be replaced by PostgreSQL/TimescaleDB without changing the ingestion contract or dashboard APIs.

## Tests

```bash
pytest -q
```

The test suite covers schema drift, quality rules, alert generation, persistence, summary calculations, ingestion, job drilldowns, readiness, metrics and demo generation.

## CI

Every pull request runs:

1. dependency installation
2. Python source compilation
3. complete pytest suite
4. Docker image build
5. real container startup
6. `/ready`, `/health`, simulation, summary and `/metrics` smoke requests

This makes CI validate the same runnable service a user starts locally rather than only checking isolated functions.

## Repository commands

```bash
make install      # install Python dependencies
make test         # run tests
make run          # start development server
make seed         # generate demo telemetry
make smoke        # hit operational endpoints
make docker-up    # build/start Compose stack
make docker-down  # stop Compose stack
```

## Production-scale extensions

The project is fully runnable as-is. For a larger enterprise deployment, optional extensions would include PostgreSQL/TimescaleDB, SSO/RBAC, alert delivery to Slack/PagerDuty, OpenTelemetry collectors, per-job threshold policies and managed deployment infrastructure.

MIT licensed. Built as an end-to-end data engineering and observability portfolio project.
