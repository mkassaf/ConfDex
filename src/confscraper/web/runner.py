from __future__ import annotations

import asyncio
import logging
import traceback

from confscraper.pipeline import scrape, scrape_conference
from confscraper.web import db as job_db

JOB_TIMEOUT = 3600  # 1 hour hard limit per job

logger = logging.getLogger(__name__)

_active_jobs: set[str] = set()


def get_active_jobs() -> set[str]:
    return _active_jobs


async def run_job(job_id: str) -> None:
    """Execute a scraping + summarization job, writing progress to SQLite."""
    if job_id in _active_jobs:
        logger.warning("Job %s already running — skipping duplicate trigger", job_id)
        return
    _active_jobs.add(job_id)
    try:
        await job_db.update_job(job_id, status="scraping", phase="Discovering papers…", error=None)
        await asyncio.wait_for(_run_job_inner(job_id), timeout=JOB_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error("Job %s exceeded %ds timeout", job_id, JOB_TIMEOUT)
        await job_db.update_job(
            job_id, status="error",
            error=f"Job timed out after {JOB_TIMEOUT // 60} minutes.",
            phase="Timed out",
        )
    finally:
        _active_jobs.discard(job_id)


async def _run_job_inner(job_id: str) -> None:
    job = await job_db.get_job(job_id)
    if not job:
        logger.error("Job %s not found", job_id)
        return

    model = job["model"]
    api_key = job["api_key"]
    topic = job["topic"]
    conference = job.get("conference")
    track_urls: list[str] = job.get("track_urls") or []
    use_llm_fallback = bool(job.get("use_llm_fallback", False))

    await job_db.update_job(job_id, status="scraping", phase="Discovering papers…")

    try:
        # ── Scrape ──────────────────────────────────────────────────────────
        if conference:
            result = await scrape_conference(
                conference,
                use_llm=use_llm_fallback,
                llm_model=model,
                llm_api_key=api_key,
            )
        else:
            result = await scrape(
                track_urls,
                use_llm=use_llm_fallback,
                llm_model=model,
                llm_api_key=api_key,
            )

        await job_db.update_job(
            job_id,
            phase=f"Scraped {result.paper_count} papers",
            progress_current=0,
            progress_total=result.paper_count,
            scrape_result=result.model_dump(mode="json"),
        )

        # ── Summarize ────────────────────────────────────────────────────────
        await job_db.update_job(job_id, status="summarizing", phase="Summarizing papers…")

        papers = result.papers
        total = len(papers)
        done = 0

        from confscraper.categorize import categorize_paper_v2

        summaries: list[dict] = []
        sem = asyncio.Semaphore(3)

        async def _one(paper):
            nonlocal done
            async with sem:
                r = await asyncio.to_thread(
                    categorize_paper_v2, paper, model, api_key, topic
                )
                done += 1
                await job_db.update_job(
                    job_id,
                    phase=f"Summarized {done}/{total}",
                    progress_current=done,
                    progress_total=total,
                )
                return r

        summaries = list(await asyncio.gather(*(_one(p) for p in papers)))

        await job_db.update_job(
            job_id,
            status="done",
            phase="Complete",
            progress_current=total,
            progress_total=total,
            summaries=summaries,
            error=None,
        )

    except Exception:
        err = traceback.format_exc()
        logger.error("Job %s failed:\n%s", job_id, err)
        await job_db.update_job(job_id, status="error", error=err, phase="Failed")
