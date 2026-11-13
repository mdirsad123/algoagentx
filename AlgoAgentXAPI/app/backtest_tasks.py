from app.backtest_celery import backtest_app
from celery.signals import task_failure, task_revoked


@backtest_app.task(name="app.tasks.run_backtest_v2_task", max_retries=0)
def run_backtest(job_id, *legacy_arguments):
    import asyncio
    from app.tasks import _run_backtest_v2_async
    return asyncio.run(_run_backtest_v2_async(str(job_id)))

@backtest_app.task(name="app.tasks.run_strategy_sandbox_v2_task", max_retries=0)
def run_admin_strategy_sandbox(job_id, admin_user_id, strategy_id, payload_dict):
    """Run admin sandbox on the existing isolated backtest CPU worker.

    Import lazily, so the dedicated worker does not import live strategy services
    just to register a task. Celery's task name matches the API dispatch name.
    """
    import asyncio
    from app.tasks import _run_strategy_sandbox_v2_async

    return asyncio.run(
        _run_strategy_sandbox_v2_async(
            str(job_id), str(admin_user_id), str(strategy_id), payload_dict
        )
    )


def _record_sandbox_terminal(job_id, status, message):
    import asyncio
    import logging
    from app.tasks import _fresh_async_engine_and_sessionmaker
    from app.services.sandbox_jobs import finish_sandbox

    async def record():
        engine, factory = _fresh_async_engine_and_sessionmaker()
        try:
            async with factory() as db:
                await finish_sandbox(db, str(job_id), status, message, {"error": message})
        finally:
            await engine.dispose()

    try:
        asyncio.run(record())
    except Exception:
        logging.getLogger(__name__).exception("Sandbox terminal status persistence failed job=%s", job_id)


@task_failure.connect
def sandbox_task_failed(sender=None, task_id=None, args=None, exception=None, **kwargs):
    if getattr(sender, "name", None) == "app.tasks.run_strategy_sandbox_v2_task":
        _record_sandbox_terminal(args[0] if args else task_id, "failed", str(exception or "Sandbox worker failed"))


@task_revoked.connect
def sandbox_task_revoked(request=None, terminated=False, expired=False, **kwargs):
    if getattr(request, "name", None) == "app.tasks.run_strategy_sandbox_v2_task":
        args = getattr(request, "args", None)
        message = "Sandbox task expired" if expired else "Sandbox task terminated" if terminated else "Sandbox task revoked"
        _record_sandbox_terminal(args[0] if args else request.id, "revoked", message)
