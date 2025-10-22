"""Celery tasks for alert detection and notification."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, select

from voc_app.celery_app import app
from voc_app.database import _SessionFactory
from voc_app.models import AlertEvent, AlertRule, Insight

logger = logging.getLogger(__name__)


@app.task(bind=True)
def evaluate_alert_rules(self) -> dict:
    """Evaluate all active alert rules against recent insights."""
    return asyncio.run(_evaluate_alert_rules_async())


async def _evaluate_alert_rules_async() -> dict:
    """Async implementation of alert rule evaluation."""
    async with _SessionFactory() as session:
        # Load active alert rules
        result = await session.execute(
            select(AlertRule).where(AlertRule.enabled == True)
        )
        alert_rules = list(result.scalars().all())

        if not alert_rules:
            logger.info("No active alert rules found")
            return {"success": True, "rules_evaluated": 0, "alerts_triggered": 0}

        # Get recent insights (last hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        insights_result = await session.execute(
            select(Insight).where(Insight.created_at >= cutoff_time)
        )
        recent_insights = list(insights_result.scalars().all())

        if not recent_insights:
            logger.info("No recent insights to evaluate")
            return {"success": True, "rules_evaluated": 0, "alerts_triggered": 0}

        logger.info(
            f"Evaluating {len(alert_rules)} rules against {len(recent_insights)} insights"
        )

        alerts_triggered = 0

        for rule in alert_rules:
            triggered_insights = _evaluate_rule(rule, recent_insights)

            if triggered_insights:
                # Create alert event
                alert_event = AlertEvent(
                    alert_rule_id=rule.id,
                    primary_insight_id=triggered_insights[0].id,
                    triggered_at=datetime.utcnow(),
                    severity=_calculate_severity(rule, triggered_insights),
                    status="open",
                    payload={
                        "insight_count": len(triggered_insights),
                        "insight_ids": [str(i.id) for i in triggered_insights],
                    },
                )
                session.add(alert_event)
                alerts_triggered += 1

                logger.info(
                    f"Alert triggered: {rule.name} with {len(triggered_insights)} insights"
                )

        await session.commit()

        return {
            "success": True,
            "rules_evaluated": len(alert_rules),
            "alerts_triggered": alerts_triggered,
        }


def _evaluate_rule(rule: AlertRule, insights: list[Insight]) -> list[Insight]:
    """Evaluate a single alert rule against insights."""
    matching_insights = []

    for insight in insights:
        if _insight_matches_rule(insight, rule):
            matching_insights.append(insight)

    # Check if threshold is met
    if rule.threshold_value and len(matching_insights) < rule.threshold_value:
        return []

    return matching_insights


def _insight_matches_rule(insight: Insight, rule: AlertRule) -> bool:
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
            mentioned = [
                cm.get("competitor_name") for cm in insight.competitor_mentions
            ]
            return any(comp in mentioned for comp in competitors)

    # Urgency rule
    elif rule_type == "urgency":
        if rule.threshold_value and insight.urgency_level:
            return insight.urgency_level >= rule.threshold_value

    return False


def _calculate_severity(rule: AlertRule, insights: list[Insight]) -> str:
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


@app.task(bind=True)
def send_alert_notification(self, alert_event_id: str) -> dict:
    """Send notification for an alert event."""
    return asyncio.run(_send_alert_notification_async(alert_event_id))


async def _send_alert_notification_async(alert_event_id: str) -> dict:
    """Async implementation of alert notification."""
    async with _SessionFactory() as session:
        result = await session.execute(
            select(AlertEvent).where(AlertEvent.id == alert_event_id)
        )
        alert_event = result.scalar_one_or_none()

        if not alert_event:
            logger.warning(f"Alert event {alert_event_id} not found")
            return {"success": False, "error": "Alert event not found"}

        # Load alert rule for channel configuration
        rule_result = await session.execute(
            select(AlertRule).where(AlertRule.id == alert_event.alert_rule_id)
        )
        alert_rule = rule_result.scalar_one()

        # TODO: Implement actual notification delivery
        # For now, just log
        logger.info(
            f"Sending alert notification: {alert_rule.name} "
            f"(severity: {alert_event.severity})"
        )

        # Example channels: email, slack, webhook
        channels = alert_rule.channels or {}

        notification_results = []
        if channels.get("email"):
            notification_results.append({"channel": "email", "success": True})

        if channels.get("slack"):
            notification_results.append({"channel": "slack", "success": True})

        return {
            "success": True,
            "alert_event_id": alert_event_id,
            "notifications": notification_results,
        }
