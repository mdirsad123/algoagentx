from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import LiveSignal, LiveTradeLog, StrategyDeployment
from .execution_engine import execute_signal

VALID_SIGNALS = {"BUY", "SELL", "EXIT", "HOLD"}


@dataclass
class WebhookResult:
    success: bool
    status: str
    reason: Optional[str] = None
    signal_id: Optional[str] = None


def _upper(value: object) -> str:
    return str(value or "").strip().upper()


def _safe_decimal(value: object) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    text = str(value).strip()
    if text.startswith("{{") and text.endswith("}}"):
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _safe_datetime(value: object) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    text = str(value).strip()
    if text.startswith("{{") and text.endswith("}}"):
        return datetime.now(timezone.utc)
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def normalize_tradingview_payload(payload: dict[str, Any]) -> dict[str, Any]:
    signal = payload.get("signal", payload.get("action"))
    symbol = payload.get("symbol", payload.get("ticker"))
    timeframe = payload.get("timeframe", payload.get("interval"))
    price = payload.get("price", payload.get("close"))
    return {
        "secret": payload.get("secret"),
        "deployment_id": payload.get("deployment_id"),
        "symbol": str(symbol or "").strip(),
        "timeframe": str(timeframe or "").strip(),
        "signal_type": _upper(signal),
        "price": _safe_decimal(price),
        "candle_time": _safe_datetime(payload.get("time")),
        "reason": payload.get("reason") or "TradingView alert",
        "raw_payload": payload,
    }


async def _write_log(db: AsyncSession, deployment: StrategyDeployment, event_type: str, message: str, level: str = "INFO", metadata: Optional[dict] = None) -> None:
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=event_type,
        level=level,
        message=message,
        metadata_json=metadata or {},
    ))


def _side_for(signal_type: str, allow_short: bool) -> tuple[Optional[str], Optional[str]]:
    if signal_type == "BUY":
        return "LONG", None
    if signal_type == "SELL":
        if not allow_short:
            return None, "Short selling is disabled for this deployment"
        return "SHORT", None
    if signal_type in {"EXIT", "HOLD"}:
        return None, None
    return None, "Invalid signal"


async def process_tradingview_webhook(db: AsyncSession, payload: dict[str, Any]) -> WebhookResult:
    data = normalize_tradingview_payload(payload)
    deployment_id = data.get("deployment_id")
    if not deployment_id:
        return WebhookResult(False, "REJECTED", "deployment_id is required")

    try:
        deployment_uuid = UUID(str(deployment_id))
    except ValueError:
        return WebhookResult(False, "REJECTED", "Invalid deployment_id")

    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_uuid))).scalar_one_or_none()
    if deployment is None:
        return WebhookResult(False, "REJECTED", "Deployment not found")

    await _write_log(db, deployment, "WEBHOOK_RECEIVED", "TradingView webhook received", metadata={"source": "TRADINGVIEW"})

    signal_type = data["signal_type"]
    side, side_rejection = _side_for(signal_type, bool(deployment.allow_short))
    rejection_reason: Optional[str] = None
    signal_status = "ACCEPTED"

    if not deployment.tradingview_secret or str(data.get("secret") or "") != str(deployment.tradingview_secret):
        rejection_reason = "Invalid secret"
    elif signal_type not in VALID_SIGNALS:
        rejection_reason = "Invalid signal"
    elif side_rejection:
        rejection_reason = side_rejection
    elif deployment.status != "RUNNING":
        rejection_reason = f"Deployment is {deployment.status}; signal saved but execution rejected"
    elif deployment.mode == "LIVE":
        rejection_reason = "LIVE mode is not enabled yet"

    if rejection_reason:
        signal_status = "REJECTED"

    signal = LiveSignal(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        strategy_id=deployment.strategy_id,
        source="TRADINGVIEW",
        symbol=data.get("symbol") or deployment.instrument,
        timeframe=data.get("timeframe") or deployment.timeframe,
        signal_type=signal_type if signal_type in VALID_SIGNALS else "HOLD",
        side=side,
        price=data.get("price"),
        candle_time=data.get("candle_time"),
        reason=data.get("reason"),
        raw_payload=data.get("raw_payload") or {},
        status=signal_status,
        rejection_reason=rejection_reason,
    )
    deployment.last_signal_at = datetime.now(timezone.utc)
    db.add(signal)
    await db.flush()

    if rejection_reason:
        await _write_log(db, deployment, "SIGNAL_REJECTED", rejection_reason, "WARNING", {"signal_id": str(signal.id), "signal_type": signal_type})
        await db.commit()
        return WebhookResult(False, "REJECTED", rejection_reason, str(signal.id))

    await _write_log(db, deployment, "SIGNAL_ACCEPTED", f"TradingView {signal_type} signal accepted", metadata={"signal_id": str(signal.id), "signal_type": signal_type})

    if signal_type == "HOLD":
        signal.status = "ACCEPTED"
        await _write_log(db, deployment, "EXECUTION_SKIPPED", "HOLD signal saved without execution", metadata={"signal_id": str(signal.id)})
    elif deployment.auto_trade_enabled:
        await execute_signal(db, deployment, signal)
    else:
        await _write_log(db, deployment, "EXECUTION_SKIPPED", "Auto trade is disabled; signal saved only", metadata={"signal_id": str(signal.id)})

    await db.commit()
    return WebhookResult(True, signal.status, signal_id=str(signal.id))
