"""Compare old ORM vs projected recovery query using stored data only."""
import asyncio
import json
import resource
import sys
import time
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from app.db.models import LiveMarketCandle
from app.tasks import _fresh_async_engine_and_sessionmaker


async def main():
    engine, sessions = _fresh_async_engine_and_sessionmaker()
    try:
        async with sessions() as db:
            cols = ('candle_time', 'open', 'high', 'low', 'close', 'volume', 'source', 'is_closed')
            stmt = select(LiveMarketCandle) if sys.argv[1] == 'orm' else select(*(getattr(LiveMarketCandle, k) for k in cols))
            stmt = stmt.where(LiveMarketCandle.deployment_id == UUID('4362f853-69aa-431f-b45f-3733ce3181ae'),
                              LiveMarketCandle.candle_time > datetime.fromisoformat('2026-11-17T22:05:00+00:00'))
            start = time.monotonic()
            before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            rows = (await db.execute(stmt)).all()
            print(json.dumps({'query': sys.argv[1], 'rows': len(rows), 'seconds': time.monotonic()-start,
                              'baseline_rss_kib': before, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}), flush=True)
    finally:
        await engine.dispose()


asyncio.run(main())