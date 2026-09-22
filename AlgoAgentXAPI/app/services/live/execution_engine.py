from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone
import hashlib
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.redis_manager import redis_manager

from ...db.models import BrokerAccount, LiveOrder, LiveSignal, LiveTradeLog, StrategyDeployment
from ..brokers.base import BrokerOrderRequest
from ..brokers.factory import get_broker_adapter, get_broker_code
from .paper_broker import fill_market_order
from .pnl_service import create_equity_point, to_decimal
from .position_service import close_position, get_open_positions, open_position
from .risk_manager import RiskResult, validate_signal_for_execution, validate_upstox_order_rules
from .trading_safety import check_execution_safety, mark_heartbeat
from .capital_service import get_effective_trading_capital
from .order_preview_service import build_live_order_preview
from .funded_guard_service import current_funded_trades_count, evaluate_funded_guard, record_funded_trade_count
from .broker_sync_service import sync_ctrader_deployment_via_gateway, sync_deployment_broker_state
from .live_latency_trace_service import LiveLatencyTraceService
from .live_event_bus import LiveEventBus
from ..brokers.ctrader_order_gateway import submit_close_position, submit_market_order


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


def _is_ctrader_broker(broker: BrokerAccount | None) -> bool:
    return get_broker_code(broker) in {"CTRADER", "CTRADER_API"} if broker is not None else False


def _client_order_id(deployment: StrategyDeployment, signal: LiveSignal, action: str = "ENTRY") -> str:
    candle_time = getattr(signal, "candle_time", None)
    candle_key = candle_time.isoformat() if hasattr(candle_time, "isoformat") else str(candle_time or "manual")
    return f"AX:{deployment.id}:{signal.id}:{candle_key}:{signal.signal_type}:{action}"


def _ctrader_client_order_id(
    deployment: StrategyDeployment,
    signal: LiveSignal,
    action: str = "ENTRY",
    *,
    scope: str | None = None,
) -> str:
    """Stable external id independent of a retry-created signal row UUID."""
    candle_time = getattr(signal, "candle_time", None)
    candle_key = candle_time.isoformat() if hasattr(candle_time, "isoformat") else str(candle_time or "manual")
    strategy_id = getattr(signal, "strategy_id", None) or getattr(deployment, "strategy_id", None) or "unknown"
    full = f"AX:{deployment.id}:{strategy_id}:{candle_key}:{signal.signal_type}:{action}:{scope or ''}"
    digest = hashlib.sha256(full.encode("utf-8")).hexdigest()[:24]
    return f"AX-{str(deployment.id)[:8]}-{action[:1]}-{digest}"[:50]


def _trace_service() -> LiveLatencyTraceService:
    return LiveLatencyTraceService(redis_manager.client if redis_manager.is_available else None)


async def _persistent_ctrader_connection_healthy(broker: BrokerAccount) -> bool:
    if not redis_manager.is_available or redis_manager.client is None:
        return False
    try:
        state = await LiveEventBus(redis_manager.client).get_health("live_market_worker")
        selected = _selected_ctrader_account(broker) or {}
        environment = "LIVE" if bool(selected.get("is_live")) or str(selected.get("account_type") or "").upper() == "LIVE" else "DEMO"
        connections = state.get("connections") if isinstance(state, dict) else None
        connection = connections.get(environment) if isinstance(connections, dict) else None
        return bool(isinstance(connection, dict) and connection.get("connected"))
    except Exception:
        return False


def _short_order_comment(client_order_id: str, prefix: str = "AX") -> str:
    safe = str(client_order_id or "")[-12:].replace(":", "").replace("-", "")
    return f"{prefix}-{safe}"[:31]


def _valid_entry_sltp(side: str, price: Decimal, stop_loss: Decimal | None, target: Decimal | None) -> tuple[bool, str | None]:
    if stop_loss is None or target is None or stop_loss <= 0 or target <= 0:
        return False, "SL/TP missing or zero. Broker order blocked for safety."
    side_u = str(side or "").upper()
    if side_u == "BUY" and not (stop_loss < price < target):
        return False, "Invalid BUY SL/TP: expected stop_loss < entry < target."
    if side_u == "SELL" and not (target < price < stop_loss):
        return False, "Invalid SELL SL/TP: expected target < entry < stop_loss."
    return True, None


async def _existing_order_for_client_id(db: AsyncSession, client_order_id: str) -> LiveOrder | None:
    if not client_order_id:
        return None
    return (await db.execute(select(LiveOrder).where(LiveOrder.client_order_id == client_order_id))).scalar_one_or_none()

def _selected_ctrader_account(broker: BrokerAccount | None) -> dict | None:
    meta = getattr(broker, "metadata_json", None) or {}
    selected = meta.get("ctrader_selected_account") if isinstance(meta, dict) else None
    return selected if isinstance(selected, dict) else None

def _ctrader_account_is_demo(broker: BrokerAccount | None) -> bool:
    selected = _selected_ctrader_account(broker)
    return str((selected or {}).get("account_type") or getattr(broker, "mode", "") or "").upper() == "DEMO"


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


