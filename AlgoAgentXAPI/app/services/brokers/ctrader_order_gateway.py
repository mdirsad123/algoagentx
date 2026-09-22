"""Strategy-process client for the market worker's persistent cTrader session."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from ...core.config import settings
from ...core.redis_manager import redis_manager
from ..live.live_event_bus import LiveEventBus
from ..live.live_latency_trace_service import LiveLatencyTraceService
from .base import BrokerOrderRequest, BrokerOrderResult


def _result_from_payload(payload: dict[str, Any]) -> BrokerOrderResult:
    price = payload.get("executed_price")
    return BrokerOrderResult(
        success=bool(payload.get("success")),
        status=str(payload.get("status") or ("FAILED" if not payload.get("success") else "ACCEPTED")),
        message=str(payload.get("message") or "cTrader order gateway completed"),
        broker_order_id=str(payload.get("broker_order_id")) if payload.get("broker_order_id") not in (None, "") else None,
        executed_price=Decimal(str(price)) if price not in (None, "") else None,
        raw_response=payload.get("raw_response") if isinstance(payload.get("raw_response"), dict) else {},
    )


async def submit_market_order(
    *,
    broker_account_id: str,
    deployment_id: str,
    order_request: BrokerOrderRequest,
    client_order_id: str,
    idempotency_key: str,
    trace_id: str | None,
) -> BrokerOrderResult:
    if not redis_manager.is_available or redis_manager.client is None:
        return BrokerOrderResult(
            False,
            "FAILED",
            "Redis is unavailable; persistent cTrader order routing failed safely.",
            raw_response={"provider": "CTRADER", "gateway": "REDIS_STREAM"},
        )
    bus = LiveEventBus(redis_manager.client)
    cached = await bus.get_order_dedupe(idempotency_key)
    if cached and not bus.order_dedupe_in_progress(cached):
        cached.setdefault("raw_response", {})["gateway_deduplicated"] = True
        return _result_from_payload(cached)
    if bus.order_dedupe_in_progress(cached):
        return BrokerOrderResult(
            False,
            "PENDING",
            "An identical cTrader order is already in flight; duplicate send blocked.",
            raw_response={"provider": "CTRADER", "gateway": "REDIS_STREAM", "dedupe_state": "PROCESSING"},
        )

    request_id = str(uuid.uuid4())
    trace = LiveLatencyTraceService(redis_manager.client)
    await trace.mark(trace_id, "t11", status="ORDER_QUEUED", order_request_id=request_id)
    payload = {
        "request_id": request_id,
        "action": "PLACE_MARKET",
        "broker_account_id": str(broker_account_id),
        "deployment_id": str(deployment_id),
        "trace_id": trace_id or "",
        "idempotency_key": idempotency_key,
        "client_order_id": client_order_id[:50],
        "order": {
            "symbol": order_request.symbol,
            "side": order_request.side,
            "qty": str(order_request.qty),
            "price": str(order_request.price) if order_request.price is not None else None,
            "stop_loss": str(order_request.stop_loss) if order_request.stop_loss is not None else None,
            "target": str(order_request.target) if order_request.target is not None else None,
            "comment": order_request.comment,
        },
    }
    await bus.publish_order_request(payload)
    try:
        response = await bus.wait_order_result(
            request_id,
            timeout_seconds=max(3, int(settings.ctrader_order_timeout_seconds) + 5),
        )
    except Exception as exc:
        return BrokerOrderResult(
            False,
            "FAILED",
            str(exc),
            raw_response={"provider": "CTRADER", "gateway": "REDIS_STREAM", "request_id": request_id},
        )
    return _result_from_payload(response)


async def submit_close_position(
    *,
    broker_account_id: str,
    deployment_id: str,
    broker_position_id: str,
    qty: Decimal,
    client_order_id: str,
    idempotency_key: str,
    trace_id: str | None,
) -> BrokerOrderResult:
    if not redis_manager.is_available or redis_manager.client is None:
        return BrokerOrderResult(False, "FAILED", "Redis is unavailable; cTrader close failed safely.")
    bus = LiveEventBus(redis_manager.client)
    cached = await bus.get_order_dedupe(idempotency_key)
    if cached and not bus.order_dedupe_in_progress(cached):
        return _result_from_payload(cached)
    if bus.order_dedupe_in_progress(cached):
        return BrokerOrderResult(False, "PENDING", "An identical cTrader close is already in flight; duplicate send blocked.")
    request_id = str(uuid.uuid4())
    trace = LiveLatencyTraceService(redis_manager.client)
    await trace.mark(trace_id, "t11", status="CLOSE_QUEUED", order_request_id=request_id)
    await bus.publish_order_request({
        "request_id": request_id,
        "action": "CLOSE_POSITION",
        "broker_account_id": str(broker_account_id),
        "deployment_id": str(deployment_id),
        "trace_id": trace_id or "",
        "idempotency_key": idempotency_key,
        "client_order_id": client_order_id[:50],
        "position_id": str(broker_position_id),
        "qty": str(qty),
    })
    try:
        response = await bus.wait_order_result(
            request_id,
            timeout_seconds=max(3, int(settings.ctrader_order_timeout_seconds) + 5),
        )
    except Exception as exc:
        return BrokerOrderResult(False, "FAILED", str(exc), raw_response={"provider": "CTRADER", "gateway": "REDIS_STREAM", "request_id": request_id})
    return _result_from_payload(response)


async def request_account_snapshot(
    *,
    broker_account_id: str,
    deployment_id: str,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    """Fetch reconcile state over the market worker's persistent session."""
    if not redis_manager.is_available or redis_manager.client is None:
        raise RuntimeError("Redis is unavailable; persistent cTrader reconciliation cannot run")
    bus = LiveEventBus(redis_manager.client)
    request_id = str(uuid.uuid4())
    await bus.publish_order_request({
        "request_id": request_id,
        "action": "RECONCILE_ACCOUNT",
        "broker_account_id": str(broker_account_id),
        "deployment_id": str(deployment_id),
        "trace_id": "",
        "idempotency_key": f"reconcile:{deployment_id}:{request_id}",
        "client_order_id": "",
    })
    response = await bus.wait_order_result(
        request_id,
        timeout_seconds=max(3, int(timeout_seconds or settings.ctrader_request_timeout_seconds) + 5),
    )
    if not response.get("success"):
        raise RuntimeError(str(response.get("message") or "Persistent cTrader reconciliation failed"))
    return response
