"""Alert detection and notification service."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from voc_app.models import AlertEvent, AlertRule, Insight

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AlertTriggerResult:
    """Result of alert rule evaluation."""

    rule: AlertRule
    triggered: bool
    matching_insights: list[Insight]
    severity: str | None = None


@dataclass(slots=True)
class AlertEvaluationSummary:
    """Summary of alert evaluation run."""

    rules_evaluated: int
    alerts_triggered: int
    trigger_results: list[AlertTriggerResult]


class AlertService:
    """Service for evaluating alert rules and managing alert events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def evaluate_rules(
        self, insights: Sequence[Insight], rules: Sequence[AlertRule] | None = None
    ) -> AlertEvaluationSummary:
        """Evaluate alert rules against insights."""
        if rules is None:
            result = await self._session.execute(
                select(AlertRule).where(AlertRule.enabled == True)
            )
            rules = list(result.scalars().all())

        trigger_results: list[AlertTriggerResult] = []
        alerts_triggered = 0

        for rule in rules:
            matching_insights = self._evaluate_rule(rule, insights)
            triggered = len(matching_insights) > 0

            if triggered and rule.threshold_value:
                # Check if volume threshold is met
                triggered = len(matching_insights) >= rule.threshold_value

            severity = None
            if triggered:
                severity = self._calculate_severity(rule, matching_insights)
                alerts_triggered += 1

                # Create alert event
                await self._create_alert_event(rule, matching_insights, severity)

            trigger_results.append(
                AlertTriggerResult(
                    rule=rule,
                    triggered=triggered,
                    matching_insights=matching_insights,
                    severity=severity,
                )
            )

        return AlertEvaluationSummary(
            rules_evaluated=len(rules),
            alerts_triggered=alerts_triggered,
            trigger_results=trigger_results,
        )

    async def get_active_alerts(
        self, *, limit: int = 50, include_resolved: bool = False
    ) -> list[AlertEvent]:
        """Retrieve active alert events."""
        query = select(AlertEvent).order_by(AlertEvent.triggered_at.desc()).limit(limit)

        if not include_resolved:
            query = query.where(AlertEvent.status == "open")

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def resolve_alert(self, alert_event_id: str, resolution_notes: str | None = None) -> AlertEvent:
        """Mark an alert as resolved."""
        result = await self._session.execute(
            select(AlertEvent).where(AlertEvent.id == alert_event_id)
        )
        alert_event = result.scalar_one()

        alert_event.status = "resolved"
        alert_event.resolved_at = datetime.utcnow()

        if resolution_notes:
            alert_event.payload = alert_event.payload or {}
            alert_event.payload["resolution_notes"] = resolution_notes

        await self._session.flush()
        return alert_event

    def _evaluate_rule(self, rule: AlertRule, insights: Sequence[Insight]) -> list[Insight]:
        """Evaluate a single rule against insights."""
        matching_insights = []

        for insight in insights:
            if self._insight_matches_rule(insight, rule):
                matching_insights.append(insight)

        return matching_insights

    def _insight_matches_rule(self, insight: Insight, rule: AlertRule) -> bool:
        """Check if an insight matches an alert rule."""
        rule_type = rule.rule_type.lower()

        # Sentiment threshold rule
        if rule_type == "sentiment_threshold":
            if rule.threshold_value and insight.sentiment_score is not None:
                return insight.sentiment_score <= rule.threshold_value

        # Keyword rule
        elif rule_type == "keyword":
            if rule.keywords:
                text = f"{insight.summary} {insight.pain_points} {insight.feature_requests}".lower()
                keywords = rule.keywords.get("terms", [])
                return any(kw.lower() in text for kw in keywords)

        # Competitor mention rule
        elif rule_type == "competitor_mention":
            if rule.competitor_filters and insight.competitor_mentions:
                competitors = rule.competitor_filters.get("names", [])
                mentioned = [cm.get("competitor_name") for cm in insight.competitor_mentions]
                return any(comp in mentioned for comp in competitors)

        # Urgency rule
        elif rule_type == "urgency":
            if rule.threshold_value and insight.urgency_level:
                return insight.urgency_level >= rule.threshold_value

        # Volume spike detection (handled at aggregate level)
        elif rule_type == "volume_spike":
            return True  # Include all insights for volume calculation

        return False

    def _calculate_severity(self, rule: AlertRule, insights: list[Insight]) -> str:
        """Calculate alert severity based on rule and insights."""
        if rule.rule_type == "sentiment_threshold":
            avg_sentiment = sum(i.sentiment_score or 0 for i in insights) / len(insights)
            if avg_sentiment < -0.7:
                return "critical"
            elif avg_sentiment < -0.4:
                return "high"
            else:
                return "medium"

        elif rule.rule_type == "urgency":
            max_urgency = max((i.urgency_level or 0) for i in insights)
            if max_urgency >= 4:
                return "critical"
            elif max_urgency >= 3:
                return "high"
            else:
                return "medium"

        # Volume-based severity
        if len(insights) >= 10:
            return "high"
        elif len(insights) >= 5:
            return "medium"
        else:
            return "low"

    async def _create_alert_event(
        self, rule: AlertRule, insights: list[Insight], severity: str
    ) -> AlertEvent:
        """Create an alert event in the database."""
        alert_event = AlertEvent(
            alert_rule_id=rule.id,
            primary_insight_id=insights[0].id if insights else None,
            triggered_at=datetime.utcnow(),
            severity=severity,
            status="open",
            payload={
                "insight_count": len(insights),
                "insight_ids": [str(i.id) for i in insights],
                "rule_type": rule.rule_type,
            },
        )
        self._session.add(alert_event)
        await self._session.flush()

        logger.info(
            f"Created alert event for rule '{rule.name}' with {len(insights)} insights (severity: {severity})"
        )

        return alert_event


async def evaluate_alert_rules(
    session: AsyncSession,
    insights: Sequence[Insight],
    rules: Sequence[AlertRule] | None = None,
) -> AlertEvaluationSummary:
    """Convenience helper for evaluating alert rules."""
    service = AlertService(session)
    return await service.evaluate_rules(insights, rules)
