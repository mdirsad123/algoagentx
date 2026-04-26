from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import LiveOrder, LivePosition, LiveSignal, LiveTradeLog, StrategyDeployment
from .pnl_service import to_decimal
from .position_service import get_open_positions


@dataclass
class RiskResult:
    allowed: bool
    reason: str | None = None
    action: str = "OPEN"  # OPEN, CLOSE_ONLY, CLOSE_AND_OPEN, HOLD


async def _write(db: AsyncSession, deployment: StrategyDeployment, event_type: str, message: str, level: str = "INFO", metadata: dict | None = None) -> None:
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=event_type,
        level=level,
        message=message,
        metadata_json=metadata or {},
    ))


async def validate_signal_for_execution(db: AsyncSession, deployment: StrategyDeployment, signal: LiveSignal) -> RiskResult:
    await _write(db, deployment, "RISK_CHECK_STARTED", f"Risk check started for {signal.signal_type}", metadata={"signal_id": str(signal.id)})

    if deployment.status != "RUNNING":
        return RiskResult(False, f"Deployment is {deployment.status}")
    if not deployment.auto_trade_enabled:
        return RiskResult(False, "Auto trade is disabled")
    if deployment.mode == "LIVE":
        return RiskResult(False, "LIVE mode is not enabled yet")
    if signal.signal_type not in {"BUY", "SELL", "EXIT", "HOLD"}:
        return RiskResult(False, "Invalid signal type")
    if signal.signal_type == "HOLD":
        return RiskResult(True, action="HOLD")
    if signal.signal_type == "SELL" and not deployment.allow_short:
        return RiskResult(False, "Short selling is disabled for this deployment")
    if signal.price is None or to_decimal(signal.price) <= 0:
        return RiskResult(False, "Signal price is required for paper execution")

    day_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    orders_today = (await db.execute(
        select(func.count(LiveOrder.id)).where(
            LiveOrder.deployment_id == deployment.id,
            LiveOrder.created_at >= day_start,
            LiveOrder.status.in_(["FILLED", "PLACED", "PENDING_DEMO"]),
        )
    )).scalar() or 0
    if int(orders_today) >= int(deployment.max_trades_per_day or 10) and signal.signal_type != "EXIT":
        return RiskResult(False, "Max trades per day reached")

    realized_today = to_decimal((await db.execute(
        select(func.coalesce(func.sum(LivePosition.realized_pnl), 0)).where(
            LivePosition.deployment_id == deployment.id,
            LivePosition.closed_at >= day_start,
        )
    )).scalar())
    if realized_today <= (to_decimal(deployment.max_daily_loss, "5000") * Decimal("-1")):
        return RiskResult(False, "Max daily loss reached")

    duplicate = (await db.execute(
        select(LiveOrder.id)
        .join(LiveSignal, LiveSignal.id == LiveOrder.signal_id)
        .where(
            LiveOrder.deployment_id == deployment.id,
            LiveSignal.candle_time == signal.candle_time,
            LiveSignal.signal_type == signal.signal_type,
            LiveOrder.status.in_(["FILLED", "PLACED", "PENDING_DEMO"]),
        )
        .limit(1)
    )).scalar_one_or_none()
    if duplicate is not None:
        return RiskResult(False, "Duplicate order for same candle and signal")

    open_positions = await get_open_positions(db, deployment.id)
    if signal.signal_type == "EXIT":
        if not open_positions:
            return RiskResult(False, "No open position to close")
        return RiskResult(True, action="CLOSE_ONLY")

    requested_side = "LONG" if signal.signal_type == "BUY" else "SHORT"
    if open_positions:
        latest = open_positions[-1]
        if latest.side == requested_side:
            return RiskResult(False, f"Already in {requested_side} position")
        return RiskResult(True, action="CLOSE_AND_OPEN")

    if len(open_positions) >= int(deployment.max_open_positions or 1):
        return RiskResult(False, "Max open positions reached")

    return RiskResult(True, action="OPEN")
