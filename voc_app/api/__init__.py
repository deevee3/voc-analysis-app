"""FastAPI REST endpoints for the Voice of Customer application."""

from fastapi import APIRouter

from . import alerts, crawls, exports, feedback, insights, sources, stats, themes, webhooks

api_router = APIRouter(prefix="/api/v1")

# Register route modules
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(crawls.router, prefix="/crawls", tags=["crawls"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(insights.router, prefix="/insights", tags=["insights"])
api_router.include_router(themes.router, prefix="/themes", tags=["themes"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])

__all__ = ["api_router"]
