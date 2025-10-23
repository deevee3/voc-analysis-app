"""YouTube crawler for video comments and community posts."""

from __future__ import annotations

import json
from typing import Any, Iterable

from crawl4ai import BrowserConfig, CacheMode, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai.utils import optimize_html

from .base import BaseCrawler, CrawlOutput, CrawlTarget


class YouTubeCrawler(BaseCrawler):
    """Collects comments and community feedback from YouTube videos."""

    name = "youtube"

    def __init__(
        self,
        *,
        video_id: str | None = None,
        channel_id: str | None = None,
        sort_by: str = "top",
        cache_mode: CacheMode = CacheMode.BYPASS,
        headless: bool = True,
        concurrent_tasks: int = 2,
    ) -> None:
        super().__init__(
            cache_mode=cache_mode,
            headless=headless,
            concurrent_tasks=concurrent_tasks,
        )
        self.video_id = video_id
        self.channel_id = channel_id
        self.sort_by = sort_by

    def get_browser_config(self) -> BrowserConfig:
        return BrowserConfig(headless=self.headless, java_script_enabled=True)

    async def build_run_config_overrides(self, target: CrawlTarget) -> dict[str, Any]:
        schema = {
            "baseSelector": "ytd-comment-thread-renderer",
            "fields": [
                {"name": "author", "selector": "a#author-text span", "type": "text"},
                {"name": "comment_text", "selector": "yt-formatted-string#content-text", "type": "text"},
                {"name": "timestamp", "selector": "a.yt-simple-endpoint span", "type": "text"},
                {"name": "likes", "selector": "span#vote-count-middle", "type": "text"},
                {"name": "reply_count", "selector": "yt-formatted-string.more-button", "type": "text"},
            ],
        }

        extraction_strategy = JsonCssExtractionStrategy(schema)

        # JavaScript to expand comments
        js_expand_comments = """
        (async () => {
            await new Promise(resolve => setTimeout(resolve, 2000));
            const commentsSection = document.querySelector('ytd-comments#comments');
            if (commentsSection) {
                commentsSection.scrollIntoView();
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        })();
        """

        return {
            "extraction_strategy": extraction_strategy,
            "js_code": js_expand_comments,
            "wait_for": "ytd-comment-thread-renderer",
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
            "video_id": target.metadata.get("video_id") or self.video_id,
            "channel_id": target.metadata.get("channel_id") or self.channel_id,
            "sort_by": self.sort_by,
            "results": extracted_json,
        }

        enriched_result = result.model_copy(update={"metadata": payload, "cleaned_html": cleaned_html})
        return CrawlOutput(target=target, raw=enriched_result, cleaned_html=cleaned_html, markdown=markdown)

    @classmethod
    def build_video_target(cls, video_id: str) -> CrawlTarget:
        """Build target for a specific YouTube video."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        return CrawlTarget(url=url, metadata={"video_id": video_id})

    @classmethod
    def build_targets_from_video_ids(cls, video_ids: Iterable[str]) -> list[CrawlTarget]:
        """Build targets from multiple video IDs."""
        return [cls.build_video_target(video_id) for video_id in video_ids]

    def build_listing_target(self) -> CrawlTarget:
        """Build target for channel or video comments."""
        if self.video_id:
            return self.build_video_target(self.video_id)
        elif self.channel_id:
            url = f"https://www.youtube.com/@{self.channel_id}/community"
            return CrawlTarget(url=url, metadata={"channel_id": self.channel_id})
        else:
            raise ValueError("YouTubeCrawler requires either video_id or channel_id")
