from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import (
    PlatformTradingSettings,
    BrokerAccount,
    BrokerOrderEvent,
    LiveOrder,
    LivePosition,
    LiveTradeLog,
    StrategyDeployment,
)
from ..brokers.factory import get_broker_adapter, get_broker_code
from .trading_safety import get_platform_trading_settings


def _dec(value: Any, default: str = "0") -> Decimal:
    try:
        if value in (None, ""):
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _safe_payload(value: Any) -> Any:
    if isinstance(value, dict):
        safe = {}
        for k, v in value.items():
            key = str(k)
            if key.lower() in {"access_token", "refresh_token", "token", "authorization", "client_secret", "password"}:
                safe[key] = "***redacted***"
            else:
                safe[key] = _safe_payload(v)
        return safe
    if isinstance(value, list):
        return [_safe_payload(v) for v in value]
    if isinstance(value, (datetime, UUID, Decimal)):
        return str(value)
    return value


def _symbol_key(value: object) -> str:
    return str(value or "").strip().upper().replace(".", "").replace("_", "").replace("-", "")


def _symbols_match(requested: object, actual: object) -> bool:
    req = _symbol_key(requested)
    act = _symbol_key(actual)
    return bool(req and act and (req == act or req.startswith(act) or act.startswith(req)))


def _normalize_order_status(value: object) -> str:
    v = str(value or "").strip().lower()
    if v in {"complete", "completed", "filled", "fill", "executed"}:
        return "FILLED"
    if v in {"cancelled", "canceled"}:
        return "CANCELLED"
    if v in {"rejected", "failed", "error"}:
        return "REJECTED"
    if v in {"open", "trigger pending", "validation pending", "put order req received", "placed", "pending", "new"}:
        return "PLACED"
    return "PLACED" if v else "PENDING"


def _extract_order_id(payload: dict[str, Any]) -> str | None:
    for key in ("order_id", "orderId", "broker_order_id", "exchange_order_id", "app_order_id", "id"):
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_order_id(data)
    return None


def _extract_order_status(payload: dict[str, Any]) -> str:
    for key in ("status", "order_status", "orderStatus", "state"):
        if payload.get(key) not in (None, ""):
            return _normalize_order_status(payload.get(key))
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_order_status(data)
    return "PENDING"


def _extract_order_price(payload: dict[str, Any]) -> Decimal | None:
    for key in ("average_price", "avg_price", "executed_price", "price", "filled_price"):
        if payload.get(key) not in (None, ""):
            return _dec(payload.get(key))
    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_order_price(data)
    return None


def _mt5_side(position: dict[str, Any]) -> str:
    try:
        return "LONG" if int(position.get("type", 0)) == 0 else "SHORT"
    except Exception:
        return "LONG"


def _mt5_opened_at(position: dict[str, Any]) -> datetime:
    value = position.get("time") or position.get("time_msc")
    try:
        if value is not None:
            ivalue = int(value)
            if ivalue > 10_000_000_000:
                ivalue = int(ivalue / 1000)
            return datetime.fromtimestamp(ivalue, tz=timezone.utc)
    except Exception:
        pass
    return datetime.now(timezone.utc)


def _upstox_position_values(position: dict[str, Any], deployment: StrategyDeployment) -> dict[str, Any] | None:
    qty = _dec(position.get("quantity") or position.get("net_quantity") or position.get("netQty") or position.get("day_buy_quantity") or 0)
    if qty == 0:
        return None
    symbol = str(
        position.get("instrument_token")
        or position.get("instrument_key")
        or position.get("tradingsymbol")
        or position.get("trading_symbol")
        or deployment.instrument_key
        or deployment.broker_symbol
        or deployment.instrument
    )
    side = "LONG" if qty > 0 else "SHORT"
    avg = _dec(position.get("average_price") or position.get("buy_price") or position.get("sell_price") or 0)
    current = _dec(position.get("last_price") or position.get("ltp") or avg, str(avg))
    pnl = _dec(position.get("pnl") or position.get("unrealised") or position.get("unrealized_pnl") or 0)
    realized = _dec(position.get("realised") or position.get("realized_pnl") or 0)
    return {"symbol": symbol, "side": side, "qty": abs(qty), "avg": avg, "current": current, "unrealized": pnl, "realized": realized, "opened_at": datetime.now(timezone.utc)}


