"""Tests for categorize.py — JSON parsing and score clamping."""
from __future__ import annotations

import json
import pytest

from confscraper.categorize import _parse_json


# ── _parse_json ───────────────────────────────────────────────────────────────

def test_parse_plain_json():
    raw = '{"score": 7, "reasoning": "relevant", "matching": []}'
    result = _parse_json(raw)
    assert result["score"] == 7


def test_parse_json_with_markdown_fence():
    raw = '```json\n{"score": 5, "reasoning": "partial"}\n```'
    result = _parse_json(raw)
    assert result["score"] == 5


def test_parse_json_with_leading_prose():
    raw = 'Here is the result:\n{"score": 3, "reasoning": "peripheral"}'
    result = _parse_json(raw)
    assert result["score"] == 3


def test_parse_json_invalid_raises():
    with pytest.raises((ValueError, json.JSONDecodeError)):
        _parse_json("not json at all")


# ── score clamping ────────────────────────────────────────────────────────────

def test_score_clamp_above_10():
    raw = max(0, min(10, int(17)))
    assert raw == 10


def test_score_clamp_below_0():
    raw = max(0, min(10, int(-3)))
    assert raw == 0


def test_score_clamp_valid_passthrough():
    for s in range(11):
        assert max(0, min(10, int(s))) == s


# ── topic score prompt sanity ─────────────────────────────────────────────────

def test_topic_score_prompt_contains_key_instructions():
    from confscraper.categorize import _TOPIC_SCORE_PROMPT_V2
    assert "{topic}" in _TOPIC_SCORE_PROMPT_V2
    assert "{title}" in _TOPIC_SCORE_PROMPT_V2
    assert "{summary}" in _TOPIC_SCORE_PROMPT_V2
    assert "primary" in _TOPIC_SCORE_PROMPT_V2.lower()


def test_summarize_prompt_contains_required_fields():
    from confscraper.categorize import _SUMMARIZE_PROMPT_V2
    for field in ("summary", "keywords", "methodology", "domain"):
        assert field in _SUMMARIZE_PROMPT_V2
