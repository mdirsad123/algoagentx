"""Dedicated durable dispatch loop. Never computes or imports live runners."""
import asyncio
import logging
from pathlib import Path
from app.services.backtest_jobs import recover_jobs

logger = logging.getLogger(__name__)


async def main():
    while True:
        try:
            await recover_jobs()
            Path("/tmp/backtest-dispatch-heartbeat").touch()
        except Exception:
            logger.exception("Backtest durable dispatch failed; pending jobs remain in PostgreSQL")
        await asyncio.sleep(30)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())