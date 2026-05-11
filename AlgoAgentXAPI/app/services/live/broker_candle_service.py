from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import BrokerAccount, LiveMarketCandle, LiveTradeLog, StrategyDeployment
from ..brokers.factory import get_broker_adapter, get_broker_code


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



def _timeframe_minutes(timeframe: str) -> int:
    tf = str(timeframe or "").strip().lower()
    aliases = {"m1": 1, "1m": 1, "m5": 5, "5m": 5, "m15": 15, "15m": 15, "m30": 30, "30m": 30, "h1": 60, "1h": 60, "h4": 240, "4h": 240, "d1": 1440, "1d": 1440}
    if tf in aliases:
        return aliases[tf]
    import re
    match = re.match(r"^(\d+)\s*([mhd])", tf)
    if match:
        n = max(1, int(match.group(1)))
        unit = match.group(2)
        return n if unit == "m" else n * 60 if unit == "h" else n * 1440
    return 1


def _is_candle_closed(candle_time: datetime, timeframe: str, *, now: datetime | None = None, grace_seconds: int = 2) -> bool:
    if candle_time.tzinfo is None:
        candle_time = candle_time.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    close_time = candle_time + timedelta(minutes=_timeframe_minutes(timeframe))
    return now >= close_time + timedelta(seconds=max(0, int(grace_seconds or 0)))

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


def _broker_source(broker: BrokerAccount) -> str:
    return get_broker_code(broker)


def _resolve_symbol(deployment: StrategyDeployment, broker: BrokerAccount) -> str:
    source = _broker_source(broker)
    if source == "UPSTOX":
        return str(getattr(deployment, "instrument_key", None) or getattr(deployment, "broker_symbol", None) or deployment.instrument).strip()
    return str(getattr(deployment, "broker_symbol", None) or deployment.instrument).strip()


async def _get_deployment_and_broker(db: AsyncSession, deployment_id: UUID) -> tuple[StrategyDeployment, BrokerAccount, str]:
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if not deployment.broker_account_id:
        raise HTTPException(status_code=400, detail="Candle snapshot requires a linked broker account")
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None:
        raise HTTPException(status_code=404, detail="Broker account not found")
    source = _broker_source(broker)
    if source not in {"MT5", "UPSTOX"}:
        raise HTTPException(status_code=400, detail=f"Unsupported candle broker provider: {source}")
    if broker.status != "CONNECTED":
        raise HTTPException(status_code=400, detail=f"{source} broker account must be CONNECTED before refreshing candles")
    if source == "UPSTOX" and not _resolve_symbol(deployment, broker):
        raise HTTPException(status_code=400, detail="Upstox deployment requires instrument_key or broker_symbol")
    return deployment, broker, source


