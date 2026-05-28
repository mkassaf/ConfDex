from __future__ import annotations

import asyncio
import csv
import io
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from confscraper.web import db as job_db
from confscraper.web.runner import run_job

_DEFAULT_JOB_LIMIT = 20


def _job_limit() -> int:
    return max(1, int(os.environ.get("MAX_JOB_HISTORY_LIMIT", _DEFAULT_JOB_LIMIT)))

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    conference: Optional[str] = None
    track_urls: Optional[list[str]] = None
    topic: Optional[str] = None
    model: str
    api_key: Optional[str] = None
    use_llm_fallback: bool = False


@router.post("", status_code=201)
async def create_job(body: CreateJobRequest, background_tasks: BackgroundTasks):
    if not body.conference and not body.track_urls:
        raise HTTPException(status_code=400, detail="Provide conference slug or track_urls.")

    job = await job_db.create_job(
        conference=body.conference,
        track_urls=body.track_urls,
        topic=body.topic,
        model=body.model,
        api_key=body.api_key,
        use_llm_fallback=body.use_llm_fallback,
    )
    await job_db.prune_old_jobs(_job_limit())
    background_tasks.add_task(run_job, job["id"])
    return job


@router.get("")
async def list_jobs():
    return await job_db.list_jobs()


@router.get("/{job_id}")
async def get_job(job_id: str):
    job = await job_db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str):
    deleted = await job_db.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")


@router.get("/{job_id}/stream")
async def stream_job(job_id: str, request: Request):
    """SSE stream that emits job progress until status is done or error."""

    async def _event_generator():
        while True:
            if await request.is_disconnected():
                break

            job = await job_db.get_job(job_id)
            if not job:
                yield f"data: {json.dumps({'event': 'error', 'detail': 'job not found'})}\n\n"
                break

            payload = {
                "status": job["status"],
                "phase": job.get("phase"),
                "progress_current": job.get("progress_current", 0),
                "progress_total": job.get("progress_total", 0),
                "error": job.get("error"),
            }
            yield f"data: {json.dumps(payload)}\n\n"

            if job["status"] in ("done", "error"):
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(_event_generator(), media_type="text/event-stream")


@router.get("/{job_id}/download")
async def download_job(job_id: str, format: str = "json"):
    job = await job_db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done":
        raise HTTPException(status_code=409, detail="Job not finished yet")

    summaries: list[dict] = job.get("summaries") or []

    if format == "csv":
        out = io.StringIO()
        fields = ["title", "source_url", "doi", "summary", "keywords", "methodology",
                  "domain", "score", "score_reasoning", "score_matching"]
        writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in summaries:
            flat = {
                k: ("; ".join(v) if isinstance(v, list) else ("" if v is None else v))
                for k, v in row.items()
            }
            writer.writerow(flat)
        content = out.getvalue()
        filename = f"confdex-{job_id[:8]}.csv"
        return StreamingResponse(
            iter([content]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Default: JSON
    content = json.dumps(summaries, indent=2, ensure_ascii=False)
    filename = f"confdex-{job_id[:8]}.json"
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
