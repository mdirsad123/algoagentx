from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_db
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
