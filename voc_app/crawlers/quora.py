"""Quora crawler for questions and answers."""

from __future__ import annotations

import json
from typing import Any, Iterable
from urllib.parse import quote_plus

from crawl4ai import BrowserConfig, CacheMode, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.utils import optimize_html

from .base import BaseCrawler, CrawlOutput, CrawlTarget


class QuoraCrawler(BaseCrawler):
    """Collects questions and answers from Quora."""

    name = "quora"

    def __init__(
        self,
        *,
        query: str | None = None,
        topic: str | None = None,
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
        self.topic = topic

    def get_browser_config(self) -> BrowserConfig:
        return BrowserConfig(headless=self.headless, java_script_enabled=True)

    async def build_run_config_overrides(self, target: CrawlTarget) -> dict[str, Any]:
        schema = {
            "baseSelector": "div[class*='Answer']",
            "fields": [
                {"name": "question", "selector": "div.q-box span.q-text", "type": "text"},
                {"name": "author", "selector": "a.author_info span.author_name", "type": "text"},
                {"name": "answer_text", "selector": "div.q-text span.q-box", "type": "text"},
                {"name": "upvotes", "selector": "button[aria-label*='upvote'] span", "type": "text"},
                {"name": "timestamp", "selector": "a.answer_permalink span", "type": "text"},
            ],
        }

        extraction_strategy = JsonCssExtractionStrategy(schema)

        # JavaScript to expand answers
        js_expand = """
        (async () => {
            await new Promise(resolve => setTimeout(resolve, 2000));
            const moreButtons = document.querySelectorAll('button[aria-label*="more"]');
            moreButtons.forEach(btn => btn.click());
            await new Promise(resolve => setTimeout(resolve, 1000));
        })();
        """

        return {
            "extraction_strategy": extraction_strategy,
            "js_code": js_expand,
            "page_timeout": 60000,
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
            "topic": self.topic,
            "results": extracted_json,
        }

        enriched_result = result.model_copy(update={"metadata": payload, "cleaned_html": cleaned_html})
        return CrawlOutput(target=target, raw=enriched_result, cleaned_html=cleaned_html, markdown=markdown)

    def build_listing_target(self) -> CrawlTarget:
        """Build target for Quora search or topic."""
        if self.query:
            return self.build_search_target(self.query)
        elif self.topic:
            url = f"https://www.quora.com/topic/{self.topic.replace(' ', '-')}"
            return CrawlTarget(url=url, metadata={"topic": self.topic})
        else:
            raise ValueError("QuoraCrawler requires either query or topic")

    @classmethod
    def build_search_target(cls, query: str) -> CrawlTarget:
        """Build target for Quora search."""
        encoded_query = quote_plus(query)
        url = f"https://www.quora.com/search?q={encoded_query}"
        return CrawlTarget(url=url, metadata={"query": query}, query=query)

    @classmethod
    def build_targets_from_queries(cls, queries: Iterable[str]) -> list[CrawlTarget]:
        """Build targets from multiple search queries."""
        return [cls.build_search_target(query) for query in queries]
