"""Tests for export functionality."""

import csv
import io
import json
import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from voc_app.main import app
from voc_app.models import DataSource, Feedback, Insight
from voc_app.tests.test_api import TestingSessionLocal, setup_test_db  # noqa: F401

client = TestClient(app)

# Import setup_test_db fixture to ensure tables are created


class TestExportEndpoints:
    """Test export API endpoints."""

    @pytest.mark.asyncio
    async def test_export_insights_csv(self):
        """Test CSV export of insights."""
        # Create test data
        async with TestingSessionLocal() as session:
            source = DataSource(
                name="Export Test Source",
                platform="reddit",
                is_active=True,
            )
            session.add(source)
            await session.flush()

            feedback = Feedback(
                data_source_id=source.id,
                raw_content="Test export content",
                posted_at=datetime.utcnow(),
            )
            session.add(feedback)
            await session.flush()

            insight = Insight(
                feedback_id=feedback.id,
                summary="Test export insight",
                sentiment_score=0.8,
                sentiment_label="positive",
                urgency_level=2,
            )
            session.add(insight)
            await session.commit()

        # Test CSV export
        response = client.get("/api/v1/exports/insights/csv")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]

        # Parse CSV content
        csv_content = response.text
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        
        assert len(rows) >= 1
        assert "id" in rows[0]
        assert "sentiment_score" in rows[0]
        assert "summary" in rows[0]

    @pytest.mark.asyncio
    async def test_export_insights_json(self):
        """Test JSON export of insights."""
        response = client.get("/api/v1/exports/insights/json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]

        # Parse JSON content
        data = json.loads(response.text)
        assert isinstance(data, list)
        
        if len(data) > 0:
            assert "id" in data[0]
            assert "sentiment_score" in data[0]
            assert "summary" in data[0]

    @pytest.mark.asyncio
    async def test_export_insights_excel(self):
        """Test Excel export of insights."""
        response = client.get("/api/v1/exports/insights/excel")
        
        # Should succeed if openpyxl is installed
        if response.status_code == 200:
            assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            assert "attachment" in response.headers["content-disposition"]
            assert ".xlsx" in response.headers["content-disposition"]
        # Or return 501 if openpyxl not available
        elif response.status_code == 501:
            assert "openpyxl" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_export_with_filters(self):
        """Test export with filter parameters."""
        # Create test data with specific sentiment
        async with TestingSessionLocal() as session:
            source = DataSource(
                name="Filter Export Source",
                platform="twitter",
                is_active=True,
            )
            session.add(source)
            await session.flush()

            feedback = Feedback(
                data_source_id=source.id,
                raw_content="Negative feedback",
                posted_at=datetime.utcnow(),
            )
            session.add(feedback)
            await session.flush()

            insight = Insight(
                feedback_id=feedback.id,
                summary="Negative insight",
                sentiment_score=-0.7,
                sentiment_label="negative",
            )
            session.add(insight)
            await session.commit()

        # Test filtered CSV export
        response = client.get(
            "/api/v1/exports/insights/csv",
            params={"sentiment_label": "negative"}
        )
        assert response.status_code == 200
        
        # Verify filtered results
        csv_content = response.text
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)
        
        # All rows should have negative sentiment
        for row in rows:
            if row["sentiment_label"]:
                assert row["sentiment_label"] == "negative"
