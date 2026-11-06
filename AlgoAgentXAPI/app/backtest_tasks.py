from app.backtest_celery import backtest_app


@backtest_app.task(name="app.tasks.run_backtest_v2_task", max_retries=0)
def run_backtest(job_id, *legacy_arguments):
    import asyncio
    from app.tasks import _run_backtest_v2_async
    return asyncio.run(_run_backtest_v2_async(str(job_id)))