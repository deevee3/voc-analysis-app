"""Trustpilot crawler for customer reviews."""

from __future__ import annotations

import json
from typing import Any, Iterable
from urllib.parse import quote_plus

from crawl4ai import BrowserConfig, CacheMode, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.utils import optimize_html

from .base import BaseCrawler, CrawlOutput, CrawlTarget


class TrustpilotCrawler(BaseCrawler):
    """Collects customer reviews from Trustpilot."""

    name = "trustpilot"

    def __init__(
        self,
        *,
        company_name: str,
        language: str = "en",
        stars_filter: str | None = None,
        cache_mode: CacheMode = CacheMode.BYPASS,
        headless: bool = True,
        concurrent_tasks: int = 2,
    ) -> None:
        super().__init__(
            cache_mode=cache_mode,
            headless=headless,
            concurrent_tasks=concurrent_tasks,
        )
        self.company_name = company_name
        self.language = language
        self.stars_filter = stars_filter

    def get_browser_config(self) -> BrowserConfig:
        return BrowserConfig(headless=self.headless, java_script_enabled=True)

    async def build_run_config_overrides(self, target: CrawlTarget) -> dict[str, Any]:
        schema = {
            "baseSelector": "article.review",
            "fields": [
                {"name": "reviewer_name", "selector": "div[data-consumer-name-typography] span", "type": "text"},
                {"name": "review_title", "selector": "h2[data-service-review-title-typography]", "type": "text"},
                {"name": "review_text", "selector": "p[data-service-review-text-typography]", "type": "text"},
                {
                    "name": "rating",
                    "selector": "div[data-service-review-rating] img",
                    "type": "attribute",
                    "attribute": "alt",
                },
                {"name": "date", "selector": "time", "type": "attribute", "attribute": "datetime"},
                {"name": "verified", "selector": "div[data-service-review-verification-status]", "type": "text"},
            ],
        }

        extraction_strategy = JsonCssExtractionStrategy(schema)

        return {
            "extraction_strategy": extraction_strategy,
            "keep_data_attributes": True,
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
            "company_name": self.company_name,
            "language": self.language,
            "stars_filter": self.stars_filter,
            "results": extracted_json,
        }

        enriched_result = result.model_copy(update={"metadata": payload, "cleaned_html": cleaned_html})
        return CrawlOutput(target=target, raw=enriched_result, cleaned_html=cleaned_html, markdown=markdown)

    def build_listing_target(self) -> CrawlTarget:
        """Build target for company review listing."""
        company_slug = self.company_name.lower().replace(" ", "-")
        url = f"https://www.trustpilot.com/review/{company_slug}"

        if self.stars_filter:
            url = f"{url}?stars={self.stars_filter}"

        return CrawlTarget(url=url, metadata={"company_name": self.company_name})

    @classmethod
    def build_targets_from_companies(
        cls, company_names: Iterable[str], *, stars_filter: str | None = None
    ) -> list[CrawlTarget]:
        """Build targets from multiple company names."""
        targets = []
        for company in company_names:
            company_slug = company.lower().replace(" ", "-")
            url = f"https://www.trustpilot.com/review/{company_slug}"
            if stars_filter:
                url = f"{url}?stars={stars_filter}"
            targets.append(CrawlTarget(url=url, metadata={"company_name": company}))
        return targets
