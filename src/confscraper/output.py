from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

from confscraper.models import Paper, ScrapeResult

# Columns for full scrape output
_PAPER_FIELDS = [
    "title", "abstract", "track", "track_label", "session", "room",
    "scheduled_at", "doi", "preprint_url", "tags", "paper_id", "source_url",
]

# Columns for --summarize output
_SUMMARY_FIELDS = ["title", "source_url", "doi", "summary", "keywords", "score"]


def _write_csv(rows: list[dict], fieldnames: list[str], path: Path | None) -> None:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        # Flatten list fields to semicolon-separated strings
        flat = {
            k: "; ".join(v) if isinstance(v, list) else ("" if v is None else v)
            for k, v in row.items()
        }
        writer.writerow(flat)
    content = out.getvalue()
    if path is None:
        sys.stdout.write(content)
    else:
        path.write_text(content, encoding="utf-8")


def write_csv_papers(result: ScrapeResult, path: Path | None) -> None:
    rows = [p.model_dump() for p in result.papers]
    _write_csv(rows, _PAPER_FIELDS, path)


def write_csv_summaries(summaries: list[dict], path: Path | None) -> None:
    _write_csv(summaries, _SUMMARY_FIELDS, path)


def write_summaries(summaries: list[dict], path: Path | None, compact: bool = False) -> None:
    indent = None if compact else 2
    text = json.dumps(summaries, indent=indent, ensure_ascii=False)
    if path is None:
        sys.stdout.write(text)
        sys.stdout.write("\n")
    else:
        path.write_text(text, encoding="utf-8")


def write_json(result: ScrapeResult, path: Path | None, compact: bool = False) -> None:
    indent = None if compact else 2
    text = result.model_dump_json(indent=indent)
    if path is None:
        sys.stdout.write(text)
        sys.stdout.write("\n")
    else:
        path.write_text(text, encoding="utf-8")


def write_ndjson(papers: list[Paper], path: Path | None) -> None:
    lines = [p.model_dump_json() for p in papers]
    content = "\n".join(lines) + "\n"
    if path is None:
        sys.stdout.write(content)
    else:
        path.write_text(content, encoding="utf-8")
