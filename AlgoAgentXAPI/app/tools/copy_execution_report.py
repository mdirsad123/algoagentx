"""Read-only per-signal copy diagnostic. Never contacts a broker or retries orders.

Usage: python -m app.tools.copy_execution_report --signal-id UUID
"""
import argparse
import asyncio
import json
from uuid import UUID

from sqlalchemy import select, text
from ..db.models import LiveOrder, LiveSignal, LiveTradeLog, StrategyDeployment
from ..db.session import async_session, engine


async def report(signal_id):
    async with async_session() as db:
        await db.execute(text('SET TRANSACTION READ ONLY'))
        signal = (await db.execute(select(LiveSignal).where(LiveSignal.id == signal_id))).scalar_one()
        deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == signal.deployment_id))).scalar_one()
        orders = (await db.execute(select(LiveOrder).where(LiveOrder.signal_id == signal_id))).scalars().all()
        logs = (await db.execute(select(LiveTradeLog).where(
            LiveTradeLog.deployment_id == deployment.id,
            LiveTradeLog.metadata_json['signal_id'].astext == str(signal_id),
        ).order_by(LiveTradeLog.created_at))).scalars().all()
        allowed = {'signal_id', 'broker_account_id', 'broker_type', 'candle_time', 'enabled',
                   'dispatch_started_at', 'account_validation_ms', 'account_metadata_cache_hit',
                   'submitted_at', 'broker_acknowledged_at', 'primary_to_submission_ms',
                   'primary_to_fill_ms', 'http_requests', 'http_429_count', 'retry_attempts',
                   'order_id', 'broker_order_id', 'order_status', 'copy_signal_status',
                   'copy_rejection_reason', 'error_type', 'reason', 'completed_at'}
        output = {'signal_id': str(signal.id), 'candle_time': signal.candle_time,
                  'primary_account': str(deployment.broker_account_id),
                  'copy_enabled_current': deployment.copy_trading_enabled,
                  'copy_accounts_current': deployment.copy_broker_account_ids,
                  'note': 'Current configuration is not evidence of historical enablement; use event records.',
                  'orders': [{'account': str(o.broker_account_id), 'id': str(o.id),
                              'broker_order_id': o.broker_order_id, 'status': o.status,
                              'created_at': o.created_at, 'updated_at': o.updated_at,
                              'timing': (o.raw_response or {}).get('execution_timing')} for o in orders],
                  'events': [{'event': row.event_type, 'recorded_at': row.created_at,
                              'details': {k:v for k,v in (row.metadata_json or {}).items() if k in allowed}}
                             for row in logs]}
        print(json.dumps(output, indent=2, default=str))
    await engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--signal-id', type=UUID, required=True)
    asyncio.run(report(parser.parse_args().signal_id))