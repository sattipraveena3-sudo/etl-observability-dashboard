import json
import random
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.config import settings


@dataclass
class QualityResult:
    null_rate: float
    duplicate_rate: float
    row_delta: float
    breached: list[str]


def detect_schema_drift(baseline: dict[str, str], current: dict[str, str]) -> dict[str, list[str]]:
    return {
        "added": sorted(current.keys() - baseline.keys()),
        "removed": sorted(baseline.keys() - current.keys()),
        "changed": sorted(
            key for key in baseline.keys() & current.keys() if baseline[key] != current[key]
        ),
    }


def check_quality(
    rows_in: int,
    rows_out: int,
    nulls: int,
    duplicates: int,
    historical_average: float,
) -> QualityResult:
    null_rate = nulls / max(rows_out, 1)
    duplicate_rate = duplicates / max(rows_out, 1)
    row_delta = abs(rows_out - historical_average) / max(historical_average, 1)
    breached: list[str] = []
    if null_rate > settings.null_rate_threshold:
        breached.append("null_rate")
    if duplicate_rate > settings.duplicate_rate_threshold:
        breached.append("duplicate_rate")
    if row_delta > settings.row_delta_threshold:
        breached.append("row_count")
    return QualityResult(null_rate, duplicate_rate, row_delta, breached)


class Store:
    def __init__(self, path: str | Path = settings.database_path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.setup()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def setup(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                create table if not exists runs(
                    id integer primary key,
                    job text not null,
                    status text not null,
                    duration real not null,
                    rows_in int not null,
                    rows_out int not null,
                    null_rate real not null,
                    duplicate_rate real not null,
                    schema_json text not null,
                    created real not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists alerts(
                    id integer primary key,
                    job text not null,
                    level text not null,
                    message text not null,
                    created real not null
                )
                """
            )
            conn.execute("create index if not exists idx_runs_job_created on runs(job, created desc)")
            conn.execute("create index if not exists idx_alerts_created on alerts(created desc)")

    def ping(self) -> bool:
        try:
            with self.connect() as conn:
                conn.execute("select 1").fetchone()
            return True
        except sqlite3.Error:
            return False

    def add_run(self, run: tuple[Any, ...]) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                insert into runs(
                    job,status,duration,rows_in,rows_out,null_rate,duplicate_rate,schema_json,created
                ) values(?,?,?,?,?,?,?,?,?)
                """,
                run,
            )
            return int(cur.lastrowid)

    def add_observation(
        self,
        *,
        job: str,
        status: str,
        duration: float,
        rows_in: int,
        rows_out: int,
        null_rate: float,
        duplicate_rate: float,
        schema: dict[str, str],
        created: float | None = None,
    ) -> dict[str, Any]:
        created = created or time.time()
        run_id = self.add_run(
            (
                job,
                status,
                duration,
                rows_in,
                rows_out,
                null_rate,
                duplicate_rate,
                json.dumps(schema, sort_keys=True),
                created,
            )
        )
        return self.get_run(run_id)

    def get_run(self, run_id: int) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("select * from runs where id = ?", (run_id,)).fetchone()
            if row is None:
                raise KeyError(run_id)
            return dict(row)

    def alert(self, job: str, level: str, message: str, created: float | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                "insert into alerts(job,level,message,created) values(?,?,?,?)",
                (job, level, message, created or time.time()),
            )

    def rows(self, table: str, limit: int = 200) -> list[dict[str, Any]]:
        if table not in {"runs", "alerts"}:
            raise ValueError("unsupported table")
        limit = max(1, min(limit, 1000))
        with self.connect() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    f"select * from {table} order by created desc limit ?", (limit,)
                )
            ]

    def job_runs(self, job: str, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 1000))
        with self.connect() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    "select * from runs where job = ? order by created desc limit ?",
                    (job, limit),
                )
            ]

    def historical_average(self, job: str, limit: int = 20) -> float:
        with self.connect() as conn:
            rows = conn.execute(
                "select rows_out from runs where job = ? order by created desc limit ?",
                (job, limit),
            ).fetchall()
        if not rows:
            return 0.0
        return sum(row["rows_out"] for row in rows) / len(rows)

    def latest_schema(self, job: str) -> dict[str, str] | None:
        with self.connect() as conn:
            row = conn.execute(
                "select schema_json from runs where job = ? order by created desc limit 1", (job,)
            ).fetchone()
        return json.loads(row["schema_json"]) if row else None

    def summary(self, window: int = 100) -> dict[str, Any]:
        runs = self.rows("runs", window)
        alerts = self.rows("alerts", window)
        if not runs:
            return {
                "total_runs": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0,
                "p95_duration": 0.0,
                "active_alerts": 0,
                "jobs": [],
            }

        durations = sorted(run["duration"] for run in runs)
        p95_idx = min(len(durations) - 1, max(0, int(round(0.95 * (len(durations) - 1)))))
        jobs: dict[str, dict[str, Any]] = {}
        for run in runs:
            item = jobs.setdefault(
                run["job"],
                {
                    "job": run["job"],
                    "runs": 0,
                    "failures": 0,
                    "latest_status": None,
                    "latest_created": 0,
                    "avg_duration": 0.0,
                    "_duration_sum": 0.0,
                },
            )
            item["runs"] += 1
            item["failures"] += int(run["status"] != "success")
            item["_duration_sum"] += run["duration"]
            if run["created"] >= item["latest_created"]:
                item["latest_status"] = run["status"]
                item["latest_created"] = run["created"]

        for item in jobs.values():
            item["avg_duration"] = round(item.pop("_duration_sum") / item["runs"], 2)

        success_count = sum(1 for run in runs if run["status"] == "success")
        return {
            "total_runs": len(runs),
            "success_rate": round(success_count / len(runs), 4),
            "avg_duration": round(sum(durations) / len(durations), 2),
            "p95_duration": round(durations[p95_idx], 2),
            "active_alerts": len(alerts),
            "jobs": sorted(jobs.values(), key=lambda x: x["job"]),
        }

    def metrics(self) -> dict[str, float | int]:
        with self.connect() as conn:
            total_runs = conn.execute("select count(*) from runs").fetchone()[0]
            failed_runs = conn.execute("select count(*) from runs where status != 'success'").fetchone()[0]
            total_alerts = conn.execute("select count(*) from alerts").fetchone()[0]
            avg_duration = conn.execute("select coalesce(avg(duration), 0) from runs").fetchone()[0]
        return {
            "runs_total": int(total_runs),
            "runs_failed_total": int(failed_runs),
            "alerts_total": int(total_alerts),
            "run_duration_seconds_avg": round(float(avg_duration), 4),
        }