def _mt5_position_values(position: dict[str, Any], deployment: StrategyDeployment) -> dict[str, Any] | None:
    qty = _dec(position.get("volume") or 0)
    if qty == 0:
        return None
    avg = _dec(position.get("price_open") or 0)
    current = _dec(position.get("price_current") or avg, str(avg))
    return {
        "symbol": str(position.get("symbol") or deployment.broker_symbol or deployment.instrument),
        "side": _mt5_side(position),
        "qty": abs(qty),
        "avg": avg,
        "current": current,
        "unrealized": _dec(position.get("profit") or 0),
        "realized": Decimal("0"),
        "opened_at": _mt5_opened_at(position),
        "stop_loss": _dec(position.get("sl")) if position.get("sl") not in (None, "", 0) else None,
        "target": _dec(position.get("tp")) if position.get("tp") not in (None, "", 0) else None,
    }


async def _write_log(db: AsyncSession, deployment: StrategyDeployment, event_type: str, message: str, level: str = "INFO", metadata: dict[str, Any] | None = None) -> None:
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=event_type,
        level=level,
        message=message,
        metadata_json=metadata or {},
    ))


async def _save_event(
    db: AsyncSession,
    *,
    provider_code: str,
    broker_account_id: UUID | None,
    deployment_id: UUID | None,
    broker_order_id: str | None,
    event_type: str,
    raw_payload: dict[str, Any],
    processed: bool = False,
) -> BrokerOrderEvent:
    event = BrokerOrderEvent(
        broker_provider_code=provider_code.upper(),
        broker_account_id=broker_account_id,
        deployment_id=deployment_id,
        broker_order_id=broker_order_id,
        event_type=event_type,
        raw_payload=_safe_payload(raw_payload),
        processed=processed,
    )
    db.add(event)
    await db.flush()
    return event


async def reconcile_orders(db: AsyncSession, deployment: StrategyDeployment, broker_orders: list[dict[str, Any]], provider_code: str) -> dict[str, int]:
    updated = 0
    unmatched = 0
    events = 0
    for raw in broker_orders or []:
        if not isinstance(raw, dict) or raw.get("success") is False:
            continue
        broker_order_id = _extract_order_id(raw)
        if not broker_order_id:
            continue
        status = _extract_order_status(raw)
        price = _extract_order_price(raw)
        await _save_event(
            db,
            provider_code=provider_code,
            broker_account_id=deployment.broker_account_id,
            deployment_id=deployment.id,
            broker_order_id=broker_order_id,
            event_type="BROKER_ORDER_SYNC",
            raw_payload=raw,
            processed=True,
        )
        events += 1
        local = (await db.execute(select(LiveOrder).where(LiveOrder.deployment_id == deployment.id, LiveOrder.broker_order_id == broker_order_id))).scalar_one_or_none()
        if local is None:
            unmatched += 1
            continue
        local.status = status
        if price is not None and price > 0:
            local.executed_price = price
        local.raw_response = {**(local.raw_response or {}), "broker_sync": _safe_payload(raw), "last_broker_sync_at": datetime.now(timezone.utc).isoformat()}
        updated += 1
    return {"orders_updated": updated, "orders_unmatched": unmatched, "order_events_saved": events}


