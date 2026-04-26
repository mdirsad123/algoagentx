from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import LiveEquityPoint, LivePosition, LiveTradeLog, StrategyDeployment


def to_decimal(value: object, default: str = "0") -> Decimal:
    try:
        if value is None or value == "":
            return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def calculate_position_pnl(side: str, entry_price: object, exit_price: object, qty: object) -> Decimal:
    entry = to_decimal(entry_price)
    exit_value = to_decimal(exit_price)
    size = to_decimal(qty)
    if str(side).upper() == "SHORT":
        return ((entry - exit_value) * size).quantize(Decimal("0.0001"))
    return ((exit_value - entry) * size).quantize(Decimal("0.0001"))


async def totals_for_deployment(db: AsyncSession, deployment_id) -> tuple[Decimal, Decimal]:
    realized_result = await db.execute(
        select(func.coalesce(func.sum(LivePosition.realized_pnl), 0)).where(LivePosition.deployment_id == deployment_id)
    )
    unrealized_result = await db.execute(
        select(func.coalesce(func.sum(LivePosition.unrealized_pnl), 0)).where(
            LivePosition.deployment_id == deployment_id,
            LivePosition.status == "OPEN",
        )
    )
    return to_decimal(realized_result.scalar()), to_decimal(unrealized_result.scalar())


async def create_equity_point(db: AsyncSession, deployment: StrategyDeployment, event: str = "EQUITY_UPDATED") -> LiveEquityPoint:
    realized, unrealized = await totals_for_deployment(db, deployment.id)
    capital = to_decimal(deployment.capital, "100000")
    equity = (capital + realized + unrealized).quantize(Decimal("0.0001"))
    point = LiveEquityPoint(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        timestamp=datetime.now(timezone.utc),
        equity=equity,
        balance=(capital + realized).quantize(Decimal("0.0001")),
        unrealized_pnl=unrealized.quantize(Decimal("0.0001")),
        realized_pnl=realized.quantize(Decimal("0.0001")),
    )
    db.add(point)
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=event,
        level="INFO",
        message=f"Equity updated to {equity}",
        metadata_json={"equity": str(equity), "realized_pnl": str(realized), "unrealized_pnl": str(unrealized)},
    ))
    return point
