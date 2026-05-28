# ── Stage 1: build React frontend ────────────────────────────────────────────
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN VITE_OUT_DIR=dist npm run build

# ── Stage 2: Python backend ───────────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.title="ConfDex" \
      org.opencontainers.image.description="Scrape, summarize, and find relevant papers from academic conferences. Self-hosted web app with local (Ollama) and remote LLM support." \
      org.opencontainers.image.url="https://github.com/mkassaf/ConfDex" \
      org.opencontainers.image.source="https://github.com/mkassaf/ConfDex" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="Mustafa Assaf"

WORKDIR /app

# uv for fast installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_SYSTEM_PYTHON=1 UV_NO_CACHE=1

# System deps for Playwright Chromium (rarely changes — cached early)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libexpat1 libxcb1 libxkbcommon0 \
    libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps before copying source so this layer is cached
# as long as pyproject.toml doesn't change.
COPY pyproject.toml ./
# Stub package so uv can resolve and install all dependencies
RUN mkdir -p src/confscraper && touch src/confscraper/__init__.py
RUN uv pip install .

# Install Playwright browser — cached unless playwright version changes
RUN python -m playwright install chromium

# Copy actual source (changes often — after all slow steps)
COPY src/ src/
# Copy built frontend into the static dir baked into the image
COPY --from=frontend /frontend/dist/ src/confscraper/web/static/
# Re-install to register the real package (deps already cached above)
RUN uv pip install --no-deps .

EXPOSE 8000
VOLUME ["/data"]

CMD ["confscraper", "serve", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--db", "/data/confdex.db"]
