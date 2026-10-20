from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    path = ROOT / ".env"
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


@dataclass(frozen=True)
class Settings:
    raw_dir: Path
    silver_dir: Path
    quarantine_dir: Path
    outputs_dir: Path
    pg_dsn: str
    kafka_bootstrap: str
    kafka_topic: str
    kafka_dlq_topic: str
    kafka_group: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str


@lru_cache
def settings() -> Settings:
    file_env = _env_file()

    def get(key: str, default: str) -> str:
        return os.getenv(key, file_env.get(key, default))

    return Settings(
        raw_dir=ROOT / get("RAW_DIR", "data/raw"),
        silver_dir=ROOT / "data/silver",
        quarantine_dir=ROOT / "data/quarantine",
        outputs_dir=ROOT / "outputs",
        pg_dsn=(f"host=localhost port={get('POSTGRES_PORT', '5432')} "
                f"dbname={get('POSTGRES_DB', 'olist')} user={get('POSTGRES_USER', 'olist')} "
                f"password={get('POSTGRES_PASSWORD', 'olist_dev_only')}"),
        kafka_bootstrap=get("KAFKA_BOOTSTRAP", f"localhost:{get('KAFKA_HOST_PORT', '29092')}"),
        kafka_topic=get("KAFKA_TOPIC", "olist.order_events"),
        kafka_dlq_topic=get("KAFKA_DLQ_TOPIC", "olist.order_events.dlq"),
        kafka_group=get("KAFKA_GROUP", "olist-order-consumer"),
        minio_endpoint=get("MINIO_ENDPOINT", f"http://localhost:{get('MINIO_API_PORT', '9000')}"),
        minio_access_key=get("MINIO_ROOT_USER", "minio"),
        minio_secret_key=get("MINIO_ROOT_PASSWORD", "minio_dev_only"),
    )