def evaluate_observation(
    store: Store,
    *,
    job: str,
    status: str,
    duration: float,
    rows_in: int,
    rows_out: int,
    null_rate: float,
    duplicate_rate: float,
    schema: dict[str, str],
    created: float | None = None,
) -> dict[str, Any]:
    historical_average = store.historical_average(job) or max(rows_out, 1)
    baseline_schema = store.latest_schema(job) or schema
    nulls = int(round(null_rate * max(rows_out, 0)))
    duplicates = int(round(duplicate_rate * max(rows_out, 0)))
    quality = check_quality(rows_in, rows_out, nulls, duplicates, historical_average)
    drift = detect_schema_drift(baseline_schema, schema)
    run = store.add_observation(
        job=job,
        status=status,
        duration=duration,
        rows_in=rows_in,
        rows_out=rows_out,
        null_rate=null_rate,
        duplicate_rate=duplicate_rate,
        schema=schema,
        created=created,
    )

    alert_messages: list[str] = []
    if status != "success":
        alert_messages.append("job execution failed")
        store.alert(job, "critical", "job execution failed", created)
    if duration > settings.slow_run_seconds:
        message = f"slow run: {duration:.1f}s exceeds {settings.slow_run_seconds:.1f}s"
        alert_messages.append(message)
        store.alert(job, "warning", message, created)
    if quality.breached:
        message = "quality breach: " + ", ".join(quality.breached)
        alert_messages.append(message)
        store.alert(job, "warning", message, created)
    if any(drift.values()):
        message = "schema drift: " + json.dumps(drift, sort_keys=True)
        alert_messages.append(message)
        store.alert(job, "warning", message, created)

    return {"run": run, "quality": asdict(quality), "schema_drift": drift, "alerts": alert_messages}


def simulate(store: Store, count: int = 24, seed: int = 7) -> None:
    rng = random.Random(seed)
    baseline = {"id": "int", "value": "float", "source": "string"}
    base_time = time.time() - max(count - 1, 0) * 300
    for i in range(count):
        job = ["orders_etl", "customer_dimensions", "events_rollup"][i % 3]
        status = "failed" if i % 13 == 0 else "success"
        rows_in = rng.randint(8000, 12000)
        rows_out = int(rows_in * rng.uniform(0.82, 0.99))
        null_rate = 0.13 if i % 9 == 0 else rng.uniform(0.005, 0.025)
        duplicate_rate = 0.07 if i % 11 == 0 else rng.uniform(0, 0.015)
        schema = baseline | ({"campaign": "string"} if i % 8 == 0 else {})
        duration = rng.uniform(30, 90) * (2.8 if i % 7 == 0 else 1)
        evaluate_observation(
            store,
            job=job,
            status=status,
            duration=duration,
            rows_in=rows_in,
            rows_out=rows_out,
            null_rate=null_rate,
            duplicate_rate=duplicate_rate,
            schema=schema,
            created=base_time + i * 300,
        )
