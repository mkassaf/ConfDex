"""Tests for FastAPI routes (jobs, llm env-keys)."""
from __future__ import annotations

import os
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from confscraper.web.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    app = create_app(db_path=tmp_path / "test.db")
    # Prevent background scraping tasks from making real network requests
    with patch("confscraper.web.routes.jobs.run_job", new=AsyncMock(return_value=None)):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


# ── POST /api/jobs ────────────────────────────────────────────────────────────

def test_create_job_ok(client):
    r = client.post("/api/jobs", json={"conference": "icse-2026", "model": "claude-sonnet-4-6"})
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["conference"] == "icse-2026"


def test_create_job_with_track_urls(client):
    r = client.post("/api/jobs", json={
        "track_urls": ["https://conf.researchr.org/track/icse-2026/icse-2026-research-track"],
        "model": "claude-sonnet-4-6",
    })
    assert r.status_code == 201


def test_create_job_missing_conference_and_urls(client):
    r = client.post("/api/jobs", json={"model": "claude-sonnet-4-6"})
    assert r.status_code == 400
    assert "conference" in r.json()["detail"].lower() or "track_urls" in r.json()["detail"].lower()


def test_create_job_no_model_scrape_only(client):
    # model is now optional; omitting it means scrape-only (no LLM)
    r = client.post("/api/jobs", json={"conference": "icse-2026"})
    assert r.status_code == 201
    assert r.json()["model"] == ""


# ── GET /api/jobs ─────────────────────────────────────────────────────────────

def test_list_jobs_empty(client):
    r = client.get("/api/jobs")
    assert r.status_code == 200
    assert r.json() == []


def test_list_jobs_after_create(client):
    client.post("/api/jobs", json={"conference": "icse-2026", "model": "claude-sonnet-4-6"})
    r = client.get("/api/jobs")
    assert r.status_code == 200
    assert len(r.json()) == 1


# ── GET /api/jobs/{id} ────────────────────────────────────────────────────────

def test_get_job_ok(client):
    created = client.post("/api/jobs", json={"conference": "icse-2026", "model": "claude-sonnet-4-6"}).json()
    r = client.get(f"/api/jobs/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_job_not_found(client):
    r = client.get("/api/jobs/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# ── DELETE /api/jobs/{id} ─────────────────────────────────────────────────────

def test_delete_job(client):
    created = client.post("/api/jobs", json={"conference": "icse-2026", "model": "claude-sonnet-4-6"}).json()
    r = client.delete(f"/api/jobs/{created['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/jobs/{created['id']}").status_code == 404


def test_delete_nonexistent_job(client):
    r = client.delete("/api/jobs/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


# ── GET /api/jobs/{id}/download ───────────────────────────────────────────────

def test_download_not_finished_returns_409(client):
    created = client.post("/api/jobs", json={"conference": "icse-2026", "model": "claude-sonnet-4-6"}).json()
    r = client.get(f"/api/jobs/{created['id']}/download?format=csv")
    assert r.status_code == 409


# ── GET /api/llm/env-keys ────────────────────────────────────────────────────

def test_env_keys_returns_dict(client):
    r = client.get("/api/llm/env-keys")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert "ANTHROPIC_API_KEY" in data
    assert isinstance(data["ANTHROPIC_API_KEY"], bool)


def test_env_keys_reflects_env(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    r = client.get("/api/llm/env-keys")
    assert r.json()["ANTHROPIC_API_KEY"] is True


def test_env_keys_false_when_unset(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.get("/api/llm/env-keys")
    assert r.json()["ANTHROPIC_API_KEY"] is False
