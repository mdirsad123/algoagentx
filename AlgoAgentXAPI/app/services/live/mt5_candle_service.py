from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import BrokerAccount, LiveMarketCandle, LiveTradeLog, StrategyDeployment
from ..brokers.factory import get_broker_adapter


def _decimal(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None or value == "":
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    text = str(value or "").strip()
    if not text:
        return datetime.now(timezone.utc)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _candle_payload(row: LiveMarketCandle) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "deployment_id": str(row.deployment_id) if row.deployment_id else None,
        "broker_account_id": str(row.broker_account_id) if row.broker_account_id else None,
        "symbol": row.symbol,
        "timeframe": row.timeframe,
        "candle_time": row.candle_time,
        "open": row.open,
        "high": row.high,
        "low": row.low,
        "close": row.close,
        "volume": row.volume,
        "source": row.source,
        "is_closed": row.is_closed,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


async def _write_log(db: AsyncSession, deployment: StrategyDeployment, event_type: str, message: str, level: str = "INFO", metadata: dict | None = None) -> None:
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=event_type,
        level=level,
        message=message,
        metadata_json=metadata or {},
    ))


async def _get_deployment_and_broker(db: AsyncSession, deployment_id: UUID) -> tuple[StrategyDeployment, BrokerAccount]:
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if not deployment.broker_account_id:
        raise HTTPException(status_code=400, detail="MT5 candle snapshot requires a linked MT5 demo broker account")
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None:
        raise HTTPException(status_code=404, detail="Broker account not found")
    if (broker.broker_name or "").upper() != "MT5" or broker.mode != "DEMO":
        raise HTTPException(status_code=400, detail="Only MT5 DEMO broker accounts are supported for candle snapshots")
    if broker.status != "CONNECTED":
        raise HTTPException(status_code=400, detail="MT5 broker account must be CONNECTED before refreshing candles")
    return deployment, broker


async def refresh_deployment_candles(db: AsyncSession, deployment_id: UUID, count: int = 300) -> dict[str, Any]:
    deployment, broker = await _get_deployment_and_broker(db, deployment_id)
    safe_count = max(1, min(int(count or 300), 2000))
    await _write_log(db, deployment, "CANDLE_REFRESH_STARTED", f"MT5 candle refresh started for {deployment.instrument} {deployment.timeframe}", metadata={"count": safe_count})

    adapter = get_broker_adapter(broker)
    rates = await adapter.get_rates(deployment.instrument, deployment.timeframe, safe_count)
    if rates and rates[0].get("success") is False:
        message = str(rates[0].get("message") or "MT5 candle refresh failed")
        await _write_log(db, deployment, "CANDLE_REFRESH_FAILED", message, "ERROR", {"response": rates[0]})
        await db.commit()
        raise HTTPException(status_code=400, detail=message)

    upserted = 0
    for item in rates:
        if item.get("success") is False:
            continue
        candle_time = _parse_dt(item.get("candle_time"))
        resolved_symbol = str(item.get("symbol") or deployment.instrument)
        values = {
            "deployment_id": deployment.id,
            "broker_account_id": broker.id,
            "symbol": resolved_symbol,
            "timeframe": deployment.timeframe,
            "candle_time": candle_time,
            "open": _decimal(item.get("open")),
            "high": _decimal(item.get("high")),
            "low": _decimal(item.get("low")),
            "close": _decimal(item.get("close")),
            "volume": _decimal(item.get("volume")) if item.get("volume") is not None else None,
            "source": "MT5",
            "is_closed": True,
            "raw_payload": item.get("raw_payload") or {},
        }
        stmt = insert(LiveMarketCandle).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_live_market_candles_dep_symbol_tf_time",
            set_={
                "broker_account_id": values["broker_account_id"],
                "open": values["open"],
                "high": values["high"],
                "low": values["low"],
                "close": values["close"],
                "volume": values["volume"],
                "source": values["source"],
                "is_closed": values["is_closed"],
                "raw_payload": values["raw_payload"],
                "updated_at": func.now(),
            },
        )
        await db.execute(stmt)
        upserted += 1

    await _write_log(db, deployment, "CANDLE_REFRESH_COMPLETED", f"MT5 candle refresh stored {upserted} candles", metadata={"count": safe_count, "stored": upserted})
    await db.commit()

    latest_rows = await get_latest_closed_candles(db, deployment_id, limit=5)
    latest = latest_rows[0] if latest_rows else None
    total_count = int((await db.execute(select(func.count(LiveMarketCandle.id)).where(LiveMarketCandle.deployment_id == deployment_id))).scalar() or 0)
    return {
        "source": "MT5",
        "symbol": deployment.instrument,
        "resolved_symbol": latest.get("symbol") if latest else deployment.instrument,
        "timeframe": deployment.timeframe,
        "requested_count": safe_count,
        "stored_count": total_count,
        "upserted_count": upserted,
        "latest_candle_time": latest.get("candle_time") if latest else None,
        "latest_close": latest.get("close") if latest else None,
        "candles": latest_rows,
    }


async def get_latest_closed_candles(db: AsyncSession, deployment_id: UUID, limit: int = 300) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit or 300), 1000))
    rows = (await db.execute(
        select(LiveMarketCandle)
        .where(LiveMarketCandle.deployment_id == deployment_id, LiveMarketCandle.is_closed.is_(True))
        .order_by(LiveMarketCandle.candle_time.desc())
        .limit(safe_limit)
    )).scalars().all()
    return [_candle_payload(row) for row in rows]


async def get_candle_snapshot(db: AsyncSession, deployment_id: UUID, limit: int = 300) -> dict[str, Any]:
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    rows = await get_latest_closed_candles(db, deployment_id, limit)
    total_count = int((await db.execute(select(func.count(LiveMarketCandle.id)).where(LiveMarketCandle.deployment_id == deployment_id))).scalar() or 0)
    latest = rows[0] if rows else None
    return {
        "source": "MT5",
        "symbol": deployment.instrument,
        "resolved_symbol": latest.get("symbol") if latest else deployment.instrument,
        "timeframe": deployment.timeframe,
        "stored_count": total_count,
        "latest_candle_time": latest.get("candle_time") if latest else None,
        "latest_close": latest.get("close") if latest else None,
        "candles": rows,
    }