async def reconcile_positions(db: AsyncSession, deployment: StrategyDeployment, broker_positions: list[dict[str, Any]], provider_code: str) -> dict[str, Any]:
    open_rows = (await db.execute(select(LivePosition).where(LivePosition.deployment_id == deployment.id, LivePosition.status == "OPEN"))).scalars().all()
    matched: set[str] = set()
    created = 0
    updated = 0
    closed = 0
    total_unrealized = Decimal("0")
    total_realized = Decimal("0")
    normalizer = _mt5_position_values if provider_code.upper() == "MT5" else _upstox_position_values

    for raw in broker_positions or []:
        if not isinstance(raw, dict) or raw.get("success") is False:
            continue
        values = normalizer(raw, deployment)
        if not values:
            continue
        total_unrealized += _dec(values.get("unrealized"))
        total_realized += _dec(values.get("realized"))
        existing = next((p for p in open_rows if str(p.id) not in matched and p.side == values["side"] and _symbols_match(p.symbol, values["symbol"])), None)
        if existing is None:
            existing = LivePosition(
                deployment_id=deployment.id,
                user_id=deployment.user_id,
                broker_account_id=deployment.broker_account_id,
                symbol=values["symbol"],
                side=values["side"],
                qty=values["qty"],
                avg_entry_price=values["avg"],
                current_price=values["current"],
                stop_loss=values.get("stop_loss"),
                target=values.get("target"),
                unrealized_pnl=values["unrealized"],
                realized_pnl=values["realized"],
                status="OPEN",
                opened_at=values.get("opened_at") or datetime.now(timezone.utc),
            )
            db.add(existing)
            await db.flush()
            open_rows.append(existing)
            created += 1
        else:
            existing.broker_account_id = deployment.broker_account_id
            existing.symbol = values["symbol"]
            existing.qty = values["qty"]
            existing.avg_entry_price = values["avg"]
            existing.current_price = values["current"]
            existing.unrealized_pnl = values["unrealized"]
            existing.realized_pnl = values["realized"]
            if values.get("stop_loss") is not None:
                existing.stop_loss = values.get("stop_loss")
            if values.get("target") is not None:
                existing.target = values.get("target")
            updated += 1
        matched.add(str(existing.id))

    now = datetime.now(timezone.utc)
    for local in open_rows:
        if str(local.id) not in matched:
            local.status = "CLOSED"
            local.closed_at = local.closed_at or now
            local.unrealized_pnl = Decimal("0")
            closed += 1

    if broker_positions:
        await _save_event(
            db,
            provider_code=provider_code,
            broker_account_id=deployment.broker_account_id,
            deployment_id=deployment.id,
            broker_order_id=None,
            event_type="BROKER_POSITION_SYNC",
            raw_payload={"positions_count": len(broker_positions), "positions": broker_positions[:25]},
            processed=True,
        )

    return {
        "positions_created": created,
        "positions_updated": updated,
        "positions_closed": closed,
        "open_positions_count": len([p for p in open_rows if p.status == "OPEN"]),
        "unrealized_pnl": str(total_unrealized),
        "realized_pnl": str(total_realized),
    }


