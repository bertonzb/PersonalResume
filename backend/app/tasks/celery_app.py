from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "deepscribe",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=600,
    task_time_limit=900,
    imports=("app.tasks.jobs",),
    beat_schedule={
        "weekly-report-monday-9am": {
            "task": "deep_research",
            "schedule": 0.0,  # 每 60 秒（开发调试），生产改为 crontab(hour=9, minute=0, day_of_week=1)
            "args": ("system", "weekly_report"),
        },
    },
)
