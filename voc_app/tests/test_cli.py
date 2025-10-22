"""Tests for CLI commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from voc_app.cli import app

runner = CliRunner()


class TestCLICommands:
    """Test suite for CLI command execution."""

    def test_init_command_succeeds(self):
        """Test database initialization command."""
        with patch("voc_app.cli._init_db", new_callable=AsyncMock) as mock_init:
            result = runner.invoke(app, ["init"])
            assert result.exit_code == 0
            assert "initialized successfully" in result.stdout.lower()
            mock_init.assert_called_once()

    def test_sources_command_with_no_sources(self):
        """Test sources listing when no sources exist."""
        with patch("voc_app.cli._list_sources", new_callable=AsyncMock):
            result = runner.invoke(app, ["sources"])
            assert result.exit_code == 0

    def test_status_command_with_no_filter(self):
        """Test status command without source filter."""
        with patch("voc_app.cli._show_status", new_callable=AsyncMock):
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0

    def test_status_command_with_source_filter(self):
        """Test status command with source filter."""
        with patch("voc_app.cli._show_status", new_callable=AsyncMock) as mock_status:
            result = runner.invoke(app, ["status", "--source", "test-source"])
            assert result.exit_code == 0

    def test_crawl_command_requires_platform(self):
        """Test crawl command validates required platform argument."""
        result = runner.invoke(app, ["crawl", "--source", "test"])
        assert result.exit_code != 0

    def test_crawl_command_requires_source(self):
        """Test crawl command validates required source argument."""
        result = runner.invoke(app, ["crawl", "--platform", "reddit"])
        assert result.exit_code != 0

    def test_crawl_command_dry_run_flag(self):
        """Test crawl command respects dry-run flag."""
        with patch("voc_app.cli._run_crawl", new_callable=AsyncMock) as mock_crawl:
            result = runner.invoke(
                app,
                [
                    "crawl",
                    "--platform",
                    "reddit",
                    "--source",
                    "test",
                    "--query",
                    "test_sub",
                    "--dry-run",
                ],
            )
            # Command should execute
            mock_crawl.assert_called_once()
            call_args = mock_crawl.call_args
            # Verify dry_run parameter was passed
            assert call_args[0][3] is True  # dry_run is 4th positional arg

    def test_crawl_command_with_limit_option(self):
        """Test crawl command accepts limit option."""
        with patch("voc_app.cli._run_crawl", new_callable=AsyncMock) as mock_crawl:
            result = runner.invoke(
                app,
                [
                    "crawl",
                    "--platform",
                    "twitter",
                    "--source",
                    "test",
                    "--query",
                    "test",
                    "--limit",
                    "50",
                ],
            )
            mock_crawl.assert_called_once()
            call_args = mock_crawl.call_args
            # Verify limit parameter was passed
            assert call_args[0][4] == 50  # limit is 5th positional arg


class TestCLIPlatformIntegration:
    """Test CLI integration with platform-specific logic."""

    @pytest.mark.asyncio
    async def test_reddit_crawl_execution_flow(self):
        """Test Reddit crawl end-to-end flow."""
        from voc_app.cli import _execute_platform_crawl, PlatformType

        with patch("voc_app.cli.RedditCrawler") as MockCrawler:
            mock_instance = MagicMock()
            mock_instance.build_listing_target.return_value = MagicMock()
            mock_instance.crawl_many = AsyncMock(return_value=[])
            MockCrawler.return_value = mock_instance

            await _execute_platform_crawl(PlatformType.REDDIT, "test_subreddit", 10)

            MockCrawler.assert_called_once_with(subreddit="test_subreddit", concurrent_tasks=2)
            mock_instance.build_listing_target.assert_called_once()
            mock_instance.crawl_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_twitter_crawl_execution_flow(self):
        """Test Twitter crawl end-to-end flow."""
        from voc_app.cli import _execute_platform_crawl, PlatformType

        with patch("voc_app.cli.TwitterCrawler") as MockCrawler:
            mock_instance = MagicMock()
            mock_instance.build_listing_target.return_value = MagicMock()
            mock_instance.crawl_many = AsyncMock(return_value=[])
            MockCrawler.return_value = mock_instance

            await _execute_platform_crawl(PlatformType.TWITTER, "test query", 10)

            MockCrawler.assert_called_once_with(query="test query", concurrent_tasks=2)
            mock_instance.build_listing_target.assert_called_once()
            mock_instance.crawl_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_crawl_requires_query_for_reddit(self):
        """Test Reddit crawl fails without query."""
        from voc_app.cli import _execute_platform_crawl, PlatformType

        with pytest.raises(ValueError, match="Reddit crawls require"):
            await _execute_platform_crawl(PlatformType.REDDIT, None, 10)

    @pytest.mark.asyncio
    async def test_crawl_requires_query_for_twitter(self):
        """Test Twitter crawl fails without query."""
        from voc_app.cli import _execute_platform_crawl, PlatformType

        with pytest.raises(ValueError, match="Twitter crawls require"):
            await _execute_platform_crawl(PlatformType.TWITTER, None, 10)
