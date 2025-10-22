"""Celery tasks for insight processing and classification."""

from __future__ import annotations

import asyncio
import logging

from celery import Task
from sqlalchemy import select

from voc_app.celery_app import app
from voc_app.database import _SessionFactory
from voc_app.models import Feedback, Insight
from voc_app.processors.classifier import classify_insights
from voc_app.processors.clustering import discover_emerging_themes
from voc_app.processors.extractor import extract_insights
from voc_app.services.insights import persist_insights

logger = logging.getLogger(__name__)


class ProcessingTask(Task):
    """Base task for processing operations."""

    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 2}
    retry_backoff = True


@app.task(base=ProcessingTask, bind=True)
def extract_feedback_insights(self, feedback_ids: list[str]) -> dict:
    """Extract insights from feedback using GPT."""
    return asyncio.run(_extract_feedback_insights_async(feedback_ids))


async def _extract_feedback_insights_async(feedback_ids: list[str]) -> dict:
    """Async implementation of insight extraction."""
    async with _SessionFactory() as session:
        # Load feedback
        result = await session.execute(
            select(Feedback).where(Feedback.id.in_(feedback_ids))
        )
        feedback_items = list(result.scalars().all())

        if not feedback_items:
            logger.warning(f"No feedback found for IDs: {feedback_ids}")
            return {"success": False, "error": "No feedback found"}

        try:
            # Extract insights
            logger.info(f"Extracting insights from {len(feedback_items)} feedback items")
            summary = await extract_insights(feedback_items, batch_size=5)

            # Persist insights
            insights_list = await persist_insights(session, summary.results)
            await session.commit()

            logger.info(
                f"Extracted {summary.success_count} insights, "
                f"failed {summary.failure_count}, "
                f"cost ${summary.total_cost.estimated_cost_usd:.4f}"
            )

            return {
                "success": True,
                "insights_created": len(insights_list),
                "success_count": summary.success_count,
                "failure_count": summary.failure_count,
                "total_cost_usd": summary.total_cost.estimated_cost_usd,
            }

        except Exception as exc:
            logger.exception(f"Insight extraction failed: {exc}")
            raise


@app.task(base=ProcessingTask, bind=True)
def classify_insight_themes(self, insight_ids: list[str]) -> dict:
    """Classify insights into themes."""
    return asyncio.run(_classify_insight_themes_async(insight_ids))


async def _classify_insight_themes_async(insight_ids: list[str]) -> dict:
    """Async implementation of theme classification."""
    async with _SessionFactory() as session:
        # Load insights
        result = await session.execute(
            select(Insight).where(Insight.id.in_(insight_ids))
        )
        insights_list = list(result.scalars().all())

        if not insights_list:
            logger.warning(f"No insights found for IDs: {insight_ids}")
            return {"success": False, "error": "No insights found"}

        try:
            # Classify themes
            logger.info(f"Classifying {len(insights_list)} insights into themes")
            results = await classify_insights(session, insights_list, use_llm=True)

            # Count successes
            success_count = sum(1 for r in results if r.success)
            total_matches = sum(len(r.matches) for r in results if r.success)

            await session.commit()

            logger.info(
                f"Classified {success_count}/{len(insights_list)} insights, "
                f"total {total_matches} theme matches"
            )

            return {
                "success": True,
                "classified_count": success_count,
                "total_matches": total_matches,
            }

        except Exception as exc:
            logger.exception(f"Theme classification failed: {exc}")
            raise


@app.task(bind=True)
def process_pending_feedback(self) -> dict:
    """Process feedback items that don't have insights yet."""
    return asyncio.run(_process_pending_feedback_async())


async def _process_pending_feedback_async() -> dict:
    """Async implementation of pending feedback processing."""
    async with _SessionFactory() as session:
        # Find feedback without insights
        subquery = select(Insight.feedback_id).subquery()
        result = await session.execute(
            select(Feedback)
            .where(~Feedback.id.in_(select(subquery)))
            .limit(50)  # Process in batches
        )
        pending_feedback = list(result.scalars().all())

        if not pending_feedback:
            logger.info("No pending feedback to process")
            return {"success": True, "processed": 0}

        logger.info(f"Processing {len(pending_feedback)} pending feedback items")

        # Extract insights
        feedback_ids = [str(f.id) for f in pending_feedback]
        extract_feedback_insights.delay(feedback_ids)

        return {"success": True, "scheduled": len(feedback_ids)}


@app.task(bind=True)
def discover_emerging_themes(self) -> dict:
    """Discover new themes from recent insights using clustering."""
    return asyncio.run(_discover_emerging_themes_async())


async def _discover_emerging_themes_async() -> dict:
    """Async implementation of theme discovery."""
    async with _SessionFactory() as session:
        # Get recent insights without theme assignments
        result = await session.execute(
            select(Insight).order_by(Insight.created_at.desc()).limit(100)
        )
        insights_list = list(result.scalars().all())

        if len(insights_list) < 10:
            logger.info("Not enough insights for theme discovery")
            return {"success": True, "clusters_found": 0}

        try:
            logger.info(f"Discovering themes from {len(insights_list)} insights")
            summary = await discover_emerging_themes(insights_list, min_cluster_size=5)

            logger.info(
                f"Discovered {len(summary.clusters)} clusters, "
                f"{summary.noise_count} noise points"
            )

            return {
                "success": True,
                "clusters_found": len(summary.clusters),
                "noise_count": summary.noise_count,
                "total_insights": summary.total_insights,
            }

        except Exception as exc:
            logger.exception(f"Theme discovery failed: {exc}")
            raise
