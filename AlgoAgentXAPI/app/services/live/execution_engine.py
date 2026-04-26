from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import BrokerAccount, LiveOrder, LiveSignal, LiveTradeLog, StrategyDeployment
from ..brokers.base import BrokerOrderRequest
from ..brokers.factory import get_broker_adapter
from .paper_broker import fill_market_order
from .pnl_service import create_equity_point, to_decimal
from .position_service import close_position, get_open_positions, open_position
from .risk_manager import validate_signal_for_execution


def _round(value: Decimal, places: str = "0.00000001") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_DOWN)


def calculate_entry_plan(deployment: StrategyDeployment, signal_type: str, price: Decimal) -> tuple[str, Decimal, Decimal, Decimal]:
    capital = to_decimal(deployment.capital, "100000")
    risk_per_trade = to_decimal(deployment.risk_per_trade, "0.01")
    price_risk_pct = to_decimal(deployment.price_risk_pct, "0.002")
    rr_ratio = to_decimal(deployment.rr_ratio, "2")

    if signal_type == "BUY":
        stop_loss = price * (Decimal("1") - price_risk_pct)
        target = price + ((price - stop_loss) * rr_ratio)
        side = "LONG"
    else:
        stop_loss = price * (Decimal("1") + price_risk_pct)
        target = price - ((stop_loss - price) * rr_ratio)
        side = "SHORT"

    risk_amount = capital * risk_per_trade
    price_risk = abs(price - stop_loss)
    qty = Decimal("0") if price_risk <= 0 else risk_amount / price_risk
    return side, _round(qty), _round(stop_loss), _round(target)


async def _log(db: AsyncSession, deployment: StrategyDeployment, event_type: str, message: str, level: str = "INFO", metadata: Optional[dict] = None) -> None:
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=event_type,
        level=level,
        message=message,
        metadata_json=metadata or {},
    ))


async def _create_error_order(
    db: AsyncSession,
    deployment: StrategyDeployment,
    signal: LiveSignal,
    side: str,
    qty: Decimal,
    price: Decimal,
    message: str,
    raw_response: Optional[dict] = None,
    stop_loss: Optional[Decimal] = None,
    target: Optional[Decimal] = None,
) -> LiveOrder:
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
        executed_price=None,
        stop_loss=stop_loss,
        target=target,
        status="ERROR",
        error_message=message,
        raw_response=raw_response or {},
    )
    db.add(order)
    await _log(db, deployment, "ORDER_ERROR", message, "ERROR", {"signal_id": str(signal.id), "symbol": signal.symbol, "side": side})
    await db.flush()
    return order


async def _execute_demo_entry(
    db: AsyncSession,
    deployment: StrategyDeployment,
    signal: LiveSignal,
    order_side: str,
    position_side: str,
    qty: Decimal,
    price: Decimal,
    stop_loss: Decimal,
    target: Decimal,
) -> LiveOrder:
    if not deployment.broker_account_id:
        signal.status = "REJECTED"
        signal.rejection_reason = "DEMO mode requires connected MT5 broker account"
        return await _create_error_order(db, deployment, signal, order_side, qty, price, signal.rejection_reason, stop_loss=stop_loss, target=target)

    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None or broker.status != "CONNECTED":
        msg = "DEMO execution requires broker account status CONNECTED. Use Brokers → Test Connection first."
        signal.status = "REJECTED"
        signal.rejection_reason = msg
        return await _create_error_order(db, deployment, signal, order_side, qty, price, msg, stop_loss=stop_loss, target=target)

    adapter = get_broker_adapter(broker)
    await _log(db, deployment, "BROKER_EXECUTION_STARTED", "MT5 demo order send started", metadata={"broker_account_id": str(broker.id), "signal_id": str(signal.id)})
    result = await adapter.place_market_order(BrokerOrderRequest(
        symbol=signal.symbol,
        side=order_side,
        qty=qty,
        price=price,
        stop_loss=stop_loss,
        target=target,
        comment="AlgoAgentX Demo",
    ))

    order = LiveOrder(
        deployment_id=deployment.id,
        signal_id=signal.id,
        user_id=deployment.user_id,
        broker_account_id=deployment.broker_account_id,
        broker_order_id=result.broker_order_id,
        symbol=signal.symbol,
        side=order_side,
        order_type="MARKET",
        qty=qty,
        entry_price=price,
        executed_price=result.executed_price if result.success else None,
        stop_loss=stop_loss,
        target=target,
        status="FILLED" if result.success else "ERROR",
        error_message=None if result.success else result.message,
        raw_response=result.raw_response,
    )
    db.add(order)
    await db.flush()

    if not result.success:
        signal.status = "ERROR"
        signal.rejection_reason = result.message
        await _log(db, deployment, "BROKER_ORDER_ERROR", result.message, "ERROR", {"signal_id": str(signal.id), "order_id": str(order.id)})
        return order

    executed_price = result.executed_price or price
    await _log(db, deployment, "BROKER_ORDER_FILLED", "MT5 demo market order filled/placed", metadata={"signal_id": str(signal.id), "order_id": str(order.id), "broker_order_id": result.broker_order_id})
    await open_position(db, deployment, signal.symbol, position_side, qty, executed_price, stop_loss, target)
    signal.status = "EXECUTED"
    return order


