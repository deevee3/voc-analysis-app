"""G2 crawler for software reviews."""

from __future__ import annotations

import json
from typing import Any, Iterable

from crawl4ai import BrowserConfig, CacheMode, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.utils import optimize_html

from .base import BaseCrawler, CrawlOutput, CrawlTarget


class G2Crawler(BaseCrawler):
    """Collects software reviews from G2."""

    name = "g2"

    def __init__(
        self,
        *,
        product_slug: str,
        rating_filter: str | None = None,
        sort: str = "most_recent",
        cache_mode: CacheMode = CacheMode.BYPASS,
        headless: bool = True,
        concurrent_tasks: int = 2,
    ) -> None:
        super().__init__(
            cache_mode=cache_mode,
            headless=headless,
            concurrent_tasks=concurrent_tasks,
        )
        self.product_slug = product_slug
        self.rating_filter = rating_filter
        self.sort = sort

    def get_browser_config(self) -> BrowserConfig:
        return BrowserConfig(headless=self.headless, java_script_enabled=True)

    async def build_run_config_overrides(self, target: CrawlTarget) -> dict[str, Any]:
        schema = {
            "baseSelector": "div.paper.paper--white",
            "fields": [
                {"name": "reviewer_name", "selector": "div.reviewer-info div.name", "type": "text"},
                {"name": "reviewer_title", "selector": "div.reviewer-info div.title", "type": "text"},
                {
                    "name": "rating",
                    "selector": "div.stars-container div.star",
                    "type": "attribute",
                    "attribute": "class",
                },
                {"name": "review_title", "selector": "h3.review-title", "type": "text"},
                {"name": "review_text", "selector": "div.review-text", "type": "text"},
                {"name": "pros", "selector": "div[itemprop='reviewBody'] div.pros", "type": "text"},
                {"name": "cons", "selector": "div[itemprop='reviewBody'] div.cons", "type": "text"},
                {"name": "date", "selector": "time", "type": "attribute", "attribute": "datetime"},
                {"name": "verified", "selector": "div.badge-verified", "type": "text"},
            ],
        }

        extraction_strategy = JsonCssExtractionStrategy(schema)

        # JavaScript to expand review text
        js_expand = """
        (async () => {
            await new Promise(resolve => setTimeout(resolve, 2000));
            const expandButtons = document.querySelectorAll('a[data-track="review-show-more"]');
            expandButtons.forEach(btn => btn.click());
            await new Promise(resolve => setTimeout(resolve, 1000));
        })();
        """

        return {
            "extraction_strategy": extraction_strategy,
            "js_code": js_expand,
            "page_timeout": 60000,
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
            "product_slug": self.product_slug,
            "rating_filter": self.rating_filter,
            "sort": self.sort,
            "results": extracted_json,
        }

        enriched_result = result.model_copy(update={"metadata": payload, "cleaned_html": cleaned_html})
        return CrawlOutput(target=target, raw=enriched_result, cleaned_html=cleaned_html, markdown=markdown)

    def build_listing_target(self) -> CrawlTarget:
        """Build target for product review listing."""
        url = f"https://www.g2.com/products/{self.product_slug}/reviews"

        query_params = []
        if self.rating_filter:
            query_params.append(f"filters[star_rating]={self.rating_filter}")
        if self.sort:
            query_params.append(f"order={self.sort}")

        if query_params:
            url = f"{url}?{'&'.join(query_params)}"

        return CrawlTarget(url=url, metadata={"product_slug": self.product_slug})

    @classmethod
    def build_targets_from_products(
        cls, product_slugs: Iterable[str], *, rating_filter: str | None = None
    ) -> list[CrawlTarget]:
        """Build targets from multiple product slugs."""
        targets = []
        for slug in product_slugs:
            url = f"https://www.g2.com/products/{slug}/reviews"
            if rating_filter:
                url = f"{url}?filters[star_rating]={rating_filter}"
            targets.append(CrawlTarget(url=url, metadata={"product_slug": slug}))
        return targets
