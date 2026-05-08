from datetime import datetime
from typing import Any

import pymysql
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.amp_fetch_stories import fetch_batch, normalize_rows
from app.models import SourceConfig


def _source_cfg(db: Session) -> SourceConfig:
    cfg = db.scalar(select(SourceConfig).limit(1))
    if cfg is None:
        raise RuntimeError("Source config is missing. Please configure AMP source first.")
    return cfg


def fetch_amp_records(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    batch_size: int = 200,
    max_rows: int = 1000,
) -> list[dict[str, Any]]:
    cfg = _source_cfg(db)
    conn = pymysql.connect(
        host=cfg.amp_host,
        port=cfg.amp_port,
        user=cfg.amp_user,
        password=cfg.amp_password,
        database=cfg.amp_database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=8,
        read_timeout=20,
        write_timeout=20,
    )
    rows_all: list[dict[str, Any]] = []
    cursor_create_time: str | None = None
    cursor_story_id: int | None = None
    try:
        while True:
            rows = fetch_batch(
                conn=conn,
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                cursor_create_time=cursor_create_time,
                cursor_story_id=cursor_story_id,
                batch_size=batch_size,
            )
            if not rows:
                break
            rows_all.extend(rows)
            last = rows[-1]
            dt = last.get("create_time")
            cursor_create_time = (
                dt.strftime("%Y-%m-%d %H:%M:%S") if hasattr(dt, "strftime") else str(dt)
            )
            cursor_story_id = int(last["story_id"])
            if len(rows_all) >= max_rows:
                break
    finally:
        conn.close()
    return normalize_rows(rows_all[:max_rows])

