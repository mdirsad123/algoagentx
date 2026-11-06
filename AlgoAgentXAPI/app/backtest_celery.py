"""Dedicated worker configuration; does not change live worker policies."""
from celery import Celery
from app.core.config import settings

backtest_app = Celery("algoagentx_backtest", broker=settings.redis_url, include=["app.backtest_tasks"])
backtest_app.conf.update(
    task_default_queue="backtest",
    task_serializer="json", accept_content=["json"], result_serializer="json",
    task_ignore_result=True, enable_utc=True, timezone="UTC",
    worker_concurrency=1, worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1,
    worker_proc_alive_timeout=120,
    task_acks_late=True, task_reject_on_worker_lost=True,
    # Keep compute alive on broker-only interruption; PG ownership fences replay.
    worker_cancel_long_running_tasks_on_connection_loss=False,
    broker_connection_retry=True, broker_connection_retry_on_startup=True,
    broker_connection_max_retries=None,
    broker_transport_options={"visibility_timeout": 21600, "socket_connect_timeout": 10,
                              "socket_timeout": 10, "socket_keepalive": True, "health_check_interval": 30},
    task_time_limit=14400,
)