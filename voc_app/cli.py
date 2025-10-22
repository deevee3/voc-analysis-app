"""Command-line interface for the Voice of Customer application."""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from voc_app.config import get_settings
from voc_app.crawlers import (
    G2Crawler,
    QuoraCrawler,
    RedditCrawler,
    TrustpilotCrawler,
    TwitterCrawler,
    YouTubeCrawler,
)
from voc_app.database import _SessionFactory, init_db
from voc_app.models import CrawlRun, DataSource
from voc_app.processors.cleaner import CleaningOptions
from voc_app.processors.ingestion import run_ingestion_pipeline
from voc_app.services.storage import StorageOptions

app = typer.Typer(help="Voice of Customer CLI")
console = Console()


class PlatformType(str, Enum):
    """Supported platforms."""

    REDDIT = "reddit"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    TRUSTPILOT = "trustpilot"
    QUORA = "quora"
    G2 = "g2"


@app.command()
def init():
    """Initialize the database schema."""
    asyncio.run(_init_db())
    console.print("[green]✓[/green] Database initialized successfully")


async def _init_db():
    await init_db()


@app.command()
def crawl(
    platform: PlatformType = typer.Option(..., "--platform", "-p", help="Platform to crawl"),
    source_name: str = typer.Option(..., "--source", "-s", help="Data source name"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query or subreddit"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without storing"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max items to crawl"),
):
    """Execute a crawl for the specified platform and source."""
    asyncio.run(_run_crawl(platform, source_name, query, dry_run, limit))


async def _run_crawl(
    platform: PlatformType,
    source_name: str,
    query: Optional[str],
    dry_run: bool,
    limit: int,
):
    settings = get_settings()
    console.print(f"[cyan]Starting {platform.value} crawl for source '{source_name}'...[/cyan]")

    async with _SessionFactory() as session:
        # Get or create data source
        result = await session.execute(
            select(DataSource).where(DataSource.name == source_name)
        )
        data_source = result.scalar_one_or_none()

        if not data_source:
            console.print(f"[yellow]Creating new data source '{source_name}'[/yellow]")
            data_source = DataSource(
                name=source_name,
                platform=platform.value,
                is_active=True,
            )
            session.add(data_source)
            await session.flush()

        # Create crawl run
        crawl_run = CrawlRun(
            data_source_id=data_source.id,
            started_at=datetime.utcnow(),
            status="running",
        )
        session.add(crawl_run)
        await session.flush()

        try:
            # Execute crawl
            outputs = await _execute_platform_crawl(platform, query, limit)

            console.print(f"[green]✓[/green] Crawled {len(outputs)} items")

            if dry_run:
                console.print("[yellow]Dry-run mode: Skipping storage[/yellow]")
                crawl_run.status = "completed"
                crawl_run.finished_at = datetime.utcnow()
                await session.commit()
                return

            # Process and store
            result = await run_ingestion_pipeline(
                session,
                data_source=data_source,
                crawl_run=crawl_run,
                outputs=outputs,
                cleaning_options=CleaningOptions(min_characters=20),
                storage_options=StorageOptions(store_files=settings.is_dev),
            )

            console.print(f"[green]✓[/green] Stored {len(result.stored_feedback_ids)} records")
            console.print(f"[yellow]⊘[/yellow] Filtered {len(result.cleaning_summary.duplicates)} duplicates")
            console.print(f"[red]✗[/red] Discarded {len(result.cleaning_summary.discarded)} items")

            crawl_run.status = "completed"
            crawl_run.finished_at = datetime.utcnow()
            crawl_run.stats = {
                "crawled": len(outputs),
                "stored": len(result.stored_feedback_ids),
                "duplicates": len(result.cleaning_summary.duplicates),
                "discarded": len(result.cleaning_summary.discarded),
            }
            await session.commit()

        except Exception as exc:
            console.print(f"[red]✗ Crawl failed: {exc}[/red]")
            crawl_run.status = "failed"
            crawl_run.finished_at = datetime.utcnow()
            await session.commit()
            raise typer.Exit(code=1)


async def _execute_platform_crawl(platform: PlatformType, query: Optional[str], limit: int):
    if platform == PlatformType.REDDIT:
        if not query:
            raise ValueError("Reddit crawls require --query (subreddit name)")
        crawler = RedditCrawler(subreddit=query, concurrent_tasks=2)
        target = crawler.build_listing_target()
        return await crawler.crawl_many([target])

    elif platform == PlatformType.TWITTER:
        if not query:
            raise ValueError("Twitter crawls require --query (search term)")
        crawler = TwitterCrawler(query=query, concurrent_tasks=2)
        target = crawler.build_listing_target()
        return await crawler.crawl_many([target])

    elif platform == PlatformType.YOUTUBE:
        if not query:
            raise ValueError("YouTube crawls require --query (video ID or channel ID)")
        # Assume query is video ID if it's 11 characters (standard YouTube video ID length)
        if len(query) == 11:
            crawler = YouTubeCrawler(video_id=query, concurrent_tasks=2)
        else:
            crawler = YouTubeCrawler(channel_id=query, concurrent_tasks=2)
        target = crawler.build_listing_target()
        return await crawler.crawl_many([target])

    elif platform == PlatformType.TRUSTPILOT:
        if not query:
            raise ValueError("Trustpilot crawls require --query (company name)")
        crawler = TrustpilotCrawler(company_name=query, concurrent_tasks=2)
        target = crawler.build_listing_target()
        return await crawler.crawl_many([target])

    elif platform == PlatformType.QUORA:
        if not query:
            raise ValueError("Quora crawls require --query (search term or topic)")
        crawler = QuoraCrawler(query=query, concurrent_tasks=2)
        target = crawler.build_listing_target()
        return await crawler.crawl_many([target])

    elif platform == PlatformType.G2:
        if not query:
            raise ValueError("G2 crawls require --query (product slug)")
        crawler = G2Crawler(product_slug=query, concurrent_tasks=2)
        target = crawler.build_listing_target()
        return await crawler.crawl_many([target])


@app.command()
def status(
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source name"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of recent runs to show"),
):
    """Display recent crawl run status."""
    asyncio.run(_show_status(source, limit))


