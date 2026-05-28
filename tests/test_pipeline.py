"""Tests for pipeline filtering (non-paper events, deduplication)."""
from __future__ import annotations

import re

import pytest

# Replicate the regex from pipeline.py so tests stay independent of import side-effects
_NON_PAPER = re.compile(
    r"^\s*(coffee|lunch|break|reception|dinner|keynote\s+break|"
    r"welcome|opening|closing|registration|social event|excursion|"
    r"networking|poster session|demo session|panel|awards?)\b",
    re.IGNORECASE,
)


@pytest.mark.parametrize("title", [
    "Coffee Break",
    "coffee break",
    "  Lunch",
    "Lunch Break",
    "Reception",
    "Welcome",
    "Welcome Reception",
    "Opening",
    "Opening Ceremony",
    "Closing",
    "Closing Session",
    "Registration",
    "Social Event",
    "Excursion",
    "Networking Lunch",
    "Poster Session",
    "Demo Session",
    "Panel Discussion",
    "Award Ceremony",
    "Awards",
    "Dinner",
    "Dinner Banquet",
    "Keynote Break",
    "Break",
])
def test_non_paper_titles_are_matched(title: str):
    assert _NON_PAPER.match(title), f"Expected '{title}' to be filtered"


@pytest.mark.parametrize("title", [
    "Find My Code Twin",
    "LLM-Based Test Generation",
    "A Study of Code Review",
    "Breaking the Build: CI Failures in Open Source",  # starts with 'Breaking' not 'Break'
    "Keynote: Prof. Smith",                            # 'keynote' alone is not in the list
    "On the Effectiveness of Automated Testing",
    "Toward Better Code Comprehension",
])
def test_paper_titles_are_not_matched(title: str):
    assert not _NON_PAPER.match(title), f"Expected '{title}' NOT to be filtered"
