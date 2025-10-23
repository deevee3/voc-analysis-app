import json

import pytest

from crawl4ai.models import CrawlResult

from voc_app.crawlers.base import CrawlTarget
from voc_app.crawlers.reddit import RedditCrawler


@pytest.mark.asyncio
async def test_process_result_normalizes_posts():
    crawler = RedditCrawler(subreddit="technology")
    target = CrawlTarget(url="https://old.reddit.com/r/technology/", metadata={})

    extracted_items = [
        {
            "title": "AI beats expectations",
            "author": "u/tester",
            "permalink": "/r/technology/comments/abc123/ai_beats_expectations/",
            "score": "1.2k",
            "num_comments": "345",
            "subreddit": "technology",
            "domain": "example.com",
        },
        {
            "title": "",
            "author": "u/ignored",
        },
    ]

    crawl_result = CrawlResult(
        url=target.url,
        html="<html></html>",
        success=True,
        cleaned_html="",
        extracted_content=json.dumps(extracted_items),
        metadata={},
    )

    output = await crawler.process_result(target, crawl_result)

    assert output.cleaned_html.startswith("Post #1: AI beats expectations")
    assert "URL: https://www.reddit.com/r/technology/comments/abc123/ai_beats_expectations/" in output.cleaned_html

    metadata = output.raw.metadata
    assert metadata["post_count"] == 1
    assert len(metadata["results"]) == 1
    assert metadata["results"][0]["title"] == "AI beats expectations"
    assert metadata["results"][0]["permalink"].startswith("https://www.reddit.com/")

    extracted = json.loads(output.raw.extracted_content)
    assert extracted[0]["title"] == "AI beats expectations"
