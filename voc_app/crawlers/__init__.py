"""Crawler implementations for the Voice of Customer application."""

from .base import BaseCrawler, CrawlOutput, CrawlTarget
from .g2 import G2Crawler
from .quora import QuoraCrawler
from .reddit import RedditCrawler
from .trustpilot import TrustpilotCrawler
from .twitter import TwitterCrawler
from .youtube import YouTubeCrawler

__all__ = [
    "BaseCrawler",
    "CrawlOutput",
    "CrawlTarget",
    "G2Crawler",
    "QuoraCrawler",
    "RedditCrawler",
    "TrustpilotCrawler",
    "TwitterCrawler",
    "YouTubeCrawler",
]
