"""Read-only diagnostics for TradeLocker candle continuity and runner backlog.

Usage:
 python -m app.tools.check_live_candle_gaps_readonly --deployment-id UUID
This performs SELECT only. Do not mistake a non-trading session closure for a
missing broker candle; look at the TradeLocker history before changing state.
"""
from __future__ import annotations
import argparse
import asyncio
from datetime import timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select

from app.db.models import LiveMarketCandle, StrategyDeployment
from app.db.session import async_session
from app.services.live.candle_catchup import plan_recovery, utc
from app.services.live.runner_scheduler import parse_timeframe_to_seconds


async def read_only_report(deployment_id: UUID) -> None:
    async with async_session() as db:
        dep = (await db.execute(select(StrategyDeployment).where(
            StrategyDeployment.id == deployment_id))).scalar_one_or_none()
        if not dep:
            print('deployment_not_found', deployment_id)
            return
        interval = parse_timeframe_to_seconds(str(dep.timeframe or 'M5'))
        cursor = utc(dep.last_processed_candle_time) if dep.last_processed_candle_time else None
        newest = (await db.execute(select(func.max(LiveMarketCandle.candle_time)).where(
            LiveMarketCandle.deployment_id == deployment_id,
            LiveMarketCandle.timeframe == dep.timeframe,
            LiveMarketCandle.is_closed.is_(True),
        ))).scalar_one_or_none()
        first = None
        if cursor:
            first = (await db.execute(select(func.min(LiveMarketCandle.candle_time)).where(
                LiveMarketCandle.deployment_id == deployment_id,
                LiveMarketCandle.timeframe == dep.timeframe,
                LiveMarketCandle.is_closed.is_(True),
                LiveMarketCandle.candle_time > cursor,
            ))).scalar_one_or_none()
        plan = plan_recovery(last_processed=cursor, first_pending=first, newest=newest,
                             timeframe_seconds=interval)
        print('deployment_id:', deployment_id)
        print('timeframe:', dep.timeframe)
        print('last_processed_open_utc:', cursor)
        print('latest_stored_open_utc:', utc(newest) if newest else None)
        print('first_pending_stored_open_utc:', utc(first) if first else None)
        print('recovery_action:', plan.action)
        print('next_to_process_utc:', plan.target)
        print('missing_open_utc:', plan.missing_open)
        print('pending_intervals:', plan.pending_bars)
        # SELECT-only proof for immediate missing candle. Market-hours context
        # is not available in this endpoint; no claim of broker omission.
        if cursor:
            expected = cursor + timedelta(seconds=interval)
            count = (await db.execute(select(func.count(LiveMarketCandle.id)).where(
                LiveMarketCandle.deployment_id == deployment_id,
                LiveMarketCandle.timeframe == dep.timeframe,
                LiveMarketCandle.is_closed.is_(True),
                LiveMarketCandle.candle_time == expected,
            ))).scalar_one()
            print('immediate_expected_exists_in_db:', bool(count))
            print('immediate_expected_open_utc:', expected)
        print('IMPORTANT: absence in DB does not prove TradeLocker published this candle.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deployment-id', required=True, type=UUID)
    args = parser.parse_args()
    asyncio.run(read_only_report(args.deployment_id))


if __name__ == '__main__':
    main()
