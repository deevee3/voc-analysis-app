"""Celery tasks for crawling operations."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from celery import Task
from sqlalchemy import select

from voc_app.celery_app import app
from voc_app.crawlers import (
    G2Crawler,
    QuoraCrawler,
    RedditCrawler,
    TrustpilotCrawler,
    TwitterCrawler,
    YouTubeCrawler,
)
from voc_app.database import _SessionFactory
from voc_app.models import CrawlRun, DataSource
from voc_app.processors.cleaner import CleaningOptions
from voc_app.processors.ingestion import run_ingestion_pipeline
from voc_app.services.scheduler import get_platform_config, should_run_crawl
from voc_app.services.storage import StorageOptions

logger = logging.getLogger(__name__)


class CrawlTask(Task):
    """Base task with error handling for crawl operations."""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@app.task(base=CrawlTask, bind=True)
def execute_crawl(self, data_source_id: str, config_override: dict[str, str] | None = None) -> dict:
    """Execute a single crawl for a data source."""
    return asyncio.run(_execute_crawl_async(data_source_id, config_override))


async def _execute_crawl_async(data_source_id: str, config_override: dict[str, str] | None) -> dict:
    """Async implementation of crawl execution."""
    async with _SessionFactory() as session:
        # Load data source
        result = await session.execute(
            select(DataSource).where(DataSource.id == data_source_id)
        )
        data_source = result.scalar_one_or_none()

        if not data_source or not data_source.is_active:
            logger.warning(f"Data source {data_source_id} not found or inactive")
            return {"success": False, "error": "Data source not found or inactive"}

        # Create crawl run
        crawl_run = CrawlRun(
            data_source_id=data_source.id,
            started_at=datetime.utcnow(),
            status="running",
        )
        session.add(crawl_run)
        await session.flush()

        try:
            # Execute platform-specific crawl
            crawler_config: dict[str, str] = dict(data_source.config or {})
            if config_override:
                crawler_config.update(config_override)

            crawler = _get_crawler(data_source.platform, crawler_config)
            if not crawler:
                raise ValueError(f"Unsupported platform: {data_source.platform}")

            target = crawler.build_listing_target()
            outputs = await crawler.crawl_many([target])

            logger.info(f"Crawled {len(outputs)} items from {data_source.platform}")

            # Process and store
            ingestion_result = await run_ingestion_pipeline(
                session,
                data_source=data_source,
                crawl_run=crawl_run,
                outputs=outputs,
                cleaning_options=CleaningOptions(min_characters=10),
                storage_options=StorageOptions(store_files=True),
            )

            summary = ingestion_result.cleaning_summary
            if summary.records:
                logger.info(
                    "Stored records (%s): %s",
                    len(summary.records),
                    [
                        {
                            "id": record.identifier,
                            "length": len(record.cleaned_text),
                        }
                        for record in summary.records
                    ],
                )
            if summary.discarded:
                logger.info(
                    "Discarded records (%s): %s",
                    len(summary.discarded),
                    [
                        {
                            "id": record.identifier,
                            "reason": record.discard_reason,
                            "length": len(record.cleaned_text),
                        }
                        for record in summary.discarded
                    ],
                )

            # Update crawl run
            crawl_run.status = "completed"
            crawl_run.finished_at = datetime.utcnow()
            crawl_run.stats = {
                "crawled": len(outputs),
                "stored": len(ingestion_result.stored_feedback_ids),
                "duplicates": len(ingestion_result.cleaning_summary.duplicates),
                "discarded": len(ingestion_result.cleaning_summary.discarded),
            }

            # Update data source
            data_source.last_crawl_at = datetime.utcnow()

            await session.commit()

            return {
                "success": True,
                "crawl_run_id": str(crawl_run.id),
                "stored_feedback_ids": ingestion_result.stored_feedback_ids,
                "stats": crawl_run.stats,
            }

        except Exception as exc:
            logger.exception(f"Crawl failed for {data_source_id}: {exc}")
            crawl_run.status = "failed"
            crawl_run.finished_at = datetime.utcnow()
            await session.commit()
            raise


def _get_crawler(platform: str, config: dict):
    """Instantiate the appropriate crawler for a platform."""
    platform = platform.lower()

    if platform == "reddit":
        subreddit = config.get("subreddit") or config.get("query")
        return RedditCrawler(subreddit=subreddit) if subreddit else None

    elif platform == "twitter":
        query = config.get("query")
        return TwitterCrawler(query=query) if query else None

    elif platform == "youtube":
        video_id = config.get("video_id")
        channel_id = config.get("channel_id")
        if video_id:
            return YouTubeCrawler(video_id=video_id)
        elif channel_id:
            return YouTubeCrawler(channel_id=channel_id)

    elif platform == "trustpilot":
        company_name = config.get("company_name")
        return TrustpilotCrawler(company_name=company_name) if company_name else None

    elif platform == "quora":
        query = config.get("query")
        return QuoraCrawler(query=query) if query else None

    elif platform == "g2":
        product_slug = config.get("product_slug")
        return G2Crawler(product_slug=product_slug) if product_slug else None

    return None


@app.task(bind=True)
def run_scheduled_crawls(self) -> dict:
    """Check and execute scheduled crawls for active data sources."""
    return asyncio.run(_run_scheduled_crawls_async())


async def _run_scheduled_crawls_async() -> dict:
    """Async implementation of scheduled crawl execution."""
    async with _SessionFactory() as session:
        result = await session.execute(
            select(DataSource).where(DataSource.is_active == True)
        )
        data_sources = result.scalars().all()

        scheduled_count = 0
        for source in data_sources:
            platform_config = get_platform_config(source.platform)

            if should_run_crawl(source.last_crawl_at, platform_config.schedule):
                logger.info(f"Scheduling crawl for {source.name} ({source.platform})")
                execute_crawl.delay(str(source.id))
                scheduled_count += 1

        return {"scheduled_count": scheduled_count}
