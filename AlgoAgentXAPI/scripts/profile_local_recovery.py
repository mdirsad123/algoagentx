"""Stored-candle CPU/RSS baseline. Read-only DB; no broker adapter or orders."""
import asyncio
import json
import resource
import sys
import time
from uuid import UUID

from sqlalchemy import select
from app.tasks import _fresh_async_engine_and_sessionmaker
from app.db.models import StrategyDeployment, Strategy
from app.services.live.broker_candle_service import load_live_candles_for_runner
from app.services.live.strategy_runner import _candles_to_dataframe
from app.services.strategy_registry import resolve_strategy
from app.services.live.incremental_adapter_registry import select_registered_adapter
from app.core.config import settings


START = time.monotonic()


def mark(stage, **fields):
    print(json.dumps(dict(stage=stage, seconds=round(time.monotonic()-START, 3),
                         peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, **fields)), flush=True)


async def main():
    assert settings.database_url.split('@')[-1].startswith('postgres_prod:')
    engine, sessions = _fresh_async_engine_and_sessionmaker()
    try:
        async with sessions() as db:
            dep = (await db.execute(select(StrategyDeployment).where(
                StrategyDeployment.id == UUID(sys.argv[1])))).scalar_one()
            strategy = (await db.execute(select(Strategy).where(Strategy.id == dep.strategy_id))).scalar_one()
            _, params, _ = resolve_strategy(strategy.id, strategy.name, strategy.parameters)
            selection = select_registered_adapter(settings=settings, source_code=strategy.parameters['source_code'],
                mode=dep.mode, instrument=dep.instrument, timeframe_seconds=300, required_history_bars=80000)
            assert selection.strategy_class
            candles = await load_live_candles_for_runner(db, dep, limit=80000)
            df = _candles_to_dataframe(candles)
            mark('loaded', candles=len(df), target=str(df.iloc[-1]['Date']))
            instance = selection.strategy_class(df, **params)
            mark('generate_start')
            generated = instance.generate()
            mark('generate_done', rows=len(generated), columns=len(generated.columns))
            assert instance.start_live_incremental(generated)
            mark('initialize_done')
            if getattr(instance, 'LIVE_INCREMENTAL_NATIVE', False):
                snapshot = instance.snapshot()
                restored = selection.strategy_class(df.tail(1), **params)
                restored.restore(snapshot, {'interface_version': 1})
                assert restored.snapshot() == snapshot
                mark('snapshot_roundtrip_done', snapshot_bytes=len(json.dumps(snapshot)))
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())