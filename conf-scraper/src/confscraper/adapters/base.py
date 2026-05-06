from __future__ import annotations

from abc import ABC, abstractmethod

from confscraper.models import Paper


class Adapter(ABC):
    @abstractmethod
    async def discover_papers(self, track_url: str) -> list[str]:
        """Return absolute paper-detail URLs found on the track listing page."""

    @abstractmethod
    def parse_paper(self, url: str, html: str) -> Paper:
        """Parse a paper detail page and return a Paper model."""

    @abstractmethod
    async def discover_tracks(self, conference_slug: str) -> list[str]:
        """Return track URLs for a conference home page (auto-discovery)."""
