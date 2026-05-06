from __future__ import annotations

import logging
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from selectolax.parser import HTMLParser

from confscraper.adapters.base import Adapter
from confscraper.browser import discover_papers_via_browser
from confscraper.http import RateLimitedClient
from confscraper.models import Paper

logger = logging.getLogger(__name__)

BASE = "https://conf.researchr.org"

# URL patterns that need a real browser (JS-rendered content)
_BROWSER_PATTERNS = re.compile(r"/(home|program|schedule)/")


def _abs(href: str, base: str) -> str:
    return href if href.startswith("http") else urljoin(base, href)


def _track_slug_from_url(url: str) -> str:
    parts = urlparse(url).path.strip("/").split("/")
    for i, p in enumerate(parts):
        if p in ("track", "details", "home") and i + 2 < len(parts):
            return parts[i + 2]
    return parts[-1]


def _track_label_from_slug(slug: str) -> str:
    words = re.split(r"[-_]", slug)
    skip = {"icse", "fse", "ase", "issta", "msr", "pldi", "popl"}
    label_words = [w for w in words if not (w.isdigit() or w in skip)]
    return " ".join(w.title() for w in label_words) if label_words else slug


def _needs_browser(url: str) -> bool:
    return bool(_BROWSER_PATTERNS.search(urlparse(url).path))


