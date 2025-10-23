"""Application configuration management for the Voice of Customer service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Final

from dotenv import load_dotenv
from sqlalchemy.engine import URL


class AppEnvironment(str, Enum):
    """Supported runtime environments."""

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


BASE_DIR: Final[Path] = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")


def _str_to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "t", "yes", "y", "on"}


def _build_oracle_async_url(
    *,
    username: str,
    password: str,
    dsn: str,
    wallet_dir: str | None,
    wallet_password: str | None,
) -> str:
    query: dict[str, str] = {"dsn": dsn}

    if wallet_dir:
        query["config_dir"] = wallet_dir
        query.setdefault("wallet_location", wallet_dir)

    if wallet_password:
        query["wallet_password"] = wallet_password

    url = URL.create(
        drivername="oracle+oracledb_async",
        username=username,
        password=password,
        host=None,
        port=None,
        database=None,
        query=query,
    )
    return str(url)


@dataclass(slots=True)
class Settings:
    """Centralized configuration values loaded from environment variables."""

    env: AppEnvironment
    debug: bool
    database_url: str
    crawl_concurrency: int
    crawl_rate_limit_per_minute: int
    openai_api_key: str | None
    alert_webhook_url: str | None
    redis_url: str
    oracle_dsn: str | None
    oracle_wallet_dir: str | None
    oracle_wallet_password: str | None
    oracle_username: str | None
    oracle_password: str | None

    @property
    def is_dev(self) -> bool:
        return self.env == AppEnvironment.DEV

    @property
    def is_test(self) -> bool:
        return self.env == AppEnvironment.TEST

    @property
    def is_prod(self) -> bool:
        return self.env == AppEnvironment.PROD

    @classmethod
    def from_env(cls) -> "Settings":
        env_name = os.getenv("VOC_APP_ENV", AppEnvironment.DEV.value)
        try:
            env = AppEnvironment(env_name)
        except ValueError as exc:
            raise ValueError(f"Unsupported VOC_APP_ENV value: {env_name}") from exc

        defaults = {
            AppEnvironment.DEV: {
                "debug": True,
                "database_url": "sqlite+aiosqlite:///./voc_app_dev.db",
                "crawl_concurrency": 2,
                "crawl_rate_limit_per_minute": 60,
            },
            AppEnvironment.TEST: {
                "debug": False,
                "database_url": "sqlite+aiosqlite:///./voc_app_test.db",
                "crawl_concurrency": 1,
                "crawl_rate_limit_per_minute": 30,
            },
            AppEnvironment.PROD: {
                "debug": False,
                "database_url": "sqlite+aiosqlite:///./voc_app.db",
                "crawl_concurrency": 4,
                "crawl_rate_limit_per_minute": 120,
            },
        }[env]

        debug = _str_to_bool(os.getenv("VOC_APP_DEBUG"), defaults["debug"])
        oracle_username = os.getenv("VOC_APP_DB_USERNAME")
        oracle_password = os.getenv("VOC_APP_DB_PASSWORD")
        oracle_dsn = os.getenv("VOC_APP_ORACLE_DSN")
        oracle_wallet_dir = os.getenv("VOC_APP_ORACLE_WALLET_DIR") or os.getenv("TNS_ADMIN")
        oracle_wallet_password = os.getenv("VOC_APP_ORACLE_WALLET_PASSWORD")

        database_url_env = os.getenv("VOC_APP_DATABASE_URL")
        database_url = database_url_env or defaults["database_url"]

        crawl_concurrency = int(
            os.getenv("VOC_APP_CRAWL_CONCURRENCY", defaults["crawl_concurrency"])
        )
        crawl_rate_limit = int(
            os.getenv("VOC_APP_CRAWL_RATE_LIMIT_PER_MINUTE", defaults["crawl_rate_limit_per_minute"])
        )

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        if not database_url_env and oracle_username and oracle_password and oracle_dsn:
            database_url = _build_oracle_async_url(
                username=oracle_username,
                password=oracle_password,
                dsn=oracle_dsn,
                wallet_dir=oracle_wallet_dir,
                wallet_password=oracle_wallet_password,
            )

        return cls(
            env=env,
            debug=debug,
            database_url=database_url,
            crawl_concurrency=crawl_concurrency,
            crawl_rate_limit_per_minute=crawl_rate_limit,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            alert_webhook_url=os.getenv("VOC_APP_ALERT_WEBHOOK_URL"),
            redis_url=redis_url,
            oracle_dsn=oracle_dsn,
            oracle_wallet_dir=oracle_wallet_dir,
            oracle_wallet_password=oracle_wallet_password,
            oracle_username=oracle_username,
            oracle_password=oracle_password,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings.from_env()
