# ETL Pipeline Observability Dashboard

I built this project to demonstrate run-level observability for Glue/PySpark-style ETL systems. A configurable simulator produces normal, slow, failed, schema-drifted, and low-quality runs. SQLite stores run history and alerts; FastAPI exposes metrics; Plotly presents duration trends and alert history.

`simulator → quality + schema checks → SQLite → FastAPI → dashboard`

## Run

```bash
docker compose up --build
```

Open `http://localhost:8000` and click **Generate demo runs**. A healthy run has stable duration and row counts, null rate below 8%, duplicates below 4%, and no schema difference. Alerts use a pluggable storage boundary that can be replaced by Slack or email delivery.

## Tests

`pip install -r requirements.txt && pytest`

## Limitations and roadmap

This monitors simulated jobs rather than a live Glue account. I would next add OpenTelemetry ingestion, Postgres, webhook delivery, baseline windows per job, seasonality-aware thresholds, authentication, and real Spark listeners.

## Suggested commits

1. `set up observability service`
2. `add SQLite metrics store`
3. `implement realistic ETL simulator`
4. `add schema drift detection`
5. `add quality threshold checks`
6. `persist alert history`
7. `add FastAPI metrics endpoints`
8. `build Plotly operations dashboard`
9. `add detector and alert tests`
10. `add Docker Compose setup`
11. `document pipeline health model`

## GitHub CLI

```bash
git init -b main
git add app/core.py && git commit -m "add metrics store and ETL simulator"
git add app/main.py app/static && git commit -m "add API and dashboard"
git add tests requirements.txt && git commit -m "add observability tests"
git add Dockerfile docker-compose.yml && git commit -m "add Docker Compose setup"
git add README.md && git commit -m "document pipeline health model"
gh repo create etl-observability-dashboard --public --source=. --remote=origin
git push -u origin main
```

MIT licensed. Research and portfolio demonstration.