async def _show_status(source_filter: Optional[str], limit: int):
    async with _SessionFactory() as session:
        query = select(CrawlRun).order_by(CrawlRun.started_at.desc()).limit(limit)

        if source_filter:
            query = query.join(DataSource).where(DataSource.name == source_filter)

        result = await session.execute(query)
        runs = result.scalars().all()

        if not runs:
            console.print("[yellow]No crawl runs found[/yellow]")
            return

        table = Table(title="Recent Crawl Runs")
        table.add_column("ID", style="cyan")
        table.add_column("Source", style="magenta")
        table.add_column("Started", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Stats", style="blue")

        for run in runs:
            stats_str = str(run.stats) if run.stats else "N/A"
            table.add_row(
                str(run.id)[:8],
                str(run.data_source_id)[:8],
                run.started_at.strftime("%Y-%m-%d %H:%M"),
                run.status,
                stats_str,
            )

        console.print(table)


@app.command()
def sources():
    """List all configured data sources."""
    asyncio.run(_list_sources())


async def _list_sources():
    async with _SessionFactory() as session:
        result = await session.execute(select(DataSource))
        sources = result.scalars().all()

        if not sources:
            console.print("[yellow]No data sources found[/yellow]")
            return

        table = Table(title="Data Sources")
        table.add_column("Name", style="cyan")
        table.add_column("Platform", style="magenta")
        table.add_column("Active", style="green")
        table.add_column("Last Crawl", style="yellow")

        for source in sources:
            last_crawl = source.last_crawl_at.strftime("%Y-%m-%d") if source.last_crawl_at else "Never"
            table.add_row(
                source.name,
                source.platform,
                "✓" if source.is_active else "✗",
                last_crawl,
            )

        console.print(table)


if __name__ == "__main__":
    app()