class ResearchrAdapter(Adapter):
    def __init__(
        self,
        client: RateLimitedClient,
        use_llm: bool = False,
        llm_model: str = "claude-sonnet-4-6",
        llm_api_key: str | None = None,
    ):
        self._client = client
        self._use_llm = use_llm
        self._llm_model = llm_model
        self._llm_api_key = llm_api_key

    async def discover_papers(self, track_url: str) -> list[str]:
        if _needs_browser(track_url):
            logger.info("JS-rendered page detected, using browser for %s", track_url)
            return await discover_papers_via_browser(track_url)

        resp = await self._client.get(track_url)
        urls = self._extract_detail_urls(resp.text, track_url)

        # If static fetch found nothing, retry with browser
        if not urls:
            logger.info("Static fetch found 0 papers, retrying with browser for %s", track_url)
            urls = await discover_papers_via_browser(track_url)

        logger.info("Discovered %d paper URLs from %s", len(urls), track_url)
        return urls

    def _extract_detail_urls(self, html: str, base_url: str) -> list[str]:
        tree = HTMLParser(html)
        seen: set[str] = set()
        urls: list[str] = []
        for node in tree.css("a[href*='/details/']"):
            href = node.attributes.get("href", "")
            if not href:
                continue
            abs_url = _abs(href, base_url)
            if re.search(r"/details/[^/]+/[^/]+/\d+", abs_url) and abs_url not in seen:
                seen.add(abs_url)
                urls.append(abs_url)
        return urls

    def parse_paper(self, url: str, html: str) -> Paper:
        tree = HTMLParser(html)

        parts = urlparse(url).path.strip("/").split("/")
        paper_id = ""
        track_slug = ""
        if len(parts) >= 4 and parts[0] == "details":
            track_slug = parts[2]
            paper_id = parts[3] if len(parts) > 3 else ""

        abstract = self._parse_abstract(tree)

        # LLM fallback if selector-based extraction missed the abstract
        if abstract is None and self._use_llm:
            from confscraper.llm import extract_abstract_from_html
            logger.info("CSS selectors missed abstract for %s, falling back to LLM", url)
            abstract = extract_abstract_from_html(html, self._llm_model, self._llm_api_key)

        return Paper(
            source_url=url,
            paper_id=paper_id,
            track=track_slug,
            track_label=_track_label_from_slug(track_slug),
            title=self._parse_title(tree),
            abstract=abstract,
            doi=self._parse_doi(tree),
            preprint_url=self._parse_preprint(tree),
            session=self._parse_session(tree),
            room=self._parse_room(tree),
            scheduled_at=self._parse_scheduled_at(tree),
            tags=self._parse_tags(tree),
        )

    def _parse_title(self, tree: HTMLParser) -> str:
        try:
            node = tree.css_first("h2.page-title")
            if node:
                return node.text(strip=True)
            for h2 in tree.css("h2"):
                text = h2.text(strip=True)
                if text:
                    return text
        except Exception:
            pass
        try:
            title_tag = tree.css_first("title")
            if title_tag:
                return title_tag.text(strip=True).split(" | ")[0]
        except Exception:
            pass
        return ""

    def _parse_abstract(self, tree: HTMLParser) -> str | None:
        try:
            # Primary (researchr): <label>Abstract</label> + sibling <div class="col-sm-10"><p>
            for label in tree.css("label"):
                if label.text(strip=True).lower() == "abstract":
                    row = label.parent
                    if row:
                        content_div = row.css_first("div.col-sm-10")
                        if content_div:
                            paragraphs = [p.text(strip=True) for p in content_div.css("p") if p.text(strip=True)]
                            if paragraphs:
                                return "\n\n".join(paragraphs)
                            text = content_div.text(strip=True)
                            if text:
                                return text
        except Exception as e:
            logger.warning("Abstract label strategy failed: %s", e)

        try:
            for selector in ("section.abstract", "div.abstract"):
                node = tree.css_first(selector)
                if node:
                    paragraphs = [p.text(strip=True) for p in node.css("p") if p.text(strip=True)]
                    if paragraphs:
                        return "\n\n".join(paragraphs)
        except Exception as e:
            logger.warning("Abstract section/div strategy failed: %s", e)

        try:
            for h3 in tree.css("h3"):
                if "abstract" in h3.text(strip=True).lower():
                    paragraphs = []
                    node = h3.next
                    while node is not None:
                        if getattr(node, "tag", None) == "h3":
                            break
                        if getattr(node, "tag", None) == "p":
                            text = node.text(strip=True)
                            if text:
                                paragraphs.append(text)
                        node = node.next
                    if paragraphs:
                        return "\n\n".join(paragraphs)
        except Exception as e:
            logger.warning("Abstract h3 strategy failed: %s", e)

        return None

    def _parse_doi(self, tree: HTMLParser) -> str | None:
        try:
            node = tree.css_first("a[href*='doi.org']")
            if node:
                return node.attributes.get("href")
        except Exception:
            pass
        return None

    def _parse_preprint(self, tree: HTMLParser) -> str | None:
        try:
            for a in tree.css("a"):
                href = a.attributes.get("href", "")
                text = a.text(strip=True).lower()
                if "arxiv.org" in href or "pre-print" in text or "preprint" in text:
                    return href
        except Exception:
            pass
        return None

    def _parse_session(self, tree: HTMLParser) -> str | None:
        try:
            for dt in tree.css("dt"):
                if "session" in dt.text(strip=True).lower():
                    dd = dt.next
                    while dd is not None and getattr(dd, "tag", None) != "dd":
                        dd = dd.next
                    if dd:
                        return dd.text(strip=True) or None
            node = tree.css_first(".session-name, .event-session")
            if node:
                return node.text(strip=True) or None
        except Exception as e:
            logger.warning("Session parsing failed: %s", e)
        return None

    def _parse_room(self, tree: HTMLParser) -> str | None:
        try:
            for dt in tree.css("dt"):
                label = dt.text(strip=True).lower()
                if "room" in label or "location" in label:
                    dd = dt.next
                    while dd is not None and getattr(dd, "tag", None) != "dd":
                        dd = dd.next
                    if dd:
                        return dd.text(strip=True) or None
            node = tree.css_first(".room-name, .event-room")
            if node:
                return node.text(strip=True) or None
        except Exception as e:
            logger.warning("Room parsing failed: %s", e)
        return None

    def _parse_scheduled_at(self, tree: HTMLParser) -> datetime | None:
        try:
            for dt in tree.css("dt"):
                label = dt.text(strip=True).lower()
                if "when" in label or "time" in label:
                    dd = dt.next
                    while dd is not None and getattr(dd, "tag", None) != "dd":
                        dd = dd.next
                    if dd:
                        return self._parse_datetime(dd.text(strip=True))
        except Exception as e:
            logger.warning("Scheduled_at parsing failed: %s", e)
        return None

    def _parse_datetime(self, text: str) -> datetime | None:
        formats = [
            "%a %d %b %Y %H:%M",
            "%a %d %b %Y %I:%M %p",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(text.strip(), fmt)
            except ValueError:
                continue
        return None

    def _parse_tags(self, tree: HTMLParser) -> list[str]:
        tags: list[str] = []
        try:
            known_tags = {
                "distinguished paper award",
                "virtual attendance",
                "best paper",
                "withdrawn",
                "artifact evaluated",
                "replication package",
            }
            for node in tree.css("span.label, span.badge, .paper-tag"):
                text = node.text(strip=True)
                if text.lower() in known_tags:
                    tags.append(text)
            body_text = tree.body.text(strip=True).lower() if tree.body else ""
            for tag in known_tags:
                if tag in body_text and tag.title() not in tags:
                    tags.append(tag.title())
        except Exception as e:
            logger.warning("Tag parsing failed: %s", e)
        return list(dict.fromkeys(tags))

    async def discover_tracks(self, conference_slug: str) -> list[str]:
        home = f"{BASE}/home/{conference_slug}"
        try:
            resp = await self._client.get(home)
        except Exception:
            home = f"{BASE}/{conference_slug}"
            resp = await self._client.get(home)

        tree = HTMLParser(resp.text)
        seen: set[str] = set()
        urls: list[str] = []
        for a in tree.css(f"a[href*='/track/{conference_slug}/']"):
            href = a.attributes.get("href", "")
            abs_url = _abs(href, home)
            if abs_url not in seen:
                seen.add(abs_url)
                urls.append(abs_url)
        logger.info("Discovered %d tracks for %s", len(urls), conference_slug)
        return urls