async def _execute_demo_close(db: AsyncSession, deployment: StrategyDeployment, signal: LiveSignal, position, price: Decimal) -> LiveOrder:
    close_side = "SELL" if position.side == "LONG" else "BUY"
    if not deployment.broker_account_id:
        return await _create_error_order(db, deployment, signal, close_side, to_decimal(position.qty), price, "DEMO close requires broker account")
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None or broker.status != "CONNECTED":
        return await _create_error_order(db, deployment, signal, close_side, to_decimal(position.qty), price, "DEMO close requires CONNECTED broker account")
    adapter = get_broker_adapter(broker)
    result = await adapter.close_position(position.symbol, position.side, to_decimal(position.qty))
    order = LiveOrder(
        deployment_id=deployment.id,
        signal_id=signal.id,
        user_id=deployment.user_id,
        broker_account_id=deployment.broker_account_id,
        broker_order_id=result.broker_order_id,
        symbol=position.symbol,
        side=close_side,
        order_type="MARKET",
        qty=to_decimal(position.qty),
        entry_price=price,
        executed_price=result.executed_price if result.success else None,
        status="FILLED" if result.success else "ERROR",
        error_message=None if result.success else result.message,
        raw_response=result.raw_response,
    )
    db.add(order)
    await db.flush()
    if result.success:
        await close_position(db, deployment, position, result.executed_price or price, reason=f"{signal.signal_type} signal")
        await _log(db, deployment, "BROKER_POSITION_CLOSED", "MT5 demo position close order filled/placed", metadata={"signal_id": str(signal.id), "order_id": str(order.id)})
    else:
        signal.status = "ERROR"
        signal.rejection_reason = result.message
        await _log(db, deployment, "BROKER_CLOSE_ERROR", result.message, "ERROR", {"signal_id": str(signal.id), "position_id": str(position.id)})
    return order


async def execute_signal(db: AsyncSession, deployment: StrategyDeployment, signal: LiveSignal) -> Optional[LiveOrder]:
    await _log(db, deployment, "EXECUTION_STARTED", f"{deployment.mode} execution started for {signal.signal_type}", metadata={"signal_id": str(signal.id)})

    if deployment.mode == "LIVE":
        signal.status = "REJECTED"
        signal.rejection_reason = "LIVE trading is not enabled yet"
        await _log(db, deployment, "RISK_REJECTED", signal.rejection_reason, "WARNING", {"signal_id": str(signal.id)})
        return None

    risk = await validate_signal_for_execution(db, deployment, signal)
    if not risk.allowed:
        signal.status = "REJECTED"
        signal.rejection_reason = risk.reason
        await _log(db, deployment, "RISK_REJECTED", risk.reason or "Risk rejected", "WARNING", {"signal_id": str(signal.id)})
        return None

    if risk.action == "HOLD":
        signal.status = "ACCEPTED"
        await _log(db, deployment, "EXECUTION_SKIPPED", "HOLD signal saved without order", metadata={"signal_id": str(signal.id)})
        await create_equity_point(db, deployment)
        return None

    price = to_decimal(signal.price)
    latest_order: Optional[LiveOrder] = None

    if risk.action in {"CLOSE_ONLY", "CLOSE_AND_OPEN"}:
        open_positions = await get_open_positions(db, deployment.id)
        for position in open_positions:
            exit_side = "SELL" if position.side == "LONG" else "BUY"
            if deployment.mode == "PAPER":
                latest_order = await fill_market_order(db, deployment, signal, exit_side, to_decimal(position.qty), price, action="EXIT")
                await close_position(db, deployment, position, price, reason=f"{signal.signal_type} signal")
            elif deployment.mode == "DEMO":
                latest_order = await _execute_demo_close(db, deployment, signal, position, price)
        await create_equity_point(db, deployment)
        if risk.action == "CLOSE_ONLY":
            if signal.status not in {"ERROR", "REJECTED"}:
                signal.status = "EXECUTED"
            return latest_order

    if signal.signal_type in {"BUY", "SELL"}:
        position_side, qty, stop_loss, target = calculate_entry_plan(deployment, signal.signal_type, price)
        if qty <= 0:
            signal.status = "REJECTED"
            signal.rejection_reason = "Calculated quantity is zero"
            await _log(db, deployment, "RISK_REJECTED", "Calculated quantity is zero", "WARNING", {"signal_id": str(signal.id)})
            return latest_order
        order_side = "BUY" if position_side == "LONG" else "SELL"
        if deployment.mode == "PAPER":
            latest_order = await fill_market_order(db, deployment, signal, order_side, qty, price, stop_loss, target, action="ENTRY")
            await open_position(db, deployment, signal.symbol, position_side, qty, price, stop_loss, target)
            signal.status = "EXECUTED"
        elif deployment.mode == "DEMO":
            latest_order = await _execute_demo_entry(db, deployment, signal, order_side, position_side, qty, price, stop_loss, target)
        await create_equity_point(db, deployment)
        return latest_order

    signal.status = "ACCEPTED"
    await create_equity_point(db, deployment)
    return latest_order
