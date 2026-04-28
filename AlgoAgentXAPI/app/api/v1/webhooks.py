from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_db
from ...services.live.broker_sync_service import apply_broker_order_webhook
from ...services.live.signal_service import process_tradingview_webhook

router = APIRouter()


@router.post("/tradingview")
async def tradingview_webhook(payload: dict[str, Any], db: AsyncSession = Depends(get_db)):
    try:
        result = await process_tradingview_webhook(db, payload)
        response = {"success": result.success, "status": result.status}
        if result.signal_id:
            response["signal_id"] = result.signal_id
        if result.reason:
            response["reason"] = result.reason
        return response
    except Exception:
        await db.rollback()
        return {"success": False, "status": "REJECTED", "reason": "Webhook processing failed"}


@router.post("/brokers/{provider_code}")
async def broker_order_webhook(provider_code: str, payload: dict[str, Any], request: Request, db: AsyncSession = Depends(get_db)):
    """Generic broker order update webhook.

    Upstox can call /api/v1/webhooks/brokers/upstox. If UPSTOX_WEBHOOK_SECRET or
    BROKER_WEBHOOK_SECRET is configured, pass it in x-webhook-secret or payload.secret.
    """
    try:
        headers = {k.lower(): v for k, v in request.headers.items()}
        return await apply_broker_order_webhook(db, provider_code, payload, headers=headers)
    except Exception as exc:
        await db.rollback()
        return {"success": False, "processed": False, "reason": str(exc)[:500]}