def _safe_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _preview_cap_applied(preview: dict | None) -> bool:
    preview = preview or {}
    risk_metadata = preview.get("risk_metadata") if isinstance(preview.get("risk_metadata"), dict) else {}
    risk_engine = preview.get("risk_engine") if isinstance(preview.get("risk_engine"), dict) else {}
    raw_lot = _safe_float(risk_metadata.get("raw_lot") or risk_metadata.get("requested_lot") or risk_engine.get("raw_lot_size"))
    final_lot = _safe_float(risk_metadata.get("final_lot") or preview.get("final_lot_size") or risk_engine.get("final_lot_size"))
    max_lot = _safe_float(risk_metadata.get("max_lot_cap") or risk_engine.get("max_lot_cap"))
    raw_qty = _safe_float(risk_metadata.get("raw_quantity") or risk_metadata.get("requested_quantity") or risk_engine.get("raw_quantity"))
    final_qty = _safe_float(risk_metadata.get("final_quantity") or preview.get("final_quantity") or risk_engine.get("final_quantity"))
    max_qty = _safe_float(risk_metadata.get("max_quantity_cap") or risk_engine.get("max_quantity_cap"))
    if raw_lot is not None and final_lot is not None and max_lot is not None and raw_lot > final_lot and final_lot <= max_lot:
        return True
    if raw_qty is not None and final_qty is not None and max_qty is not None and raw_qty > final_qty and final_qty <= max_qty:
        return True
    return False


def _broker_payload_ok(preview: dict | None) -> bool:
    preview = preview or {}
    payload = preview.get("broker_payload_preview") or preview.get("broker_order_payload_preview")
    if not isinstance(payload, dict) or not payload.get("side") or not payload.get("symbol"):
        return False
    has_size = payload.get("volume") not in (None, "", 0) or payload.get("quantity") not in (None, "", 0)
    return bool(has_size and payload.get("sl") is not None and payload.get("tp") is not None)


