from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.dependencies import get_current_user, get_db
from ...db.models import AlertEvent, BrokerAccount, PriceAlert, UserNotificationChannel
from ...schemas.alerts import (
    AlertCreate,
    AlertEventOut,
    AlertOut,
    AlertTestNotificationIn,
    AlertUpdate,
    TelegramChannelIn,
    TelegramChannelOut,
)
from ...services.alerts.health import alert_health
from ...services.alerts.telegram import resolve_chat_id, send_telegram
from ...utils.api_response import success_response

router = APIRouter()


def _user_id(current_user: dict) -> str:
    return str(current_user.get("user_id") or current_user.get("id") or "")


def _validate_full_alert(alert: PriceAlert) -> None:
    if alert.alert_type in {"CROSSING_UP", "CROSSING_DOWN"}:
        if alert.target_price is None:
            raise HTTPException(status_code=422, detail="target_price is required for crossing alerts")
    elif alert.alert_type in {"ENTERING_ZONE", "LEAVING_ZONE"}:
        if alert.zone_low is None or alert.zone_high is None or Decimal(alert.zone_low) >= Decimal(alert.zone_high):
            raise HTTPException(status_code=422, detail="Valid zone_low and zone_high are required for zone alerts")
    else:
        raise HTTPException(status_code=422, detail="Unsupported alert_type")
    if alert.trigger_mode not in {"ONCE", "RECURRING"}:
        raise HTTPException(status_code=422, detail="Unsupported trigger_mode")


async def _validate_broker_account(db: AsyncSession, *, user_id: str, provider: str, broker_account_id: UUID | None) -> None:
    if str(provider or "").upper() != "MT5":
        raise HTTPException(status_code=422, detail="Phase 1 live price alerts currently support the MT5 Agent feed. Additional providers are planned for later phases.")
    if broker_account_id is None:
        raise HTTPException(status_code=422, detail="broker_account_id is required for MT5 live price alerts")
    account = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == broker_account_id, BrokerAccount.user_id == user_id))).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Broker account not found")
    code = str(account.broker_code or account.broker_name or "").upper().strip()
    if code != "MT5":
        raise HTTPException(status_code=422, detail="Selected broker account is not an MT5 account")


