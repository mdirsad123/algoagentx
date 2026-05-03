from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import BrokerAccount, LiveOrder, LiveSignal, LiveTradeLog, StrategyDeployment
from ..brokers.base import BrokerOrderRequest
from ..brokers.factory import get_broker_adapter, get_broker_code
from .paper_broker import fill_market_order
from .pnl_service import create_equity_point, to_decimal
from .position_service import close_position, get_open_positions, open_position
from .risk_manager import validate_signal_for_execution, validate_upstox_order_rules
from .trading_safety import LIVE_DISABLED_MESSAGE, check_execution_safety, mark_heartbeat
from .live_approval_service import check_live_execution_gate
from .order_preview_service import build_live_order_preview


def _round(value: Decimal, places: str = "0.00000001") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_DOWN)


def _result_volume(result, fallback: Decimal) -> Decimal:
    raw = getattr(result, "raw_response", None) or {}
    try:
        request = raw.get("request") if isinstance(raw, dict) else {}
        if isinstance(request, dict) and request.get("volume") not in (None, ""):
            return to_decimal(request.get("volume"), str(fallback))
        volume_debug = raw.get("volume_debug") if isinstance(raw, dict) else {}
        if isinstance(volume_debug, dict) and volume_debug.get("normalized_volume") not in (None, ""):
            return to_decimal(volume_debug.get("normalized_volume"), str(fallback))
    except Exception:
        pass
    return fallback


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
    if str(getattr(deployment, "quantity_mode", "RISK_BASED") or "RISK_BASED").upper() == "FIXED_QTY":
        qty = to_decimal(getattr(deployment, "fixed_quantity", None), "0")
    else:
        qty = Decimal("0") if price_risk <= 0 else risk_amount / price_risk
    return side, _round(qty, "1") if str(getattr(deployment, "quantity_mode", "") or "").upper() == "FIXED_QTY" else _round(qty), _round(stop_loss), _round(target)


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
    sizing_metadata: Optional[dict] = None,
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
        raw_response={**(raw_response or {}), **({"sizing": sizing_metadata} if sizing_metadata else {})},
    )
    if sizing_metadata:
        for field, key in {
            "quantity_mode": "quantity_mode",
            "requested_lot": "requested_lot",
            "final_lot": "final_lot",
            "requested_quantity": "requested_quantity",
            "final_quantity": "final_quantity",
            "risk_amount": "risk_amount",
            "actual_risk": "actual_risk",
            "instrument_spec_snapshot": "instrument_spec_snapshot",
            "runtime_config_snapshot": "runtime_config_snapshot",
        }.items():
            if hasattr(order, field):
                setattr(order, field, sizing_metadata.get(key))
    db.add(order)
    await _log(db, deployment, "ORDER_ERROR", message, "ERROR", {"signal_id": str(signal.id), "symbol": signal.symbol, "side": side, "sizing": sizing_metadata or {}})
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
    sizing_metadata: Optional[dict] = None,
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
    await _log(db, deployment, "BROKER_EXECUTION_STARTED", "MT5 demo order send started", metadata={"broker_account_id": str(broker.id), "signal_id": str(signal.id), "sizing": sizing_metadata or {}})
    broker_symbol = getattr(deployment, "broker_symbol", None) or signal.symbol
    result = await adapter.place_market_order(BrokerOrderRequest(
        symbol=broker_symbol,
        side=order_side,
        qty=qty,
        price=price,
        stop_loss=stop_loss,
        target=target,
        comment="AlgoAgentX Demo",
        max_lot=getattr(deployment, "mt5_demo_max_lot", None),
    ))
    actual_qty = _result_volume(result, qty)

    order = LiveOrder(
        deployment_id=deployment.id,
        signal_id=signal.id,
        user_id=deployment.user_id,
        broker_account_id=deployment.broker_account_id,
        broker_order_id=result.broker_order_id,
        symbol=broker_symbol,
        side=order_side,
        order_type="MARKET",
        qty=actual_qty,
        entry_price=price,
        executed_price=result.executed_price if result.success else None,
        stop_loss=stop_loss,
        target=target,
        status="FILLED" if result.success else "ERROR",
        error_message=None if result.success else result.message,
        raw_response={**(result.raw_response or {}), **({"sizing": sizing_metadata} if sizing_metadata else {})},
    )
    if sizing_metadata:
        for field, key in {
            "quantity_mode": "quantity_mode",
            "requested_lot": "requested_lot",
            "final_lot": "final_lot",
            "requested_quantity": "requested_quantity",
            "final_quantity": "final_quantity",
            "risk_amount": "risk_amount",
            "actual_risk": "actual_risk",
            "instrument_spec_snapshot": "instrument_spec_snapshot",
            "runtime_config_snapshot": "runtime_config_snapshot",
        }.items():
            if hasattr(order, field):
                setattr(order, field, sizing_metadata.get(key))
    db.add(order)
    await db.flush()

    if not result.success:
        signal.status = "ERROR"
        signal.rejection_reason = result.message
        await _log(db, deployment, "BROKER_ORDER_ERROR", result.message, "ERROR", {"signal_id": str(signal.id), "order_id": str(order.id)})
        return order

    executed_price = result.executed_price or price
    await _log(db, deployment, "BROKER_ORDER_FILLED", "MT5 demo market order filled/placed", metadata={"signal_id": str(signal.id), "order_id": str(order.id), "broker_order_id": result.broker_order_id, "sizing": sizing_metadata or {}})
    await open_position(db, deployment, broker_symbol, position_side, actual_qty, executed_price, stop_loss, target)
    signal.status = "EXECUTED"
    return order


