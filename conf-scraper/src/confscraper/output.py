from __future__ import annotations

import json
import sys
from pathlib import Path

from confscraper.models import Paper, ScrapeResult


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
