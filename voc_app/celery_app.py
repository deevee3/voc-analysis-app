"""Celery application configuration for background tasks."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from voc_app.config import get_settings

settings = get_settings()

app = Celery(
    "voc_app",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "voc_app.tasks.crawl_tasks",
        "voc_app.tasks.processing_tasks",
        "voc_app.tasks.alert_tasks",
    ],
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,  # 24 hours
)

# Periodic task schedule
app.conf.beat_schedule = {
    "scheduled-crawls": {
        "task": "voc_app.tasks.crawl_tasks.run_scheduled_crawls",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    "process-pending-feedback": {
        "task": "voc_app.tasks.processing_tasks.process_pending_feedback",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
    "check-alerts": {
        "task": "voc_app.tasks.alert_tasks.evaluate_alert_rules",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    "discover-themes": {
        "task": "voc_app.tasks.processing_tasks.discover_emerging_themes",
        "schedule": crontab(hour="*/6"),  # Every 6 hours
    },
}

# Task routing
app.conf.task_routes = {
    "voc_app.tasks.crawl_tasks.*": {"queue": "crawl"},
    "voc_app.tasks.processing_tasks.*": {"queue": "processing"},
    "voc_app.tasks.alert_tasks.*": {"queue": "alerts"},
}


if __name__ == "__main__":
    app.start()
