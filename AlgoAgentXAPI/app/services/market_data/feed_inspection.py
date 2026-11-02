"""Read-only inspection of isolated broker history versus canonical backtest OHLCV."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import MarketData, MarketDataFeedCandle, MarketDataSyncRun


def display_price(value) -> str:
    """Readable 5dp Decimal formatting; NEVER mutate stored OHLCV."""
    if value is None:
        return ""
    return format(Decimal(str(value)).quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP), "f")


async def inspect_feed_storage(db: AsyncSession, config) -> dict:
    """Counts and 5 latest source OHLCV rows, without publishing/mutating anything."""
    source = (await db.execute(select(func.count(MarketDataFeedCandle.timestamp),
        func.min(MarketDataFeedCandle.timestamp), func.max(MarketDataFeedCandle.timestamp)).where(
        MarketDataFeedCandle.feed_id == config.id))).one()
    legacy = (await db.execute(select(func.count(MarketData.timestamp),
        func.min(MarketData.timestamp), func.max(MarketData.timestamp)).where(
        MarketData.instrument_id == config.instrument_id,
        MarketData.timeframe == config.timeframe))).one()
    samples = (await db.execute(select(MarketDataFeedCandle).where(
        MarketDataFeedCandle.feed_id == config.id).order_by(
        MarketDataFeedCandle.timestamp.desc()).limit(5))).scalars().all()
    latest_run = (await db.execute(select(MarketDataSyncRun).where(
        MarketDataSyncRun.feed_id == config.id).order_by(
        MarketDataSyncRun.created_at.desc()).limit(1))).scalar_one_or_none()
    return {
        "feed_id": str(config.id), "provider": config.provider, "broker_symbol": config.broker_symbol,
        "instrument_id": config.instrument_id, "timeframe": config.timeframe,
        "source": {"table": "market_data_feed_candles", "count": source[0],
                   "first": source[1], "last": source[2]},
        "canonical": {"table": "market_data", "count": legacy[0],
                      "first": legacy[1], "last": legacy[2]},
        "is_primary": config.is_primary, "publish_approved": config.publish_approved,
        "last_run_status": latest_run.status if latest_run else None,
        "last_run_dry_run": latest_run.dry_run if latest_run else None,
        "latest_candles": [{"timestamp": candle.timestamp,
                            "open": display_price(candle.open), "high": display_price(candle.high),
                            "low": display_price(candle.low), "close": display_price(candle.close),
                            "volume": str(candle.volume)} for candle in samples],
        "note": "Source candles are independently stored. Legacy backtest data is not automatically merged from another broker.",
    }