async def _execute_demo_close(db: AsyncSession, deployment: StrategyDeployment, signal: LiveSignal, position, price: Decimal) -> LiveOrder:
    close_side = "SELL" if position.side == "LONG" else "BUY"
    if not deployment.broker_account_id:
        signal.status = "REJECTED"
        signal.rejection_reason = "DEMO close requires broker account"
        return await _create_error_order(db, deployment, signal, close_side, to_decimal(position.qty), price, signal.rejection_reason)
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None or broker.status != "CONNECTED":
        signal.status = "REJECTED"
        signal.rejection_reason = "DEMO close requires CONNECTED broker account"
        return await _create_error_order(db, deployment, signal, close_side, to_decimal(position.qty), price, signal.rejection_reason)
    adapter = get_broker_adapter(broker)
    await _log(db, deployment, "BROKER_CLOSE_STARTED", "MT5 demo close order send started", metadata={"signal_id": str(signal.id), "position_id": str(position.id), "symbol": position.symbol})
    result = await adapter.close_position(position.symbol, position.side, to_decimal(position.qty))
    actual_qty = _result_volume(result, to_decimal(position.qty))

    order = LiveOrder(
        deployment_id=deployment.id,
        signal_id=signal.id,
        user_id=deployment.user_id,
        broker_account_id=deployment.broker_account_id,
        broker_order_id=result.broker_order_id,
        symbol=position.symbol,
        side=close_side,
        order_type="MARKET",
        qty=actual_qty,
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
        signal.status = "EXECUTED"
        await _log(db, deployment, "BROKER_POSITION_CLOSED", "MT5 demo position close order filled/placed", metadata={"signal_id": str(signal.id), "order_id": str(order.id), "broker_order_id": result.broker_order_id})
    else:
        signal.status = "ERROR"
        signal.rejection_reason = result.message
        await _log(db, deployment, "BROKER_CLOSE_ERROR", result.message, "ERROR", {"signal_id": str(signal.id), "position_id": str(position.id), "order_id": str(order.id)})
    return order


async def _execute_upstox_entry(
    db: AsyncSession,
    deployment: StrategyDeployment,
    signal: LiveSignal,
    order_side: str,
    position_side: str,
    qty: Decimal,
    price: Decimal,
    stop_loss: Decimal,
    target: Decimal,
    sizing_metadata: Optional[dict] = None,
) -> LiveOrder:
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None or broker.status != "CONNECTED":
        msg = "Upstox execution requires CONNECTED broker account"
        signal.status = "REJECTED"
        signal.rejection_reason = msg
        return await _create_error_order(db, deployment, signal, order_side, qty, price, msg, stop_loss=stop_loss, target=target)

    risk = await validate_upstox_order_rules(db, deployment, signal, qty, price)
    if not risk.allowed:
        signal.status = "REJECTED"
        signal.rejection_reason = risk.reason
        return await _create_error_order(db, deployment, signal, order_side, qty, price, risk.reason or "Upstox risk rejected", stop_loss=stop_loss, target=target)

    instrument_key = getattr(deployment, "instrument_key", None) or getattr(deployment, "broker_symbol", None) or signal.symbol
    adapter = get_broker_adapter(broker)
    await _log(db, deployment, "UPSTOX_ORDER_STARTED", "Upstox order send started", metadata={"instrument_key": instrument_key, "signal_id": str(signal.id), "side": order_side, "qty": str(qty), "sizing": sizing_metadata or {}})
    result = await adapter.place_market_order(BrokerOrderRequest(
        symbol=signal.symbol,
        instrument_key=instrument_key,
        side=order_side,
        qty=qty,
        price=price,
        stop_loss=stop_loss,
        target=target,
        product_type=getattr(deployment, "product_type", "MIS"),
        order_variety=getattr(deployment, "order_variety", "REGULAR"),
        tag=f"AAX-{str(deployment.id)[:8]}",
    ))
    status = result.status if result.success else "ERROR"
    order = LiveOrder(
        deployment_id=deployment.id, signal_id=signal.id, user_id=deployment.user_id, broker_account_id=deployment.broker_account_id,
        broker_order_id=result.broker_order_id, symbol=instrument_key, side=order_side, order_type="MARKET", qty=qty, entry_price=price,
        executed_price=result.executed_price if result.success else None, stop_loss=stop_loss, target=target, status=status,
        error_message=None if result.success else result.message, raw_response={**(result.raw_response or {}), **({"sizing": sizing_metadata} if sizing_metadata else {})},
    )
    if sizing_metadata:
        for field, key in {
            "quantity_mode": "quantity_mode",
            "requested_lot": "requested_lot",
            "final_lot": "final_lot",
            "requested_quantity": "requested_quantity",
            "final_quantity": "final_quantity",
            "risk_amount": "risk_amount",
            "actual_risk": "actual_risk",
            "instrument_spec_snapshot": "instrument_spec_snapshot",
            "runtime_config_snapshot": "runtime_config_snapshot",
        }.items():
            if hasattr(order, field):
                setattr(order, field, sizing_metadata.get(key))
    db.add(order)
    await db.flush()
    if not result.success:
        signal.status = "ERROR"
        signal.rejection_reason = result.message
        await _log(db, deployment, "UPSTOX_ORDER_ERROR", result.message, "ERROR", {"signal_id": str(signal.id), "order_id": str(order.id)})
        return order

    signal.status = "EXECUTED"
    executed_price = result.executed_price or price
    await open_position(db, deployment, instrument_key, position_side, qty, executed_price, stop_loss, target)
    await _log(db, deployment, "UPSTOX_ORDER_PLACED", "Upstox order placed", metadata={"signal_id": str(signal.id), "order_id": str(order.id), "broker_order_id": result.broker_order_id, "status": status, "sizing": sizing_metadata or {}})
    return order


async def _execute_upstox_close(db: AsyncSession, deployment: StrategyDeployment, signal: LiveSignal, position, price: Decimal) -> LiveOrder:
    close_side = "SELL" if position.side == "LONG" else "BUY"
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None or broker.status != "CONNECTED":
        msg = "Upstox close requires CONNECTED broker account"
        signal.status = "REJECTED"
        signal.rejection_reason = msg
        return await _create_error_order(db, deployment, signal, close_side, to_decimal(position.qty), price, msg)

    risk = await validate_upstox_order_rules(db, deployment, signal, to_decimal(position.qty), price)
    if not risk.allowed:
        signal.status = "REJECTED"
        signal.rejection_reason = risk.reason
        return await _create_error_order(db, deployment, signal, close_side, to_decimal(position.qty), price, risk.reason or "Upstox close rejected")

    adapter = get_broker_adapter(broker)
    result = await adapter.place_market_order(BrokerOrderRequest(
        symbol=position.symbol, instrument_key=position.symbol, side=close_side, qty=to_decimal(position.qty), price=price, product_type=getattr(deployment, "product_type", "MIS"), tag=f"AAX-EXIT-{str(deployment.id)[:8]}"
    ))
    order = LiveOrder(
        deployment_id=deployment.id, signal_id=signal.id, user_id=deployment.user_id, broker_account_id=deployment.broker_account_id,
        broker_order_id=result.broker_order_id, symbol=position.symbol, side=close_side, order_type="MARKET", qty=to_decimal(position.qty),
        entry_price=price, executed_price=result.executed_price if result.success else None, status=result.status if result.success else "ERROR",
        error_message=None if result.success else result.message, raw_response=result.raw_response,
    )
    db.add(order)
    await db.flush()
    if result.success:
        await close_position(db, deployment, position, result.executed_price or price, reason=f"{signal.signal_type} signal")
        signal.status = "EXECUTED"
        await _log(db, deployment, "UPSTOX_POSITION_CLOSE_PLACED", "Upstox close order placed", metadata={"signal_id": str(signal.id), "order_id": str(order.id), "broker_order_id": result.broker_order_id})
    else:
        signal.status = "ERROR"
        signal.rejection_reason = result.message
        await _log(db, deployment, "UPSTOX_CLOSE_ERROR", result.message, "ERROR", {"signal_id": str(signal.id), "order_id": str(order.id)})
    return order


async def execute_signal(db: AsyncSession, deployment: StrategyDeployment, signal: LiveSignal) -> Optional[LiveOrder]:
    await _log(db, deployment, "EXECUTION_STARTED", f"{deployment.mode} execution started for {signal.signal_type}", metadata={"signal_id": str(signal.id)})

    if deployment.mode == "LIVE":
        gate = await check_live_execution_gate(db, deployment)
        if not gate.allowed:
            signal.status = "REJECTED"
            signal.rejection_reason = gate.reason or LIVE_DISABLED_MESSAGE
            await _log(db, deployment, "LIVE_EXECUTION_BLOCKED", signal.rejection_reason, "WARNING", {"signal_id": str(signal.id), "approval_gate": True})
            return None
        # Final production connector intentionally remains blocked until provider-specific LIVE execution is certified.
        signal.status = "REJECTED"
        signal.rejection_reason = LIVE_DISABLED_MESSAGE
        await _log(db, deployment, "LIVE_EXECUTION_BLOCKED", signal.rejection_reason, "WARNING", {"signal_id": str(signal.id), "final_connector_gate": True})
        return None

    safety = await check_execution_safety(db, deployment, signal)
    if not safety.allowed:
        signal.status = "REJECTED"
        signal.rejection_reason = safety.reason
        await _log(db, deployment, "SAFETY_REJECTED", safety.reason or "Safety rejected", "WARNING", {"signal_id": str(signal.id)})
        return None

    await mark_heartbeat(db, deployment)

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
                broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none() if deployment.broker_account_id else None
                if broker is not None and get_broker_code(broker) == "UPSTOX":
                    latest_order = await _execute_upstox_close(db, deployment, signal, position, price)
                else:
                    latest_order = await _execute_demo_close(db, deployment, signal, position, price)
        await create_equity_point(db, deployment)
        if latest_order is not None and latest_order.status == "ERROR":
            await _log(db, deployment, "EXECUTION_ABORTED", "Entry skipped because MT5 position close failed", "ERROR", {"signal_id": str(signal.id), "order_id": str(latest_order.id)})
            return latest_order
        if risk.action == "CLOSE_ONLY":
            if signal.status not in {"ERROR", "REJECTED"}:
                signal.status = "EXECUTED"
            return latest_order

    if signal.signal_type in {"BUY", "SELL"}:
        current_open_positions = await get_open_positions(db, deployment.id)
        max_open_positions = int(getattr(deployment, "max_open_positions", 1) or 1)
        if len(current_open_positions) >= max_open_positions:
            signal.status = "REJECTED"
            signal.rejection_reason = "Max open positions reached."
            await _log(db, deployment, "MAX_OPEN_POSITIONS_REACHED", "Max open positions reached. New signal skipped.", "WARNING", {"signal_id": str(signal.id), "open_positions": len(current_open_positions), "max_open_positions": max_open_positions})
            return latest_order
        broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none() if deployment.broker_account_id else None
        broker_code = get_broker_code(broker) if broker is not None else ("PAPER" if deployment.mode == "PAPER" else "MT5")
        preview = await build_live_order_preview(
            db,
            deployment=deployment,
            broker_code=broker_code,
            symbol=signal.symbol or deployment.instrument,
            side=signal.signal_type,
            entry_price=price,
            runtime_config=None,
            strict_instrument=deployment.mode in {"DEMO", "LIVE"},
            preview_mode="AUTO_LIVE_SIGNAL",
        )
        if preview.get("validation_status") != "OK":
            # PAPER may keep legacy behavior when an old deployment has no instrument master; DEMO/LIVE never fallback.
            if deployment.mode in {"DEMO", "LIVE"}:
                signal.status = "REJECTED"
                signal.rejection_reason = preview.get("rejected_reason") or "Risk engine rejected order sizing"
                await _log(db, deployment, "RISK_ENGINE_REJECTED", signal.rejection_reason, "WARNING", {"signal_id": str(signal.id), "preview": preview})
                return latest_order
            position_side, qty, stop_loss, target = calculate_entry_plan(deployment, signal.signal_type, price)
            sizing_metadata = {"legacy_fallback": True, "rejected_preview": preview}
        else:
            position_side = "LONG" if signal.signal_type == "BUY" else "SHORT"
            order_side = signal.signal_type
            stop_loss = to_decimal(preview.get("stop_loss"), "0")
            target = to_decimal(preview.get("target"), "0")
            if str(preview.get("quantity_mode") or "").upper() == "LOTS":
                qty = to_decimal(preview.get("final_lot_size"), "0")
            else:
                qty = to_decimal(preview.get("final_quantity"), "0")
            sizing_metadata = preview.get("risk_metadata") or {}
        if qty <= 0:
            signal.status = "REJECTED"
            signal.rejection_reason = "Calculated lot/quantity is zero"
            await _log(db, deployment, "RISK_REJECTED", "Calculated lot/quantity is zero", "WARNING", {"signal_id": str(signal.id), "sizing": sizing_metadata})
            return latest_order
        order_side = "BUY" if position_side == "LONG" else "SELL"
        if deployment.mode == "PAPER":
            latest_order = await fill_market_order(db, deployment, signal, order_side, qty, price, stop_loss, target, action="ENTRY")
            if latest_order is not None:
                raw = getattr(latest_order, "raw_response", None) or {}
                latest_order.raw_response = {**raw, **({"sizing": sizing_metadata} if sizing_metadata else {})}
                for field, key in {
                    "quantity_mode": "quantity_mode",
                    "requested_lot": "requested_lot",
                    "final_lot": "final_lot",
                    "requested_quantity": "requested_quantity",
                    "final_quantity": "final_quantity",
                    "risk_amount": "risk_amount",
                    "actual_risk": "actual_risk",
                    "instrument_spec_snapshot": "instrument_spec_snapshot",
                    "runtime_config_snapshot": "runtime_config_snapshot",
                }.items():
                    if hasattr(latest_order, field):
                        setattr(latest_order, field, sizing_metadata.get(key))
            await open_position(db, deployment, signal.symbol, position_side, qty, price, stop_loss, target)
            signal.status = "EXECUTED"
            await _log(db, deployment, "PAPER_ORDER_SIZED", "Paper order sized with shared risk engine", metadata={"signal_id": str(signal.id), "sizing": sizing_metadata})
        elif deployment.mode == "DEMO":
            if broker is not None and get_broker_code(broker) == "UPSTOX":
                latest_order = await _execute_upstox_entry(db, deployment, signal, order_side, position_side, qty, price, stop_loss, target, sizing_metadata=sizing_metadata)
            else:
                latest_order = await _execute_demo_entry(db, deployment, signal, order_side, position_side, qty, price, stop_loss, target, sizing_metadata=sizing_metadata)
        await create_equity_point(db, deployment)
        return latest_order

    signal.status = "ACCEPTED"
    await create_equity_point(db, deployment)
    return latest_order
