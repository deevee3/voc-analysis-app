"""Tests for the ingestion pipeline."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from voc_app.crawlers import CrawlOutput, CrawlTarget
from voc_app.models import CrawlRun, DataSource, Feedback
from voc_app.processors.cleaner import CleaningOptions
from voc_app.processors.ingestion import IngestionPipeline, run_ingestion_pipeline
from voc_app.services.storage import StorageOptions


@pytest.fixture
def mock_session():
    """Provide a mock AsyncSession."""
    session = AsyncMock()
    session.add_all = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def sample_data_source():
    """Provide a sample DataSource."""
    return DataSource(
        id=uuid.uuid4(),
        name="test_source",
        platform="reddit",
        is_active=True,
    )


@pytest.fixture
def sample_crawl_run(sample_data_source):
    """Provide a sample CrawlRun."""
    return CrawlRun(
        id=uuid.uuid4(),
        data_source_id=sample_data_source.id,
        started_at=datetime.utcnow(),
        status="completed",
    )


@pytest.fixture
def sample_crawl_outputs():
    """Provide sample CrawlOutput records."""
    mock_result = MagicMock()
    mock_result.html = "Sample HTML content with enough characters to pass validation rules"
    mock_result.success = True
    mock_result.metadata = {"source": "test"}

    target = CrawlTarget(url="https://example.com/post/1", metadata={"id": "post_1"})
    output = CrawlOutput(
        target=target,
        raw=mock_result,
        cleaned_html="Cleaned HTML content",
        markdown="# Sample Markdown",
    )
    return [output]


class TestIngestionPipeline:
    """Test suite for IngestionPipeline."""

    @pytest.mark.asyncio
    async def test_ingest_processes_valid_outputs(
        self, mock_session, sample_data_source, sample_crawl_run, sample_crawl_outputs
    ):
        """Valid outputs should be processed and stored."""
        pipeline = IngestionPipeline(
            mock_session,
            cleaning_options=CleaningOptions(min_characters=10, deduplicate=False),
            storage_options=StorageOptions(store_files=False),
        )

        # Mock storage service to return feedback records
        mock_feedback = Feedback(
            id=uuid.uuid4(),
            data_source_id=sample_data_source.id,
            crawl_run_id=sample_crawl_run.id,
            raw_content="content",
            url="https://example.com/post/1",
        )
        pipeline.storage_service.persist_outputs = AsyncMock(return_value=[mock_feedback])

        result = await pipeline.ingest(
            data_source=sample_data_source,
            crawl_run=sample_crawl_run,
            outputs=sample_crawl_outputs,
        )

        assert len(result.stored_feedback_ids) == 1
        assert result.cleaning_summary.records is not None

    @pytest.mark.asyncio
    async def test_ingest_filters_duplicates(
        self, mock_session, sample_data_source, sample_crawl_run
    ):
        """Duplicate outputs should be filtered out."""
        mock_result = MagicMock()
        mock_result.html = "Identical content here with enough text to pass min length check"
        mock_result.success = True
        mock_result.metadata = {}

        outputs = [
            CrawlOutput(
                target=CrawlTarget(url="https://example.com/1", metadata={}),
                raw=mock_result,
                cleaned_html=mock_result.html,
                markdown=None,
            ),
            CrawlOutput(
                target=CrawlTarget(url="https://example.com/2", metadata={}),
                raw=mock_result,
                cleaned_html=mock_result.html,
                markdown=None,
            ),
        ]

        pipeline = IngestionPipeline(
            mock_session,
            cleaning_options=CleaningOptions(deduplicate=True, min_characters=20),
            storage_options=StorageOptions(store_files=False),
        )
        pipeline.storage_service.persist_outputs = AsyncMock(return_value=[])

        result = await pipeline.ingest(
            data_source=sample_data_source,
            crawl_run=sample_crawl_run,
            outputs=outputs,
        )

        assert len(result.cleaning_summary.duplicates) > 0

    @pytest.mark.asyncio
    async def test_ingest_discards_short_content(
        self, mock_session, sample_data_source, sample_crawl_run
    ):
        """Content below min_characters should be discarded."""
        mock_result = MagicMock()
        mock_result.html = "Short"
        mock_result.success = True
        mock_result.metadata = {}

        outputs = [
            CrawlOutput(
                target=CrawlTarget(url="https://example.com/short", metadata={}),
                raw=mock_result,
                cleaned_html=mock_result.html,
                markdown=None,
            )
        ]

        pipeline = IngestionPipeline(
            mock_session,
            cleaning_options=CleaningOptions(min_characters=50, deduplicate=False),
            storage_options=StorageOptions(store_files=False),
        )

        result = await pipeline.ingest(
            data_source=sample_data_source,
            crawl_run=sample_crawl_run,
            outputs=outputs,
        )

        assert len(result.stored_feedback_ids) == 0
        assert len(result.cleaning_summary.discarded) > 0

    @pytest.mark.asyncio
    async def test_convenience_helper(
        self, mock_session, sample_data_source, sample_crawl_run, sample_crawl_outputs
    ):
        """Test module-level helper function."""
        # Mock the IngestionPipeline.ingest method
        mock_feedback = Feedback(
            id=uuid.uuid4(),
            data_source_id=sample_data_source.id,
            crawl_run_id=sample_crawl_run.id,
            raw_content="content",
            url="https://example.com/post/1",
        )

        # Patch persist_outputs at module level
        import voc_app.services.storage as storage_module

        original_persist = storage_module.CrawlStorageService.persist_outputs
        storage_module.CrawlStorageService.persist_outputs = AsyncMock(return_value=[mock_feedback])

        try:
            result = await run_ingestion_pipeline(
                mock_session,
                data_source=sample_data_source,
                crawl_run=sample_crawl_run,
                outputs=sample_crawl_outputs,
            )

            assert result.stored_feedback_ids is not None
        finally:
            storage_module.CrawlStorageService.persist_outputs = original_persist
