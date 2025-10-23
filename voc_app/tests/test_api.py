"""Integration tests for FastAPI endpoints."""

import uuid
from datetime import datetime, timedelta

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from voc_app.api.dependencies import get_db
from voc_app.main import app
from voc_app.models import AlertRule, Base, DataSource, Feedback, Insight, InsightThemeLink, Theme


# Test database setup - use file-based DB to avoid aiosqlite in-memory connection issues
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

TestingSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    """Override database dependency for testing."""
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create test database tables once for the session."""
    import asyncio
    # Import all models to ensure metadata is populated
    from voc_app.models import (
        AlertEvent,
        AlertRule,
        CrawlRun,
        DataSource,
        Feedback,
        Insight,
        InsightThemeLink,
        Theme,
    )
    
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    # Create tables
    asyncio.run(create_tables())
    yield
    # Drop tables
    asyncio.run(drop_tables())


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestDataSourceEndpoints:
    """Test data source CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_data_source(self, client):
        """Test creating a new data source."""
        payload = {
            "name": "Test Source",
            "platform": "reddit",
            "config": {"subreddit": "test"},
            "is_active": True,
        }

        response = client.post("/api/v1/sources", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Source"
        assert data["platform"] == "reddit"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_data_sources(self, client):
        """Test listing data sources."""
        # Create a source first
        async with TestingSessionLocal() as session:
            source = DataSource(
                name="Test Source",
                platform="reddit",
                is_active=True,
            )
            session.add(source)
            await session.commit()

        response = client.get("/api/v1/sources")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_data_source_by_id(self, client):
        """Test getting a specific data source."""
        async with TestingSessionLocal() as session:
            source = DataSource(
                name="Test Source",
                platform="reddit",
                is_active=True,
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)
            source_id = str(source.id)

        response = client.get(f"/api/v1/sources/{source_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == source_id
        assert data["name"] == "Test Source"

    @pytest.mark.asyncio
    async def test_update_data_source(self, client):
        """Test updating a data source."""
        async with TestingSessionLocal() as session:
            source = DataSource(
                name="Test Source",
                platform="reddit",
                is_active=True,
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)
            source_id = str(source.id)

        payload = {"name": "Updated Source", "is_active": False}
        response = client.patch(f"/api/v1/sources/{source_id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Source"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_data_source(self, client):
        """Test deleting a data source."""
        async with TestingSessionLocal() as session:
            source = DataSource(
                name="Test Source",
                platform="reddit",
                is_active=True,
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)
            source_id = str(source.id)

        response = client.delete(f"/api/v1/sources/{source_id}")
        assert response.status_code == 204


class TestCrawlEndpoints:
    """Test crawl management endpoints."""

    @pytest.mark.asyncio
    async def test_trigger_crawl_requires_valid_id(self, client):
        """Triggering with invalid UUID should fail."""
        response = client.post(
            "/api/v1/crawls/trigger",
            json={"data_source_id": "not-a-uuid"},
        )
        assert response.status_code == 400
        assert "Invalid data_source_id" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_trigger_crawl_enqueue_task(self, client):
        """Trigger crawl should enqueue Celery task with overrides merged."""
        async with TestingSessionLocal() as session:
            source = DataSource(
                name="Trigger Source",
                platform="reddit",
                config={"subreddit": "testsub"},
                is_active=True,
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)
            source_id = str(source.id)

        with patch("voc_app.api.crawls.execute_crawl.delay") as mock_delay:
            mock_delay.return_value.id = "task-123"

            response = client.post(
                "/api/v1/crawls/trigger",
                json={
                    "data_source_id": source_id,
                    "query_override": {"query": "override-sub"},
                },
            )

        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "task-123"
        mock_delay.assert_called_once_with(source_id, {"subreddit": "testsub", "query": "override-sub"})

    @pytest.mark.asyncio
    async def test_trigger_crawl_missing_reddit_config(self, client):
        """Trigger crawl without subreddit should return validation error."""
        async with TestingSessionLocal() as session:
            source = DataSource(
                name="Missing Config Source",
                platform="reddit",
                config={},
                is_active=True,
            )
            session.add(source)
            await session.commit()
            await session.refresh(source)
            source_id = str(source.id)

        response = client.post(
            "/api/v1/crawls/trigger",
            json={"data_source_id": source_id},
        )

        assert response.status_code == 400
        assert "Reddit sources require" in response.json()["detail"]


class TestInsightEndpoints:
    """Test insight endpoints."""

    @pytest.mark.asyncio
    async def test_list_insights(self, client):
        """Test listing insights."""
        async with TestingSessionLocal() as session:
            feedback = Feedback(
                data_source_id=uuid.uuid4(),
                raw_content="Test content",
                posted_at=datetime.utcnow(),
            )
            session.add(feedback)
            await session.flush()

            insight = Insight(
                feedback_id=feedback.id,
                summary="Test insight",
                sentiment_score=0.5,
            )
            session.add(insight)
            await session.commit()

        response = client.get("/api/v1/insights")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_insight_by_id(self, client):
        """Test getting a specific insight."""
        async with TestingSessionLocal() as session:
            feedback = Feedback(
                data_source_id=uuid.uuid4(),
                raw_content="Test content",
                posted_at=datetime.utcnow(),
            )
            session.add(feedback)
            await session.flush()

            insight = Insight(
                feedback_id=feedback.id,
                summary="Test insight",
                sentiment_score=0.5,
            )
            session.add(insight)
            await session.commit()
            await session.refresh(insight)
            insight_id = str(insight.id)

        response = client.get(f"/api/v1/insights/{insight_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == insight_id
        assert data["summary"] == "Test insight"

    @pytest.mark.asyncio
    async def test_insight_filters(self, client):
        """Test insight filtering by platform, theme, keyword, and sentiment."""
        created_at = datetime.utcnow() - timedelta(days=1)
        posted_at = datetime.utcnow() - timedelta(days=2)

        async with TestingSessionLocal() as session:
            source = DataSource(
                name="Filter Source",
                platform="reddit",
                is_active=True,
            )
            session.add(source)
            await session.flush()

            feedback = Feedback(
                data_source_id=source.id,
                raw_content="Battery keeps dying",
                clean_content="battery keeps dying",
                language="en",
                posted_at=posted_at,
            )
            session.add(feedback)
            await session.flush()

            insight = Insight(
                feedback_id=feedback.id,
                summary="Battery issue detected",
                sentiment_score=-0.6,
                urgency_level=4,
                sentiment_label="negative",
                journey_stage="post_purchase",
            )
            session.add(insight)
            await session.flush()
            # Override created_at for deterministic filtering
            insight.created_at = created_at

            theme = Theme(name="Battery", description="Battery problems", is_system=False)
            session.add(theme)
            await session.flush()

            link = InsightThemeLink(insight_id=insight.id, theme_id=theme.id)
            session.add(link)

            await session.commit()

        base_path = "/api/v1/insights"

        response = client.get(base_path, params={"platform": "reddit"})
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.get(base_path, params={"theme_name": "Battery"})
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.get(base_path, params={"keyword": "battery"})
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.get(
            base_path,
            params={
                "min_sentiment": -1,
                "max_sentiment": 0,
                "min_urgency": 3,
                "max_urgency": 5,
                "journey_stage": "post_purchase",
                "sentiment_label": "negative",
            },
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.get(
            base_path,
            params={
                "created_after": (created_at - timedelta(minutes=1)).isoformat(),
                "created_before": (created_at + timedelta(minutes=1)).isoformat(),
                "posted_after": (posted_at - timedelta(minutes=1)).isoformat(),
                "posted_before": (posted_at + timedelta(minutes=1)).isoformat(),
            },
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.get(
            base_path,
            params={
                "platform": "reddit",
                "theme_name": "Battery",
                "keyword": "battery",
                "min_sentiment": -1,
                "max_sentiment": 0,
                "created_after": (created_at - timedelta(minutes=1)).isoformat(),
                "created_before": (created_at + timedelta(minutes=1)).isoformat(),
            },
        )
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestThemeEndpoints:
    """Test theme endpoints."""

    @pytest.mark.asyncio
    async def test_create_theme(self, client):
        """Test creating a new theme."""
        payload = {
            "name": "Test Theme",
            "description": "A test theme",
            "is_system": False,
        }

        response = client.post("/api/v1/themes", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Theme"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_themes(self, client):
        """Test listing themes."""
        async with TestingSessionLocal() as session:
            theme = Theme(
                name="Test Theme",
                description="Test",
                is_system=False,
            )
            session.add(theme)
            await session.commit()

        response = client.get("/api/v1/themes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestAlertEndpoints:
    """Test alert endpoints."""

    @pytest.mark.asyncio
    async def test_create_alert_rule(self, client):
        """Test creating an alert rule."""
        payload = {
            "name": "Test Alert",
            "rule_type": "sentiment_threshold",
            "threshold_value": -0.5,
            "enabled": True,
        }

        response = client.post("/api/v1/alerts/rules", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Alert"
        assert data["rule_type"] == "sentiment_threshold"

    @pytest.mark.asyncio
    async def test_list_alert_rules(self, client):
        """Test listing alert rules."""
        async with TestingSessionLocal() as session:
            rule = AlertRule(
                name="Test Rule",
                rule_type="keyword",
                enabled=True,
            )
            session.add(rule)
            await session.commit()

        response = client.get("/api/v1/alerts/rules")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestPagination:
    """Test pagination functionality."""


class TestFeedbackEndpoints:
    """Test feedback list filtering."""

    @pytest.mark.asyncio
    async def test_feedback_filters(self, client):
        """Test feedback filtering by keyword, platform, and posted date."""
        first_posted = datetime.utcnow() - timedelta(days=3)
        second_posted = datetime.utcnow() - timedelta(days=1)

        async with TestingSessionLocal() as session:
            source_one = DataSource(
                name="Filter Source One",
                platform="reddit",
                is_active=True,
            )
            source_two = DataSource(
                name="Filter Source Two",
                platform="g2",
                is_active=True,
            )
            session.add_all([source_one, source_two])
            await session.flush()

            feedback_one = Feedback(
                data_source_id=source_one.id,
                raw_content="Love the battery life",
                clean_content="love the battery life",
                language="en",
                posted_at=first_posted,
            )
            feedback_two = Feedback(
                data_source_id=source_two.id,
                raw_content="Service was terrible",
                clean_content="service was terrible",
                language="en",
                posted_at=second_posted,
            )
            session.add_all([feedback_one, feedback_two])
            await session.commit()

        base_path = "/api/v1/feedback"

        response = client.get(base_path, params={"keyword": "terrible"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "terrible" in data[0]["clean_content"]

        response = client.get(base_path, params={"platform": "reddit"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["data_source_id"]

        response = client.get(
            base_path,
            params={"posted_after": (first_posted + timedelta(hours=1)).isoformat()},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "terrible" in data[0]["clean_content"]

    @pytest.mark.asyncio
    async def test_pagination_skip_limit(self, client):
        """Test pagination with skip and limit parameters."""
        # Create multiple sources
        async with TestingSessionLocal() as session:
            for i in range(10):
                source = DataSource(
                    name=f"Source {i}",
                    platform="reddit",
                    is_active=True,
                )
                session.add(source)
            await session.commit()

        # Test with pagination
        response = client.get("/api/v1/sources?skip=2&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestErrorHandling:
    """Test API error handling."""

    def test_invalid_uuid_format(self, client):
        """Test error handling for invalid UUID."""
        response = client.get("/api/v1/sources/invalid-uuid")
        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]

    def test_resource_not_found(self, client):
        """Test 404 for non-existent resource."""
        fake_uuid = str(uuid.uuid4())
        response = client.get(f"/api/v1/sources/{fake_uuid}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
