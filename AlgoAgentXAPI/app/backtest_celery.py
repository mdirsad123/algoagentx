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

SANDBOX_TASK_NAME = "app.tasks.run_strategy_sandbox_v2_task"


def _has_registered_sandbox_task(names) -> bool:
    """Celery can add annotations like `[rate_limit=None]` to task names."""
    return any(
        isinstance(name, str) and
        (name == SANDBOX_TASK_NAME or name.startswith(SANDBOX_TASK_NAME + " ["))
        for name in (names or ())
    )


def sandbox_worker_state(timeout: float = 1.5) -> str:
    """Diagnostic, not a dispatch gate when remote control cannot reply.

    `ready`: a backtest-queue consumer explicitly reports this task.
    `misconfigured`: that consumer replied with tasks but lacks the task.
    `unconfirmed`: workers did not reply consistently/quickly enough.

    This avoids false HTTP 503s when a perfectly healthy worker is busy,
    its remote-control responses time out, or unrelated Celery workers reply.
    Redis delivery and the PostgreSQL job row remain authoritative.
    """
    try:
        inspector = backtest_app.control.inspect(timeout=timeout)
        queues = inspector.active_queues() if inspector is not None else None
        if not queues:
            return "unconfirmed"
        consumers = [worker for worker, declared in queues.items() if any(
            isinstance(queue, dict) and queue.get("name") == "backtest"
            for queue in (declared or [])
        )]
        if not consumers:
            return "unconfirmed"
        registered = inspector.registered()
        if not registered:
            return "unconfirmed"
        observed = [registered[worker] for worker in consumers if worker in registered]
        if not observed:
            return "unconfirmed"
        if any(_has_registered_sandbox_task(tasks) for tasks in observed):
            return "ready"
        # Only report a definite mismatch if *every* responding backtest
        # consumer was inspected and none registers the Sandbox task.
        return "misconfigured" if len(observed) == len(consumers) else "unconfirmed"
    except Exception:
        return "unconfirmed"


def is_backtest_queue_consumed(timeout: float = 1.5) -> bool:
    """Strict check for diagnostics/tests, not a brittle HTTP preflight."""
    return sandbox_worker_state(timeout=timeout) == "ready"
