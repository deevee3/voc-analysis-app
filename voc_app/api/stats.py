"""API endpoints for dashboard statistics."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from voc_app.models import AlertEvent, DataSource, Insight

from .dependencies import DatabaseSession

router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview(session: DatabaseSession):
    """Get high-level dashboard metrics.
    
    Returns:
        - Total insights count
        - Average sentiment score
        - Active data sources count
        - Open alerts count
        - Recent activity trends
    """
    # Total insights
    total_insights_result = await session.execute(
        select(func.count(Insight.id))
    )
    total_insights = total_insights_result.scalar() or 0
    
    # Average sentiment
    avg_sentiment_result = await session.execute(
        select(func.avg(Insight.sentiment_score)).where(
            Insight.sentiment_score.isnot(None)
        )
    )
    avg_sentiment = avg_sentiment_result.scalar()
    avg_sentiment = float(avg_sentiment) if avg_sentiment else 0.0
    
    # Active sources
    active_sources_result = await session.execute(
        select(func.count(DataSource.id)).where(DataSource.is_active == True)
    )
    active_sources = active_sources_result.scalar() or 0
    
    # Open alerts
    open_alerts_result = await session.execute(
        select(func.count(AlertEvent.id)).where(AlertEvent.status == "open")
    )
    open_alerts = open_alerts_result.scalar() or 0
    
    # Sentiment breakdown
    sentiment_breakdown_result = await session.execute(
        select(
            Insight.sentiment_label,
            func.count(Insight.id).label("count")
        )
        .where(Insight.sentiment_label.isnot(None))
        .group_by(Insight.sentiment_label)
    )
    sentiment_breakdown = {
        row[0]: row[1] for row in sentiment_breakdown_result.all()
    }
    
    # Recent insights (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_insights_result = await session.execute(
        select(func.count(Insight.id)).where(
            Insight.created_at >= seven_days_ago
        )
    )
    recent_insights = recent_insights_result.scalar() or 0
    
    return {
        "total_insights": total_insights,
        "avg_sentiment": round(avg_sentiment, 2),
        "active_sources": active_sources,
        "open_alerts": open_alerts,
        "sentiment_breakdown": sentiment_breakdown,
        "recent_insights_7d": recent_insights,
    }


@router.get("/sentiment-trend")
async def get_sentiment_trend(
    session: DatabaseSession,
    days: int = 30,
):
    """Get sentiment trend over time.
    
    Args:
        days: Number of days to look back (default: 30)
        
    Returns:
        Daily sentiment averages
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get daily sentiment averages
    result = await session.execute(
        select(
            func.date(Insight.created_at).label("date"),
            func.avg(Insight.sentiment_score).label("avg_sentiment"),
            func.count(Insight.id).label("count")
        )
        .where(Insight.created_at >= cutoff_date)
        .where(Insight.sentiment_score.isnot(None))
        .group_by(func.date(Insight.created_at))
        .order_by(func.date(Insight.created_at))
    )
    
    trend_data = [
        {
            "date": str(row[0]),
            "avg_sentiment": float(row[1]) if row[1] else 0.0,
            "count": row[2],
        }
        for row in result.all()
    ]
    
    return {"trend": trend_data}


@router.get("/recent-insights")
async def get_recent_insights(
    session: DatabaseSession,
    limit: int = 10,
):
    """Get most recent insights.
    
    Args:
        limit: Number of insights to return (default: 10)
        
    Returns:
        List of recent insights with basic info
    """
    result = await session.execute(
        select(Insight)
        .order_by(Insight.created_at.desc())
        .limit(limit)
    )
    insights = result.scalars().all()
    
    return {
        "insights": [
            {
                "id": str(insight.id),
                "summary": insight.summary,
                "sentiment_score": float(insight.sentiment_score) if insight.sentiment_score else None,
                "sentiment_label": insight.sentiment_label,
                "urgency_level": insight.urgency_level,
                "created_at": insight.created_at.isoformat() if insight.created_at else None,
            }
            for insight in insights
        ]
    }
