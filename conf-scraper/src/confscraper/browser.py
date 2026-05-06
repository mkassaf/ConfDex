from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Page

from confscraper import __version__

logger = logging.getLogger(__name__)

USER_AGENT = f"confscraper/{__version__} (+github.com/mkassaf/conf-scraper)"


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


async def discover_papers_via_browser(url: str) -> list[str]:
    """
    For JS-heavy pages (home/program pages), use a headless browser to:
    1. Render the page fully
    2. Collect all visible /details/ links
    3. Click each event-modal trigger, capture AJAX-loaded detail URLs from modals
    """
    logger.info("Browser-based discovery for %s", url)
    detail_urls: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        # Intercept navigation and AJAX responses to harvest detail URLs
        async def on_response(response):
            try:
                ct = response.headers.get("content-type", "")
                if "html" in ct:
                    body = await response.text()
                    for m in re.finditer(r'/details/[^\s"\'<>]+/\d+[^\s"\'<>]*', body):
                        detail_urls.add(urljoin(url, m.group()))
            except Exception:
                pass

        page.on("response", on_response)

        await page.goto(url, wait_until="networkidle", timeout=60_000)

        # Collect static detail links first
        static_links = await page.eval_on_selector_all(
            "a[href*='/details/']",
            "els => els.map(e => e.href)"
        )
        for link in static_links:
            if re.search(r'/details/[^/]+/[^/]+/\d+', link):
                detail_urls.add(link)

        # Click each event-modal trigger to load AJAX content
        modal_triggers = await page.query_selector_all("a[data-event-modal]")
        logger.info("Found %d event modal triggers to click", len(modal_triggers))

        for i, trigger in enumerate(modal_triggers):
            try:
                await trigger.click()
                # Wait for modal to appear and potentially load detail URL
                await asyncio.sleep(0.5)
                # Collect any new detail links in the modal
                modal_links = await page.eval_on_selector_all(
                    ".modal a[href*='/details/'], #hidden-modal a[href*='/details/'], [id*='modal'] a[href*='/details/']",
                    "els => els.map(e => e.href)"
                )
                for link in modal_links:
                    if re.search(r'/details/[^/]+/[^/]+/\d+', link):
                        detail_urls.add(link)
                # Close modal if open
                try:
                    close_btn = await page.query_selector(".modal.in .close, .modal.show .close")
                    if close_btn:
                        await close_btn.click()
                        await asyncio.sleep(0.2)
                except Exception:
                    # Dismiss with Escape
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.2)
            except Exception as e:
                logger.debug("Modal click %d failed: %s", i, e)

        await browser.close()

    logger.info("Browser discovery found %d detail URLs", len(detail_urls))
    return list(detail_urls)
