from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

import pytest
from selectolax.parser import HTMLParser

from confscraper.adapters.researchr import ResearchrAdapter
from confscraper.models import Paper

FIXTURES = Path(__file__).parent / "fixtures"

PAPER_URL = "https://conf.researchr.org/details/icse-2026/icse-2026-research-track/28/find-my-code-twin"
TRACK_URL = "https://conf.researchr.org/track/icse-2026/icse-2026-research-track"


@pytest.fixture
def adapter():
    return ResearchrAdapter(client=None)  # type: ignore[arg-type]


def _html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestParsePaper:
    def test_title(self, adapter: ResearchrAdapter):
        paper = adapter.parse_paper(PAPER_URL, _html("paper_detail.html"))
        assert "Find My Code Twin" in paper.title

    def test_abstract_extracted(self, adapter: ResearchrAdapter):
        paper = adapter.parse_paper(PAPER_URL, _html("paper_detail.html"))
        assert paper.abstract is not None
        assert "SNIPPET SEARCH" in paper.abstract

    def test_abstract_two_paragraphs_joined(self, adapter: ResearchrAdapter):
        paper = adapter.parse_paper(PAPER_URL, _html("paper_detail.html"))
        assert paper.abstract is not None
        assert "34%" in paper.abstract

    def test_no_authors_field(self, adapter: ResearchrAdapter):
        paper = adapter.parse_paper(PAPER_URL, _html("paper_detail.html"))
        assert not hasattr(paper, "authors")

    def test_doi(self, adapter: ResearchrAdapter):
        paper = adapter.parse_paper(PAPER_URL, _html("paper_detail.html"))
        assert paper.doi == "https://doi.org/10.1145/3786583.3786881"

    def test_preprint_url(self, adapter: ResearchrAdapter):
        paper = adapter.parse_paper(PAPER_URL, _html("paper_detail.html"))
        assert paper.preprint_url is not None
        assert "arxiv.org" in paper.preprint_url

    def test_session(self, adapter: ResearchrAdapter):
        paper = adapter.parse_paper(PAPER_URL, _html("paper_detail.html"))
        assert paper.session == "AI for Software Engineering 1"

    def test_room(self, adapter: ResearchrAdapter):
        paper = adapter.parse_paper(PAPER_URL, _html("paper_detail.html"))
        assert paper.room == "Asia I"

    def test_tags(self, adapter: ResearchrAdapter):
        paper = adapter.parse_paper(PAPER_URL, _html("paper_detail.html"))
        assert any("distinguished" in t.lower() for t in paper.tags)

    def test_paper_id(self, adapter: ResearchrAdapter):
        paper = adapter.parse_paper(PAPER_URL, _html("paper_detail.html"))
        assert paper.paper_id == "28"

    def test_track_slug(self, adapter: ResearchrAdapter):
        paper = adapter.parse_paper(PAPER_URL, _html("paper_detail.html"))
        assert paper.track == "icse-2026-research-track"

    def test_no_abstract_returns_none(self, adapter: ResearchrAdapter):
        no_abs_url = "https://conf.researchr.org/details/icse-2026/icse-2026-workshop/5/workshop-paper"
        paper = adapter.parse_paper(no_abs_url, _html("paper_no_abstract.html"))
        assert paper.abstract is None

    def test_paper_is_valid_model(self, adapter: ResearchrAdapter):
        paper = adapter.parse_paper(PAPER_URL, _html("paper_detail.html"))
        assert isinstance(paper, Paper)
        assert paper.source_url == PAPER_URL


class TestDiscoverPapers:
    def test_discover_deduplicates(self, adapter: ResearchrAdapter):
        html = (FIXTURES / "track_listing.html").read_text()
        tree = HTMLParser(html)
        seen: set[str] = set()
        urls: list[str] = []
        for node in tree.css("a[href*='/details/']"):
            href = node.attributes.get("href", "")
            abs_url = urljoin(TRACK_URL, href)
            if re.search(r"/details/[^/]+/[^/]+/\d+", abs_url) and abs_url not in seen:
                seen.add(abs_url)
                urls.append(abs_url)

        assert len(urls) == 3
        assert all("/details/" in u for u in urls)

    def test_non_detail_links_excluded(self, adapter: ResearchrAdapter):
        html = (FIXTURES / "track_listing.html").read_text()
        tree = HTMLParser(html)
        urls = []
        for node in tree.css("a[href*='/details/']"):
            href = node.attributes.get("href", "")
            abs_url = urljoin(TRACK_URL, href)
            if re.search(r"/details/[^/]+/[^/]+/\d+", abs_url):
                urls.append(abs_url)

        assert not any("/track/" in u for u in urls)
