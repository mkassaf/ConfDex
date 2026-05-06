# conf-scraper

Scrapes paper titles and abstracts from conference websites (primarily `conf.researchr.org`) and outputs a single JSON file.

Works with any `conf.researchr.org` URL — track pages, workshop home pages, and program pages. JavaScript-rendered pages (where papers load on click) are handled automatically using a headless browser. An optional LLM fallback extracts abstracts when CSS selectors fail, supporting Claude, OpenAI, Gemini, Ollama, and any other litellm-compatible provider.

## Installation

**Requires Python 3.11+**

```bash
# From source
git clone https://github.com/mkassaf/conf-scraper.git
cd conf-scraper
pip install -e .

# Directly from GitHub
pip install git+https://github.com/mkassaf/conf-scraper.git
```

After install, verify it works:

```bash
confscraper --help
```

> **macOS note:** if `confscraper` is not found, add the user bin to your PATH:
> ```bash
> export PATH="$HOME/Library/Python/3.11/bin:$PATH"
> ```
> Add that line to `~/.zshrc` or `~/.bashrc` to make it permanent.

---

## Usage

### Scrape a single track page

```bash
confscraper https://conf.researchr.org/track/icse-2026/icse-2026-research-track \
            -o icse-2026-research.json
```

### Scrape multiple tracks into one file

```bash
confscraper \
  https://conf.researchr.org/track/icse-2026/icse-2026-research-track \
  https://conf.researchr.org/track/icse-2026/icse-2026-seip-track \
  -o icse-2026.json
```

### Auto-discover all tracks for a conference

```bash
confscraper --conference icse-2026 -o icse-2026.json
```

### Workshop / home pages (JavaScript-rendered)

Workshop and program pages load their paper lists via JavaScript. The scraper detects these URLs automatically and launches a headless browser to click through and collect all paper links — no extra flags needed:

```bash
confscraper https://conf.researchr.org/home/icse-2026/greens-2026 -o greens-2026.json
```

### Extract abstracts only

```bash
confscraper https://conf.researchr.org/track/icse-2026/icse-2026-research-track \
  | jq '.papers[] | {title, abstract}'
```

### NDJSON output (one paper per line, no wrapper)

```bash
confscraper https://conf.researchr.org/track/icse-2026/icse-2026-research-track \
            --ndjson -o papers.ndjson
```

---

## LLM-assisted extraction

Pass `--llm` to enable an LLM fallback for pages where the abstract cannot be found by CSS selectors. Supports any [litellm-compatible](https://docs.litellm.ai/docs/providers) provider.

### API key resolution (automatic)

You do not need to pass a key explicitly. The scraper checks in this order:

1. `--api-key` CLI flag
2. Provider env var auto-detected from the model name (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`, …)
3. `LITELLM_API_KEY` generic fallback
4. No key — for local models like Ollama

### Claude (default)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
confscraper URL --llm -o papers.json
```

```bash
# Or pass the key inline
confscraper URL --llm --api-key sk-ant-... -o papers.json
```

### OpenAI

```bash
export OPENAI_API_KEY=sk-...
confscraper URL --llm --model gpt-4o -o papers.json
```

### Gemini

```bash
export GEMINI_API_KEY=...
confscraper URL --llm --model gemini/gemini-1.5-pro -o papers.json
```

### Ollama (local, no key needed)

```bash
# Make sure Ollama is running: ollama serve
confscraper URL --llm --model ollama/llama3.2 -o papers.json
```

### Set the model globally via env var

```bash
export LLM_MODEL=ollama/llama3.2
confscraper URL --llm -o papers.json
```

---

## All options

| Flag | Default | Description |
|---|---|---|
| `-o / --output` | stdout | Output file path |
| `-c / --conference` | — | Conference slug for auto-discovery (e.g. `icse-2026`) |
| `--ndjson` | off | One JSON object per line, no wrapper object |
| `--compact` | off | Minify JSON output |
| `--concurrency` | 5 | Max concurrent HTTP requests |
| `--rate` | 5.0 | Max requests per second |
| `--timeout` | 30.0 | HTTP timeout in seconds |
| `--llm` | off | Enable LLM fallback for abstract extraction |
| `--model` | `claude-sonnet-4-6` | LLM model string — any litellm provider (env: `LLM_MODEL`) |
| `--api-key` | — | LLM API key — falls back to provider env vars automatically |
| `-v / --verbose` | off | Debug logging |

---

## Output format

```json
{
  "schema_version": "1.0",
  "conference": "icse-2026",
  "source_urls": ["https://conf.researchr.org/track/..."],
  "scraped_at": "2026-05-06T14:32:11Z",
  "paper_count": 142,
  "papers": [
    {
      "source_url": "https://conf.researchr.org/details/...",
      "paper_id": "28",
      "track": "icse-2026-research-track",
      "track_label": "Research Track",
      "title": "Find My Code Twin: Improving Snippet Search ...",
      "abstract": "We present SNIPPET SEARCH, a high-performance code search tool ...",
      "doi": "https://doi.org/10.1145/...",
      "preprint_url": null,
      "session": "AI for Software Engineering 1",
      "room": "Asia I",
      "scheduled_at": null,
      "tags": ["Distinguished Paper Award"]
    }
  ]
}
```

Missing fields are `null`, never omitted. When scraping multiple tracks, all papers share the flat `papers` array and the `track` field disambiguates them.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```