async def _log_live_engine_qa_preview(
    db: AsyncSession,
    deployment: StrategyDeployment,
    *,
    signal: LiveSignal,
    preview: dict | None,
    strategy_stop_loss=None,
    strategy_target=None,
) -> None:
    preview = preview or {}
    base = {
        "context": "execute_signal",
        "signal_id": str(signal.id),
        "signal_type": signal.signal_type,
        "strategy_stop_loss": strategy_stop_loss,
        "strategy_target": strategy_target,
    }
    await _log(db, deployment, "LIVE_ENGINE_QA_SIGNAL_CONTRACT_PASS", "Live engine signal contract validated", metadata={**base, "signal_reason": getattr(signal, "reason", None)})

    entry_plan = preview.get("entry_plan") if isinstance(preview.get("entry_plan"), dict) else {}
    if entry_plan.get("status") == "OK" and preview.get("stop_loss") is not None and preview.get("target") is not None:
        await _log(db, deployment, "LIVE_ENGINE_QA_SLTP_PASS", "Live engine SL/TP contract validated", metadata={**base, "entry_price": preview.get("entry_price"), "final_stop_loss": preview.get("stop_loss"), "final_target": preview.get("target"), "sl_mode": entry_plan.get("sl_mode"), "stop_loss_source": entry_plan.get("stop_loss_source"), "target_source": entry_plan.get("target_source"), "risk_points": entry_plan.get("risk_points"), "reward_points": entry_plan.get("reward_points"), "rr_ratio": entry_plan.get("rr_ratio")})

    if str(preview.get("validation_status") or preview.get("status") or "").upper() == "OK":
        risk_metadata = preview.get("risk_metadata") if isinstance(preview.get("risk_metadata"), dict) else {}
        await _log(db, deployment, "LIVE_ENGINE_QA_RISK_PASS", "Live engine risk sizing validated", metadata={**base, "effective_capital": risk_metadata.get("effective_capital") or preview.get("effective_capital"), "effective_capital_source": risk_metadata.get("effective_capital_source") or preview.get("effective_capital_source"), "risk_percent": risk_metadata.get("risk_percent"), "risk_amount": risk_metadata.get("risk_amount") or preview.get("risk_amount"), "position_size_mode": risk_metadata.get("position_size_mode"), "raw_lot": risk_metadata.get("raw_lot"), "final_lot": risk_metadata.get("final_lot") or preview.get("final_lot_size"), "raw_quantity": risk_metadata.get("raw_quantity"), "final_quantity": risk_metadata.get("final_quantity") or preview.get("final_quantity"), "max_lot_cap": risk_metadata.get("max_lot_cap"), "cap_applied": _preview_cap_applied(preview)})
        if _broker_payload_ok(preview):
            await _log(db, deployment, "LIVE_ENGINE_QA_BROKER_PAYLOAD_PASS", "Live engine broker payload validated", metadata={**base, "broker_payload_preview": preview.get("broker_payload_preview") or preview.get("broker_order_payload_preview"), "cap_applied": _preview_cap_applied(preview)})


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
        trace_id=getattr(signal, "trace_id", None),
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
    await _trace_service().mark(getattr(signal, "trace_id", None), "t15", status="LOCAL_ERROR_ORDER_UPDATED", order_id=str(order.id))
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

    ok, sltp_error = _valid_entry_sltp(order_side, price, stop_loss, target)
    if not ok:
        signal.status = "REJECTED"
        signal.rejection_reason = sltp_error
        await _log(db, deployment, "LIVE_SLTP_SAFETY_BLOCKED", sltp_error or "SL/TP safety blocked order", "ERROR", {"signal_id": str(signal.id), "side": order_side, "entry_price": str(price), "stop_loss": str(stop_loss), "target": str(target)})
        return await _create_error_order(db, deployment, signal, order_side, qty, price, sltp_error or "SL/TP safety blocked order", stop_loss=stop_loss, target=target, sizing_metadata=sizing_metadata)

    client_order_id = _client_order_id(deployment, signal, "ENTRY")
    existing_order = await _existing_order_for_client_id(db, client_order_id)
    if existing_order is not None:
        signal.status = "EXECUTED" if existing_order.status in {"FILLED", "PLACED"} else signal.status
        await _log(db, deployment, "DUPLICATE_ORDER_BLOCKED", "Duplicate broker order blocked by client_order_id", "WARNING", {"signal_id": str(signal.id), "order_id": str(existing_order.id), "client_order_id": client_order_id})
        return existing_order

    adapter = get_broker_adapter(broker, db)
    await _log(db, deployment, "BROKER_EXECUTION_STARTED", "MT5 demo order send started", metadata={"broker_account_id": str(broker.id), "signal_id": str(signal.id), "client_order_id": client_order_id, "sizing": sizing_metadata or {}})
    broker_symbol = getattr(deployment, "broker_symbol", None) or signal.symbol
    result = await adapter.place_market_order(BrokerOrderRequest(
        symbol=broker_symbol,
        side=order_side,
        qty=qty,
        price=price,
        stop_loss=stop_loss,
        target=target,
        comment=_short_order_comment(client_order_id, "AX"),
        max_lot=getattr(deployment, "mt5_demo_max_lot", None),
        tag=client_order_id,
        idempotency_key=client_order_id,
    ))
    actual_qty = _result_volume(result, qty)

    order = LiveOrder(
        deployment_id=deployment.id,
        signal_id=signal.id,
        user_id=deployment.user_id,
        broker_account_id=deployment.broker_account_id,
        broker_order_id=result.broker_order_id,
        client_order_id=client_order_id,
        idempotency_key=client_order_id,
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
        raw_response={**(result.raw_response or {}), "client_order_id": client_order_id, **({"sizing": sizing_metadata} if sizing_metadata else {})},
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
    adapter = get_broker_adapter(broker, db)
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


async def _execute_ctrader_entry(
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
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none() if deployment.broker_account_id else None
    if broker is None or broker.status != "CONNECTED":
        msg = "cTrader demo execution requires CONNECTED broker account"
        signal.status = "REJECTED"
        signal.rejection_reason = msg
        return await _create_error_order(db, deployment, signal, order_side, qty, price, msg, stop_loss=stop_loss, target=target)
    if not bool(getattr(settings, "ctrader_demo_trading_enabled", True)):
        msg = "cTrader demo auto trading is disabled by platform configuration."
        signal.status = "REJECTED"
        signal.rejection_reason = msg
        return await _create_error_order(db, deployment, signal, order_side, qty, price, msg, stop_loss=stop_loss, target=target)
    if not _selected_ctrader_account(broker):
        msg = "cTrader account selection required before routing live deployment signals."
        signal.status = "REJECTED"
        signal.rejection_reason = msg
        return await _create_error_order(db, deployment, signal, order_side, qty, price, msg, stop_loss=stop_loss, target=target)
    if not _ctrader_account_is_demo(broker):
        msg = "cTrader live trading is not enabled yet."
        signal.status = "REJECTED"
        signal.rejection_reason = msg
        return await _create_error_order(db, deployment, signal, order_side, qty, price, msg, stop_loss=stop_loss, target=target)

    broker_symbol = getattr(deployment, "broker_symbol", None) or getattr(deployment, "instrument_key", None) or signal.symbol
    trace_id = str(getattr(signal, "trace_id", None) or "") or None
    client_order_id = _ctrader_client_order_id(deployment, signal, "ENTRY")
    idempotency_key = hashlib.sha256(f"CTRADER:{client_order_id}".encode()).hexdigest()
    existing = await _existing_order_for_client_id(db, client_order_id)
    if existing is not None:
        signal.status = "EXECUTED" if existing.status in {"FILLED", "PLACED", "ACCEPTED"} else signal.status
        await _log(db, deployment, "DUPLICATE_ORDER_BLOCKED", "Existing cTrader client order id reused; broker send skipped", "WARNING", {"signal_id": str(signal.id), "order_id": str(existing.id), "client_order_id": client_order_id})
        return existing

    order_request = BrokerOrderRequest(
        symbol=broker_symbol,
        side=order_side,
        qty=qty,
        price=price,
        stop_loss=stop_loss,
        target=target,
        comment="AlgoAgentX cTrader DEMO deployment",
        tag=client_order_id,
        idempotency_key=idempotency_key,
    )
    await _log(db, deployment, "CTRADER_SIGNAL_ROUTED", "cTrader DEMO signal routed to order service", metadata={"signal_id": str(signal.id), "symbol": broker_symbol, "side": order_side, "qty": str(qty), "client_order_id": client_order_id, "trace_id": trace_id, "sizing": sizing_metadata or {}})
    if settings.live_event_pipeline_enabled and settings.ctrader_persistent_connection_enabled:
        result = await submit_market_order(
            broker_account_id=str(broker.id),
            deployment_id=str(deployment.id),
            order_request=order_request,
            client_order_id=client_order_id,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
        )
    else:
        adapter = get_broker_adapter(broker, db)
        result = await adapter.place_market_order(order_request)
    actual_qty = _result_volume(result, qty)
    order = LiveOrder(
        trace_id=trace_id,
        deployment_id=deployment.id,
        signal_id=signal.id,
        user_id=deployment.user_id,
        broker_account_id=deployment.broker_account_id,
        broker_order_id=result.broker_order_id,
        client_order_id=client_order_id,
        idempotency_key=idempotency_key,
        symbol=broker_symbol,
        side=order_side,
        order_type="MARKET",
        qty=actual_qty,
        entry_price=price,
        executed_price=result.executed_price if result.success else None,
        stop_loss=stop_loss,
        target=target,
        status=("FILLED" if result.status == "FILLED" else "PLACED") if result.success else "ERROR",
        error_message=None if result.success else result.message,
        raw_response={**(result.raw_response or {}), **({"provider": "CTRADER", "sizing": sizing_metadata} if sizing_metadata else {"provider": "CTRADER"})},
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
    await _trace_service().mark(trace_id, "t15", status="LOCAL_ORDER_UPDATED", order_id=str(order.id))
    if not result.success:
        signal.status = "ERROR"
        signal.rejection_reason = result.message
        await _log(db, deployment, "CTRADER_ORDER_ERROR", result.message, "ERROR", {"signal_id": str(signal.id), "order_id": str(order.id), "broker_response": result.raw_response or {}})
        return order
    if result.status != "FILLED":
        signal.status = "ACCEPTED"
        await _log(db, deployment, "CTRADER_ORDER_AWAITING_FILL", "Broker accepted cTrader order; awaiting execution event and reconciliation", metadata={"signal_id": str(signal.id), "order_id": str(order.id), "broker_order_id": result.broker_order_id})
        return order
    executed_price = result.executed_price or price
    signal.status = "EXECUTED"
    live_position = await open_position(db, deployment, broker_symbol, position_side, actual_qty, executed_price, stop_loss, target)
    broker_position_id = (result.raw_response or {}).get("position_id")
    if broker_position_id:
        live_position.broker_position_id = str(broker_position_id)
    await _trace_service().mark(trace_id, "t16", status="LOCAL_POSITION_UPDATED", order_id=str(order.id))
    await _log(db, deployment, "CTRADER_ORDER_PLACED", "cTrader DEMO order placed", metadata={"signal_id": str(signal.id), "order_id": str(order.id), "broker_order_id": result.broker_order_id, "broker_position_id": broker_position_id, "broker_response": result.raw_response or {}, "sizing": sizing_metadata or {}})
    return order


async def _execute_ctrader_close(db: AsyncSession, deployment: StrategyDeployment, signal: LiveSignal, position, price: Decimal) -> LiveOrder:
    close_side = "SELL" if position.side == "LONG" else "BUY"
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none() if deployment.broker_account_id else None
    if broker is None or broker.status != "CONNECTED" or not _selected_ctrader_account(broker):
        msg = "cTrader close requires CONNECTED broker account and selected cTrader account"
        signal.status = "REJECTED"
        signal.rejection_reason = msg
        return await _create_error_order(db, deployment, signal, close_side, to_decimal(position.qty), price, msg)
    if not _ctrader_account_is_demo(broker):
        msg = "cTrader live trading is not enabled yet."
        signal.status = "REJECTED"
        signal.rejection_reason = msg
        return await _create_error_order(db, deployment, signal, close_side, to_decimal(position.qty), price, msg)
    adapter = get_broker_adapter(broker, db)
    trace_id = str(getattr(signal, "trace_id", None) or "") or None
    # One reversal may close several broker positions. Each close must have its
    # own stable id; a single candle-level id would silently skip later legs.
    client_order_id = _ctrader_client_order_id(deployment, signal, "EXIT", scope=str(position.id))
    idempotency_key = hashlib.sha256(f"CTRADER:{client_order_id}".encode()).hexdigest()
    existing = await _existing_order_for_client_id(db, client_order_id)
    if existing is not None:
        signal.status = "EXECUTED" if existing.status in {"FILLED", "PLACED", "ACCEPTED", "RECONCILED"} else signal.status
        await _log(db, deployment, "DUPLICATE_ORDER_BLOCKED", "Existing cTrader close client order id reused; broker send skipped", "WARNING", {"signal_id": str(signal.id), "order_id": str(existing.id), "client_order_id": client_order_id})
        return existing
    await _log(db, deployment, "CTRADER_CLOSE_STARTED", "cTrader DEMO close order requested", metadata={"signal_id": str(signal.id), "position_id": str(position.id), "symbol": position.symbol})
    broker_position_id = getattr(position, "broker_position_id", None)
    if not broker_position_id:
        try:
            if settings.live_event_pipeline_enabled and settings.ctrader_persistent_connection_enabled:
                await sync_ctrader_deployment_via_gateway(db, deployment.id, commit=False)
                await db.refresh(position)
                broker_position_id = getattr(position, "broker_position_id", None)
            else:
                broker_positions = await adapter.get_positions(position.symbol)
                wanted_side = "LONG" if position.side == "LONG" else "SHORT"
                matched = next((p for p in broker_positions if str(p.get("side") or "").upper() == wanted_side and p.get("broker_position_id")), None)
                broker_position_id = (matched or {}).get("broker_position_id")
            if broker_position_id:
                position.broker_position_id = str(broker_position_id)
        except Exception:
            broker_position_id = None
    if not broker_position_id:
        msg = "cTrader broker position id is unavailable. Sync Broker before closing this position."
        signal.status = "REJECTED"
        signal.rejection_reason = msg
        return await _create_error_order(db, deployment, signal, close_side, to_decimal(position.qty), price, msg)
    if settings.live_event_pipeline_enabled and settings.ctrader_persistent_connection_enabled:
        result = await submit_close_position(
            broker_account_id=str(broker.id),
            deployment_id=str(deployment.id),
            broker_position_id=str(broker_position_id),
            qty=to_decimal(position.qty),
            client_order_id=client_order_id,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
        )
    else:
        result = await adapter.close_position(str(broker_position_id), close_side, to_decimal(position.qty))
    if not result.success and "not found" in str(result.message or "").lower():
        # A broker-side SL/TP or manual close can win the race after the pre-trade
        # sync. This is an idempotent close: broker truth already says the position
        # is gone, so reconcile the local row instead of turning the strategy
        # signal into an execution error.
        position.status = "CLOSED"
        position.closed_at = position.closed_at or datetime.now(timezone.utc)
        position.current_price = price
        position.unrealized_pnl = Decimal("0")
        reconciled = LiveOrder(
            trace_id=trace_id,
            deployment_id=deployment.id, signal_id=signal.id, user_id=deployment.user_id, broker_account_id=deployment.broker_account_id,
            broker_order_id=None, client_order_id=client_order_id, idempotency_key=idempotency_key, symbol=position.symbol, side=close_side, order_type="MARKET", qty=to_decimal(position.qty),
            entry_price=price, executed_price=None, status="RECONCILED", error_message=None,
            raw_response={"provider": "CTRADER", "broker_already_closed": True, "broker_position_id": str(broker_position_id), "message": result.message},
        )
        db.add(reconciled)
        await db.flush()
        await _trace_service().mark(trace_id, "t15", status="LOCAL_ORDER_RECONCILED", order_id=str(reconciled.id))
        await _trace_service().mark(trace_id, "t16", status="LOCAL_POSITION_RECONCILED", order_id=str(reconciled.id))
        signal.status = "EXECUTED"
        signal.rejection_reason = None
        await _log(db, deployment, "CTRADER_POSITION_ALREADY_CLOSED", "cTrader position was already closed at broker; local position reconciled", "INFO", {"signal_id": str(signal.id), "position_id": str(position.id), "broker_position_id": str(broker_position_id)})
        return reconciled
    order = LiveOrder(
        trace_id=trace_id,
        deployment_id=deployment.id, signal_id=signal.id, user_id=deployment.user_id, broker_account_id=deployment.broker_account_id,
        broker_order_id=result.broker_order_id, client_order_id=client_order_id, idempotency_key=idempotency_key, symbol=position.symbol, side=close_side, order_type="MARKET", qty=to_decimal(position.qty),
        entry_price=price, executed_price=result.executed_price if result.success else None, status=("FILLED" if result.status == "FILLED" else "PLACED") if result.success else "ERROR",
        error_message=None if result.success else result.message, raw_response={**(result.raw_response or {}), "provider": "CTRADER"},
    )
    db.add(order)
    await db.flush()
    await _trace_service().mark(trace_id, "t15", status="LOCAL_ORDER_UPDATED", order_id=str(order.id))
    if result.success and result.status == "FILLED":
        await close_position(db, deployment, position, result.executed_price or price, reason=f"{signal.signal_type} signal")
        await _trace_service().mark(trace_id, "t16", status="LOCAL_POSITION_UPDATED", order_id=str(order.id))
        signal.status = "EXECUTED"
        await _log(db, deployment, "CTRADER_POSITION_CLOSED", "cTrader DEMO position close order placed", metadata={"signal_id": str(signal.id), "order_id": str(order.id), "broker_order_id": result.broker_order_id})
    elif result.success:
        signal.status = "ACCEPTED"
        await _log(db, deployment, "CTRADER_CLOSE_AWAITING_FILL", "Broker accepted cTrader close; awaiting fill and reconciliation", metadata={"signal_id": str(signal.id), "order_id": str(order.id), "broker_order_id": result.broker_order_id})
    else:
        signal.status = "ERROR"
        signal.rejection_reason = result.message
        await _log(db, deployment, "CTRADER_CLOSE_ERROR", result.message, "ERROR", {"signal_id": str(signal.id), "position_id": str(position.id), "order_id": str(order.id)})
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
    client_order_id = _client_order_id(deployment, signal, "ENTRY")
    existing_order = await _existing_order_for_client_id(db, client_order_id)
    if existing_order is not None:
        signal.status = "EXECUTED" if existing_order.status in {"FILLED", "PLACED", "SUBMITTED", "PENDING"} else signal.status
        await _log(db, deployment, "DUPLICATE_ORDER_BLOCKED", "Duplicate Upstox order blocked by client_order_id", "WARNING", {"signal_id": str(signal.id), "order_id": str(existing_order.id), "client_order_id": client_order_id})
        return existing_order
    adapter = get_broker_adapter(broker, db)
    await _log(db, deployment, "UPSTOX_ORDER_STARTED", "Upstox order send started", metadata={"instrument_key": instrument_key, "signal_id": str(signal.id), "side": order_side, "qty": str(qty), "client_order_id": client_order_id, "sizing": sizing_metadata or {}})
    result = await adapter.place_market_order(BrokerOrderRequest(
        symbol=instrument_key,
        instrument_key=instrument_key,
        side=order_side,
        qty=qty,
        price=price,
        stop_loss=stop_loss,
        target=target,
        product_type=getattr(deployment, "product_type", "MIS"),
        order_variety=getattr(deployment, "order_variety", "REGULAR"),
        tag=f"AlgoAgentX-{str(deployment.id)[:8]}-{str(signal.id)[:8]}",
        idempotency_key=client_order_id,
    ))
    status = result.status if result.success else "ERROR"
    order = LiveOrder(
        deployment_id=deployment.id, signal_id=signal.id, user_id=deployment.user_id, broker_account_id=deployment.broker_account_id,
        broker_order_id=result.broker_order_id, client_order_id=client_order_id, idempotency_key=client_order_id, symbol=instrument_key, side=order_side, order_type="MARKET", qty=qty, entry_price=price,
        executed_price=result.executed_price if result.success else None, stop_loss=stop_loss, target=target, status=status,
        error_message=None if result.success else result.message, raw_response={**(result.raw_response or {}), "client_order_id": client_order_id, **({"sizing": sizing_metadata} if sizing_metadata else {})},
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

    adapter = get_broker_adapter(broker, db)
    result = await adapter.place_market_order(BrokerOrderRequest(
        symbol=position.symbol, instrument_key=position.symbol, side=close_side, qty=to_decimal(position.qty), price=price, product_type=getattr(deployment, "product_type", "MIS"), tag=f"AlgoAgentX-EXIT-{str(deployment.id)[:8]}-{str(signal.id)[:8]}"
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
    trace_id = str(getattr(signal, "trace_id", None) or "") or None
    latency_trace = _trace_service()
    await latency_trace.mark(trace_id, "t9", status="EXECUTION_STARTED", signal_id=str(signal.id))
    await _log(db, deployment, "EXECUTION_STARTED", f"{deployment.mode} execution started for {signal.signal_type}", metadata={"signal_id": str(signal.id)})
    await _log(db, deployment, "LIVE_ENGINE_QA_STARTED", "Live engine final QA execution started", metadata={"context": "execute_signal", "signal_id": str(signal.id), "mode": deployment.mode, "signal_type": signal.signal_type})

    if str(deployment.mode or "").upper() == "PAPER":
        signal.status = "REJECTED"
        signal.rejection_reason = "PAPER deployments are deprecated. Please create a DEMO or LIVE broker deployment."
        await _log(db, deployment, "PAPER_DEPRECATED", signal.rejection_reason, "WARNING", {"signal_id": str(signal.id)})
        return None

    # Broker state is execution truth. Refresh it immediately before risk checks
    # so a position that was closed by broker SL/TP/manual action cannot remain
    # locally OPEN and incorrectly reject the next signal. Background sync still
    # runs independently; this pre-trade sync is the final race-safe guard.
    broker_for_sync = None
    if deployment.broker_account_id:
        broker_for_sync = (
            await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))
        ).scalar_one_or_none()
    if deployment.broker_account_id and str(deployment.mode or "").upper() in {"DEMO", "LIVE"}:
        try:
            persistent_ctrader = bool(
                broker_for_sync is not None
                and _is_ctrader_broker(broker_for_sync)
                and settings.live_event_pipeline_enabled
                and settings.ctrader_persistent_connection_enabled
            )
            last_sync = getattr(deployment, "last_broker_sync_at", None)
            if last_sync is not None and last_sync.tzinfo is None:
                last_sync = last_sync.replace(tzinfo=timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - last_sync).total_seconds() if last_sync else None
            cached_state_fresh = bool(
                persistent_ctrader
                and age_seconds is not None
                and age_seconds <= max(0, int(settings.broker_state_max_age_seconds))
                and await _persistent_ctrader_connection_healthy(broker_for_sync)
            )
            if cached_state_fresh:
                await _log(db, deployment, "PRE_TRADE_BROKER_CACHE", "Fresh continuously reconciled cTrader state used for risk checks", metadata={"signal_id": str(signal.id), "age_seconds": round(age_seconds or 0, 3)})
            elif persistent_ctrader:
                await sync_ctrader_deployment_via_gateway(db, deployment.id, commit=False)
            else:
                await sync_deployment_broker_state(db, deployment.id)
            deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment.id))).scalar_one()
            await _log(db, deployment, "PRE_TRADE_BROKER_SYNC", "Broker state verified before execution risk checks", metadata={"signal_id": str(signal.id), "persistent_ctrader": persistent_ctrader, "cached_state_fresh": cached_state_fresh})
        except Exception as exc:
            signal.status = "REJECTED"
            signal.rejection_reason = f"Broker state refresh failed safely before execution: {exc}"
            await _log(db, deployment, "PRE_TRADE_BROKER_SYNC_FAILED", signal.rejection_reason, "ERROR", {"signal_id": str(signal.id)})
            return None

    # A funded hard-rule breach may pause the deployment/disable Auto Trade.
    # That must block NEW risk, never an explicit/risk-reducing close. Keep the
    # existing Standard and LIVE entry gates unchanged; only funded close-only
    # actions receive this narrow capital-protection override.
    funded_close_only = False
    if str(getattr(deployment, "account_policy_type", "STANDARD") or "STANDARD").upper() == "FUNDED":
        open_for_close = await get_open_positions(db, deployment.id)
        if str(signal.signal_type or "").upper() == "EXIT" and open_for_close and str(deployment.mode or "").upper() != "LIVE":
            # Preserve the platform's independent LIVE execution safety block.
            # Funded guard state may not block a DEMO/risk-reducing close, but
            # funded support must not implicitly enable real LIVE execution.
            funded_close_only = True
        elif str(signal.signal_type or "").upper() in {"BUY", "SELL"} and open_for_close:
            requested_side = "LONG" if str(signal.signal_type).upper() == "BUY" else "SHORT"
            opposite_exists = any(str(position.side or "").upper() != requested_side for position in open_for_close)
            new_entry_gates_closed = (
                str(deployment.status or "").upper() != "RUNNING"
                or not bool(deployment.auto_trade_enabled)
            )
            funded_close_only = opposite_exists and new_entry_gates_closed

    if funded_close_only:
        risk = RiskResult(True, action="CLOSE_ONLY")
        await _log(db, deployment, "FUNDED_RISK_REDUCING_CLOSE_ALLOWED", "Funded guard allowed risk-reducing close while new-entry gates are closed", metadata={"signal_id": str(signal.id), "signal_type": signal.signal_type, "deployment_status": deployment.status, "auto_trade_enabled": deployment.auto_trade_enabled})
    else:
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
        await latency_trace.mark(trace_id, "t10", status="BASE_RISK_CHECKS_FINISHED")

    if risk.action == "HOLD":
        signal.status = "ACCEPTED"
        await _log(db, deployment, "EXECUTION_SKIPPED", "HOLD signal saved without order", metadata={"signal_id": str(signal.id)})
        await create_equity_point(db, deployment)
        return None

    price = to_decimal(signal.price)
    signal_payload = signal.raw_payload if isinstance(getattr(signal, "raw_payload", None), dict) else {}
    strategy_stop_loss = signal_payload.get("strategy_stop_loss")
    strategy_target = signal_payload.get("strategy_target")
    latest_order: Optional[LiveOrder] = None

    if risk.action in {"CLOSE_ONLY", "CLOSE_AND_OPEN"}:
        open_positions = await get_open_positions(db, deployment.id)
        for position in open_positions:
            exit_side = "SELL" if position.side == "LONG" else "BUY"
            if deployment.mode == "PAPER":
                latest_order = await fill_market_order(db, deployment, signal, exit_side, to_decimal(position.qty), price, action="EXIT")
                await close_position(db, deployment, position, price, reason=f"{signal.signal_type} signal")
            elif deployment.mode in {"DEMO", "LIVE"}:
                broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none() if deployment.broker_account_id else None
                if broker is not None and get_broker_code(broker) == "UPSTOX":
                    latest_order = await _execute_upstox_close(db, deployment, signal, position, price)
                elif _is_ctrader_broker(broker):
                    latest_order = await _execute_ctrader_close(db, deployment, signal, position, price)
                else:
                    latest_order = await _execute_demo_close(db, deployment, signal, position, price)
            if latest_order is not None and (
                latest_order.status == "ERROR"
                or (risk.action == "CLOSE_AND_OPEN" and latest_order.status not in {"FILLED", "RECONCILED"})
            ):
                # Check every close leg, not just the last position in a
                # multi-position reversal. Never open new risk on an ACK.
                await create_equity_point(db, deployment)
                await _log(db, deployment, "EXECUTION_ABORTED", "Entry skipped until every broker position close is confirmed filled" if latest_order.status != "ERROR" else "Broker position close failed", "WARNING" if latest_order.status != "ERROR" else "ERROR", {"signal_id": str(signal.id), "order_id": str(latest_order.id), "close_status": latest_order.status})
                return latest_order
        await create_equity_point(db, deployment)
        if risk.action == "CLOSE_ONLY":
            if signal.status not in {"ERROR", "REJECTED", "ACCEPTED"}:
                signal.status = "EXECUTED"
            return latest_order

    if signal.signal_type in {"BUY", "SELL"}:
        funded_decision = None
        if str(getattr(deployment, "account_policy_type", "STANDARD") or "STANDARD").upper() == "FUNDED":
            # A reverse signal has already completed its close leg above. Refresh
            # broker truth and re-run funded rules before adding any new risk.
            try:
                if (
                    broker_for_sync is not None
                    and _is_ctrader_broker(broker_for_sync)
                    and settings.live_event_pipeline_enabled
                    and settings.ctrader_persistent_connection_enabled
                ):
                    await sync_ctrader_deployment_via_gateway(db, deployment.id, commit=False)
                else:
                    await sync_deployment_broker_state(db, deployment.id)
                deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment.id))).scalar_one()
                funded_decision = await evaluate_funded_guard(
                    db, deployment, signal_id=signal.id, purpose="ENTRY", persist_decision=True, auto_pause_on_breach=True
                )
            except Exception as exc:
                signal.status = "REJECTED"
                signal.rejection_reason = f"Funded guard failed safely: {exc}"
                await _log(db, deployment, "FUNDED_GUARD_ERROR", signal.rejection_reason, "ERROR", {"signal_id": str(signal.id)})
                return latest_order
            if not funded_decision.allowed_new_entry:
                signal.status = "REJECTED"
                signal.rejection_reason = funded_decision.reason or "Funded guard blocked new entry"
                await _log(db, deployment, "FUNDED_ENTRY_BLOCKED", signal.rejection_reason, "WARNING", {"signal_id": str(signal.id), "funded_guard": funded_decision.to_dict()})
                return latest_order

            # Additional user safety caps remain stricter guards, but they are not
            # the prop-firm DD calculation. Evaluate them only for the new entry.
            funded_orders_today = await current_funded_trades_count(db, deployment)
            if funded_orders_today >= int(deployment.max_trades_per_day or 10):
                signal.status = "REJECTED"
                signal.rejection_reason = "Max trades per day reached"
                await _log(db, deployment, "MAX_TRADES_REACHED", signal.rejection_reason, "WARNING", {"signal_id": str(signal.id)})
                return latest_order

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
            stop_loss=strategy_stop_loss,
            strategy_target=strategy_target,
            runtime_config=None,
            strict_instrument=deployment.mode in {"DEMO", "LIVE"},
            preview_mode="AUTO_LIVE_SIGNAL",
            funded_guard=funded_decision.to_dict() if funded_decision is not None else None,
            risk_amount_override=funded_decision.effective_risk_amount if funded_decision is not None else None,
            risk_percent_override=funded_decision.effective_risk_pct if funded_decision is not None else None,
        )
        preview_log_metadata = {
            "signal_id": str(signal.id),
            "strategy_stop_loss": strategy_stop_loss,
            "strategy_target": strategy_target,
            "preview_stop_loss": preview.get("stop_loss"),
            "preview_target": preview.get("target"),
            "strategy_sltp_received": preview.get("strategy_sltp_received"),
        }
        audit_preview = {
            "validation_status": preview.get("validation_status"),
            "status": preview.get("status"),
            "rejected_reason": preview.get("rejected_reason"),
            "symbol": preview.get("symbol"),
            "side": preview.get("side"),
            "entry_price": preview.get("entry_price"),
            "latest_price": preview.get("latest_price"),
            "stop_loss": preview.get("stop_loss"),
            "target": preview.get("target"),
            "strategy_stop_loss": preview.get("strategy_stop_loss"),
            "strategy_target": preview.get("strategy_target"),
            "strategy_sltp_received": preview.get("strategy_sltp_received"),
            "quantity_mode": preview.get("quantity_mode"),
            "final_lot_size": preview.get("final_lot_size"),
            "final_quantity": preview.get("final_quantity"),
            "risk_amount": preview.get("risk_amount"),
            "actual_risk_amount": preview.get("actual_risk_amount"),
            "account_currency": preview.get("account_currency"),
            "entry_plan": preview.get("entry_plan"),
            "risk_metadata": preview.get("risk_metadata"),
            "broker_payload_preview": preview.get("broker_payload_preview"),
            "funded_guard": preview.get("funded_guard"),
        }
        await _log(db, deployment, "ORDER_PREVIEW_BUILT", "Live order preview built from signal", metadata=preview_log_metadata)
        entry_plan_snapshot = preview.get("entry_plan") if isinstance(preview.get("entry_plan"), dict) else {}
        await _log(
            db,
            deployment,
            "LIVE_SLTP_RESOLVED",
            "Live SL/TP resolved for signal",
            metadata={
                "signal_id": str(signal.id),
                "entry_price": float(price),
                "side": signal.signal_type,
                "sl_mode": entry_plan_snapshot.get("sl_mode"),
                "strategy_stop_loss": strategy_stop_loss,
                "strategy_target": strategy_target,
                "final_stop_loss": preview.get("stop_loss"),
                "final_target": preview.get("target"),
                "stop_loss_source": entry_plan_snapshot.get("stop_loss_source"),
                "target_source": entry_plan_snapshot.get("target_source"),
                "validation_status": preview.get("validation_status"),
                "rejected_reason": preview.get("rejected_reason"),
            },
        )

        await _log_live_engine_qa_preview(db, deployment, signal=signal, preview=preview, strategy_stop_loss=strategy_stop_loss, strategy_target=strategy_target)

        if preview.get("validation_status") != "OK":
            # PAPER may keep legacy behavior when an old deployment has no instrument master; DEMO/LIVE never fallback.
            if deployment.mode in {"DEMO", "LIVE"}:
                signal.status = "REJECTED"
                signal.rejection_reason = preview.get("rejected_reason") or "Risk engine rejected order sizing"
                await _log(db, deployment, "RISK_ENGINE_REJECTED", signal.rejection_reason, "WARNING", {**preview_log_metadata, "preview": preview})
                return latest_order
            position_side, qty, stop_loss, target = calculate_entry_plan(deployment, signal.signal_type, price)
            sizing_metadata = {"legacy_fallback": True, "rejected_preview": preview, "audit_preview": audit_preview, **preview_log_metadata}
        else:
            position_side = "LONG" if signal.signal_type == "BUY" else "SHORT"
            order_side = signal.signal_type
            stop_loss = to_decimal(preview.get("stop_loss"), "0")
            target = to_decimal(preview.get("target"), "0")
            if str(preview.get("quantity_mode") or "").upper() == "LOTS":
                qty = to_decimal(preview.get("final_lot_size"), "0")
            else:
                qty = to_decimal(preview.get("final_quantity"), "0")
            sizing_metadata = {
                **(preview.get("risk_metadata") or {}),
                **preview_log_metadata,
                "validation_status": preview.get("validation_status"),
                "entry_plan": preview.get("entry_plan"),
                "broker_payload_preview": preview.get("broker_payload_preview"),
                "audit_preview": audit_preview,
            }
        if qty <= 0:
            signal.status = "REJECTED"
            signal.rejection_reason = "Calculated lot/quantity is zero"
            await _log(db, deployment, "RISK_REJECTED", "Calculated lot/quantity is zero", "WARNING", {"signal_id": str(signal.id), "sizing": sizing_metadata})
            return latest_order
        order_side = "BUY" if position_side == "LONG" else "SELL"
        if deployment.mode in {"DEMO", "LIVE"}:
            ok, sltp_error = _valid_entry_sltp(order_side, price, stop_loss, target)
            if not ok:
                signal.status = "REJECTED"
                signal.rejection_reason = sltp_error
                await _log(db, deployment, "LIVE_SLTP_SAFETY_BLOCKED", sltp_error or "SL/TP safety blocked order", "ERROR", {"signal_id": str(signal.id), "side": order_side, "entry_price": str(price), "stop_loss": str(stop_loss), "target": str(target), "sizing": sizing_metadata})
                return await _create_error_order(db, deployment, signal, order_side, qty, price, sltp_error or "SL/TP safety blocked order", stop_loss=stop_loss, target=target, sizing_metadata=sizing_metadata)
        await latency_trace.mark(trace_id, "t10", status="RISK_CHECKS_FINISHED")
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
        elif deployment.mode in {"DEMO", "LIVE"}:
            if broker is not None and get_broker_code(broker) == "UPSTOX":
                latest_order = await _execute_upstox_entry(db, deployment, signal, order_side, position_side, qty, price, stop_loss, target, sizing_metadata=sizing_metadata)
            elif _is_ctrader_broker(broker):
                latest_order = await _execute_ctrader_entry(db, deployment, signal, order_side, position_side, qty, price, stop_loss, target, sizing_metadata=sizing_metadata)
            else:
                latest_order = await _execute_demo_entry(db, deployment, signal, order_side, position_side, qty, price, stop_loss, target, sizing_metadata=sizing_metadata)
        if (
            latest_order is not None
            and str(getattr(deployment, "account_policy_type", "STANDARD") or "STANDARD").upper() == "FUNDED"
            and str(getattr(latest_order, "status", "") or "").upper() in {"FILLED", "PLACED", "SUBMITTED", "PENDING", "PENDING_DEMO"}
        ):
            await record_funded_trade_count(db, deployment)
        await create_equity_point(db, deployment)
        return latest_order

    signal.status = "ACCEPTED"
    await create_equity_point(db, deployment)
    return latest_order
