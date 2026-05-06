# Conference Paper Scraper — Implementation Plan

## 1. Goal

A **pip-installable CLI tool** that scrapes paper titles, authors, and abstracts from conference websites — primarily `conf.researchr.org` — and outputs **a single JSON file** with the results.

Locked-in constraints:
- **Distribution**: Python package, installable via `pip install` (locally, from GitHub, or PyPI).
- **Interface**: CLI command, runnable on Windows / macOS / Linux from any terminal.
- **Output**: JSON file (default) or stdout. JSON is the deliverable.
- **Use case**: pre-publication conference programs where DBLP / arXiv don't yet have the papers.

## 2. Distribution shape

```
pip install conf-scraper                                       # later, after PyPI publish
pip install git+https://github.com/mkassaf/conf-scraper.git    # works from day one
pip install -e .                                               # local development
```

After install, the user types:

```bash
confscraper https://conf.researchr.org/track/icse-2026/icse-2026-research-track \
            -o icse-2026-research.json
```

That's the whole UX. Cross-platform because it's pure Python; no PyInstaller, no platform-specific binaries to maintain.

## 3. Project layout

```
conf-scraper/
├── pyproject.toml              # build config + [project.scripts] entry point
├── README.md
├── src/
│   └── confscraper/
│       ├── __init__.py
│       ├── __main__.py         # `python -m confscraper`
│       ├── cli.py              # typer entry point — registered as `confscraper`
│       ├── models.py           # pydantic: Paper, Author, ScrapeResult
│       ├── http.py             # httpx async client + retry/limit
│       ├── pipeline.py         # orchestrator
│       ├── output.py           # JSON writer
│       └── adapters/
│           ├── __init__.py
│           ├── base.py         # Adapter ABC
│           └── researchr.py    # FIRST DELIVERABLE
└── tests/
    ├── fixtures/               # saved HTML snapshots
    └── test_researchr.py
```

`pyproject.toml` registers the CLI:

```toml
[project.scripts]
confscraper = "confscraper.cli:app"
```

## 4. JSON output schema

Single JSON file, UTF-8, pretty-printed by default (flag to disable):

```json
{
  "schema_version": "1.0",
  "conference": "icse-2026",
  "source_urls": [
    "https://conf.researchr.org/track/icse-2026/icse-2026-research-track"
  ],
  "scraped_at": "2026-05-06T14:32:11Z",
  "paper_count": 142,
  "papers": [
    {
      "source_url": "https://conf.researchr.org/details/icse-2026/icse-2026-research-track/...",
      "paper_id": "28",
      "track": "icse-2026-research-track",
      "track_label": "Research Track",
      "title": "Find My Code Twin: Improving SNIPPET SEARCH ...",
      "authors": [
        {
          "name": "Seokjun Ko",
          "affiliation": "Samsung Electronics Co.",
          "profile_url": "https://conf.researchr.org/profile/icse-2026/seokjunko"
        }
      ],
      "abstract": "We present SNIPPET SEARCH, a high-performance ...",
      "doi": "https://doi.org/10.1145/3786583.3786881",
      "preprint_url": null,
      "session": "AI for Software Engineering 1",
      "room": "Asia I",
      "scheduled_at": "2026-04-15T11:45:00-03:00",
      "tags": ["Virtual Attendance"]
    }
  ]
}
```

Design notes:
- Top-level wrapper carries scrape metadata (when, where, how many) — useful for downstream pipelines.
- `papers` is a flat array. If multiple tracks scraped at once, papers from all tracks share the array; the `track` field disambiguates.
- Missing fields are `null`, not omitted — keeps consumers simple.
- `--ndjson` flag emits one paper per line (no wrapper) for streaming consumers.

## 5. CLI surface

```bash
# Single track, output to file
confscraper TRACK_URL -o papers.json

# Multiple tracks merged into one JSON
confscraper URL1 URL2 URL3 -o icse-2026.json

# Auto-discover all tracks for a conference (researchr only)
confscraper --conference icse-2026 -o icse-2026.json

# Stream to stdout (pipe-friendly)
confscraper TRACK_URL | jq '.papers[] | .title'

# NDJSON output for incremental processing
confscraper TRACK_URL --ndjson -o papers.ndjson

# Tuning
confscraper TRACK_URL --concurrency 3 --rate 2 --timeout 30 -o out.json

# Cache to skip re-fetching unchanged pages on re-run
confscraper TRACK_URL --cache .confscraper-cache.db -o out.json
```

Defaults: concurrency 5, rate 5 req/s, timeout 30 s, no cache, pretty JSON.

## 6. Data model

```python
class Author(BaseModel):
    name: str
    affiliation: str | None = None
    profile_url: str | None = None

class Paper(BaseModel):
    source_url: str
    paper_id: str
    track: str
    track_label: str
    title: str
    authors: list[Author] = []
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
```

`ScrapeResult.model_dump_json(indent=2)` gives the output file directly.

## 7. Researchr adapter spec

### 7.1 URL patterns (verified)

| Page | Pattern |
|---|---|
| Track | `/track/{conf}/{track-slug}` |
| Paper detail | `/details/{conf}/{track-slug}/{numeric-id}/{title-slug}` |
| Author | `/profile/{conf}/{handle}` |

### 7.2 Stage 1 — list paper detail URLs from a track page

1. Fetch track page (one HTTP GET).
2. Parse with `selectolax`.
3. Collect all `a[href*='/details/']` hrefs, normalize to absolute, dedupe.
4. Return list.

### 7.3 Stage 2 — parse a paper detail page

