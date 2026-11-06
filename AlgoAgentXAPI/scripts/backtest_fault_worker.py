"""Fault-injection worker; hard-gated to the isolated test database."""
import asyncio
import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.backtest_celery import backtest_app
from app.services.backtest_jobs import execute_job, execution_engine, guard_finalization
from app.core.config import settings

if "backtest_repair_test" not in settings.database_url:
    raise RuntimeError("Fault injection is forbidden outside the isolated test database")


@backtest_app.task(name="backtest_test.execute", ignore_result=True)
def execute_test(job_id):
    async def run():
        engine = execution_engine()
        try:
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            async def body(db, user, payload, plan):
                attempts = (await db.execute(text("SELECT attempts FROM backtest_execution WHERE job_id=:job"), {"job": job_id})).scalar_one()
                if payload.get("kill_first") and attempts == 1:
                    os.kill(os.getpid(), signal.SIGKILL)
                await asyncio.sleep(payload.get("delay", 0))
                await db.execute(text("INSERT INTO backtest_test_effect (job_id, amount) VALUES (:job,10)"), {"job": job_id})
                await guard_finalization(db)
                await db.execute(text("UPDATE job_status SET status='completed' WHERE id=:job"), {"job": job_id})
                await db.commit()
                return {"status": "completed"}
            return await execute_job(job_id, sessions, body)
        finally:
            await engine.dispose()
    return asyncio.run(run())


if __name__ == "__main__":
    backtest_app.worker_main(["worker", "--loglevel=info", "--concurrency=1", "--prefetch-multiplier=1",
                             "--max-tasks-per-child=1", "--without-gossip", "--without-mingle",
                             "-Q", "backtest", "-n", "backtest_test@%h"])