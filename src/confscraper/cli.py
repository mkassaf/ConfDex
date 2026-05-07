from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

from confscraper.llm import DEFAULT_MODEL
from confscraper.output import write_csv_papers, write_csv_summaries, write_json, write_ndjson, write_summaries
from confscraper.pipeline import scrape, scrape_conference

app = typer.Typer(
    name="confscraper",
    help="Scrape paper titles and abstracts from conference websites.",
    add_completion=False,
)
console = Console(stderr=True)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)],
    )


@app.command()
def main(
    track_urls: Annotated[
        Optional[list[str]],
        typer.Argument(help="One or more URLs to scrape (track, home, or program pages)."),
    ] = None,
    conference: Annotated[
        Optional[str],
        typer.Option("--conference", "-c", help="Conference slug for auto-discovery (e.g. icse-2026)."),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output file path. Defaults to stdout."),
    ] = None,
    ndjson: Annotated[
        bool,
        typer.Option("--ndjson", help="Emit one JSON object per line (no wrapper)."),
    ] = False,
    compact: Annotated[
        bool,
        typer.Option("--compact", help="Minify JSON output."),
    ] = False,
    concurrency: Annotated[
        int,
        typer.Option("--concurrency", help="Max concurrent requests."),
    ] = 5,
    rate: Annotated[
        float,
        typer.Option("--rate", help="Max requests per second."),
    ] = 5.0,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="HTTP timeout in seconds."),
    ] = 30.0,
    llm: Annotated[
        bool,
        typer.Option("--llm", help="Enable LLM fallback for abstract extraction when CSS selectors fail."),
    ] = False,
    model: Annotated[
        str,
        typer.Option(
            "--model",
            help=(
                "LLM model for --llm and --summarize. Any litellm-supported model string. "
                "Examples: claude-sonnet-4-6, gpt-4o, gemini/gemini-1.5-pro, ollama/llama3.2. "
                f"Env: LLM_MODEL. Default: {DEFAULT_MODEL}"
            ),
        ),
    ] = "",
    api_key: Annotated[
        Optional[str],
        typer.Option(
            "--api-key",
            help=(
                "LLM API key. Falls back to provider env vars automatically "
                "(ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.) or LITELLM_API_KEY. "
                "Not needed for local models (ollama/...)."
            ),
        ),
    ] = None,
    csv: Annotated[
        bool,
        typer.Option("--csv", help="Output as CSV instead of JSON."),
    ] = False,
    summarize: Annotated[
        bool,
        typer.Option(
            "--summarize",
            help="Summarize each abstract and extract keywords using an LLM. Output: title, summary, keywords.",
        ),
    ] = False,
    topic: Annotated[
        Optional[str],
        typer.Option(
            "--topic",
            help=(
                'Topic to score relevance against when --summarize is set. '
                'Each paper gets a 0-10 relevance score. '
                'Example: --topic "Green agentic AI"'
            ),
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug logging."),
    ] = False,
) -> None:
    _setup_logging(verbose)

    if not track_urls and not conference:
        console.print("[red]Error:[/red] provide at least one URL or --conference.")
        raise typer.Exit(code=1)

    if topic and not summarize:
        console.print("[yellow]Warning:[/yellow] --topic has no effect without --summarize.")

    resolved_model = model or os.environ.get("LLM_MODEL", DEFAULT_MODEL)

    if llm:
        console.print(f"LLM fallback enabled — model: [cyan]{resolved_model}[/cyan]")
    if summarize:
        label = f"Summarize + score (topic: [bold]{topic}[/bold])" if topic else "Summarize + keywords"
        console.print(f"{label} — model: [cyan]{resolved_model}[/cyan]")
        # Validate model up-front so a bad model name / missing key fails fast
        from confscraper.categorize import validate_model
        try:
            validate_model(resolved_model, api_key)
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1)

    # --- Scrape ---
    try:
        if conference:
            result = asyncio.run(
                scrape_conference(
                    conference,
                    concurrency=concurrency,
                    rate=rate,
                    timeout=timeout,
                    use_llm=llm,
                    llm_model=resolved_model,
                    llm_api_key=api_key,
                )
            )
        else:
            result = asyncio.run(
                scrape(
                    track_urls or [],
                    concurrency=concurrency,
                    rate=rate,
                    timeout=timeout,
                    use_llm=llm,
                    llm_model=resolved_model,
                    llm_api_key=api_key,
                )
            )
    except Exception as e:
        console.print(f"[red]Fatal error:[/red] {e}")
        raise typer.Exit(code=1)

    console.print(f"[green]Scraped {result.paper_count} papers.[/green]")

    # --- Categorize (optional) ---
    if summarize:
        from confscraper.categorize import categorize_papers

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            MofNCompleteColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Categorizing papers…", total=result.paper_count)

            async def _run_categorize():
                from confscraper.categorize import categorize_papers as _cat
                sem = asyncio.Semaphore(concurrency)
                results = []
                for paper in result.papers:
                    async with sem:
                        from confscraper.categorize import categorize_paper
                        r = await asyncio.to_thread(
                            categorize_paper, paper, resolved_model, api_key, topic
                        )
                        results.append(r)
                        progress.advance(task)
                return results

            summaries = asyncio.run(_run_categorize())

        if csv:
            write_csv_summaries(summaries, output)
        else:
            write_summaries(summaries, output, compact=compact)
        raise typer.Exit(code=0)

    # --- Normal output ---
    if csv:
        write_csv_papers(result, output)
    elif ndjson:
        write_ndjson(result.papers, output)
    else:
        write_json(result, output, compact=compact)

    if result.paper_count == 0:
        raise typer.Exit(code=1)
