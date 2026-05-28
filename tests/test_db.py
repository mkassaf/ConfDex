"""Tests for the SQLite job store (db.py)."""
from __future__ import annotations

import pytest

from confscraper.web import db as job_db


@pytest.fixture(autouse=True)
async def fresh_db(tmp_path):
    job_db.set_db_path(tmp_path / "test.db")
    await job_db.init_db()


# ── helpers ──────────────────────────────────────────────────────────────────

async def _make(status: str = "pending", **kw) -> dict:
    job = await job_db.create_job(
        conference=kw.get("conference", "icse-2026"),
        track_urls=None,
        topic=kw.get("topic"),
        model=kw.get("model", "claude-sonnet-4-6"),
        api_key=None,
    )
    if status != "pending":
        await job_db.update_job(job["id"], status=status)
        job = await job_db.get_job(job["id"])
    return job


# ── create / get ─────────────────────────────────────────────────────────────

async def test_create_job_returns_dict():
    job = await _make()
    assert isinstance(job, dict)
    assert job["id"]
    assert job["status"] == "pending"
    assert job["conference"] == "icse-2026"


async def test_get_job_roundtrip():
    job = await _make()
    fetched = await job_db.get_job(job["id"])
    assert fetched is not None
    assert fetched["id"] == job["id"]


async def test_get_nonexistent_returns_none():
    result = await job_db.get_job("00000000-0000-0000-0000-000000000000")
    assert result is None


# ── update ────────────────────────────────────────────────────────────────────

async def test_update_status():
    job = await _make()
    await job_db.update_job(job["id"], status="scraping", phase="Discovering papers…")
    updated = await job_db.get_job(job["id"])
    assert updated["status"] == "scraping"
    assert updated["phase"] == "Discovering papers…"


async def test_update_progress():
    job = await _make()
    await job_db.update_job(job["id"], progress_current=5, progress_total=20)
    updated = await job_db.get_job(job["id"])
    assert updated["progress_current"] == 5
    assert updated["progress_total"] == 20


# ── delete ────────────────────────────────────────────────────────────────────

async def test_delete_job_returns_true():
    job = await _make()
    result = await job_db.delete_job(job["id"])
    assert result is True
    assert await job_db.get_job(job["id"]) is None


async def test_delete_nonexistent_returns_false():
    result = await job_db.delete_job("00000000-0000-0000-0000-000000000000")
    assert result is False


# ── list_incomplete_jobs ──────────────────────────────────────────────────────

async def test_list_incomplete_jobs_returns_running_only():
    pending = await _make("pending")
    scraping = await _make("scraping")
    summarizing = await _make("summarizing")
    done = await _make("done")
    error = await _make("error")

    incomplete = await job_db.list_incomplete_jobs()
    ids = {j["id"] for j in incomplete}

    assert pending["id"] in ids
    assert scraping["id"] in ids
    assert summarizing["id"] in ids
    assert done["id"] not in ids
    assert error["id"] not in ids


async def test_list_incomplete_jobs_empty():
    await _make("done")
    assert await job_db.list_incomplete_jobs() == []


# ── prune_old_jobs ────────────────────────────────────────────────────────────

async def test_prune_removes_oldest_when_over_limit():
    for _ in range(5):
        await _make("done")

    deleted = await job_db.prune_old_jobs(limit=3)
    assert deleted == 2

    jobs = await job_db.list_jobs()
    assert len(jobs) == 3


async def test_prune_under_limit_deletes_nothing():
    await _make("done")
    await _make("done")
    deleted = await job_db.prune_old_jobs(limit=5)
    assert deleted == 0


async def test_prune_never_deletes_running_jobs():
    await _make("scraping")
    await _make("scraping")
    await _make("done")

    # limit=1 but 2 jobs are running — can only free the done one
    deleted = await job_db.prune_old_jobs(limit=1)
    assert deleted == 1

    incomplete = await job_db.list_incomplete_jobs()
    assert len(incomplete) == 2


async def test_prune_error_jobs_are_prunable():
    await _make("error")
    await _make("error")
    deleted = await job_db.prune_old_jobs(limit=1)
    assert deleted == 1
