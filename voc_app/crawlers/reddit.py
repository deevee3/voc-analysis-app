"""Reddit crawler leveraging Crawl4AI for subreddit/topic monitoring."""

from __future__ import annotations

import json
from typing import Any, Iterable
from urllib.parse import urljoin

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
        return BrowserConfig(
            headless=self.headless,
            java_script_enabled=True,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )

    async def build_run_config_overrides(self, target: CrawlTarget) -> dict[str, Any]:
        raw_schema = {
            "baseSelector": "div.thing",
            "fields": [
                {"name": "title", "selector": "a.title", "type": "text"},
                {"name": "author", "selector": "a.author", "type": "text"},
                {
                    "name": "permalink",
                    "selector": "a.title",
                    "type": "attribute",
                    "attribute": "href",
                },
                {"name": "score", "selector": "div.score.unvoted", "type": "text"},
                {"name": "num_comments", "selector": "a.comments", "type": "text"},
                {"name": "subreddit", "selector": "a.subreddit", "type": "text"},
                {"name": "domain", "selector": "span.domain a", "type": "text"},
            ],
        }
        extraction_strategy = JsonCssExtractionStrategy(raw_schema)
        return {
            "extraction_strategy": extraction_strategy,
        }

    async def process_result(self, target: CrawlTarget, result) -> CrawlOutput:
        raw_html = result.cleaned_html or result.html or ""
        optimized_html = optimize_html(raw_html, threshold=50) if raw_html else ""
        markdown = None
        if result.markdown:
            markdown_attr = getattr(result.markdown, "raw_markdown", None)
            markdown = markdown_attr if isinstance(markdown_attr, str) else str(result.markdown)

        extracted_json: list[dict[str, Any]] = []
        if result.extracted_content:
            try:
                extracted_json = json.loads(result.extracted_content)
            except (TypeError, json.JSONDecodeError):
                extracted_json = []

        posts: list[dict[str, Any]] = []
        for item in extracted_json:
            title = (item or {}).get("title")
            if not title:
                continue

            permalink = item.get("permalink")
            if permalink:
                permalink = urljoin("https://www.reddit.com", permalink)

            post_payload = {
                "title": title.strip(),
                "author": (item.get("author") or "").strip() or None,
                "permalink": permalink,
                "score": (item.get("score") or "").strip() or None,
                "num_comments": (item.get("num_comments") or "").strip() or None,
                "subreddit": (item.get("subreddit") or "").strip() or None,
                "domain": (item.get("domain") or "").strip() or None,
            }

            posts.append({k: v for k, v in post_payload.items() if v})

        if posts:
            posts = posts[:50]

        post_text_blocks: list[str] = []
        for index, post in enumerate(posts, start=1):
            lines = [f"Post #{index}: {post['title']}"]
            if author := post.get("author"):
                lines.append(f"Author: {author}")
            if score := post.get("score"):
                lines.append(f"Score: {score}")
            if num_comments := post.get("num_comments"):
                lines.append(f"Comments: {num_comments}")
            if subreddit := post.get("subreddit"):
                lines.append(f"Subreddit: {subreddit}")
            if domain := post.get("domain"):
                lines.append(f"Domain: {domain}")
            if permalink := post.get("permalink"):
                lines.append(f"URL: {permalink}")
            post_text_blocks.append("\n".join(lines))

        normalized_content = "\n\n".join(post_text_blocks).strip()
        if not normalized_content:
            normalized_content = optimized_html or raw_html

        final_content = normalized_content or optimized_html or raw_html

        payload = {
            "subreddit": self.subreddit,
            "sort": self.sort,
            "time_filter": self.time_filter,
            "include_comments": self.include_comments,
            "post_count": len(posts),
            "results": posts,
        }
        enriched_result = result.model_copy(
            update={
                "metadata": payload,
                "cleaned_html": final_content,
                "html": final_content,
                "extracted_content": json.dumps(posts) if posts else None,
            }
        )
        return CrawlOutput(target=target, raw=enriched_result, cleaned_html=final_content, markdown=markdown)

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
        url = f"https://old.reddit.com/r/{self.subreddit}/{self.sort}/?t={self.time_filter}"
        return CrawlTarget(url=url, metadata={"subreddit": self.subreddit, "sort": self.sort})
