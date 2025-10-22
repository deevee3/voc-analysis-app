"""Tests for YouTube, Trustpilot, Quora, and G2 crawlers."""

import pytest

from voc_app.crawlers import G2Crawler, QuoraCrawler, TrustpilotCrawler, YouTubeCrawler
from voc_app.crawlers.base import CrawlTarget


class TestYouTubeCrawler:
    """Test suite for YouTubeCrawler."""

    def test_crawler_initialization_with_video_id(self):
        """Test YouTubeCrawler initializes with video ID."""
        crawler = YouTubeCrawler(video_id="dQw4w9WgXcQ")
        assert crawler.name == "youtube"
        assert crawler.video_id == "dQw4w9WgXcQ"

    def test_crawler_initialization_with_channel_id(self):
        """Test YouTubeCrawler initializes with channel ID."""
        crawler = YouTubeCrawler(channel_id="TestChannel")
        assert crawler.channel_id == "TestChannel"

    def test_build_video_target(self):
        """Test building target for a specific video."""
        target = YouTubeCrawler.build_video_target("test_video_123")
        assert "youtube.com/watch?v=test_video_123" in target.url
        assert target.metadata["video_id"] == "test_video_123"

    def test_build_targets_from_video_ids(self):
        """Test building multiple video targets."""
        video_ids = ["video1", "video2", "video3"]
        targets = YouTubeCrawler.build_targets_from_video_ids(video_ids)

        assert len(targets) == 3
        assert all("youtube.com/watch" in t.url for t in targets)

    def test_build_listing_target_with_video_id(self):
        """Test listing target for video."""
        crawler = YouTubeCrawler(video_id="test123")
        target = crawler.build_listing_target()
        assert "test123" in target.url

    def test_build_listing_target_with_channel_id(self):
        """Test listing target for channel."""
        crawler = YouTubeCrawler(channel_id="TestChannel")
        target = crawler.build_listing_target()
        assert "TestChannel" in target.url
        assert "community" in target.url

    def test_build_listing_target_raises_without_id(self):
        """Test error when neither video nor channel ID provided."""
        crawler = YouTubeCrawler()
        with pytest.raises(ValueError, match="requires either video_id or channel_id"):
            crawler.build_listing_target()


class TestTrustpilotCrawler:
    """Test suite for TrustpilotCrawler."""

    def test_crawler_initialization(self):
        """Test TrustpilotCrawler initialization."""
        crawler = TrustpilotCrawler(company_name="Test Company")
        assert crawler.name == "trustpilot"
        assert crawler.company_name == "Test Company"

    def test_build_listing_target(self):
        """Test building company review target."""
        crawler = TrustpilotCrawler(company_name="Test Company")
        target = crawler.build_listing_target()

        assert "trustpilot.com/review" in target.url
        assert "test-company" in target.url
        assert target.metadata["company_name"] == "Test Company"

    def test_build_listing_target_with_stars_filter(self):
        """Test building target with star rating filter."""
        crawler = TrustpilotCrawler(company_name="Test Company", stars_filter="5")
        target = crawler.build_listing_target()

        assert "stars=5" in target.url

    def test_build_targets_from_companies(self):
        """Test building multiple company targets."""
        companies = ["Company A", "Company B", "Company C"]
        targets = TrustpilotCrawler.build_targets_from_companies(companies)

        assert len(targets) == 3
        assert all("trustpilot.com/review" in t.url for t in targets)

    def test_build_targets_with_stars_filter(self):
        """Test building targets with star filter."""
        companies = ["Company A"]
        targets = TrustpilotCrawler.build_targets_from_companies(companies, stars_filter="4")

        assert "stars=4" in targets[0].url


