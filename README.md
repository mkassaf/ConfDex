# ConfDex

Scrapes paper titles and abstracts from conference websites (primarily `conf.researchr.org`), summarizes them with an LLM, and scores each paper's relevance to a topic of your choice.

Works with any `conf.researchr.org` URL — track pages, workshop home pages, and program pages. JavaScript-rendered pages are handled automatically via a headless browser. Supports local models via Ollama and any remote provider (Claude, OpenAI, DeepSeek, Gemini, Groq, Mistral, …) through [litellm](https://docs.litellm.ai/docs/providers).

Available as a **CLI tool** or a **self-hosted web app**.

---

## Table of Contents

- [Web App (recommended)](#web-app-recommended)
  - [Docker deployment](#docker-deployment)
  - [Manual deployment](#manual-deployment)
- [CLI installation](#cli-installation)
- [CLI usage](#cli-usage)
  - [Scraping](#scraping)
  - [Summarize & score](#summarize--score)
  - [LLM providers](#llm-providers)
  - [Output formats](#output-formats)
  - [All options](#all-options)
- [Development](#development)

---

## Web App (recommended)

The web app provides a browser UI to submit scraping jobs, pick an LLM (local or remote), watch real-time progress, and browse / download results.

### Docker deployment

**Requirements:** Docker and Docker Compose. Nothing else — no Python, Node, or git needed.

```bash
# 1. Download the compose file and env template
curl -O https://raw.githubusercontent.com/mkassaf/ConfDex/main/docker-compose.yml
curl -O https://raw.githubusercontent.com/mkassaf/ConfDex/main/.env.example
cp .env.example .env

# 2. (Optional) edit .env to add remote API keys
#    Leave blank if you only plan to use local Ollama models

# 3. Start
docker compose up -d
```

Docker Compose pulls the pre-built image `mkassaf/confdex:latest` from Docker Hub automatically. Open **http://localhost:8000**.

To pass API keys without a `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-... docker compose up -d
```

To build the image yourself from source instead:

```bash
git clone https://github.com/mkassaf/ConfDex.git
cd ConfDex
cp .env.example .env
docker compose up --build -d
```

#### Platform support

| Platform | Works? |
|---|---|
| Linux server / VPS (x86-64) | ✅ Recommended for always-on hosting |
| macOS with Intel | ✅ |
| Windows (Docker Desktop) | ✅ |
| macOS Apple Silicon (M1/M2/M3) | ✅ via Docker's automatic emulation |
| Raspberry Pi 4/5 (arm64) | ✅ via Docker's automatic emulation |

> **Note:** the published image is currently `amd64` only. Docker Desktop handles emulation transparently on ARM machines, but native ARM performance requires a multi-platform build.

#### Updating to the latest version

```bash
docker compose pull
docker compose up -d
```

Open **http://localhost:8000** in your browser.

Ollama is included as a sidecar service. To install a local model, open the web UI, select **Local (Ollama)** in the LLM selector, and click **Install a model**.

#### GPU-accelerated Ollama (NVIDIA)

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

#### Persisting data

Job history and results are stored in a Docker volume (`confdex_data`). Downloaded models are stored in `ollama_models`. Both survive container restarts.

#### Environment variables (`.env`)

| Variable | Provider |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic Claude |
| `OPENAI_API_KEY` | OpenAI |
| `DEEPSEEK_API_KEY` | DeepSeek |
| `GEMINI_API_KEY` | Google Gemini |
| `GROQ_API_KEY` | Groq |
| `MISTRAL_API_KEY` | Mistral |

Keys set here are used as server-side defaults. You can also enter a key directly in the web UI per job.

---

### Manual deployment

**Requirements:** Python 3.11+, Node.js 20+.

```bash
git clone https://github.com/mkassaf/ConfDex.git
cd ConfDex

# 1. Install Python dependencies
pip install -e .

# 2. Build the React frontend
cd frontend
npm install
npm run build      # outputs to src/confscraper/web/static/
cd ..

# 3. Start the server
confscraper serve --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000**.

**Options for `confscraper serve`:**

| Flag | Default | Description |
|---|---|---|
| `--host` | `0.0.0.0` | Bind address |
| `--port` | `8000` | Port |
| `--db` | `confdex.db` | SQLite database path |
| `--reload` | off | Auto-reload on code change (dev only) |

To expose the server on your network, set `--host 0.0.0.0` (already the default). To restrict to localhost only, use `--host 127.0.0.1`.

#### Ollama for local models (manual deployment)

If you want to use local models without Docker, install Ollama separately:

```bash
# Install Ollama: https://ollama.com
ollama serve          # starts the Ollama daemon
ollama pull llama3.2  # install a model
```

Then select **Local (Ollama)** in the web UI. You can also install models directly from the UI.

#### Running as a background service (Linux/systemd)

```ini
# /etc/systemd/system/confdex.service
[Unit]
Description=ConfDex web server
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/ConfDex
ExecStart=confscraper serve --host 0.0.0.0 --port 8000 --db /var/lib/confdex/jobs.db
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now confdex
```

---

## CLI installation

**Requires Python 3.11+**

```bash
# From source
git clone https://github.com/mkassaf/ConfDex.git
cd ConfDex
pip install -e .

# Directly from GitHub
pip install git+https://github.com/mkassaf/ConfDex.git
```

> **macOS note:** if `confscraper` is not found after install, add the user bin to your PATH:
> ```bash
> export PATH="$HOME/Library/Python/3.11/bin:$PATH"
> ```
> Add that line to `~/.zshrc` or `~/.bashrc` to make it permanent.

---

## CLI usage

### Scraping

```bash
# Single track page
confscraper scrape https://conf.researchr.org/track/icse-2026/icse-2026-research-track \
                   -o icse-2026-research.json

# Multiple tracks merged into one file
confscraper scrape URL1 URL2 -o icse-2026.json

# Auto-discover all tracks for a conference
confscraper scrape --conference icse-2026 -o icse-2026.json

# Workshop / home pages (JavaScript-rendered — detected automatically)
confscraper scrape https://conf.researchr.org/home/icse-2026/greens-2026 -o greens.json
```

### Summarize & score

Pass `--summarize` to run each abstract through an LLM. Add `--topic` to also get a relevance score (0–10) for each paper.

```bash
# Summarize with a local Ollama model
confscraper scrape URL --summarize --model ollama/llama3.2 -o summaries.json

# Summarize + score against a topic
confscraper scrape URL --summarize --topic "software testing with LLMs" \
                       --model ollama/llama3.2 -o summaries.json

# Use a remote model
confscraper scrape URL --summarize --topic "green computing" \
                       --model deepseek/deepseek-chat \
                       --api-key $DEEPSEEK_API_KEY -o summaries.json
```

Summary output per paper:

```json
{
  "title": "Find My Code Twin: ...",
  "source_url": "https://conf.researchr.org/details/...",
  "doi": "10.1145/...",
  "summary": "This paper addresses the problem of code retrieval at scale. It proposes SNIPPET SEARCH, a semantic clustering approach...",
  "keywords": ["code search", "semantic clustering", "embeddings", "software engineering", "retrieval"],
  "methodology": "tool or framework",
  "domain": "software engineering tools",
  "score": 4,
  "score_reasoning": "The paper focuses on code retrieval rather than software testing, but its semantic search techniques are applicable.",
  "score_matching": ["semantic search applicable to test case retrieval"]
}
```

### LLM providers

API keys are resolved automatically — no need to pass `--api-key` if the env var is set:

| Provider | Model string | Key env var |
|---|---|---|
| Anthropic Claude (default) | `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| OpenAI | `gpt-4o`, `gpt-4o-mini` | `OPENAI_API_KEY` |
| DeepSeek | `deepseek/deepseek-chat` | `DEEPSEEK_API_KEY` |
| Google Gemini | `gemini/gemini-1.5-pro` | `GEMINI_API_KEY` |
| Groq | `groq/llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| Mistral | `mistral/mistral-large-latest` | `MISTRAL_API_KEY` |
| Ollama (local) | `ollama/llama3.2` | *(none needed)* |

Any other [litellm-compatible](https://docs.litellm.ai/docs/providers) provider also works.

```bash
# Set model globally via env var
export LLM_MODEL=ollama/llama3.2
confscraper scrape URL --summarize -o summaries.json
```

### Output formats

```bash
# JSON (default)
confscraper scrape URL -o papers.json

# CSV (scrape)
confscraper scrape URL --csv -o papers.csv

# CSV (summarize)
confscraper scrape URL --summarize --csv -o summaries.csv

# NDJSON (one object per line)
confscraper scrape URL --ndjson -o papers.ndjson

# Compact JSON (no indentation)
confscraper scrape URL --compact -o papers.json
```

**Scrape CSV columns:** `title`, `abstract`, `track`, `track_label`, `session`, `room`, `scheduled_at`, `doi`, `preprint_url`, `tags`, `paper_id`, `source_url`

**Summary CSV columns:** `title`, `source_url`, `doi`, `summary`, `keywords`, `methodology`, `domain`, `score`, `score_reasoning`, `score_matching`

### All options

```
confscraper scrape [OPTIONS] [TRACK_URLS]...
```

| Flag | Default | Description |
|---|---|---|
| `-c / --conference` | — | Conference slug for auto-discovery (e.g. `icse-2026`) |
| `-o / --output` | stdout | Output file path |
| `--summarize` | off | Summarize abstracts + extract keywords via LLM |
| `--topic TEXT` | — | Score relevance against this topic (0–10); requires `--summarize` |
| `--model` | `claude-sonnet-4-6` | LLM model string (env: `LLM_MODEL`) |
| `--api-key` | — | LLM API key (falls back to provider env vars) |
| `--llm` | off | Enable LLM fallback for abstract extraction when CSS selectors fail |
| `--csv` | off | Output as CSV instead of JSON |
| `--ndjson` | off | One JSON object per line, no wrapper |
| `--compact` | off | Minify JSON output |
| `--concurrency` | 5 | Max concurrent HTTP requests |
| `--rate` | 5.0 | Max requests per second |
| `--timeout` | 30.0 | HTTP timeout in seconds |
| `-v / --verbose` | off | Debug logging |

---

## Development

```bash
pip install -e ".[dev]"
pytest

# Run the web server in dev mode (auto-reload)
confscraper serve --reload

# Develop the frontend with hot reload
cd frontend
npm install
npm run dev   # starts Vite dev server on :5173, proxies /api to :8000
```