| Field | Selector / strategy | Fallback |
|---|---|---|
| `title` | First `<h2>` after breadcrumb | `<title>` minus suffix |
| `abstract` | `<h3>Abstract</h3>` → following `<p>` siblings until next `<h3>` | `<strong>Abstract</strong>` variant |
| `authors` | Anchors under `Who` block | None — array stays empty |
| `doi` | `a[href*='doi.org']` | None |
| `preprint_url` | `a[text='Pre-print']` or `href*='arxiv.org'` | None |
| `session`, `room`, `scheduled_at` | Parsed from `When` block | None |
| `tags` | Inline labels: `Distinguished Paper Award`, `Virtual Attendance` | Empty list |
| `paper_id` | Numeric segment of URL | Always present |

Defensive: each field in its own `try/except`, missing → `None` + WARNING log. Pipeline never crashes on a single bad page.

## 8. Tech stack (final, pinned)

| Component | Library | Why |
|---|---|---|
| HTTP | `httpx[http2]` | Async, HTTP/2, connection pooling |
| HTML parsing | `selectolax` | ~10× faster than BeautifulSoup |
| Rate limiting | `aiolimiter` | Async token bucket |
| Retries | `tenacity` | Decorator API |
| Models | `pydantic >= 2` | JSON serialization built in |
| CLI | `typer` | Type-hint-driven, minimal boilerplate |
| Logging | `rich` | Pretty console output |
| Cache (optional) | stdlib `sqlite3` | Zero deps |
| Tests | `pytest` + saved HTML | Offline, deterministic |

`pyproject.toml` declares Python ≥ 3.11.

## 9. Robustness defaults

- **Concurrency**: 5 in flight, configurable.
- **Rate**: 5 req/s.
- **Retries**: 3 tries, exponential backoff (1 s, 2 s, 4 s); only retry on 5xx + `httpx.TransportError`. Never retry 4xx.
- **`User-Agent`**: `confscraper/{version} (+github.com/mkassaf/conf-scraper)`.
- **Honor `Retry-After`** when present.
- **Timeout**: 30 s connect/read.
- **Per-paper failures don't abort**: collect successes, summarize failures at end of run with non-zero exit code if any fields were unrecoverable.

## 10. Implementation phases

| Phase | Scope | Effort |
|---|---|---|
| **P1 — Walking skeleton** | Sync, single track, prints JSON to stdout. End-to-end against ICSE 2026 Research Track. | half day |
| **P2 — Async + rate limit + retry** | Convert to `httpx.AsyncClient`, `aiolimiter`, `tenacity`. | half day |
| **P3 — Multi-track + dedupe + `-o` flag** | Accept N URLs, merge, dedupe by `paper_id`, write to file. | half day |
| **P4 — Conference auto-discovery** | `--conference icse-2026` lists all tracks from the home page and scrapes them all. | half day |
| **P5 — Packaging** | `pyproject.toml`, entry point, `pip install -e .` works. README with usage. | half day |
| **P6 — Tests + CI** | Pytest against saved HTML fixtures. GitHub Actions runs on push. | half day |
| **P7 — Optional cache** | sqlite HTTP cache with conditional GET (`If-None-Match`). | half day |

Total to a usable, installable tool: **P1–P5, ~2.5 days**. P6 and P7 are quality polish.

## 11. Edge cases

- **No abstract yet** (workshop in early planning): emit `abstract: null`, log INFO, continue.
- **Joint sessions** (same paper in two tracks): dedupe by `paper_id`, keep first occurrence, log a note.
- **Multi-paragraph abstracts**: preserve paragraph breaks as `\n\n` in the JSON string.
- **Withdrawn / cancelled papers**: detail page exists, no abstract; flag with `tags: ["Withdrawn"]`.
- **HTML entities + Unicode**: `selectolax` decodes; verify with author names containing accents and Chinese characters.
- **Renamed title slugs across re-runs**: key on `(track, paper_id)` only — slug is cosmetic.
- **Site temporarily 5xx**: retries handle transient failures; if a page exhausts retries, exclude from output and report in stderr summary. Exit code 0 if ≥80% success, else 1.
- **Researchr platform updates**: pin a smoke test that fetches one known paper and asserts non-empty abstract — early warning when the template changes.

## 12. Repo bootstrap checklist

- [ ] `mkdir conf-scraper && cd conf-scraper && uv init` (or `python -m venv` + `pip`)
- [ ] Create directory structure from §3
- [ ] Write `pyproject.toml` with deps from §8 and `[project.scripts]` entry
- [ ] Stub `Adapter` ABC: `discover_papers(track_url) -> list[str]`, `parse_paper(url, html) -> Paper`
- [ ] Implement `researchr.py` against §7
- [ ] Save 4 HTML fixtures: Research Track paper, SEIP paper, workshop paper, paper with no abstract
- [ ] Write parsing tests against fixtures (P6 can come last but stubbing test files now is cheap)
- [ ] Build `cli.py` with `typer`
- [ ] `pip install -e .` and verify `confscraper --help` works
- [ ] Run end-to-end against ICSE 2026 Research Track, eyeball the JSON
- [ ] Push to GitHub; tag v0.1.0

## 13. Future extensions (not blocking)

- `--filter-keywords agentic,energy` to mark papers relevant to a thesis topic.
- Cross-source enrichment: post-scrape, look up each paper on arXiv by title + first author, attach `arxiv_id` if found.
- Diff mode: compare two scrape JSONs of the same conference, surface added/changed papers.
- Additional adapters: `openreview` (uses official API, no scraping), `easychair`.
- Wire into the existing n8n / Claude Desktop digest pipeline so scraping triggers a digest email automatically.
