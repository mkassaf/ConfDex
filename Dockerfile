# ── Stage 1: build React frontend ────────────────────────────────────────────
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN VITE_OUT_DIR=dist npm run build

# ── Stage 2: Python backend ───────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# System deps for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libexpat1 libxcb1 libxkbcommon0 \
    libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src/ src/

RUN pip install --no-cache-dir .
RUN python -m playwright install chromium

# Copy built frontend into static directory
COPY --from=frontend /frontend/dist/ src/confscraper/web/static/

EXPOSE 8000

VOLUME ["/data"]

CMD ["confscraper", "serve", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--db", "/data/confdex.db"]
