from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.services import email_service

router = APIRouter()


def _require_admin(current_user: dict) -> None:
    if str(current_user.get("role") or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


class TestEmailRequest(BaseModel):
    to_email: str


@router.get("/settings/status")
async def email_settings_status(current_user: dict = Depends(get_current_user)):
    _require_admin(current_user)
    status = email_service.smtp_status()
    username = getattr(email_service, "_smtp_username")()
    status["smtp_username"] = email_service._masked(username)
    return status


@router.post("/test")
async def send_test_email(payload: TestEmailRequest, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    _require_admin(current_user)
    html = email_service.build_notification_html(
        "AlgoAgentX test email",
        "SMTP email notifications are configured correctly. This is a test email from your admin settings.",
        None,
    )
    sent = await email_service.send_email(str(payload.to_email), "AlgoAgentX SMTP test email", html)
    if not sent:
        raise HTTPException(status_code=503, detail="Test email was not sent. Check SMTP configuration and backend logs.")
    return {"success": True, "message": "Test email sent"}
