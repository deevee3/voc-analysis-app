"""Shared crawling abstractions for the Voice of Customer pipeline."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Sequence

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.models import CrawlResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CrawlTarget:
    """Information required to crawl a single resource."""

    url: str
    metadata: dict[str, Any] = field(default_factory=dict)
    query: Optional[str] = None


@dataclass(slots=True)
class CrawlOutput:
    """Normalized crawl response used by downstream processors."""

    target: CrawlTarget
    raw: CrawlResult
    cleaned_html: Optional[str]
    markdown: Optional[str]


class BaseCrawler(ABC):
    """Abstract base class wrapping Crawl4AI usage for platform-specific crawlers."""

    name: str = "base"

    def __init__(
        self,
        *,
        cache_mode: CacheMode = CacheMode.BYPASS,
        headless: bool = True,
        concurrent_tasks: int = 2,
    ) -> None:
        self.cache_mode = cache_mode
        self.headless = headless
        self.concurrent_tasks = max(concurrent_tasks, 1)

    async def crawl_many(self, targets: Sequence[CrawlTarget]) -> list[CrawlOutput]:
        """Crawl many targets sequentially or concurrently depending on configuration."""

        if not targets:
            return []

        browser_config = self.get_browser_config()

        async with AsyncWebCrawler(config=browser_config) as crawler:
            semaphore = asyncio.Semaphore(self.concurrent_tasks)

            async def _run(target: CrawlTarget) -> CrawlOutput:
                async with semaphore:
                    return await self._crawl_target(crawler, target)

            tasks = [asyncio.create_task(_run(target)) for target in targets]
            results: list[CrawlOutput] = []
            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception("Crawler %s failed: %s", self.name, exc)
                    continue
                results.append(result)
            return results

    async def crawl_one(self, target: CrawlTarget) -> CrawlOutput:
        """Convenience wrapper for single target crawl."""

        browser_config = self.get_browser_config()
        async with AsyncWebCrawler(config=browser_config) as crawler:
            return await self._crawl_target(crawler, target)

    async def _crawl_target(
        self, crawler: AsyncWebCrawler, target: CrawlTarget
    ) -> CrawlOutput:
        run_config = await self.get_run_config(target)
        logger.debug(
            "Running %s crawler for %s with config %s", self.name, target.url, run_config
        )
        result = await crawler.arun(url=target.url, config=run_config)
        logger.debug(
            "Crawler %s completed %s - success=%s", self.name, target.url, result.success
        )
        return await self.process_result(target, result)

    async def get_run_config(self, target: CrawlTarget) -> CrawlerRunConfig:
        """Build the Crawl4AI run configuration for a target."""

        overrides = await self.build_run_config_overrides(target)
        if "cache_mode" in overrides:
            return CrawlerRunConfig(**overrides)
        return CrawlerRunConfig(cache_mode=self.cache_mode, **overrides)

    async def build_run_config_overrides(self, target: CrawlTarget) -> dict[str, Any]:
        """Hook for subclasses to customize run configuration attributes."""

        return {}

    def get_browser_config(self) -> BrowserConfig:
        """Return the browser configuration used for the crawler."""

        return BrowserConfig(headless=self.headless)

    @abstractmethod
    async def process_result(self, target: CrawlTarget, result: CrawlResult) -> CrawlOutput:
        """Convert a Crawl4AI result into the shared `CrawlOutput` structure."""

    @staticmethod
    def build_targets(urls: Iterable[str], **metadata: Any) -> list[CrawlTarget]:
        """Helper to build targets from bare URLs with shared metadata."""

        return [CrawlTarget(url=url, metadata=dict(metadata)) for url in urls]
