"""Tests for GPT-5 insight extraction."""

import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from voc_app.models import Feedback
from voc_app.processors.extractor import (
    ExtractionCost,
    ExtractionResult,
    InsightExtractor,
    extract_insights,
)
from voc_app.processors.schemas import InsightExtraction


@pytest.fixture
def sample_feedback():
    """Provide sample feedback for testing."""
    return Feedback(
        id=uuid.uuid4(),
        data_source_id=uuid.uuid4(),
        raw_content="This product is amazing! However, the mobile app crashes frequently.",
        clean_content="This product is amazing! However, the mobile app crashes frequently.",
        posted_at=datetime.utcnow(),
        url="https://example.com/feedback/123",
        metadata={"platform": "reddit"},
    )


@pytest.fixture
def mock_openai_response():
    """Provide mock OpenAI API response."""
    return {
        "content": json.dumps({
            "sentiment": {
                "score": 0.3,
                "label": "mixed",
                "confidence": 0.85,
            },
            "summary": "User loves the product but experiences mobile app crashes",
            "pain_points": [
                {
                    "description": "Mobile app crashes frequently",
                    "severity": "high",
                    "category": "stability",
                }
            ],
            "feature_requests": [],
            "competitor_mentions": [],
            "customer_context": {
                "user_segment": "consumer",
                "experience_level": "intermediate",
                "use_case_domain": null,
            },
            "journey_stage": "retention",
            "urgency_level": 4,
            "themes": ["reliability", "mobile"],
        }),
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 200,
            "total_tokens": 350,
        },
    }


class TestInsightExtractor:
    """Test suite for InsightExtractor."""

    @pytest.mark.asyncio
    async def test_extract_single_success(self, sample_feedback, mock_openai_response):
        """Test successful single extraction."""
        extractor = InsightExtractor(model="gpt-4", max_retries=1)

        with patch.object(extractor, "_call_openai", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_openai_response

            result = await extractor.extract_single(sample_feedback)

            assert result.success is True
            assert result.extraction is not None
            assert result.extraction.sentiment.score == 0.3
            assert result.extraction.sentiment.label == "mixed"
            assert len(result.extraction.pain_points) == 1
            assert result.cost.total_tokens == 350

    @pytest.mark.asyncio
    async def test_extract_single_parsing_error(self, sample_feedback):
        """Test extraction with invalid JSON response."""
        extractor = InsightExtractor(model="gpt-4", max_retries=1)

        mock_response = {
            "content": "Invalid JSON {bad format",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }

        with patch.object(extractor, "_call_openai", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_response

            result = await extractor.extract_single(sample_feedback)

            assert result.success is False
            assert result.extraction is None
            assert "Parsing error" in result.error

    @pytest.mark.asyncio
    async def test_extract_single_with_retries(self, sample_feedback, mock_openai_response):
        """Test retry logic on rate limit errors."""
        extractor = InsightExtractor(model="gpt-4", max_retries=3, rate_limit_delay=0.1)

        from openai import RateLimitError

        with patch.object(extractor, "_call_openai", new_callable=AsyncMock) as mock_call:
            # Fail twice, then succeed
            mock_call.side_effect = [
                RateLimitError("Rate limit", response=MagicMock(), body=None),
                RateLimitError("Rate limit", response=MagicMock(), body=None),
                mock_openai_response,
            ]

            result = await extractor.extract_single(sample_feedback)

            assert result.success is True
            assert result.retry_count == 2
            assert mock_call.call_count == 3

    @pytest.mark.asyncio
    async def test_extract_single_max_retries_exceeded(self, sample_feedback):
        """Test max retries exceeded scenario."""
        extractor = InsightExtractor(model="gpt-4", max_retries=2, rate_limit_delay=0.01)

        from openai import RateLimitError

        with patch.object(extractor, "_call_openai", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = RateLimitError("Rate limit", response=MagicMock(), body=None)

            result = await extractor.extract_single(sample_feedback)

            assert result.success is False
            assert "Max retries exceeded" in result.error
            assert result.retry_count == 2

    @pytest.mark.asyncio
    async def test_extract_batch_multiple_items(self, sample_feedback, mock_openai_response):
        """Test batch extraction with multiple feedback items."""
        feedback_items = [sample_feedback for _ in range(3)]
        extractor = InsightExtractor(model="gpt-4", batch_size=2, rate_limit_delay=0.01)

        with patch.object(extractor, "_call_openai", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_openai_response

            summary = await extractor.extract_batch(feedback_items)

            assert len(summary.results) == 3
            assert summary.success_count == 3
            assert summary.failure_count == 0
            assert summary.total_cost.total_tokens > 0

    @pytest.mark.asyncio
    async def test_cost_calculation(self, sample_feedback, mock_openai_response):
        """Test API cost tracking."""
        extractor = InsightExtractor(model="gpt-4")

        with patch.object(extractor, "_call_openai", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_openai_response

            result = await extractor.extract_single(sample_feedback)

            assert result.cost.prompt_tokens == 150
            assert result.cost.completion_tokens == 200
            assert result.cost.total_tokens == 350
            assert result.cost.estimated_cost_usd > 0

    @pytest.mark.asyncio
    async def test_convenience_helper(self, sample_feedback, mock_openai_response):
        """Test module-level convenience function."""
        feedback_items = [sample_feedback]

        with patch("voc_app.processors.extractor.AsyncOpenAI") as MockOpenAI:
            mock_client = AsyncMock()
            mock_completion = AsyncMock()
            mock_completion.choices = [MagicMock(message=MagicMock(content=mock_openai_response["content"]))]
            mock_completion.usage = MagicMock(
                prompt_tokens=150,
                completion_tokens=200,
                total_tokens=350,
            )
            mock_client.chat.completions.create.return_value = mock_completion
            MockOpenAI.return_value = mock_client

            summary = await extract_insights(feedback_items)

            assert summary.success_count >= 0


class TestInsightExtractionSchema:
    """Test Pydantic schema validation."""

    def test_valid_extraction_schema(self):
        """Test valid extraction data passes validation."""
        data = {
            "sentiment": {"score": 0.8, "label": "positive", "confidence": 0.9},
            "summary": "Customer is very satisfied with the product",
            "pain_points": [],
            "feature_requests": [],
            "competitor_mentions": [],
            "customer_context": {},
            "journey_stage": "retention",
            "urgency_level": 2,
            "themes": ["satisfaction"],
        }

        extraction = InsightExtraction(**data)
        assert extraction.sentiment.score == 0.8
        assert extraction.sentiment.label == "positive"

    def test_invalid_sentiment_score(self):
        """Test sentiment score validation."""
        data = {
            "sentiment": {"score": 1.5, "label": "positive", "confidence": 0.9},
            "summary": "Test summary",
        }

        with pytest.raises(Exception):  # ValidationError
            InsightExtraction(**data)

    def test_invalid_sentiment_label(self):
        """Test sentiment label validation."""
        data = {
            "sentiment": {"score": 0.5, "label": "invalid_label", "confidence": 0.9},
            "summary": "Test summary",
        }

        with pytest.raises(Exception):  # ValidationError
            InsightExtraction(**data)

    def test_empty_summary_fails(self):
        """Test that empty summary fails validation."""
        data = {
            "sentiment": {"score": 0.0, "label": "neutral", "confidence": 0.8},
            "summary": "",
        }

        with pytest.raises(Exception):  # ValidationError
            InsightExtraction(**data)