async def _owned_alert(db: AsyncSession, alert_id: UUID, user_id: str) -> PriceAlert:
    row = (await db.execute(select(PriceAlert).where(PriceAlert.id == alert_id, PriceAlert.user_id == user_id, PriceAlert.status != "DELETED"))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return row


@router.post("", response_model=dict)
@router.post("/", response_model=dict)
async def create_alert(
    payload: AlertCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user_id = _user_id(current_user)
    await _validate_broker_account(db, user_id=user_id, provider=payload.provider, broker_account_id=payload.broker_account_id)
    row = PriceAlert(
        user_id=user_id,
        broker_account_id=payload.broker_account_id,
        symbol=payload.symbol,
        provider=payload.provider,
        alert_type=payload.alert_type,
        target_price=payload.target_price,
        zone_low=payload.zone_low,
        zone_high=payload.zone_high,
        status="ACTIVE",
        runtime_state="ARMED",
        trigger_mode=payload.trigger_mode,
        cooldown_seconds=payload.cooldown_seconds,
        rearm_distance=payload.rearm_distance,
        rearm_type=payload.rearm_type,
        expires_at=payload.expires_at,
        telegram_enabled=payload.telegram_enabled,
        browser_enabled=False,
        whatsapp_enabled=False,
        metadata_json=payload.metadata,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(AlertOut.model_validate(row).model_dump(mode="json"), "Alert created")


@router.get("", response_model=dict)
@router.get("/", response_model=dict)
async def list_alerts(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=200, ge=1, le=500),
):
    query = select(PriceAlert).where(PriceAlert.user_id == _user_id(current_user), PriceAlert.status != "DELETED")
    if status_filter:
        query = query.where(PriceAlert.status == status_filter.upper())
    rows = (await db.execute(query.order_by(desc(PriceAlert.created_at)).limit(limit))).scalars().all()
    return success_response([AlertOut.model_validate(x).model_dump(mode="json") for x in rows])


@router.get("/history", response_model=dict)
async def alert_history(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    rows = (await db.execute(
        select(AlertEvent)
        .where(AlertEvent.user_id == _user_id(current_user))
        .order_by(desc(AlertEvent.created_at))
        .offset(offset)
        .limit(limit)
    )).scalars().all()
    return success_response([AlertEventOut.model_validate(x).model_dump(mode="json") for x in rows])


@router.get("/history/{event_id}", response_model=dict)
async def alert_history_detail(
    event_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = (await db.execute(select(AlertEvent).where(AlertEvent.id == event_id, AlertEvent.user_id == _user_id(current_user)))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert event not found")
    return success_response(AlertEventOut.model_validate(row).model_dump(mode="json"))


@router.get("/health", response_model=dict)
async def alerts_health(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return success_response(await alert_health(db, _user_id(current_user)))


@router.get("/telegram-channel", response_model=dict)
async def get_telegram_channel(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user_id = _user_id(current_user)
    row = (await db.execute(select(UserNotificationChannel).where(UserNotificationChannel.user_id == user_id, UserNotificationChannel.channel == "TELEGRAM"))).scalar_one_or_none()
    fallback = str(getattr(settings, "telegram_default_chat_id", "") or "").strip()
    data = TelegramChannelOut(
        configured=bool((row and row.external_recipient_id) or fallback),
        chat_id=str(row.external_recipient_id) if row else None,
        enabled=bool(row.enabled) if row else bool(fallback),
        verified=bool(row.verified) if row else False,
        using_global_fallback=bool(not row and fallback),
    )
    return success_response(data.model_dump(mode="json"))


@router.put("/telegram-channel", response_model=dict)
async def put_telegram_channel(
    payload: TelegramChannelIn,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user_id = _user_id(current_user)
    row = (await db.execute(select(UserNotificationChannel).where(UserNotificationChannel.user_id == user_id, UserNotificationChannel.channel == "TELEGRAM"))).scalar_one_or_none()
    if row is None:
        row = UserNotificationChannel(user_id=user_id, channel="TELEGRAM", external_recipient_id=payload.chat_id.strip(), enabled=payload.enabled, verified=False)
        db.add(row)
    else:
        changed = row.external_recipient_id != payload.chat_id.strip()
        row.external_recipient_id = payload.chat_id.strip()
        row.enabled = payload.enabled
        if changed:
            row.verified = False
    await db.commit()
    return success_response({"configured": True, "chat_id": row.external_recipient_id, "enabled": row.enabled, "verified": row.verified, "using_global_fallback": False}, "Telegram channel saved")


@router.post("/test-notification", response_model=dict)
async def test_notification(
    payload: AlertTestNotificationIn,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user_id = _user_id(current_user)
    chat_id, using_fallback = await resolve_chat_id(db, user_id, payload.chat_id)
    if not chat_id:
        raise HTTPException(status_code=400, detail="Configure a Telegram chat ID first")
    result = await send_telegram(chat_id, "🔔 AlgoAgentX Telegram Test\n\nPhase 1 alert delivery is configured successfully.")
    if not result.ok:
        raise HTTPException(status_code=502, detail=f"Telegram test failed: {result.error}")
    row = (await db.execute(select(UserNotificationChannel).where(UserNotificationChannel.user_id == user_id, UserNotificationChannel.channel == "TELEGRAM"))).scalar_one_or_none()
    if row and str(row.external_recipient_id) == str(chat_id):
        row.verified = True
        await db.commit()
    return success_response({"status": "SENT", "telegram_api_accepted": True, "message_id": result.message_id, "using_global_fallback": using_fallback}, "Telegram API accepted the test notification")


@router.get("/{alert_id}", response_model=dict)
async def get_alert(
    alert_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = await _owned_alert(db, alert_id, _user_id(current_user))
    return success_response(AlertOut.model_validate(row).model_dump(mode="json"))


@router.patch("/{alert_id}", response_model=dict)
async def update_alert(
    alert_id: UUID,
    payload: AlertUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = await _owned_alert(db, alert_id, _user_id(current_user))
    changes = payload.model_dump(exclude_unset=True)
    next_provider = str(changes.get("provider") or row.provider)
    next_broker_account_id = changes.get("broker_account_id", row.broker_account_id)
    await _validate_broker_account(db, user_id=_user_id(current_user), provider=next_provider, broker_account_id=next_broker_account_id)
    if "metadata" in changes:
        changes["metadata_json"] = changes.pop("metadata")
    condition_changed = any(k in changes for k in {"symbol", "provider", "broker_account_id", "alert_type", "target_price", "zone_low", "zone_high"})
    for key, value in changes.items():
        setattr(row, key, value)
    if row.alert_type in {"CROSSING_UP", "CROSSING_DOWN"}:
        row.zone_low = None
        row.zone_high = None
    elif row.alert_type in {"ENTERING_ZONE", "LEAVING_ZONE"}:
        row.target_price = None
    _validate_full_alert(row)
    if condition_changed:
        row.last_price = None
        row.last_market_timestamp = None
        row.runtime_state = "ARMED"
        if row.status in {"COMPLETED", "EXPIRED"}:
            row.status = "ACTIVE"
    await db.commit()
    await db.refresh(row)
    return success_response(AlertOut.model_validate(row).model_dump(mode="json"), "Alert updated")


@router.post("/{alert_id}/enable", response_model=dict)
async def enable_alert(
    alert_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = await _owned_alert(db, alert_id, _user_id(current_user))
    row.status = "ACTIVE"
    row.runtime_state = "ARMED"
    row.last_price = None
    row.rearm_eligible_at = None
    await db.commit()
    return success_response(AlertOut.model_validate(row).model_dump(mode="json"), "Alert enabled")


@router.post("/{alert_id}/disable", response_model=dict)
async def disable_alert(
    alert_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = await _owned_alert(db, alert_id, _user_id(current_user))
    row.status = "DISABLED"
    row.runtime_state = "DISABLED"
    await db.commit()
    return success_response(AlertOut.model_validate(row).model_dump(mode="json"), "Alert disabled")


@router.delete("/{alert_id}", response_model=dict)
async def delete_alert(
    alert_id: UUID,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = await _owned_alert(db, alert_id, _user_id(current_user))
    row.status = "DELETED"
    row.runtime_state = "DISABLED"
    meta = dict(row.metadata_json or {})
    meta["deleted_at"] = datetime.now(timezone.utc).isoformat()
    row.metadata_json = meta
    await db.commit()
    return success_response({"deleted": True, "alert_id": str(alert_id)}, "Alert deleted; history preserved")
