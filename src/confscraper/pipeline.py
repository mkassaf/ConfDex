from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

from confscraper.adapters.researchr import ResearchrAdapter
from confscraper.http import RateLimitedClient
from confscraper.models import Paper, ScrapeResult

logger = logging.getLogger(__name__)
console = Console(stderr=True)


async def scrape(
    urls: list[str],
    conference: str | None = None,
    concurrency: int = 5,
    rate: float = 5.0,
    timeout: float = 30.0,
    use_llm: bool = False,
    llm_model: str = "claude-sonnet-4-6",
    llm_api_key: str | None = None,
) -> ScrapeResult:
    async with RateLimitedClient(concurrency=concurrency, rate=rate, timeout=timeout) as client:
        adapter = ResearchrAdapter(client, use_llm=use_llm, llm_model=llm_model, llm_api_key=llm_api_key)

        detail_urls: list[str] = []
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Discovering papers…", total=len(urls))
            for track_url in urls:
                try:
                    paper_urls = await adapter.discover_papers(track_url)
                    detail_urls.extend(paper_urls)
                except Exception as e:
                    logger.error("Failed to discover papers from %s: %s", track_url, e)
                progress.advance(task)

        # Deduplicate by paper_id (keep first occurrence)
        seen_ids: set[str] = set()
        unique_urls: list[str] = []
        for paper_url in detail_urls:
            m = re.search(r"/details/[^/]+/[^/]+/(\d+)", paper_url)
            pid = m.group(1) if m else paper_url
            if pid not in seen_ids:
                seen_ids.add(pid)
                unique_urls.append(paper_url)

        logger.info("Fetching %d unique papers…", len(unique_urls))

        papers: list[Paper] = []
        failures: list[str] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching papers…", total=len(unique_urls))
            sem = asyncio.Semaphore(concurrency)

            async def fetch_one(paper_url: str) -> Paper | None:
                async with sem:
                    try:
                        resp = await client.get(paper_url)
                        return adapter.parse_paper(paper_url, resp.text)
                    except Exception as e:
                        logger.warning("Failed to fetch %s: %s", paper_url, e)
                        failures.append(paper_url)
                        return None
                    finally:
                        progress.advance(task)

            results = await asyncio.gather(*(fetch_one(u) for u in unique_urls))

        for r in results:
            if r is not None:
                papers.append(r)

        if failures:
            console.print(f"[yellow]Warning:[/yellow] {len(failures)} papers failed to fetch:")
            for f in failures:
                console.print(f"  [dim]{f}[/dim]")

        return ScrapeResult(
            conference=conference,
            source_urls=urls,
            scraped_at=datetime.now(timezone.utc),
            paper_count=len(papers),
            papers=papers,
        )


async def scrape_conference(
    conference_slug: str,
    concurrency: int = 5,
    rate: float = 5.0,
    timeout: float = 30.0,
    use_llm: bool = False,
    llm_model: str = "claude-sonnet-4-6",
    llm_api_key: str | None = None,
) -> ScrapeResult:
    async with RateLimitedClient(concurrency=concurrency, rate=rate, timeout=timeout) as client:
        adapter = ResearchrAdapter(client, use_llm=use_llm, llm_model=llm_model, llm_api_key=llm_api_key)
        track_urls = await adapter.discover_tracks(conference_slug)

    if not track_urls:
        raise ValueError(f"No tracks found for conference '{conference_slug}'")

    console.print(f"Found [bold]{len(track_urls)}[/bold] tracks for [cyan]{conference_slug}[/cyan]")
    return await scrape(
        track_urls,
        conference=conference_slug,
        concurrency=concurrency,
        rate=rate,
        timeout=timeout,
        use_llm=use_llm,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
    )
