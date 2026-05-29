"""Tests for pipeline filtering (non-paper events, deduplication)."""
from __future__ import annotations

import re

import pytest

# Mirror both regexes from pipeline.py
_NON_PAPER_PREFIX = re.compile(
    r"^\s*(coffee|lunch|break|reception|dinner|keynote\s+break|"
    r"welcome|opening|closing|registration|social event|excursion|"
    r"networking|poster session|demo session|panel|awards?|"
    r"talk[\s:]+|open\s+spaces?|group\s+photo|announcement|"
    r"feijoada|samba|banquet|gala|tour|visit|ceremony|"
    r"ice\s*breaker|lightning\s+talk|invited\s+talk|"
    r"industry\s+talk|sponsor|exhibition)\b",
    re.IGNORECASE,
)

_NON_PAPER_ANYWHERE = re.compile(
    r"\b(group\s+photo|award\s+ceremony|awards?\s+ceremony|"
    r"best\s+paper\s+award|conference\s+dinner|gala\s+dinner|"
    r"city\s+tour|social\s+event|excursion|announcement)\b",
    re.IGNORECASE,
)


def _is_non_paper_by_title(title: str) -> bool:
    return bool(_NON_PAPER_PREFIX.match(title) or _NON_PAPER_ANYWHERE.search(title))


# ── Prefix-matched events ─────────────────────────────────────────────────────

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
    "Awards",
    "Dinner",
    "Dinner Banquet",
    "Keynote Break",
    "Break",
    # New patterns
    "Talk: Innovate SAIFely with AI",
    "Talk Invited: Topic X",
    "Open Spaces",
    "Open Space Discussion",
    "Group Photo",
    "Announcement",
    "Samba Night",
    "Banquet Dinner",
    "Gala Event",
    "City Tour",
    "Visit to Museum",
    "Award Ceremony",
    "Ice Breaker",
    "Lightning Talk: Performance",
    "Invited Talk: Prof. Smith",
    "Industry Talk",
    "Sponsor Presentation",
    "Exhibition Hall Opening",
])
def test_non_paper_titles_are_matched(title: str):
    assert _is_non_paper_by_title(title), f"Expected '{title}' to be filtered"


# ── "Anywhere" events (mid-title) ─────────────────────────────────────────────

@pytest.mark.parametrize("title", [
    "XP 2026 Group Photo",
    "XP 2026 Awards Ceremony",
    "XP 2027 Announcement",
    "ICSE Best Paper Award",
    "Conference Dinner and Social",
    "Gala Dinner 2026",
    "City Tour — Optional",
])
def test_non_paper_mid_title_are_matched(title: str):
    assert _is_non_paper_by_title(title), f"Expected '{title}' to be filtered"


# ── Real paper titles must NOT be filtered ────────────────────────────────────

@pytest.mark.parametrize("title", [
    "Find My Code Twin",
    "LLM-Based Test Generation",
    "A Study of Code Review",
    "Breaking the Build: CI Failures in Open Source",
    "Keynote: Prof. Smith",                            # 'keynote' alone is not in the prefix list
    "On the Effectiveness of Automated Testing",
    "Toward Better Code Comprehension",
    "An Empirical Study of Open Source Contributions",
    "Visiting Researchers in Software Engineering",    # starts with 'Visit' but not 'Visit ' alone
    "Announcing a New Framework for Mutation Testing", # 'Announc' but not 'Announcement'
    "Social Coding Practices in GitHub",               # 'Social' but not 'Social Event'
])
def test_paper_titles_are_not_matched(title: str):
    assert not _is_non_paper_by_title(title), f"Expected '{title}' NOT to be filtered"
