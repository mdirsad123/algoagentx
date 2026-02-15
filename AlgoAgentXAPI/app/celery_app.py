from celery import Celery
from celery.schedules import crontab
from .core.config import settings

# Initialize Celery with Redis backend
celery_app = Celery(
    "AlgoAgentXAPI",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks",
        "app.services.ai_screener.job_handlers"
    ]
)

# Configure Celery settings
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    
    # Beat scheduler settings
    beat_schedule={
        # Backtest cleanup task - runs daily at 2 AM UTC
        "cleanup-old-jobs": {
            "task": "app.tasks.cleanup_old_jobs_task",
            "schedule": crontab(hour=2, minute=0),
            "args": (30, 100),  # Keep 30 days, batch size 100
        },
        
        # AI Screener scheduled runs - every 30 minutes
        "ai-screener-news-refresh-scheduled": {
            "task": "app.tasks.run_ai_screener_news_task",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
            "args": (
                "scheduled-news-refresh",  # job_id
                "system",  # user_id
                {
                    "symbols": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"],
                    "top_n": 10
                }
            ),
        },
        
        "ai-screener-announcements-refresh-scheduled": {
            "task": "app.tasks.run_ai_screener_announcements_task",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
            "args": (
                "scheduled-announcements-refresh",  # job_id
                "system",  # user_id
                {
                    "symbols": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"],
                    "top_n": 10
                }
            ),
        },
    }
)


def is_celery_available() -> bool:
    """Check if Celery is available and configured."""
    try:
        # Try to ping the broker
        with celery_app.connection_or_acquire() as conn:
            conn.ensure_connection(max_retries=1)
            return True
    except Exception:
        return False


# Export the app
__all__ = ["celery_app", "is_celery_available"]