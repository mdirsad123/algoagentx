from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import LiveOrder, LiveSignal, LiveTradeLog, StrategyDeployment


async def fill_market_order(
    db: AsyncSession,
    deployment: StrategyDeployment,
    signal: LiveSignal,
    side: str,
    qty: Decimal,
    price: Decimal,
    stop_loss: Optional[Decimal] = None,
    target: Optional[Decimal] = None,
    action: str = "ENTRY",
) -> LiveOrder:
    status = "FILLED" if deployment.mode == "PAPER" else "PENDING_DEMO"
    order = LiveOrder(
        deployment_id=deployment.id,
        signal_id=signal.id,
        user_id=deployment.user_id,
        broker_account_id=deployment.broker_account_id,
        symbol=signal.symbol,
        side=side,
        order_type="MARKET",
        qty=qty,
        entry_price=price,
        executed_price=price if deployment.mode == "PAPER" else None,
        stop_loss=stop_loss,
        target=target,
        status=status,
        raw_response={"mode": deployment.mode, "broker": "PAPER_ENGINE", "action": action},
    )
    db.add(order)
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type="ORDER_FILLED" if status == "FILLED" else "ORDER_CREATED",
        level="INFO",
        message=f"{deployment.mode} {side} market order {status.lower()} for {signal.symbol}",
        metadata_json={"signal_id": str(signal.id), "qty": str(qty), "price": str(price), "status": status, "action": action},
    ))
    await db.flush()
    return order
