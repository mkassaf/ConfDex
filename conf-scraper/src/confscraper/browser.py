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


async def discover_papers_via_browser(url: str) -> list[str]:
    """
    For JS-heavy pages (home/program pages):
    1. Render the page with Playwright
    2. Collect all static /details/ links
    3. For each data-event-modal ID, trigger the jQuery click handler
       and capture the JSON response (which contains the modal HTML)
    4. Parse detail URLs from the modal HTML fragments
    """
    logger.info("Browser-based discovery for %s", url)
    detail_urls: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        # Collect modal AJAX responses as they arrive
        modal_htmls: list[str] = []

        async def on_response(resp) -> None:
            if "eventDetailsModal" not in resp.url:
                return
            try:
                body = await resp.text()
                # Response is a JSON array: [{"action":"append","id":"event-modals","value":"<HTML>"}]
                items = json.loads(body)
                for item in items:
                    if isinstance(item, dict) and "value" in item:
                        modal_htmls.append(item["value"])
            except Exception as e:
                logger.debug("Modal response parse error: %s", e)

        page.on("response", on_response)
        await page.goto(url, wait_until="networkidle", timeout=60_000)
        html = await page.content()

        # Static /details/ links (directly in page HTML)
        for link in _detail_urls_from_html(html, url):
            detail_urls.add(link)

        # Extract all event modal IDs
        event_ids = re.findall(r'data-event-modal=["\']([^"\']+)["\']', html)
        logger.info("Found %d event modal IDs", len(event_ids))

        # Trigger jQuery click on each event-modal element in batches.
        # jQuery's .trigger("click") fires the bound handler which makes the AJAX call.
        sem = asyncio.Semaphore(_AJAX_CONCURRENCY)

        async def trigger_modal(event_id: str) -> None:
            async with sem:
                try:
                    await page.evaluate(
                        '(id) => jQuery("[data-event-modal=" + JSON.stringify(id) + "]").first().trigger("click")',
                        event_id,
                    )
                    # Brief pause to allow the AJAX request to fire
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.debug("Modal trigger failed for %s: %s", event_id, e)

        await asyncio.gather(*(trigger_modal(eid) for eid in event_ids))

        # Wait for any in-flight responses to land
        await asyncio.sleep(2)
        await browser.close()

    # Parse detail URLs from all collected modal HTML fragments
    for fragment in modal_htmls:
        for link in _detail_urls_from_html(fragment, url):
            detail_urls.add(link)

    logger.info("Browser discovery found %d detail URLs", len(detail_urls))
    return list(detail_urls)