async def sync_deployment_broker_state(db: AsyncSession, deployment_id: UUID | str) -> dict[str, Any]:
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if deployment is None:
        raise ValueError("Deployment not found")
    if not deployment.broker_account_id:
        raise ValueError("No broker account connected to this deployment")
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None:
        raise ValueError("Broker account not found")
    provider_code = get_broker_code(broker)
    adapter = get_broker_adapter(broker, db)
    now = datetime.now(timezone.utc)

    orders: list[dict[str, Any]] = []
    positions: list[dict[str, Any]] = []
    warnings: list[str] = []

    if hasattr(adapter, "get_orders"):
        orders = await adapter.get_orders() or []
        if orders and isinstance(orders[0], dict) and orders[0].get("success") is False:
            warnings.append(str(orders[0].get("message") or "Broker orders fetch failed"))
            orders = []
    if hasattr(adapter, "get_positions"):
        if provider_code == "MT5":
            try:
                positions = await adapter.get_positions(deployment.instrument) or []
            except TypeError:
                positions = await adapter.get_positions() or []
        else:
            positions = await adapter.get_positions() or []
        if positions and isinstance(positions[0], dict) and positions[0].get("success") is False:
            warnings.append(str(positions[0].get("message") or "Broker positions fetch failed"))
            positions = []

    order_result = await reconcile_orders(db, deployment, orders, provider_code)
    position_result = await reconcile_positions(db, deployment, positions, provider_code)

    deployment.last_broker_sync_at = now
    deployment.last_live_sync_at = now
    deployment.live_sync_error_count = 0
    deployment.live_sync_last_error = None
    deployment.last_heartbeat_at = now
    await _write_log(
        db,
        deployment,
        "BROKER_STATE_SYNCED" if not warnings else "BROKER_SYNC_WARNING",
        f"{provider_code} broker sync completed" if not warnings else f"{provider_code} broker sync completed with warnings",
        "INFO" if not warnings else "WARNING",
        {"provider_code": provider_code, "orders_count": len(orders), "positions_count": len(positions), "warnings": warnings, **order_result, **position_result},
    )
    await db.commit()
    return {
        "success": True,
        "deployment_id": str(deployment.id),
        "provider_code": provider_code,
        "last_broker_sync_at": now.isoformat(),
        "orders_count": len(orders),
        "positions_count": len(positions),
        "warnings": warnings,
        **order_result,
        **position_result,
    }


def clamp_live_sync_interval(settings: PlatformTradingSettings, value: int | None) -> int:
    min_s = int(getattr(settings, "min_broker_sync_interval_seconds", 5) or 5)
    max_s = int(getattr(settings, "max_broker_sync_interval_seconds", 300) or 300)
    default_s = int(getattr(settings, "default_broker_sync_interval_seconds", 10) or 10)
    min_s = max(5, min_s)
    max_s = min(300, max(max_s, min_s))
    raw = int(value or default_s)
    return max(min_s, min(max_s, raw))


async def should_auto_sync_deployment(db: AsyncSession, deployment: StrategyDeployment, settings: PlatformTradingSettings | None = None) -> tuple[bool, str, int]:
    settings = settings or await get_platform_trading_settings(db)
    interval = clamp_live_sync_interval(settings, getattr(deployment, "live_sync_interval_seconds", None))
    if not bool(getattr(settings, "broker_auto_sync_enabled", True)):
        return False, "Platform broker auto sync is disabled", interval
    if deployment.status != "RUNNING":
        return False, f"Deployment is {deployment.status}", interval
    if not bool(getattr(deployment, "live_sync_enabled", False)):
        return False, "Deployment live sync is OFF", interval
    if not deployment.broker_account_id:
        return False, "No broker account", interval
    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None or broker.status != "CONNECTED":
        return False, "Broker is not CONNECTED", interval
    last_sync = getattr(deployment, "last_live_sync_at", None) or getattr(deployment, "last_broker_sync_at", None)
    if last_sync is not None:
        elapsed = (datetime.now(timezone.utc) - last_sync).total_seconds()
        if elapsed < interval:
            return False, f"Not due for {int(interval - elapsed)}s", interval
    return True, "Due", interval


async def auto_sync_deployment_if_due(db: AsyncSession, deployment: StrategyDeployment) -> dict[str, Any]:
    settings = await get_platform_trading_settings(db)
    due, reason, interval = await should_auto_sync_deployment(db, deployment, settings)
    deployment.live_sync_interval_seconds = interval
    if not due:
        return {"deployment_id": str(deployment.id), "synced": False, "reason": reason, "interval_seconds": interval}
    try:
        result = await sync_deployment_broker_state(db, deployment.id)
        result["auto_sync"] = True
        return result
    except Exception as exc:
        await db.rollback()
        fresh = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment.id))).scalar_one_or_none()
        if fresh is not None:
            fresh.live_sync_error_count = int(getattr(fresh, "live_sync_error_count", 0) or 0) + 1
            fresh.live_sync_last_error = str(exc)[:2000]
            if fresh.live_sync_error_count >= 5:
                fresh.live_sync_enabled = False
                level = "WARNING"
                message = "Live broker auto-sync disabled after repeated errors"
            else:
                level = "ERROR"
                message = "Live broker auto-sync failed"
            await _write_log(db, fresh, "AUTO_BROKER_SYNC_FAILED", message, level, {"error": str(exc), "error_count": fresh.live_sync_error_count})
            await db.commit()
        raise


