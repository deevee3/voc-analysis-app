"""Twitter/X crawler leveraging Crawl4AI search pages."""

from __future__ import annotations

import json
from typing import Any, Iterable
from urllib.parse import quote_plus

from crawl4ai import BrowserConfig, CacheMode, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.utils import optimize_html

from .base import BaseCrawler, CrawlOutput, CrawlTarget


class TwitterCrawler(BaseCrawler):
    """Collects public tweets for configured queries while retaining metadata."""

    name = "twitter"

    def __init__(
        self,
        *,
        query: str | None = None,
        language: str | None = "en",
        result_type: str = "latest",
        cache_mode: CacheMode = CacheMode.BYPASS,
        headless: bool = True,
        concurrent_tasks: int = 2,
    ) -> None:
        super().__init__(
            cache_mode=cache_mode,
            headless=headless,
            concurrent_tasks=concurrent_tasks,
        )
        self.query = query
        self.language = language
        self.result_type = result_type

    def get_browser_config(self) -> BrowserConfig:
        return BrowserConfig(headless=self.headless, java_script_enabled=True)

    async def build_run_config_overrides(self, target: CrawlTarget) -> dict[str, Any]:
        schema = {
            "tweet_url": "a[href*='/status/']::attr(href)",
            "author_name": "div[data-testid='User-Name'] span:first-child",
            "author_handle": "div[data-testid='User-Name'] span:nth-child(2)",
            "timestamp": "time::attr(datetime)",
            "content": "div[data-testid='tweetText']",
            "metrics": {
                "replies": "div[data-testid='reply'] span",
                "retweets": "div[data-testid='retweet'] span",
                "likes": "div[data-testid='like'] span",
            },
        }
        extraction_strategy = JsonCssExtractionStrategy(schema)
        filters: dict[str, Any] = {}
        if self.language:
            filters["lang"] = self.language

        return {
            "cache_mode": self.cache_mode,
            "css_selector": "article[data-testid='tweet']",
            "extraction_strategy": extraction_strategy,
            "keep_data_attributes": True,
            "keep_attrs": ["data-testid", "href"],
            "filters": filters,
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
            "query": target.query or self.query,
            "language": self.language,
            "result_type": self.result_type,
            "results": extracted_json,
        }
        enriched_result = result.model_copy(update={"metadata": payload, "cleaned_html": cleaned_html})
        return CrawlOutput(target=target, raw=enriched_result, cleaned_html=cleaned_html, markdown=markdown)

    def build_listing_target(self) -> CrawlTarget:
        if not self.query:
            raise ValueError("TwitterCrawler requires a search query for listing target.")
        return self.build_search_target(self.query)

    @classmethod
    def build_search_target(cls, query: str, *, result_type: str = "latest") -> CrawlTarget:
        return CrawlTarget(url=cls._build_search_url(query, result_type=result_type), metadata={"query": query})

    @classmethod
    def build_targets_from_queries(
        cls, queries: Iterable[str], *, result_type: str = "latest"
    ) -> list[CrawlTarget]:
        return [cls.build_search_target(query, result_type=result_type) for query in queries]

    @staticmethod
    def _build_search_url(query: str, *, result_type: str = "latest") -> str:
        encoded_query = quote_plus(query)
        url = f"https://twitter.com/search?q={encoded_query}&src=typed_query"
        if result_type == "latest":
            url = f"{url}&f=live"
        elif result_type == "top":
            url = f"{url}&f=top"
        return url
