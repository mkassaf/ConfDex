from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Paper(BaseModel):
    source_url: str
    paper_id: str
    track: str
    track_label: str
    title: str
    abstract: str | None = None
    doi: str | None = None
    preprint_url: str | None = None
    session: str | None = None
    room: str | None = None
    scheduled_at: datetime | None = None
    tags: list[str] = []


class ScrapeResult(BaseModel):
    schema_version: str = "1.0"
    conference: str | None = None
    source_urls: list[str]
    scraped_at: datetime
    paper_count: int
    papers: list[Paper]
