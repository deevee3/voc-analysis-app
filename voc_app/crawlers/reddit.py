"""Reddit crawler leveraging Crawl4AI for subreddit/topic monitoring."""

from __future__ import annotations

import json
from typing import Any, Iterable

from crawl4ai import BrowserConfig, CacheMode, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.utils import optimize_html

from .base import BaseCrawler, CrawlOutput, CrawlTarget


class RedditCrawler(BaseCrawler):
    """Collects posts from Reddit listings while preserving citations."""

    name = "reddit"

    def __init__(
        self,
        *,
        subreddit: str,
        sort: str = "hot",
        time_filter: str = "day",
        include_comments: bool = False,
        cache_mode: CacheMode = CacheMode.BYPASS,
        headless: bool = True,
        concurrent_tasks: int = 2,
    ) -> None:
        super().__init__(
            cache_mode=cache_mode,
            headless=headless,
            concurrent_tasks=concurrent_tasks,
        )
        self.subreddit = subreddit
        self.sort = sort
        self.time_filter = time_filter
        self.include_comments = include_comments

    def get_browser_config(self) -> BrowserConfig:
        return BrowserConfig(headless=self.headless, java_script_enabled=True)

    async def build_run_config_overrides(self, target: CrawlTarget) -> dict[str, Any]:
        raw_schema = {
            "title": "article h3",
            "author": "a[href*='user']",
            "permalink": "a[data-click-id='comments']::attr(href)",
            "upvotes": "div[data-click-id='upvote']",
            "content": "div[data-test-id='post-content']",
            "posted": "a[data-click-id='timestamp']",
        }
        extraction_strategy = JsonCssExtractionStrategy(raw_schema)
        return {
            "cache_mode": self.cache_mode,
            "css_selector": "div[data-testid='post-container']",
            "extraction_strategy": extraction_strategy,
            "keep_data_attributes": True,
            "keep_attrs": ["href", "data-click-id"],
        }

    async def process_result(self, target: CrawlTarget, result) -> CrawlOutput:
        cleaned_html = optimize_html(result.cleaned_html or result.html or "", threshold=50)
        markdown = None
        if result.markdown:
            markdown_attr = getattr(result.markdown, "raw_markdown", None)
            markdown = markdown_attr if isinstance(markdown_attr, str) else str(result.markdown)

        extracted_json = []
        if result.extracted_content:
            try:
                extracted_json = json.loads(result.extracted_content)
            except (TypeError, json.JSONDecodeError):
                extracted_json = []

        payload = {
            "subreddit": self.subreddit,
            "sort": self.sort,
            "time_filter": self.time_filter,
            "include_comments": self.include_comments,
            "results": extracted_json,
        }
        enriched_result = result.model_copy(update={"metadata": payload, "cleaned_html": cleaned_html})
        return CrawlOutput(target=target, raw=enriched_result, cleaned_html=cleaned_html, markdown=markdown)

    @classmethod
    def build_targets_from_queries(
        cls, queries: Iterable[str], subreddit: str, *, base_url: str = "https://www.reddit.com"
    ) -> list[CrawlTarget]:
        return [
            CrawlTarget(
                url=f"{base_url}/r/{subreddit}/search/?q={query}&restrict_sr=1",
                metadata={"query": query},
                query=query,
            )
            for query in queries
        ]

    def build_listing_target(self) -> CrawlTarget:
        url = f"https://www.reddit.com/r/{self.subreddit}/{self.sort}/?t={self.time_filter}"
        return CrawlTarget(url=url, metadata={"subreddit": self.subreddit, "sort": self.sort})
