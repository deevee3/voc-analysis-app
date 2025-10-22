"""Scheduling and throttling configuration for crawl operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass(slots=True)
class ScheduleConfig:
    """Configuration for crawl scheduling."""

    enabled: bool = True
    cron_expression: str | None = None
    interval_minutes: int | None = None
    max_concurrent_crawls: int = 1
    retry_failed_after_minutes: int = 60


@dataclass(slots=True)
class ThrottleConfig:
    """Rate limiting configuration for crawlers."""

    requests_per_minute: int = 10
    requests_per_hour: int = 100
    concurrent_requests: int = 2
    backoff_on_error: bool = True
    backoff_multiplier: float = 2.0
    max_backoff_seconds: int = 300


@dataclass(slots=True)
class PlatformScheduleConfig:
    """Per-platform scheduling and throttling rules."""

    platform: str
    schedule: ScheduleConfig
    throttle: ThrottleConfig


# Default configurations per platform
DEFAULT_PLATFORM_CONFIGS = {
    "reddit": PlatformScheduleConfig(
        platform="reddit",
        schedule=ScheduleConfig(interval_minutes=30, max_concurrent_crawls=2),
        throttle=ThrottleConfig(requests_per_minute=30, concurrent_requests=2),
    ),
    "twitter": PlatformScheduleConfig(
        platform="twitter",
        schedule=ScheduleConfig(interval_minutes=15, max_concurrent_crawls=1),
        throttle=ThrottleConfig(requests_per_minute=15, concurrent_requests=1),
    ),
    "youtube": PlatformScheduleConfig(
        platform="youtube",
        schedule=ScheduleConfig(interval_minutes=60, max_concurrent_crawls=2),
        throttle=ThrottleConfig(requests_per_minute=20, concurrent_requests=2),
    ),
    "trustpilot": PlatformScheduleConfig(
        platform="trustpilot",
        schedule=ScheduleConfig(interval_minutes=120, max_concurrent_crawls=1),
        throttle=ThrottleConfig(requests_per_minute=10, concurrent_requests=1),
    ),
    "quora": PlatformScheduleConfig(
        platform="quora",
        schedule=ScheduleConfig(interval_minutes=60, max_concurrent_crawls=1),
        throttle=ThrottleConfig(requests_per_minute=10, concurrent_requests=1),
    ),
    "g2": PlatformScheduleConfig(
        platform="g2",
        schedule=ScheduleConfig(interval_minutes=240, max_concurrent_crawls=1),
        throttle=ThrottleConfig(requests_per_minute=5, concurrent_requests=1),
    ),
}


def get_platform_config(platform: str) -> PlatformScheduleConfig:
    """Get scheduling config for a platform."""
    return DEFAULT_PLATFORM_CONFIGS.get(
        platform.lower(),
        PlatformScheduleConfig(
            platform=platform,
            schedule=ScheduleConfig(interval_minutes=60),
            throttle=ThrottleConfig(),
        ),
    )


def should_run_crawl(
    last_run_at: datetime | None,
    config: ScheduleConfig,
    now: datetime | None = None,
) -> bool:
    """Determine if a crawl should run based on schedule config."""
    if not config.enabled:
        return False

    if now is None:
        now = datetime.utcnow()

    if last_run_at is None:
        return True

    if config.interval_minutes:
        next_run = last_run_at + timedelta(minutes=config.interval_minutes)
        return now >= next_run

    return False


def calculate_next_run(
    last_run_at: datetime,
    config: ScheduleConfig,
) -> datetime:
    """Calculate the next scheduled run time."""
    if config.interval_minutes:
        return last_run_at + timedelta(minutes=config.interval_minutes)

    # Default: run every hour if no config
    return last_run_at + timedelta(hours=1)
