"""Command-line interface for the Voice of Customer application."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import delete, func, select
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
def seed_demo_data(
    force: bool = typer.Option(
        False,
        "--force",
        help="Delete existing demo records before seeding",
    ),
):
    """Seed the database with demo data for dashboards and insights."""

    asyncio.run(_seed_demo_data(force))


async def _seed_demo_data(force: bool) -> None:
    console.print("[cyan]Seeding demo data...[/cyan]")

    async with _SessionFactory() as session:
        if force:
            console.print("[yellow]Clearing existing demo records...[/yellow]")
            await session.execute(delete(AlertEvent))
            await session.execute(delete(AlertRule))
            await session.execute(delete(InsightThemeLink))
            await session.execute(delete(Theme))
            await session.execute(delete(Insight))
            await session.execute(delete(Feedback))
            await session.execute(delete(CrawlRun))
            await session.execute(delete(DataSource))
            await session.commit()

        existing_count = await session.execute(select(func.count(Insight.id)))
        if existing_count.scalar_one() > 0:
            console.print(
                "[yellow]Insights already exist. Use --force to reseed demo data.[/yellow]"
            )
            return

        now = datetime.now(timezone.utc)

        data_sources = [
            DataSource(
                name="Reddit Brand Mentions",
                platform="reddit",
                is_active=True,
                last_crawl_at=now - timedelta(hours=6),
            ),
            DataSource(
                name="Support Tickets",
                platform="zendesk",
                is_active=True,
                last_crawl_at=now - timedelta(hours=2),
            ),
        ]
        session.add_all(data_sources)
        await session.flush()

        feedback_items = [
            Feedback(
                data_source_id=data_sources[0].id,
                raw_content="Battery drains within two hours even on standby.",
                clean_content="battery drains within two hours even on standby",
                language="en",
                posted_at=now - timedelta(days=2),
                url="https://reddit.com/r/brandname/posts/123",
                extra_metadata={"platform": "reddit", "subreddit": "brandname"},
            ),
            Feedback(
                data_source_id=data_sources[0].id,
                raw_content="Really happy with the new dashboard layout!",
                clean_content="really happy with the new dashboard layout",
                language="en",
                posted_at=now - timedelta(days=1, hours=3),
                url="https://reddit.com/r/brandname/posts/124",
                extra_metadata={"platform": "reddit", "subreddit": "brandname"},
            ),
            Feedback(
                data_source_id=data_sources[1].id,
                raw_content="Order #4567 still hasn't shipped after two weeks.",
                clean_content="order 4567 still hasn't shipped after two weeks",
                language="en",
                posted_at=now - timedelta(hours=20),
                url="https://support.brand.com/tickets/4567",
                extra_metadata={"channel": "email"},
            ),
        ]
        session.add_all(feedback_items)
        await session.flush()

        insights = [
            Insight(
                feedback_id=feedback_items[0].id,
                summary="Customers report severe battery drain within hours of use.",
                sentiment_score=-0.75,
                sentiment_label="negative",
                urgency_level=5,
                journey_stage="post_purchase",
                pain_points={"hardware": "battery longevity"},
            ),
            Insight(
                feedback_id=feedback_items[1].id,
                summary="Positive feedback on the redesigned analytics dashboard UI.",
                sentiment_score=0.65,
                sentiment_label="positive",
                urgency_level=1,
                journey_stage="advocacy",
                feature_requests={"dashboard": "dark mode toggle"},
            ),
            Insight(
                feedback_id=feedback_items[2].id,
                summary="Customers experience severe shipping delays beyond promised window.",
                sentiment_score=-0.5,
                sentiment_label="negative",
                urgency_level=4,
                journey_stage="onboarding",
                customer_context={"order_id": "4567"},
            ),
        ]
        session.add_all(insights)
        await session.flush()

        themes = [
            Theme(name="Battery", description="Hardware battery issues", is_system=False),
            Theme(name="Shipping", description="Fulfillment and logistics", is_system=False),
            Theme(name="Product", description="Product experience", is_system=False),
        ]
        session.add_all(themes)
        await session.flush()

        theme_links = [
            InsightThemeLink(insight_id=insights[0].id, theme_id=themes[0].id),
            InsightThemeLink(insight_id=insights[0].id, theme_id=themes[2].id),
            InsightThemeLink(insight_id=insights[1].id, theme_id=themes[2].id),
            InsightThemeLink(insight_id=insights[2].id, theme_id=themes[1].id),
        ]
        session.add_all(theme_links)

        alert_rule = AlertRule(
            name="Negative Sentiment Spike",
            rule_type="sentiment_threshold",
            threshold_value=-0.5,
            enabled=True,
            channels={"webhook": True},
        )
        session.add(alert_rule)
        await session.flush()

        alert_event = AlertEvent(
            alert_rule_id=alert_rule.id,
            primary_insight_id=insights[0].id,
            triggered_at=now - timedelta(hours=1),
            severity="high",
            status="open",
            payload={
                "sentiment_score": -0.75,
                "insight_summary": insights[0].summary,
            },
        )
        session.add(alert_event)

        await session.commit()

        console.print("[green]✓[/green] Demo data seeded successfully")


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
                cleaning_options=CleaningOptions(min_characters=10),
                storage_options=StorageOptions(store_files=settings.is_dev),
            )

            console.print(f"[green]✓[/green] Stored {len(result.stored_feedback_ids)} records")
            console.print(f"[yellow]⊘[/yellow] Filtered {len(result.cleaning_summary.duplicates)} duplicates")
            console.print(f"[red]✗[/red] Discarded {len(result.cleaning_summary.discarded)} items")

            if result.cleaning_summary.discarded:
                discarded_rows = [
                    (
                        record.discard_reason or "unknown",
                        len(record.cleaned_text),
                    )
                    for record in result.cleaning_summary.discarded
                ]
                console.print("[yellow]Discard reasons:[/yellow] " + str(discarded_rows))

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
