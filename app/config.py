import os
from dataclasses import dataclass


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    database_path: str = os.getenv("DATABASE_PATH", "data/metrics.db")
    null_rate_threshold: float = _float("NULL_RATE_THRESHOLD", 0.08)
    duplicate_rate_threshold: float = _float("DUPLICATE_RATE_THRESHOLD", 0.04)
    row_delta_threshold: float = _float("ROW_DELTA_THRESHOLD", 0.35)
    slow_run_seconds: float = _float("SLOW_RUN_SECONDS", 120.0)
    ingestion_api_key: str = os.getenv("INGESTION_API_KEY", "")


settings = Settings()
