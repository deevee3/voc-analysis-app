"""Service for persisting extracted insights to the database."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from voc_app.models import Insight
from voc_app.processors.extractor import ExtractionResult
from voc_app.processors.schemas import InsightExtraction


class InsightPersistenceService:
    """Handles storage of extracted insights with source attribution."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist_extraction_results(
        self, results: Sequence[ExtractionResult]
    ) -> list[Insight]:
        """Convert extraction results to database insights and persist."""
        insights: list[Insight] = []

        for result in results:
            if not result.success or not result.extraction:
                continue

            insight = self._map_extraction_to_insight(result)
            insights.append(insight)

        if insights:
            self._session.add_all(insights)
            await self._session.flush()

        return insights

    def _map_extraction_to_insight(self, result: ExtractionResult) -> Insight:
        """Map ExtractionResult to Insight model."""
        extraction = result.extraction

        # Map pain points
        pain_points = [
            {
                "description": pp.description,
                "severity": pp.severity,
                "category": pp.category,
            }
            for pp in extraction.pain_points
        ]

        # Map feature requests
        feature_requests = [
            {
                "description": fr.description,
                "priority": fr.priority,
                "use_case": fr.use_case,
            }
            for fr in extraction.feature_requests
        ]

        # Map competitor mentions
        competitor_mentions = [
            {
                "competitor_name": cm.competitor_name,
                "context": cm.context,
                "sentiment": cm.sentiment,
            }
            for cm in extraction.competitor_mentions
        ]

        # Map customer context
        customer_context = {
            "user_segment": extraction.customer_context.user_segment,
            "experience_level": extraction.customer_context.experience_level,
            "use_case_domain": extraction.customer_context.use_case_domain,
        }

        return Insight(
            feedback_id=result.feedback_id,
            sentiment_score=extraction.sentiment.score,
            sentiment_label=extraction.sentiment.label,
            summary=extraction.summary,
            pain_points=pain_points if pain_points else None,
            feature_requests=feature_requests if feature_requests else None,
            competitor_mentions=competitor_mentions if competitor_mentions else None,
            customer_context=customer_context,
            journey_stage=extraction.journey_stage,
            urgency_level=extraction.urgency_level,
        )


async def persist_insights(
    session: AsyncSession,
    results: Sequence[ExtractionResult],
) -> list[Insight]:
    """Convenience helper for persisting extraction results."""
    service = InsightPersistenceService(session)
    return await service.persist_extraction_results(results)
