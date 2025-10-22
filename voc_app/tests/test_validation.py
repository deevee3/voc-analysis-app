"""Tests for data validation logic."""

import uuid
from datetime import datetime

import pytest

from voc_app.models import Feedback, Insight
from voc_app.processors.validation import DataValidator, validate_feedback, validate_insights


class TestFeedbackValidation:
    """Test suite for Feedback validation."""

    def test_valid_feedback_passes(self):
        """Well-formed feedback should pass validation."""
        feedback = Feedback(
            id=uuid.uuid4(),
            data_source_id=uuid.uuid4(),
            raw_content="Sample feedback content",
            posted_at=datetime.utcnow(),
            url="https://example.com/post/123",
        )
        validator = DataValidator()
        result = validator.validate_feedback([feedback])

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_missing_raw_content_fails(self):
        """Feedback without raw_content should fail."""
        feedback = Feedback(
            id=uuid.uuid4(),
            data_source_id=uuid.uuid4(),
            raw_content="",
            posted_at=datetime.utcnow(),
        )
        validator = DataValidator()
        result = validator.validate_feedback([feedback])

        assert result.is_valid is False
        assert any("raw_content" in issue.field for issue in result.issues)

    def test_missing_timestamp_fails(self):
        """Feedback without posted_at should fail."""
        feedback = Feedback(
            id=uuid.uuid4(),
            data_source_id=uuid.uuid4(),
            raw_content="Content here",
            posted_at=None,
        )
        validator = DataValidator()
        result = validator.validate_feedback([feedback])

        assert result.is_valid is False
        assert any("posted_at" in issue.field for issue in result.issues)

    def test_missing_data_source_fails(self):
        """Feedback without data_source_id should fail."""
        feedback = Feedback(
            id=uuid.uuid4(),
            data_source_id=None,
            raw_content="Content here",
            posted_at=datetime.utcnow(),
        )
        validator = DataValidator()
        result = validator.validate_feedback([feedback])

        assert result.is_valid is False
        assert any("data_source_id" in issue.field for issue in result.issues)

    def test_convenience_helper(self):
        """Test module-level validation helper."""
        feedback = Feedback(
            id=uuid.uuid4(),
            data_source_id=uuid.uuid4(),
            raw_content="Valid content",
            posted_at=datetime.utcnow(),
        )
        result = validate_feedback([feedback])

        assert result.is_valid is True


class TestInsightValidation:
    """Test suite for Insight validation."""

    def test_valid_insight_passes(self):
        """Well-formed insight should pass validation."""
        insight = Insight(
            id=uuid.uuid4(),
            feedback_id=uuid.uuid4(),
            sentiment_score=0.75,
            sentiment_label="positive",
            summary="Customer is happy with the product",
        )
        validator = DataValidator()
        result = validator.validate_insights([insight])

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_missing_feedback_id_fails(self):
        """Insight without feedback_id should fail."""
        insight = Insight(
            id=uuid.uuid4(),
            feedback_id=None,
            summary="Summary text",
        )
        validator = DataValidator()
        result = validator.validate_insights([insight])

        assert result.is_valid is False
        assert any("feedback_id" in issue.field for issue in result.issues)

    def test_out_of_range_sentiment_score_fails(self):
        """Sentiment score outside [-1, 1] should fail."""
        insight = Insight(
            id=uuid.uuid4(),
            feedback_id=uuid.uuid4(),
            sentiment_score=1.5,
            summary="Summary text",
        )
        validator = DataValidator()
        result = validator.validate_insights([insight])

        assert result.is_valid is False
        assert any("sentiment_score" in issue.field for issue in result.issues)

    def test_missing_summary_fails(self):
        """Insight without summary should fail."""
        insight = Insight(
            id=uuid.uuid4(),
            feedback_id=uuid.uuid4(),
            summary=None,
        )
        validator = DataValidator()
        result = validator.validate_insights([insight])

        assert result.is_valid is False
        assert any("summary" in issue.field for issue in result.issues)

    def test_empty_summary_fails(self):
        """Insight with empty summary should fail."""
        insight = Insight(
            id=uuid.uuid4(),
            feedback_id=uuid.uuid4(),
            summary="   ",
        )
        validator = DataValidator()
        result = validator.validate_insights([insight])

        assert result.is_valid is False
        assert any("summary" in issue.field for issue in result.issues)

    def test_convenience_helper(self):
        """Test module-level validation helper."""
        insight = Insight(
            id=uuid.uuid4(),
            feedback_id=uuid.uuid4(),
            sentiment_score=-0.3,
            summary="Customer had concerns",
        )
        result = validate_insights([insight])

        assert result.is_valid is True
