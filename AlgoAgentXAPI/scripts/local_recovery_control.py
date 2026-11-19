"""Local diagnostics and controlled queue submission; no cursor SQL updates."""
import asyncio
import hashlib
import json
import sys
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, func, text
from app.tasks import _fresh_async_engine_and_sessionmaker, verified_gap_reseed_task
from app.db.models import StrategyDeployment, LiveMarketCandle, LiveOrder, Strategy

NAS = '4362f853-69aa-431f-b45f-3733ce3181ae'
GOLD = '75daebe6-ccb4-4197-af61-e8048ca6eb60'


async def main():
    engine, sessions = _fresh_async_engine_and_sessionmaker()
    try:
        async with sessions() as db:
            for value in (NAS, GOLD):
                dep = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == UUID(value)))).scalar_one()
                latest = (await db.execute(select(func.max(LiveMarketCandle.candle_time)).where(
                    LiveMarketCandle.deployment_id == dep.id, LiveMarketCandle.is_closed.is_(True)))).scalar_one()
                orders = (await db.execute(select(func.count()).select_from(LiveOrder).where(LiveOrder.deployment_id == dep.id))).scalar_one()
                source = (await db.execute(select(Strategy.parameters).where(Strategy.id == dep.strategy_id))).scalar_one()
                print(json.dumps(dict(deployment=value, instrument=dep.instrument, cursor=str(dep.last_processed_candle_time),
                    latest=str(latest), orders=orders, auto_trade=dep.auto_trade_enabled,
                    parameters_sha256=hashlib.sha256(json.dumps(source, sort_keys=True, default=str).encode()).hexdigest())), flush=True)
                if sys.argv[1] == 'rearm-fixed-validation' and value == NAS:
                    import redis
                    from pathlib import Path
                    from app.core.config import settings
                    from app.services.live.recovery_lifecycle import keys
                    r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                    lease, queue, status = keys(value)
                    prior = r.hgetall(status)
                    assert prior['reason'] == 'HTTP_500' and prior['status'] == 'REQUIRES_ATTENTION'
                    assert not r.exists(lease, queue)
                    assert dep.last_processed_candle_time.isoformat() == '2026-11-17T22:05:00+00:00'
                    Path('/tmp/pre-validation-rearm.json').write_text(json.dumps(prior, indent=2))
                    changed = r.eval("""
                        if redis.call('HGET', KEYS[1], 'task_id') == ARGV[1]
                            and redis.call('HGET', KEYS[1], 'reason') == 'HTTP_500'
                            and redis.call('EXISTS', KEYS[2], KEYS[3]) == 0 then
                            redis.call('HSET', KEYS[1], 'status', 'RETRYABLE', 'reason', 'OPERATOR_REPAIRED_UTC_VALIDATION',
                                'retry_at', '0', 'repair_note', 'UTC validation normalization corrected; no cursor modification')
                            return 1
                        end
                        return 0
                    """, 3, status, lease, queue, prior['task_id'])
                    assert changed == 1
                    print('FIXED_VALIDATION_REARMED_WITH_BACKUP', flush=True)
                    r.close()
                if sys.argv[1] == 'enqueue' and value == NAS:
                    result = verified_gap_reseed_task.apply_async(args=[value,
                        (dep.last_processed_candle_time + timedelta(minutes=5)).isoformat(), latest.isoformat()],
                        queue='local_verified_recovery')
                    print('RECOVERY_TASK_ID=' + result.id, flush=True)
            if sys.argv[1] == 'status':
                rows = (await db.execute(text("SELECT deployment_id,candle_open,candle_count FROM live_incremental_checkpoints"))).all()
                print('CHECKPOINTS=' + str(rows), flush=True)
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())