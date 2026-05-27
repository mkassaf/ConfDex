from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    conference TEXT,
    track_urls TEXT,
    topic TEXT,
    model TEXT NOT NULL,
    api_key TEXT,
    use_llm_fallback INTEGER NOT NULL DEFAULT 0,
    phase TEXT,
    progress_current INTEGER NOT NULL DEFAULT 0,
    progress_total INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    scrape_result TEXT,
    summaries TEXT
)
"""

_DB_PATH: Path = Path("confdex.db")


def set_db_path(path: Path) -> None:
    global _DB_PATH
    _DB_PATH = path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: aiosqlite.Row) -> dict:
    d = dict(row)
    for field in ("track_urls", "scrape_result", "summaries"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    d["use_llm_fallback"] = bool(d.get("use_llm_fallback", 0))
    return d


async def init_db() -> None:
    async with aiosqlite.connect(_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(_CREATE_TABLE)
        await conn.commit()


async def create_job(
    conference: str | None,
    track_urls: list[str] | None,
    topic: str | None,
    model: str,
    api_key: str | None,
    use_llm_fallback: bool = False,
) -> dict:
    job_id = str(uuid.uuid4())
    now = _now()
    async with aiosqlite.connect(_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(
            """INSERT INTO jobs
               (id, created_at, updated_at, status, conference, track_urls,
                topic, model, api_key, use_llm_fallback)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                job_id, now, now, "pending",
                conference,
                json.dumps(track_urls) if track_urls else None,
                topic, model, api_key,
                1 if use_llm_fallback else 0,
            ),
        )
        await conn.commit()
        row = await conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        return _row_to_dict(await row.fetchone())


async def get_job(job_id: str) -> dict | None:
    async with aiosqlite.connect(_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        row = await conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        record = await row.fetchone()
        return _row_to_dict(record) if record else None


async def list_jobs() -> list[dict]:
    async with aiosqlite.connect(_DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        rows = await conn.execute(
            "SELECT id, created_at, updated_at, status, conference, topic, model, "
            "phase, progress_current, progress_total, error "
            "FROM jobs ORDER BY created_at DESC"
        )
        return [dict(r) for r in await rows.fetchall()]


async def update_job(job_id: str, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    # Serialize complex fields
    for field in ("track_urls", "scrape_result", "summaries"):
        if field in fields and not isinstance(fields[field], str):
            fields[field] = json.dumps(fields[field])
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [job_id]
    async with aiosqlite.connect(_DB_PATH) as conn:
        await conn.execute(f"UPDATE jobs SET {set_clause} WHERE id=?", values)
        await conn.commit()


async def delete_job(job_id: str) -> bool:
    async with aiosqlite.connect(_DB_PATH) as conn:
        cur = await conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        await conn.commit()
        return cur.rowcount > 0