async def sync_all_running_deployments(db: AsyncSession) -> dict[str, Any]:
    settings = await get_platform_trading_settings(db)
    rows = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.status == "RUNNING", StrategyDeployment.broker_account_id.is_not(None)))).scalars().all()
    results = []
    errors = []
    skipped = []
    for row in rows:
        try:
            result = await auto_sync_deployment_if_due(db, row)
            if result.get("success") or result.get("synced"):
                results.append(result)
            else:
                skipped.append(result)
        except Exception as exc:
            errors.append({"deployment_id": str(row.id), "error": str(exc)})
    return {"checked": len(rows), "synced": len(results), "skipped": skipped, "errors": errors, "platform_auto_sync_enabled": bool(getattr(settings, "broker_auto_sync_enabled", True)), "results": results}


async def apply_broker_order_webhook(db: AsyncSession, provider_code: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    provider = str(provider_code or "").upper().strip()
    headers = headers or {}
    configured_secret = os.getenv(f"{provider}_WEBHOOK_SECRET") or os.getenv("BROKER_WEBHOOK_SECRET")
    provided_secret = headers.get("x-webhook-secret") or headers.get("x-upstox-webhook-secret") or str(payload.get("secret") or "")
    if configured_secret and provided_secret != configured_secret:
        event = await _save_event(db, provider_code=provider, broker_account_id=None, deployment_id=None, broker_order_id=_extract_order_id(payload), event_type="BROKER_WEBHOOK_REJECTED", raw_payload={"reason": "invalid_secret", "payload": payload}, processed=False)
        await db.commit()
        return {"success": False, "processed": False, "reason": "Invalid broker webhook secret", "event_id": str(event.id)}

    broker_order_id = _extract_order_id(payload)
    status = _extract_order_status(payload)
    price = _extract_order_price(payload)
    local = None
    if broker_order_id:
        local = (await db.execute(select(LiveOrder).where(LiveOrder.broker_order_id == broker_order_id).order_by(LiveOrder.created_at.desc()).limit(1))).scalar_one_or_none()

    deployment_id = local.deployment_id if local else None
    broker_account_id = local.broker_account_id if local else None
    event = await _save_event(db, provider_code=provider, broker_account_id=broker_account_id, deployment_id=deployment_id, broker_order_id=broker_order_id, event_type="BROKER_ORDER_WEBHOOK", raw_payload=payload, processed=bool(local))

    if local is not None:
        local.status = status
        if price is not None and price > 0:
            local.executed_price = price
        local.raw_response = {**(local.raw_response or {}), "broker_webhook": _safe_payload(payload), "broker_webhook_event_id": str(event.id)}
        deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == local.deployment_id))).scalar_one_or_none()
        if deployment is not None:
            deployment.last_broker_sync_at = datetime.now(timezone.utc)
            await _write_log(db, deployment, "BROKER_ORDER_WEBHOOK", f"{provider} order webhook updated order {broker_order_id} to {status}", "INFO", {"event_id": str(event.id), "broker_order_id": broker_order_id, "status": status})
    await db.commit()
    return {"success": True, "processed": bool(local), "event_id": str(event.id), "broker_order_id": broker_order_id, "status": status}


async def broker_sync_loop() -> None:
    import asyncio
    import logging
    from ...core.config import settings
    from ...db.session import async_session

    logger = logging.getLogger(__name__)
    interval = max(5, int(getattr(settings, "live_broker_sync_loop_seconds", 5) or 5))
    while True:
        try:
            async with async_session() as db:
                await sync_all_running_deployments(db)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Broker sync loop failed safely: %s", exc)
        await asyncio.sleep(interval)
