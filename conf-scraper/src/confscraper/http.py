from __future__ import annotations

import asyncio
import logging

import httpx
from aiolimiter import AsyncLimiter
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from confscraper import __version__

logger = logging.getLogger(__name__)

USER_AGENT = f"confscraper/{__version__} (+github.com/mkassaf/conf-scraper)"


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


def _make_retry_decorator(attempts: int = 3):
    return retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )


class RateLimitedClient:
    def __init__(
        self,
        concurrency: int = 5,
        rate: float = 5.0,
        timeout: float = 30.0,
    ):
        self._limiter = AsyncLimiter(rate, 1.0)
        self._semaphore = asyncio.Semaphore(concurrency)
        self._timeout = httpx.Timeout(timeout)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> RateLimitedClient:
        self._client = httpx.AsyncClient(
            http2=True,
            headers={"User-Agent": USER_AGENT},
            timeout=self._timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_) -> None:
        if self._client:
            await self._client.aclose()

    async def get(self, url: str) -> httpx.Response:
        assert self._client is not None, "Use inside async context manager"

        @_make_retry_decorator()
        async def _fetch() -> httpx.Response:
            async with self._semaphore:
                async with self._limiter:
                    logger.debug("GET %s", url)
                    resp = await self._client.get(url)  # type: ignore[union-attr]
                    if resp.status_code >= 500:
                        resp.raise_for_status()
                    # Honor Retry-After on 429
                    if resp.status_code == 429:
                        delay = float(resp.headers.get("Retry-After", "5"))
                        logger.warning("429 rate-limited; sleeping %.1fs", delay)
                        await asyncio.sleep(delay)
                        resp.raise_for_status()
                    return resp

        return await _fetch()
