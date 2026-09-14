from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.models import UserNotificationChannel

IST = ZoneInfo("Asia/Kolkata")


@dataclass
class WhatsAppSendResult:
    ok: bool
    status_code: int | None
    message_id: str | None
    response: dict
    error: str | None = None
    retryable: bool = False
    ambiguous: bool = False


@dataclass(frozen=True)
class WhatsAppTemplateDispatch:
    """Resolved Twilio Content Template and variables for one alert event."""

    kind: str
    content_sid: str | None
    variables: dict[str, str]


def _normalize_whatsapp_number(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.lower().startswith("whatsapp:"):
        return raw
    return f"whatsapp:{raw}"


def _setting(name: str) -> str:
    return str(getattr(settings, name, "") or "").strip()


def whatsapp_configured() -> bool:
    return bool(
        _setting("twilio_account_sid")
        and _setting("twilio_auth_token")
        and _setting("twilio_from_whatsapp_number")
    )


def whatsapp_template_status() -> dict[str, bool]:
    """Template configuration flags exposed to the Alerts UI.

    TWILIO_CONTENT_SID remains a backwards-compatible fallback. New deployments
    should configure dedicated APPROACHING and TRIGGERED template SIDs.
    """
    legacy = bool(_setting("twilio_content_sid"))
    approaching = bool(_setting("twilio_content_sid_approaching"))
    triggered = bool(_setting("twilio_content_sid_triggered"))
    return {
        "legacy": legacy,
        "approaching": approaching,
        "triggered": triggered,
        "any": legacy or approaching or triggered,
    }


async def resolve_whatsapp_recipient(
    db: AsyncSession,
    user_id: str,
    explicit: str | None = None,
) -> tuple[str | None, bool]:
    if explicit:
        return _normalize_whatsapp_number(explicit), False
    channel = (await db.execute(
        select(UserNotificationChannel).where(
            UserNotificationChannel.user_id == user_id,
            UserNotificationChannel.channel == "WHATSAPP",
            UserNotificationChannel.enabled.is_(True),
        )
    )).scalar_one_or_none()
    if channel and channel.external_recipient_id:
        return _normalize_whatsapp_number(str(channel.external_recipient_id)), False
    fallback = _normalize_whatsapp_number(_setting("twilio_to_whatsapp_number"))
    return fallback, bool(fallback)


def _money(value: Decimal | float | str | None) -> str:
    try:
        return f"{Decimal(str(value)):.2f}"
    except Exception:
        return str(value or "—")


def _payload_parts(event, alert) -> tuple[dict, dict, dict]:
    payload = event.payload if isinstance(event.payload, dict) else {}
    snapshot = (payload.get("alert_snapshot") or {}) if isinstance(payload, dict) else {}
    approach = (payload.get("approach") or {}) if isinstance(payload, dict) else {}
    return payload, snapshot, approach


def _target_text(event, alert) -> str:
    _, snapshot, _ = _payload_parts(event, alert)
    target = snapshot.get("target_price", alert.target_price)
    low = snapshot.get("zone_low", alert.zone_low)
    high = snapshot.get("zone_high", alert.zone_high)
    if target is not None:
        return _money(target)
    if low is not None and high is not None:
        return f"{_money(low)} - {_money(high)}"
    return "—"


def _event_time_text(event) -> str:
    ts = (event.condition_detected_at or datetime.now(tz=IST)).astimezone(IST)
    return ts.strftime("%d-%b-%Y %I:%M:%S %p")


def _event_id_text(event) -> str:
    return f"AAX-{str(event.id).split('-')[0].upper()}"


def _condition_text(event) -> str:
    return str(event.condition_type or "").replace("_", " ").title()


def _is_approach_event(event) -> bool:
    payload, _, _ = _payload_parts(event, None)
    if str(payload.get("event_kind") or "").upper() == "APPROACH":
        return True
    return str(event.condition_type or "").upper().startswith("APPROACHING_")


def _approach_direction(event) -> str:
    _, _, approach = _payload_parts(event, None)
    side = str(approach.get("side") or "").upper()
    if side == "BELOW":
        return "From Below"
    if side == "ABOVE":
        return "From Above"
    return "Approaching"


def _approach_distance(event) -> str:
    _, _, approach = _payload_parts(event, None)
    return _money(approach.get("distance_to_boundary"))


def build_whatsapp_message(event, alert) -> str:
    """Plain Body fallback used only when no Twilio Content SID is configured."""
    condition = _condition_text(event)
    if _is_approach_event(event):
        return (
            "🟡 AlgoAgentX Approaching Alert\n\n"
            f"Symbol: {event.symbol}\n"
            f"Status: {condition}\n"
            f"Level / Zone: {_target_text(event, alert)}\n"
            f"Current Price: {_money(event.trigger_price)}\n"
            f"Distance: {_approach_distance(event)}\n"
            f"Direction: {_approach_direction(event)}\n"
            f"Triggered: {_event_time_text(event)} IST\n"
            f"Alert ID: {_event_id_text(event)}\n\n"
            "Please review the chart before taking any trading action."
        )
    return (
        "🔴 AlgoAgentX Price Alert\n\n"
        f"Symbol: {event.symbol}\n"
        f"Status: {condition}\n"
        f"Level / Zone: {_target_text(event, alert)}\n"
        f"Current Price: {_money(event.trigger_price)}\n"
        f"Triggered: {_event_time_text(event)} IST\n"
        f"Alert ID: {_event_id_text(event)}\n\n"
        "Price condition has been reached. Please review the chart before taking any trading action."
    )


def build_content_variables(event, alert, template_kind: str = "legacy") -> dict[str, str]:
    """Build variables for the configured Twilio Content Template.

    template_kind="approaching" matches the recommended 8-variable template.
    template_kind="triggered" matches the recommended 6-variable template.
    template_kind="legacy" preserves the old 4-variable mapping for backward compatibility.
    """
    if template_kind == "approaching":
        return {
            "1": str(event.symbol),
            "2": _condition_text(event),
            "3": _target_text(event, alert),
            "4": _money(event.trigger_price),
            "5": _approach_distance(event),
            "6": _approach_direction(event),
            "7": _event_time_text(event),
            "8": _event_id_text(event),
        }
    if template_kind == "triggered":
        return {
            "1": str(event.symbol),
            "2": _condition_text(event),
            "3": _target_text(event, alert),
            "4": _money(event.trigger_price),
            "5": _event_time_text(event),
            "6": _event_id_text(event),
        }
    return {
        "1": str(event.symbol),
        "2": _condition_text(event),
        "3": _target_text(event, alert),
        "4": _money(event.trigger_price),
    }


def build_template_dispatch(event, alert) -> WhatsAppTemplateDispatch:
    """Choose APPROACHING vs TRIGGERED template, with legacy SID fallback."""
    legacy_sid = _setting("twilio_content_sid") or None
    if _is_approach_event(event):
        sid = _setting("twilio_content_sid_approaching") or legacy_sid
        kind = "approaching" if _setting("twilio_content_sid_approaching") else "legacy"
    else:
        sid = _setting("twilio_content_sid_triggered") or legacy_sid
        kind = "triggered" if _setting("twilio_content_sid_triggered") else "legacy"
    return WhatsAppTemplateDispatch(
        kind=kind,
        content_sid=sid,
        variables=build_content_variables(event, alert, kind),
    )


def build_test_template_dispatch() -> WhatsAppTemplateDispatch:
    """Choose a configured template for the Alerts-page Test WhatsApp action."""
    triggered_sid = _setting("twilio_content_sid_triggered")
    if triggered_sid:
        return WhatsAppTemplateDispatch(
            kind="triggered",
            content_sid=triggered_sid,
            variables={
                "1": "XAUUSDm",
                "2": "Test Alert",
                "3": "4320.00 - 4325.00",
                "4": "4324.94",
                "5": datetime.now(tz=IST).strftime("%d-%b-%Y %I:%M:%S %p"),
                "6": "AAX-TEST0001",
            },
        )
    approaching_sid = _setting("twilio_content_sid_approaching")
    if approaching_sid:
        return WhatsAppTemplateDispatch(
            kind="approaching",
            content_sid=approaching_sid,
            variables={
                "1": "XAUUSDm",
                "2": "Approaching Zone",
                "3": "4320.00 - 4325.00",
                "4": "4326.96",
                "5": "1.96",
                "6": "From Above",
                "7": datetime.now(tz=IST).strftime("%d-%b-%Y %I:%M:%S %p"),
                "8": "AAX-TEST0001",
            },
        )
    legacy_sid = _setting("twilio_content_sid")
    return WhatsAppTemplateDispatch(
        kind="legacy",
        content_sid=legacy_sid or None,
        variables={
            "1": "AlgoAgentX",
            "2": "Test Notification",
            "3": "WhatsApp Alert",
            "4": "Ready",
        },
    )


async def send_whatsapp(
    to_number: str,
    text: str,
    *,
    content_sid: str | None = None,
    content_variables: dict[str, str] | None = None,
) -> WhatsAppSendResult:
    account_sid = _setting("twilio_account_sid")
    auth_token = _setting("twilio_auth_token")
    from_number = _normalize_whatsapp_number(_setting("twilio_from_whatsapp_number"))
    # Explicit SID lets the caller choose APPROACHING vs TRIGGERED. If omitted,
    # preserve the old single-TWILIO_CONTENT_SID behavior.
    selected_content_sid = str(content_sid or "").strip() or _setting("twilio_content_sid")
    to_number = _normalize_whatsapp_number(to_number)

    if not account_sid or not auth_token or not from_number:
        return WhatsAppSendResult(False, None, None, {}, "Twilio WhatsApp credentials are not configured")
    if not to_number:
        return WhatsAppSendResult(False, None, None, {}, "WhatsApp recipient is not configured")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    data: dict[str, str] = {"From": from_number, "To": to_number}
    if selected_content_sid:
        data["ContentSid"] = selected_content_sid
        data["ContentVariables"] = json.dumps(content_variables or {}, separators=(",", ":"))
    else:
        data["Body"] = text

    timeout = aiohttp.ClientTimeout(total=float(getattr(settings, "twilio_timeout_seconds", 10) or 10))
    auth = aiohttp.BasicAuth(account_sid, auth_token)
    try:
        async with aiohttp.ClientSession(timeout=timeout, auth=auth) as session:
            async with session.post(url, data=data) as response:
                try:
                    payload = await response.json(content_type=None)
                except Exception:
                    payload = {"raw": await response.text()}
                ok = response.status in {200, 201} and bool(payload.get("sid"))
                retryable = response.status == 429 or response.status >= 500
                return WhatsAppSendResult(
                    ok=ok,
                    status_code=response.status,
                    message_id=str(payload.get("sid")) if payload.get("sid") else None,
                    response=payload,
                    error=None if ok else str(payload.get("message") or f"Twilio HTTP {response.status}"),
                    retryable=bool(not ok and retryable),
                    ambiguous=False,
                )
    except aiohttp.ClientConnectorError as exc:
        return WhatsAppSendResult(False, None, None, {}, str(exc), retryable=True, ambiguous=False)
    except (asyncio.TimeoutError, aiohttp.ServerTimeoutError, aiohttp.ClientPayloadError, aiohttp.ClientConnectionError) as exc:
        # Twilio message creation has no caller-provided idempotency key. A timeout
        # after request transmission is ambiguous, so do not blindly retry.
        return WhatsAppSendResult(False, None, None, {}, str(exc), retryable=False, ambiguous=True)
    except Exception as exc:
        return WhatsAppSendResult(False, None, None, {}, str(exc), retryable=False, ambiguous=True)