class TestQuoraCrawler:
    """Test suite for QuoraCrawler."""

    def test_crawler_initialization_with_query(self):
        """Test QuoraCrawler initialization with query."""
        crawler = QuoraCrawler(query="Test Query")
        assert crawler.name == "quora"
        assert crawler.query == "Test Query"

    def test_crawler_initialization_with_topic(self):
        """Test QuoraCrawler initialization with topic."""
        crawler = QuoraCrawler(topic="Technology")
        assert crawler.topic == "Technology"

    def test_build_search_target(self):
        """Test building search target."""
        target = QuoraCrawler.build_search_target("test query")
        assert "quora.com/search" in target.url
        assert target.metadata["query"] == "test query"
        assert target.query == "test query"

    def test_build_targets_from_queries(self):
        """Test building multiple search targets."""
        queries = ["query1", "query2", "query3"]
        targets = QuoraCrawler.build_targets_from_queries(queries)

        assert len(targets) == 3
        assert all("quora.com/search" in t.url for t in targets)

    def test_build_listing_target_with_query(self):
        """Test listing target with search query."""
        crawler = QuoraCrawler(query="test")
        target = crawler.build_listing_target()
        assert "search" in target.url

    def test_build_listing_target_with_topic(self):
        """Test listing target with topic."""
        crawler = QuoraCrawler(topic="Technology")
        target = crawler.build_listing_target()
        assert "topic" in target.url
        assert "Technology" in target.url

    def test_build_listing_target_raises_without_query_or_topic(self):
        """Test error when neither query nor topic provided."""
        crawler = QuoraCrawler()
        with pytest.raises(ValueError, match="requires either query or topic"):
            crawler.build_listing_target()


class TestG2Crawler:
    """Test suite for G2Crawler."""

    def test_crawler_initialization(self):
        """Test G2Crawler initialization."""
        crawler = G2Crawler(product_slug="test-product")
        assert crawler.name == "g2"
        assert crawler.product_slug == "test-product"

    def test_build_listing_target(self):
        """Test building product review target."""
        crawler = G2Crawler(product_slug="test-product")
        target = crawler.build_listing_target()

        assert "g2.com/products/test-product/reviews" in target.url
        assert target.metadata["product_slug"] == "test-product"

    def test_build_listing_target_with_rating_filter(self):
        """Test building target with rating filter."""
        crawler = G2Crawler(product_slug="test-product", rating_filter="5")
        target = crawler.build_listing_target()

        assert "filters[star_rating]=5" in target.url

    def test_build_listing_target_with_sort(self):
        """Test building target with sort parameter."""
        crawler = G2Crawler(product_slug="test-product", sort="highest_rating")
        target = crawler.build_listing_target()

        assert "order=highest_rating" in target.url

    def test_build_targets_from_products(self):
        """Test building multiple product targets."""
        product_slugs = ["product-a", "product-b", "product-c"]
        targets = G2Crawler.build_targets_from_products(product_slugs)

        assert len(targets) == 3
        assert all("g2.com/products" in t.url for t in targets)

    def test_build_targets_with_rating_filter(self):
        """Test building targets with rating filter."""
        product_slugs = ["product-a"]
        targets = G2Crawler.build_targets_from_products(product_slugs, rating_filter="4")

        assert "filters[star_rating]=4" in targets[0].url


class TestCrawlerIntegration:
    """Integration tests for new crawlers."""

    def test_all_crawlers_extend_base(self):
        """Verify all crawlers properly extend BaseCrawler."""
        from voc_app.crawlers.base import BaseCrawler

        assert issubclass(YouTubeCrawler, BaseCrawler)
        assert issubclass(TrustpilotCrawler, BaseCrawler)
        assert issubclass(QuoraCrawler, BaseCrawler)
        assert issubclass(G2Crawler, BaseCrawler)

    def test_all_crawlers_have_unique_names(self):
        """Verify each crawler has a unique identifier."""
        crawlers = [
            YouTubeCrawler(video_id="test"),
            TrustpilotCrawler(company_name="test"),
            QuoraCrawler(query="test"),
            G2Crawler(product_slug="test"),
        ]

        names = [c.name for c in crawlers]
        assert len(names) == len(set(names))  # All unique

    def test_all_crawlers_support_browser_config(self):
        """Verify all crawlers provide browser configuration."""
        crawlers = [
            YouTubeCrawler(video_id="test"),
            TrustpilotCrawler(company_name="test"),
            QuoraCrawler(query="test"),
            G2Crawler(product_slug="test"),
        ]

        for crawler in crawlers:
            config = crawler.get_browser_config()
            assert config is not None
            assert hasattr(config, "headless")