async def refresh_deployment_candles(db: AsyncSession, deployment_id: UUID, count: int = 300) -> dict[str, Any]:
    deployment, broker, source = await _get_deployment_and_broker(db, deployment_id)
    safe_count = max(1, min(int(count or 300), 2000))
    resolved_symbol = _resolve_symbol(deployment, broker)
    await _write_log(db, deployment, "CANDLE_REFRESH_STARTED", f"{source} candle refresh started for {resolved_symbol} {deployment.timeframe}", metadata={"count": safe_count, "source": source})

    adapter = get_broker_adapter(broker, db)
    try:
        rates = await adapter.get_rates(resolved_symbol, deployment.timeframe, safe_count)
    except Exception as exc:
        message = str(exc)
        await _write_log(db, deployment, "CANDLE_REFRESH_FAILED", message, "ERROR", {"source": source, "symbol": resolved_symbol})
        await db.commit()
        raise HTTPException(status_code=400, detail=message)

    if rates and rates[0].get("success") is False:
        message = str(rates[0].get("message") or f"{source} candle refresh failed")
        await _write_log(db, deployment, "CANDLE_REFRESH_FAILED", message, "ERROR", {"response": rates[0], "source": source})
        await db.commit()
        raise HTTPException(status_code=400, detail=message)

    upserted = 0
    skipped_forming = 0
    now_utc = datetime.now(timezone.utc)
    for item in rates:
        if item.get("success") is False:
            continue
        candle_time = _parse_dt(item.get("candle_time"))
        # MT5/Upstox timestamps are candle OPEN times. Do not save the currently
        # forming candle as closed; the strategy runner must only see candles
        # whose full timeframe has completed. Example: M5 candle 20:05 becomes
        # eligible after 20:10:02.
        if not _is_candle_closed(candle_time, deployment.timeframe, now=now_utc, grace_seconds=2):
            skipped_forming += 1
            continue
        row_symbol = str(item.get("symbol") or resolved_symbol)
        values = {
            "deployment_id": deployment.id,
            "broker_account_id": broker.id,
            "symbol": row_symbol,
            "timeframe": deployment.timeframe,
            "candle_time": candle_time,
            "open": _decimal(item.get("open")),
            "high": _decimal(item.get("high")),
            "low": _decimal(item.get("low")),
            "close": _decimal(item.get("close")),
            "volume": _decimal(item.get("volume")) if item.get("volume") is not None else None,
            "source": source,
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

    await _write_log(db, deployment, "CANDLE_REFRESH_COMPLETED", f"{source} candle refresh stored {upserted} closed candles", metadata={"count": safe_count, "stored": upserted, "skipped_forming": skipped_forming, "source": source})
    await db.commit()

    latest_rows = await get_latest_closed_candles(db, deployment_id, limit=5)
    latest = latest_rows[0] if latest_rows else None
    total_count = int((await db.execute(select(func.count(LiveMarketCandle.id)).where(LiveMarketCandle.deployment_id == deployment_id))).scalar() or 0)
    next_closed_expected_at = None
    latest_open_time = latest.get("candle_time") if latest else None
    if latest_open_time:
        try:
            base_dt = latest_open_time if isinstance(latest_open_time, datetime) else _parse_dt(latest_open_time)
            next_closed_expected_at = base_dt + timedelta(minutes=_timeframe_minutes(deployment.timeframe) * 2, seconds=2)
        except Exception:
            next_closed_expected_at = None
    return {
        "source": source,
        "symbol": deployment.instrument,
        "resolved_symbol": latest.get("symbol") if latest else resolved_symbol,
        "broker_symbol": getattr(deployment, "broker_symbol", None),
        "instrument_key": getattr(deployment, "instrument_key", None) or (resolved_symbol if source == "UPSTOX" else None),
        "timeframe": deployment.timeframe,
        "requested_count": safe_count,
        "stored_count": total_count,
        "upserted_count": upserted,
        "skipped_forming_count": skipped_forming,
        "latest_candle_time": latest.get("candle_time") if latest else None,
        "latest_close": latest.get("close") if latest else None,
        "next_closed_candle_expected_at": next_closed_expected_at,
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
    broker = None
    source = "MT5"
    resolved_symbol = getattr(deployment, "broker_symbol", None) or deployment.instrument
    if deployment.broker_account_id:
        broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
        if broker is not None:
            source = _broker_source(broker)
            resolved_symbol = _resolve_symbol(deployment, broker) or resolved_symbol
    rows = await get_latest_closed_candles(db, deployment_id, limit)
    total_count = int((await db.execute(select(func.count(LiveMarketCandle.id)).where(LiveMarketCandle.deployment_id == deployment_id))).scalar() or 0)
    latest = rows[0] if rows else None
    latest_open_time = latest.get("candle_time") if latest else None
    next_closed_expected_at = None
    if latest_open_time:
        try:
            base_dt = latest_open_time if isinstance(latest_open_time, datetime) else _parse_dt(latest_open_time)
            next_closed_expected_at = base_dt + timedelta(minutes=_timeframe_minutes(deployment.timeframe) * 2, seconds=2)
        except Exception:
            next_closed_expected_at = None
    return {
        "source": latest.get("source") if latest else source,
        "symbol": deployment.instrument,
        "resolved_symbol": latest.get("symbol") if latest else resolved_symbol,
        "broker_symbol": getattr(deployment, "broker_symbol", None),
        "instrument_key": getattr(deployment, "instrument_key", None) or (resolved_symbol if source == "UPSTOX" else None),
        "timeframe": deployment.timeframe,
        "stored_count": total_count,
        "latest_candle_time": latest.get("candle_time") if latest else None,
        "latest_close": latest.get("close") if latest else None,
        "next_closed_candle_expected_at": next_closed_expected_at,
        "candles": rows,
    }
