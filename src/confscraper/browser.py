from __future__ import annotations

import asyncio
import json
import logging
import re
from urllib.parse import urljoin

from playwright.async_api import async_playwright
from selectolax.parser import HTMLParser

from confscraper import __version__

logger = logging.getLogger(__name__)

USER_AGENT = f"confscraper/{__version__} (+github.com/mkassaf/ConfDex)"

_AJAX_CONCURRENCY = 8


async def fetch_rendered(url: str, wait_selector: str = "body") -> str:
    """Fetch a page using a headless browser and return the fully-rendered HTML."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle", timeout=60_000)
        try:
            await page.wait_for_selector(wait_selector, timeout=10_000)
        except Exception:
            pass
        html = await page.content()
        await browser.close()
        return html


def _detail_urls_from_html(html: str, base_url: str) -> list[str]:
    """Extract /details/.../{id}/... URLs from an HTML fragment."""
    found = []
    for m in re.finditer(r"/details/[^\s\"'<>\\]+/\d+[^\s\"'<>\\]*", html):
        url = urljoin(base_url, m.group())
        if re.search(r"/details/[^/]+/[^/]+/\d+", url):
            found.append(url)
    return found


_BROWSER_TIMEOUT = 180  # seconds total for browser-based discovery


async def _discover_papers_via_browser_inner(url: str) -> list[str]:
    detail_urls: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        modal_htmls: list[str] = []

        async def on_response(resp) -> None:
            if "eventDetailsModal" not in resp.url:
                return
            try:
                body = await resp.text()
                items = json.loads(body)
                for item in items:
                    if isinstance(item, dict) and "value" in item:
                        modal_htmls.append(item["value"])
            except Exception as e:
                logger.debug("Modal response parse error: %s", e)

        page.on("response", on_response)
        await page.goto(url, wait_until="networkidle", timeout=60_000)
        html = await page.content()

        for link in _detail_urls_from_html(html, url):
            detail_urls.add(link)

        event_ids = re.findall(r'data-event-modal=["\']([^"\']+)["\']', html)
        logger.info("Found %d event modal IDs", len(event_ids))

        sem = asyncio.Semaphore(_AJAX_CONCURRENCY)

        async def trigger_modal(event_id: str) -> None:
            async with sem:
                try:
                    await page.evaluate(
                        '(id) => jQuery("[data-event-modal=" + JSON.stringify(id) + "]").first().trigger("click")',
                        event_id,
                    )
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.debug("Modal trigger failed for %s: %s", event_id, e)

        await asyncio.gather(*(trigger_modal(eid) for eid in event_ids))
        await asyncio.sleep(2)
        await browser.close()

    for fragment in modal_htmls:
        for link in _detail_urls_from_html(fragment, url):
            detail_urls.add(link)

    return list(detail_urls)


async def discover_papers_via_browser(url: str) -> list[str]:
    """Browser-based paper discovery with a hard timeout to prevent hung jobs."""
    logger.info("Browser-based discovery for %s", url)
    try:
        urls = await asyncio.wait_for(
            _discover_papers_via_browser_inner(url),
            timeout=_BROWSER_TIMEOUT,
        )
        logger.info("Browser discovery found %d detail URLs", len(urls))
        return urls
    except asyncio.TimeoutError:
        logger.error("Browser discovery timed out after %ds for %s", _BROWSER_TIMEOUT, url)
        raise RuntimeError(
            f"Browser-based paper discovery timed out after {_BROWSER_TIMEOUT}s for {url}. "
            "The conference page may be too slow or structured differently."
        )
