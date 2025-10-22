"""Tests for Celery background tasks."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from voc_app.models import AlertEvent, AlertRule, CrawlRun, DataSource, Feedback, Insight


class TestCrawlTasks:
    """Test suite for crawl tasks."""

    @pytest.mark.asyncio
    async def test_execute_crawl_creates_crawl_run(self):
        """Test that execute_crawl creates a CrawlRun record."""
        from voc_app.tasks.crawl_tasks import _execute_crawl_async

        data_source_id = str(uuid.uuid4())

        with patch("voc_app.tasks.crawl_tasks._SessionFactory") as MockSession, \
             patch("voc_app.tasks.crawl_tasks._get_crawler") as mock_get_crawler:
            
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session

            # Mock data source
            mock_data_source = DataSource(
                id=data_source_id,
                name="test_source",
                platform="reddit",
                is_active=True,
                config={"subreddit": "test"},
            )
            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_data_source

            # Mock crawler
            mock_crawler = MagicMock()
            mock_crawler.build_listing_target.return_value = MagicMock()
            mock_crawler.crawl_many = AsyncMock(return_value=[])
            mock_get_crawler.return_value = mock_crawler

            # Mock ingestion
            with patch("voc_app.tasks.crawl_tasks.run_ingestion_pipeline") as mock_ingest:
                mock_result = MagicMock()
                mock_result.stored_feedback_ids = []
                mock_result.cleaning_summary.duplicates = []
                mock_result.cleaning_summary.discarded = []
                mock_ingest.return_value = mock_result

                result = await _execute_crawl_async(data_source_id, None)

                assert result["success"] is True
                mock_session.add.assert_called()
                mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_execute_crawl_handles_inactive_source(self):
        """Test that inactive data sources are skipped."""
        from voc_app.tasks.crawl_tasks import _execute_crawl_async

        data_source_id = str(uuid.uuid4())

        with patch("voc_app.tasks.crawl_tasks._SessionFactory") as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session
            mock_session.execute.return_value.scalar_one_or_none.return_value = None

            result = await _execute_crawl_async(data_source_id, None)

            assert result["success"] is False
            assert "not found" in result["error"]

    def test_get_crawler_returns_correct_instance(self):
        """Test crawler instantiation for different platforms."""
        from voc_app.tasks.crawl_tasks import _get_crawler

        # Reddit
        crawler = _get_crawler("reddit", {"subreddit": "test"})
        assert crawler is not None
        assert crawler.name == "reddit"

        # Twitter
        crawler = _get_crawler("twitter", {"query": "test"})
        assert crawler is not None
        assert crawler.name == "twitter"

        # YouTube
        crawler = _get_crawler("youtube", {"video_id": "test123"})
        assert crawler is not None
        assert crawler.name == "youtube"

        # Unsupported platform
        crawler = _get_crawler("unknown", {})
        assert crawler is None


class TestProcessingTasks:
    """Test suite for processing tasks."""

    @pytest.mark.asyncio
    async def test_extract_feedback_insights_success(self):
        """Test successful insight extraction."""
        from voc_app.tasks.processing_tasks import _extract_feedback_insights_async

        feedback_ids = [str(uuid.uuid4())]

        with patch("voc_app.tasks.processing_tasks._SessionFactory") as MockSession, \
             patch("voc_app.tasks.processing_tasks.extract_insights") as mock_extract, \
             patch("voc_app.tasks.processing_tasks.persist_insights") as mock_persist:
            
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session

            # Mock feedback
            mock_feedback = Feedback(
                id=feedback_ids[0],
                data_source_id=uuid.uuid4(),
                raw_content="test content",
                posted_at=datetime.utcnow(),
            )
            mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_feedback]

            # Mock extraction summary
            mock_summary = MagicMock()
            mock_summary.success_count = 1
            mock_summary.failure_count = 0
            mock_summary.results = []
            mock_summary.total_cost.estimated_cost_usd = 0.001
            mock_extract.return_value = mock_summary

            mock_persist.return_value = []

            result = await _extract_feedback_insights_async(feedback_ids)

            assert result["success"] is True
            assert result["success_count"] == 1
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_classify_insight_themes_success(self):
        """Test successful theme classification."""
        from voc_app.tasks.processing_tasks import _classify_insight_themes_async

        insight_ids = [str(uuid.uuid4())]

        with patch("voc_app.tasks.processing_tasks._SessionFactory") as MockSession, \
             patch("voc_app.tasks.processing_tasks.classify_insights") as mock_classify:
            
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session

            # Mock insight
            mock_insight = Insight(
                id=insight_ids[0],
                feedback_id=uuid.uuid4(),
                summary="test summary",
            )
            mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_insight]

            # Mock classification results
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.matches = []
            mock_classify.return_value = [mock_result]

            result = await _classify_insight_themes_async(insight_ids)

            assert result["success"] is True
            assert result["classified_count"] >= 0


class TestAlertTasks:
    """Test suite for alert tasks."""

    def test_insight_matches_sentiment_threshold_rule(self):
        """Test sentiment threshold rule matching."""
        from voc_app.tasks.alert_tasks import _insight_matches_rule

        insight = Insight(
            id=uuid.uuid4(),
            feedback_id=uuid.uuid4(),
            summary="test",
            sentiment_score=-0.8,
        )

        rule = AlertRule(
            id=uuid.uuid4(),
            name="Negative Sentiment",
            rule_type="sentiment_threshold",
            threshold_value=-0.5,
            enabled=True,
        )

        assert _insight_matches_rule(insight, rule) is True

    def test_insight_matches_keyword_rule(self):
        """Test keyword rule matching."""
        from voc_app.tasks.alert_tasks import _insight_matches_rule

        insight = Insight(
            id=uuid.uuid4(),
            feedback_id=uuid.uuid4(),
            summary="The app crashes frequently",
        )

        rule = AlertRule(
            id=uuid.uuid4(),
            name="Crash Keywords",
            rule_type="keyword",
            keywords={"terms": ["crash", "error", "bug"]},
            enabled=True,
        )

        assert _insight_matches_rule(insight, rule) is True

    def test_calculate_severity_from_sentiment(self):
        """Test severity calculation based on sentiment."""
        from voc_app.tasks.alert_tasks import _calculate_severity

        insights = [
            Insight(id=uuid.uuid4(), feedback_id=uuid.uuid4(), summary="test", sentiment_score=-0.8),
            Insight(id=uuid.uuid4(), feedback_id=uuid.uuid4(), summary="test", sentiment_score=-0.9),
        ]

        rule = AlertRule(
            id=uuid.uuid4(),
            name="Test Rule",
            rule_type="sentiment_threshold",
            enabled=True,
        )

        severity = _calculate_severity(rule, insights)
        assert severity in ["critical", "high", "medium", "low"]

    @pytest.mark.asyncio
    async def test_evaluate_alert_rules_no_active_rules(self):
        """Test alert evaluation with no active rules."""
        from voc_app.tasks.alert_tasks import _evaluate_alert_rules_async

        with patch("voc_app.tasks.alert_tasks._SessionFactory") as MockSession:
            mock_session = AsyncMock()
            MockSession.return_value.__aenter__.return_value = mock_session
            mock_session.execute.return_value.scalars.return_value.all.return_value = []

            result = await _evaluate_alert_rules_async()

            assert result["success"] is True
            assert result["rules_evaluated"] == 0
