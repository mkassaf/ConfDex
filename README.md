# ConfDex

Scrapes paper titles and abstracts from conference websites (primarily `conf.researchr.org`), summarizes them with an LLM, and scores each paper's relevance to a topic of your choice.

Works with any `conf.researchr.org` URL — track pages, workshop home pages, and program pages. JavaScript-rendered pages are handled automatically via a headless browser. Supports local models via Ollama and any remote provider (Claude, OpenAI, DeepSeek, Gemini, Groq, Mistral, …) through [litellm](https://docs.litellm.ai/docs/providers).

Available as a **CLI tool** or a **self-hosted web app**.

---

## Table of Contents

- [Web App (recommended)](#web-app-recommended)
  - [Docker deployment](#docker-deployment)
  - [Password protection](#set-an-admin-password)
  - [HTTPS (self-signed / IP)](#https-with-a-self-signed-certificate-ip-address-no-domain)
  - [HTTPS (domain)](#https-with-a-domain-name)
  - [Deploy to AWS EC2](#deploy-to-aws-ec2-with-auto-deploy-via-github-actions)
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

**Requirements:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac/Windows) or [Docker Engine + Compose](https://docs.docker.com/engine/install/) (Linux). Nothing else — no Python, Node, or git needed.

#### 1. Download the compose file

```bash
curl -O https://raw.githubusercontent.com/mkassaf/ConfDex/main/docker-compose.yml
```

#### 2. (Optional) set API keys for remote LLMs

```bash
curl -O https://raw.githubusercontent.com/mkassaf/ConfDex/main/.env.example
cp .env.example .env
# Open .env and fill in whichever keys you need
```

Skip this step if you only plan to use local Ollama models — you can also enter API keys directly in the web UI per job.

#### 3. Start

```bash
docker compose up -d
```

Docker Compose pulls the pre-built image from Docker Hub automatically. Open **http://localhost:8000**.

Ollama is included — no separate install needed. To add a local model, open the web UI, select **Local (Ollama)** in the LLM selector, and click **Install a model**.

#### Stop / restart

```bash
docker compose down       # stop (data is preserved in volumes)
docker compose up -d      # start again
```

#### Update to the latest version

```bash
docker compose pull
docker compose up -d
```

#### Set an admin password

Add `ADMIN_PASSWORD` to your `.env` file to password-protect the entire UI:

```bash
# .env
ADMIN_PASSWORD=your-strong-password
```

When set, the browser will ask for the password on every visit (HTTP Basic Auth). Leave it blank to run without authentication (e.g. on a local machine behind a firewall).

You can also pass it inline without a `.env` file:

```bash
ADMIN_PASSWORD=your-strong-password docker compose up -d
```

#### HTTPS with a self-signed certificate (IP address, no domain)

Use this when you want HTTPS but don't have a domain name — just an IP address.

**Requirements:** ports 80 and 443 open.

Add `HOST_IP` to your `.env`:

```bash
# .env
HOST_IP=192.168.1.100        # your server's IP address
ADMIN_PASSWORD=your-strong-password
```

Start everything:

```bash
docker compose -f docker-compose.yml -f docker-compose.selfsigned.yml up -d
```

The app is now at **https://192.168.1.100**. On the first start, a self-signed certificate is generated automatically and stored in a Docker volume (persists across restarts).

> **Browser warning:** because the certificate is self-signed, your browser will show a security warning. Click **Advanced → Proceed** (Chrome) or **Accept the Risk** (Firefox) to continue.

#### HTTPS with a domain name

**Requirements:** a domain pointing to your server, ports 80 and 443 open.

Add `DOMAIN` to your `.env`:

```bash
# .env
DOMAIN=confdex.example.com
ADMIN_PASSWORD=your-strong-password
```

**Step 1 — issue the SSL certificate (run once):**

```bash
# Start only nginx and certbot temporarily with HTTP
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d nginx certbot

# Issue the certificate
docker compose -f docker-compose.yml -f docker-compose.https.yml run --rm certbot \
  certonly --webroot --webroot-path /var/www/certbot \
  --email you@example.com --agree-tos --no-eff-email \
  -d confdex.example.com
```

**Step 2 — start everything:**

```bash
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d
```

The app is now at **https://confdex.example.com**. Certificates auto-renew every 12 hours.

#### GPU-accelerated Ollama (NVIDIA only)

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

#### Persisting data

Job history and results are stored in a Docker volume (`confdex_data`). Downloaded models are stored in `ollama_models`. Both survive container restarts.

#### Environment variables (`.env`)

| Variable | Description |
|---|---|
| `ADMIN_USERNAME` | Username for the web UI (default: `admin`) |
| `ADMIN_PASSWORD` | Password for the web UI (leave blank to disable auth) |
| `DOMAIN` | Your domain name (required for domain-based HTTPS) |
| `HOST_IP` | Your server's IP address (required for self-signed HTTPS) |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GROQ_API_KEY` | Groq API key |
| `MISTRAL_API_KEY` | Mistral API key |

LLM keys set here are used as server-side defaults. You can also enter a key directly in the web UI per job.

#### Automated deployment via GitHub Actions

If you want GitHub to redeploy your server automatically on every push, go to your repo → **Settings → Secrets and variables → Actions** and add:

**Secrets** (sensitive values, never visible after saving):

| Secret | Description |
|---|---|
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `ADMIN_PASSWORD` | Password for the ConfDex web UI |
| `SSH_PRIVATE_KEY` | Private key for SSH authentication |

**Variables** (non-sensitive, used in `if` conditions):

| Variable | Description |
|---|---|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `SSH_HOST` | Server IP or hostname |
| `SSH_USER` | SSH login username |

When `SSH_HOST` variable is set, the workflow SSHes into your server after every push and runs `docker compose pull && docker compose up -d` automatically.

---

### Deploy to AWS EC2 with auto-deploy via GitHub Actions

This sets up ConfDex on an AWS EC2 instance and configures GitHub to redeploy it automatically on every push to `main`.

#### Step 1 — Launch an EC2 instance

1. Go to **EC2 → Launch Instance** in the AWS Console.
2. Choose **Ubuntu 24.04 LTS** (or Amazon Linux 2023).
3. Instance type: **t3.medium** (2 vCPU / 4 GB RAM) — minimum for running Ollama models. Use `t3.small` if you only need remote LLMs.
4. **Key pair:** create a new key pair (RSA, `.pem` format). Download and save it — you'll need the private key for GitHub.
5. **Security group:** allow inbound traffic on:
   - **SSH** port 22 (your IP only, or anywhere for convenience)
   - **HTTP** port 80 (anywhere)
   - **HTTPS** port 443 (anywhere)
6. Storage: **20 GB** minimum (Ollama models can be large).
7. Launch the instance and note the **Public IPv4 address**.
8. (Recommended) Allocate an **Elastic IP** and associate it with the instance so the IP doesn't change on restart: **EC2 → Elastic IPs → Allocate → Associate**.

#### Step 2 — Bootstrap the server (run once)

From your local machine, run the bootstrap script. It installs Docker, downloads the compose files, and starts the app:

```bash
# Clone the repo locally if you haven't already
git clone https://github.com/mkassaf/ConfDex.git
cd ConfDex

bash scripts/setup-server.sh <your-ec2-ip> <your-admin-password>
# Example:
bash scripts/setup-server.sh 203.0.113.10 MyPassword123
```

> If you're using Amazon Linux instead of Ubuntu, edit the script and change `SSH_USER="ubuntu"` to `SSH_USER="ec2-user"`.

After the script finishes, open **https://your-ec2-ip** in your browser. Accept the self-signed certificate warning, then log in with:
- **Username:** *(leave blank)*
- **Password:** your admin password

#### Step 3 — Configure GitHub Actions for auto-deploy

Every push to `main` will build a new Docker image and deploy it to your server automatically.

Go to your GitHub repo → **Settings → Secrets and variables → Actions**.

Add the following **Secrets** (sensitive — hidden after saving):

| Secret | Value |
|---|---|
| `DOCKERHUB_TOKEN` | Docker Hub access token ([create one here](https://hub.docker.com/settings/security)) |
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `ADMIN_PASSWORD` | Your ConfDex admin password |
| `SSH_PRIVATE_KEY` | Contents of the `.pem` key file you downloaded in Step 1 |

Add the following **Variables** (non-sensitive — visible in logs):

| Variable | Value |
|---|---|
| `SSH_HOST` | Your EC2 public IP (e.g. `203.0.113.10`) |
| `SSH_USER` | `ubuntu` (or `ec2-user` for Amazon Linux) |

Once configured, push any change to `main` — GitHub Actions will:
1. Build and push the Docker image to Docker Hub
2. SSH into your EC2 instance and run `docker compose pull && docker compose up -d`

#### Step 4 — Update manually (without GitHub Actions)

```bash
ssh ubuntu@your-ec2-ip
cd ~/confdex
docker compose -f docker-compose.yml -f docker-compose.selfsigned.yml pull
docker compose -f docker-compose.yml -f docker-compose.selfsigned.yml up -d
```

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

Mustafa Assaf