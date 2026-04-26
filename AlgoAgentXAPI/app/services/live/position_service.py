from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import LivePosition, LiveTradeLog, StrategyDeployment
from .pnl_service import calculate_position_pnl, to_decimal


async def get_open_positions(db: AsyncSession, deployment_id) -> list[LivePosition]:
    rows = await db.execute(
        select(LivePosition)
        .where(LivePosition.deployment_id == deployment_id, LivePosition.status == "OPEN")
        .order_by(LivePosition.opened_at.asc())
    )
    return list(rows.scalars().all())


async def get_latest_open_position(db: AsyncSession, deployment_id) -> Optional[LivePosition]:
    rows = await db.execute(
        select(LivePosition)
        .where(LivePosition.deployment_id == deployment_id, LivePosition.status == "OPEN")
        .order_by(LivePosition.opened_at.desc())
        .limit(1)
    )
    return rows.scalar_one_or_none()


async def open_position(
    db: AsyncSession,
    deployment: StrategyDeployment,
    symbol: str,
    side: str,
    qty: Decimal,
    entry_price: Decimal,
    stop_loss: Optional[Decimal],
    target: Optional[Decimal],
) -> LivePosition:
    position = LivePosition(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        broker_account_id=deployment.broker_account_id,
        symbol=symbol,
        side=side,
        qty=qty,
        avg_entry_price=entry_price,
        current_price=entry_price,
        stop_loss=stop_loss,
        target=target,
        unrealized_pnl=Decimal("0"),
        realized_pnl=Decimal("0"),
        status="OPEN",
    )
    db.add(position)
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type="POSITION_OPENED",
        level="INFO",
        message=f"{side} paper position opened for {symbol}",
        metadata_json={"qty": str(qty), "entry_price": str(entry_price), "stop_loss": str(stop_loss), "target": str(target)},
    ))
    await db.flush()
    return position


async def close_position(
    db: AsyncSession,
    deployment: StrategyDeployment,
    position: LivePosition,
    exit_price: Decimal,
    reason: str = "Signal exit",
) -> Decimal:
    pnl = calculate_position_pnl(position.side, position.avg_entry_price, exit_price, position.qty)
    position.current_price = exit_price
    position.unrealized_pnl = Decimal("0")
    position.realized_pnl = pnl
    position.status = "CLOSED"
    position.closed_at = datetime.now(timezone.utc)
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type="POSITION_CLOSED",
        level="INFO",
        message=f"{position.side} paper position closed for {position.symbol}",
        metadata_json={"exit_price": str(exit_price), "realized_pnl": str(pnl), "reason": reason},
    ))
    await db.flush()
    return pnl


async def update_unrealized_pnl(db: AsyncSession, position: LivePosition, mark_price: Decimal) -> Decimal:
    pnl = calculate_position_pnl(position.side, position.avg_entry_price, mark_price, position.qty)
    position.current_price = mark_price
    position.unrealized_pnl = pnl
    await db.flush()
    return pnl
