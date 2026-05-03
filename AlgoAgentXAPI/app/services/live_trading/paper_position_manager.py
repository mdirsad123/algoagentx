from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import Instrument, LiveMarketCandle, LivePosition, LiveTradeLog, StrategyDeployment
from ..live.pnl_service import to_decimal, create_equity_point


def _d(value: Any, default: str = "0") -> Decimal:
    return to_decimal(value, default)


async def _log(db: AsyncSession, deployment: StrategyDeployment, event_type: str, message: str, level: str = "INFO", metadata: dict[str, Any] | None = None) -> None:
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=event_type,
        level=level,
        message=message,
        metadata_json=metadata or {},
    ))


async def _instrument_spec(db: AsyncSession, deployment: StrategyDeployment) -> Instrument | None:
    symbol = str(deployment.instrument or "").strip().upper()
    if not symbol:
        return None
    return (await db.execute(
        select(Instrument).where(Instrument.symbol.ilike(symbol)).order_by(Instrument.is_active.desc(), Instrument.id.asc()).limit(1)
    )).scalar_one_or_none()


def calculate_live_position_pnl(position: LivePosition, exit_price: Decimal, instrument: Instrument | None = None) -> Decimal:
    """Calculate paper PnL with instrument metadata when available.

    LOTS: price move / tick_size * tick_value_per_lot * lots
    SHARES/UNITS: price move * quantity
    """
    side = str(position.side or "LONG").upper()
    entry = _d(position.avg_entry_price)
    qty = _d(position.qty)
    move = exit_price - entry
    if side == "SHORT":
        move = entry - exit_price

    quantity_mode = str(getattr(instrument, "quantity_mode", "") or "").upper() if instrument else ""
    if quantity_mode == "LOTS":
        tick_size = _d(getattr(instrument, "tick_size", None), "0") if instrument else Decimal("0")
        tick_value = _d(getattr(instrument, "tick_value_per_lot", None), "0") if instrument else Decimal("0")
        if tick_size > 0 and tick_value > 0:
            return ((move / tick_size) * tick_value * qty).quantize(Decimal("0.0001"))
    return (move * qty).quantize(Decimal("0.0001"))


def _exit_for_candle(position: LivePosition, candle: LiveMarketCandle) -> tuple[str, Decimal] | None:
    side = str(position.side or "").upper()
    sl = _d(position.stop_loss) if position.stop_loss is not None else None
    tp = _d(position.target) if position.target is not None else None
    low = _d(candle.low)
    high = _d(candle.high)
    if side == "LONG":
        sl_hit = sl is not None and low <= sl
        tp_hit = tp is not None and high >= tp
        if sl_hit:
            return "STOP_LOSS_HIT", sl  # conservative when both hit
        if tp_hit:
            return "TAKE_PROFIT_HIT", tp
    elif side == "SHORT":
        sl_hit = sl is not None and high >= sl
        tp_hit = tp is not None and low <= tp
        if sl_hit:
            return "STOP_LOSS_HIT", sl
        if tp_hit:
            return "TAKE_PROFIT_HIT", tp
    return None


async def process_paper_positions_for_deployment(db: AsyncSession, deployment_id: UUID | str) -> dict[str, Any]:
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if deployment is None:
        raise ValueError("Deployment not found")
    mode = str(deployment.mode or "PAPER").upper()
    if mode != "PAPER":
        await _log(db, deployment, "PAPER_POSITION_MANAGER_SKIPPED", "Paper position manager only manages PAPER deployments.", "INFO", {"mode": mode})
        await db.flush()
        return {"processed": 0, "closed": 0, "mode": mode, "message": "Paper manager skipped because deployment is not PAPER."}

    positions = (await db.execute(
        select(LivePosition).where(LivePosition.deployment_id == deployment.id, LivePosition.status == "OPEN").order_by(LivePosition.opened_at.asc())
    )).scalars().all()
    instrument = await _instrument_spec(db, deployment)
    closed: list[dict[str, Any]] = []
    updated = 0

    for position in positions:
        candles = (await db.execute(
            select(LiveMarketCandle)
            .where(
                LiveMarketCandle.deployment_id == deployment.id,
                LiveMarketCandle.timeframe == deployment.timeframe,
                LiveMarketCandle.is_closed.is_(True),
                LiveMarketCandle.candle_time >= position.opened_at,
            )
            .order_by(LiveMarketCandle.candle_time.asc())
            .limit(1000)
        )).scalars().all()
        if not candles:
            continue
        # Keep mark-to-market current using latest candle close.
        latest = candles[-1]
        position.current_price = _d(latest.close)
        position.unrealized_pnl = calculate_live_position_pnl(position, _d(latest.close), instrument)
        updated += 1

        exit_match: tuple[str, Decimal, LiveMarketCandle] | None = None
        for candle in candles:
            exit_result = _exit_for_candle(position, candle)
            if exit_result:
                reason, exit_price = exit_result
                exit_match = (reason, exit_price, candle)
                break
        if not exit_match:
            continue

        reason, exit_price, candle = exit_match
        pnl = calculate_live_position_pnl(position, exit_price, instrument)
        position.current_price = exit_price
        position.unrealized_pnl = Decimal("0")
        position.realized_pnl = pnl
        position.status = "CLOSED"
        position.closed_at = candle.candle_time or datetime.now(timezone.utc)
        await _log(db, deployment, reason, f"Paper position {reason.replace('_', ' ').lower()} at {exit_price}", "INFO", {"position_id": str(position.id), "exit_price": str(exit_price), "pnl": str(pnl), "candle_time": str(candle.candle_time)})
        await _log(db, deployment, "POSITION_CLOSED", f"Paper position closed: {reason}", "INFO", {"position_id": str(position.id), "exit_reason": reason, "realized_pnl": str(pnl)})
        closed.append({"position_id": str(position.id), "exit_reason": reason, "exit_price": str(exit_price), "realized_pnl": str(pnl), "closed_at": str(position.closed_at)})

    if updated or closed:
        await create_equity_point(db, deployment, event="PAPER_POSITION_MANAGER_UPDATED")
    await db.flush()
    return {"processed": len(positions), "updated": updated, "closed": len(closed), "closed_positions": closed, "mode": mode, "message": f"Processed {len(positions)} PAPER positions; closed {len(closed)}."}
