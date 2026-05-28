"""Tests for runner.py — active-job tracking and duplicate guard."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from confscraper.web import runner
from confscraper.web import db as job_db


@pytest.fixture(autouse=True)
async def clean_state(tmp_path):
    """Fresh DB and empty active-jobs set for every test."""
    job_db.set_db_path(tmp_path / "test.db")
    await job_db.init_db()
    runner._active_jobs.clear()
    yield
    runner._active_jobs.clear()


# ── get_active_jobs ───────────────────────────────────────────────────────────

def test_active_jobs_starts_empty():
    assert runner.get_active_jobs() == set()


def test_active_jobs_is_same_object():
    assert runner.get_active_jobs() is runner._active_jobs


# ── duplicate guard ───────────────────────────────────────────────────────────

async def test_run_job_skips_if_already_active(tmp_path):
    job = await job_db.create_job(
        conference="icse-2026", track_urls=None, topic=None,
        model="claude-sonnet-4-6", api_key=None,
    )
    job_id = job["id"]

    # Simulate job already running
    runner._active_jobs.add(job_id)

    # run_job should return early without changing status
    await runner.run_job(job_id)

    fetched = await job_db.get_job(job_id)
    # Status should still be 'pending' — run_job exited before doing anything
    assert fetched["status"] == "pending"


async def test_active_jobs_cleaned_up_after_run(tmp_path):
    """_active_jobs must not leak after a job completes (even with error)."""
    job = await job_db.create_job(
        conference="icse-2026", track_urls=None, topic=None,
        model="claude-sonnet-4-6", api_key=None,
    )
    job_id = job["id"]

    # Mock scraping so no real network calls are made
    mock_result = MagicMock()
    mock_result.paper_count = 0
    mock_result.papers = []
    mock_result.model_dump.return_value = {}

    with patch("confscraper.web.runner.scrape_conference", new_callable=AsyncMock, return_value=mock_result):
        await runner.run_job(job_id)

    assert job_id not in runner._active_jobs


# ── list_incomplete_jobs integration ─────────────────────────────────────────

async def test_incomplete_jobs_excludes_active():
    """Watchdog should not re-queue jobs already in _active_jobs."""
    job = await job_db.create_job(
        conference="icse-2026", track_urls=None, topic=None,
        model="claude-sonnet-4-6", api_key=None,
    )
    await job_db.update_job(job["id"], status="scraping")
    runner._active_jobs.add(job["id"])

    active = runner.get_active_jobs()
    incomplete = await job_db.list_incomplete_jobs()
    stuck = [j for j in incomplete if j["id"] not in active]

    assert stuck == []  # not stuck — it's actively running
