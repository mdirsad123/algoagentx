from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_current_user, get_db
from ...db.models import BrokerAccount, LiveTradingApproval, User
from ...utils.api_response import success_response

router = APIRouter()
admin_router = APIRouter()


class LiveApprovalRequestIn(BaseModel):
    broker_account_id: Optional[UUID] = None
    requested_markets: list[str] = Field(default_factory=lambda: ["ALL"])
    max_daily_loss: Optional[Decimal] = None
    max_order_value: Optional[Decimal] = None
    max_trades_per_day: Optional[int] = Field(default=None, ge=1)
    risk_disclaimer_accepted: bool = False
    notes: Optional[str] = None


class LiveApprovalDecisionIn(BaseModel):
    notes: Optional[str] = None
    approved_markets: Optional[list[str]] = None
    max_daily_loss: Optional[Decimal] = None
    max_order_value: Optional[Decimal] = None
    max_trades_per_day: Optional[int] = Field(default=None, ge=1)


def _uid(current_user: dict) -> UUID:
    return UUID(str(current_user["user_id"]))


def _broker_currency(broker: BrokerAccount | None) -> str | None:
    if broker is None:
        return None
    meta = getattr(broker, "metadata_json", None) or {}
    if not isinstance(meta, dict):
        return None
    selected = meta.get("ctrader_selected_account") or meta.get("selected_account") or meta.get("mt5_selected_account") or {}
    last_test = meta.get("last_test") or meta.get("account_info") or {}
    for source in (selected, last_test, meta):
        if isinstance(source, dict):
            value = source.get("currency") or source.get("deposit_asset") or source.get("account_currency")
            if value:
                return str(value).upper()
    return None


def _selected_account_summary(broker: BrokerAccount | None) -> dict[str, Any] | None:
    meta = getattr(broker, "metadata_json", None) or {}
    if not isinstance(meta, dict):
        return None
    selected = meta.get("ctrader_selected_account") or meta.get("selected_account") or meta.get("mt5_selected_account") or meta.get("account_info") or meta.get("last_test")
    if not isinstance(selected, dict):
        return None
    allowed = {"login", "login_id", "account_login", "account_number", "server", "server_name", "currency", "deposit_asset", "mode", "account_type", "trading_mode", "balance", "equity"}
    return {str(k): v for k, v in selected.items() if str(k) in allowed}


def _infer_broker_mode(broker: BrokerAccount | None) -> str | None:
    if broker is None:
        return None
    broker_mode = str(getattr(broker, "mode", "") or "").upper()
    selected = _selected_account_summary(broker) or {}
    account_mode = str(selected.get("mode") or selected.get("account_type") or selected.get("trading_mode") or "").upper()
    if account_mode in {"LIVE", "REAL"}:
        return "LIVE"
    if account_mode == "DEMO":
        return "DEMO"
    return broker_mode or None


def _out(row: LiveTradingApproval) -> dict[str, Any]:
    broker = row.broker_account
    user = row.user
    approver = row.approver
    return {
        "id": str(row.id),
        "user_id": str(row.user_id),
        "user_name": getattr(user, "fullname", None),
        "user_email": getattr(user, "email", None),
        "broker_account_id": str(row.broker_account_id) if row.broker_account_id else None,
        "broker_name": getattr(broker, "account_label", None) or getattr(broker, "broker_name", None),
        "broker_provider": getattr(broker, "broker_name", None),
        "broker_code": getattr(broker, "broker_code", None),
        "account_label": getattr(broker, "account_label", None),
        "broker_mode": getattr(broker, "mode", None),
        "mode": _infer_broker_mode(broker),
        "approval_mode": _infer_broker_mode(broker),
        "broker_status": getattr(broker, "status", None),
        "currency": _broker_currency(broker),
        "server_name": getattr(broker, "server_name", None),
        "login_id": getattr(broker, "login_id", None),
        "selected_account": _selected_account_summary(broker),
        "approved_by": str(row.approved_by) if row.approved_by else None,
        "approved_by_email": getattr(approver, "email", None),
        "status": row.status,
        "approved_markets": row.approved_markets or [],
        "max_daily_loss": row.max_daily_loss,
        "max_order_value": row.max_order_value,
        "max_trades_per_day": row.max_trades_per_day,
        "notes": row.notes,
        "risk_disclaimer_accepted_at": row.risk_disclaimer_accepted_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.post("/request")
async def request_live_approval(payload: LiveApprovalRequestIn, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = _uid(current_user)
    if not payload.risk_disclaimer_accepted:
        raise HTTPException(status_code=400, detail="Risk disclaimer must be accepted before requesting broker deployment approval")
    if payload.broker_account_id:
        broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == payload.broker_account_id, BrokerAccount.user_id == user_id))).scalar_one_or_none()
        if not broker:
            raise HTTPException(status_code=404, detail="Broker account not found")
        if str(broker.status or "").upper() != "CONNECTED":
            raise HTTPException(status_code=400, detail="Only CONNECTED broker accounts can be submitted for deployment approval")
        existing_rows = (await db.execute(select(LiveTradingApproval).where(
            LiveTradingApproval.user_id == user_id,
            LiveTradingApproval.broker_account_id == payload.broker_account_id,
            LiveTradingApproval.status.in_(["PENDING", "APPROVED"]),
        ).order_by(LiveTradingApproval.updated_at.desc()))).scalars().all()
        existing = next((row for row in existing_rows if row.status == "PENDING"), None) or next((row for row in existing_rows if row.status == "APPROVED"), None)
        if existing is not None:
            if existing.status == "APPROVED":
                raise HTTPException(status_code=400, detail="This broker account is already approved.")
            return success_response(_out(existing), "Approval already pending for this broker.")
    row = LiveTradingApproval(
        user_id=user_id,
        broker_account_id=payload.broker_account_id,
        status="PENDING",
        approved_markets=[m.upper() for m in (payload.requested_markets or ["ALL"])],
        max_daily_loss=payload.max_daily_loss,
        max_order_value=payload.max_order_value,
        max_trades_per_day=payload.max_trades_per_day,
        notes=payload.notes,
        risk_disclaimer_accepted_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(_out(row), "Live trading approval request submitted")


@router.get("/approved-brokers")
async def list_approved_brokers(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    user_id = _uid(current_user)
    rows = (await db.execute(
        select(LiveTradingApproval)
        .join(BrokerAccount, BrokerAccount.id == LiveTradingApproval.broker_account_id)
        .where(
            LiveTradingApproval.user_id == user_id,
            LiveTradingApproval.status == "APPROVED",
            LiveTradingApproval.risk_disclaimer_accepted_at.is_not(None),
            BrokerAccount.status == "CONNECTED",
        )
        .order_by(LiveTradingApproval.updated_at.desc())
    )).scalars().all()
    payload = []
    for row in rows:
        broker = row.broker_account
        selected_summary = _selected_account_summary(broker)
        inferred_mode = _infer_broker_mode(broker)
        currency = _broker_currency(broker)
        payload.append({
            "approval_id": str(row.id),
            "broker_account_id": str(row.broker_account_id),
            "broker_name": getattr(broker, "broker_name", None),
            "broker_code": getattr(broker, "broker_code", None),
            "account_label": getattr(broker, "account_label", None),
            "mode": inferred_mode,
            "approval_mode": inferred_mode,
            "broker_mode": getattr(broker, "mode", None),
            "status": row.status,
            "broker_status": getattr(broker, "status", None),
            "approved_markets": row.approved_markets or ["ALL"],
            "max_daily_loss": row.max_daily_loss,
            "max_order_value": row.max_order_value,
            "max_trades_per_day": row.max_trades_per_day,
            "approved_at": row.updated_at,
            "currency": currency,
            "server_name": getattr(broker, "server_name", None) or (selected_summary or {}).get("server") or (selected_summary or {}).get("server_name"),
            "login_id": getattr(broker, "login_id", None) or (selected_summary or {}).get("login") or (selected_summary or {}).get("login_id") or (selected_summary or {}).get("account_login") or (selected_summary or {}).get("account_number"),
            "selected_account": selected_summary,
        })
    return success_response(payload, "Approved broker accounts loaded")


@router.get("")
async def list_my_live_approvals(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    rows = (await db.execute(select(LiveTradingApproval).where(LiveTradingApproval.user_id == _uid(current_user)).order_by(LiveTradingApproval.created_at.desc()))).scalars().all()
    return success_response([_out(row) for row in rows])


@admin_router.get("")
async def list_live_approvals(status: Optional[str] = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    stmt = select(LiveTradingApproval).order_by(LiveTradingApproval.created_at.desc())
    if status:
        stmt = stmt.where(LiveTradingApproval.status == status.upper())
    rows = (await db.execute(stmt)).scalars().all()
    return success_response([_out(row) for row in rows])


@admin_router.get("/{approval_id}")
async def get_live_approval(approval_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    row = (await db.execute(select(LiveTradingApproval).where(LiveTradingApproval.id == approval_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Live approval not found")
    return success_response(_out(row))


async def _decision(db: AsyncSession, approval_id: UUID, current_user: dict, status: str, payload: LiveApprovalDecisionIn | None = None) -> dict[str, Any]:
    row = (await db.execute(select(LiveTradingApproval).where(LiveTradingApproval.id == approval_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Live approval not found")
    payload = payload or LiveApprovalDecisionIn()
    row.status = status
    row.approved_by = _uid(current_user)
    row.updated_at = datetime.now(timezone.utc)
    if payload.notes is not None:
        row.notes = payload.notes
    if status == "APPROVED":
        if payload.approved_markets is not None:
            row.approved_markets = [m.upper() for m in (payload.approved_markets or ["ALL"])]
        elif not row.approved_markets:
            row.approved_markets = ["ALL"]
        if payload.max_daily_loss is not None:
            row.max_daily_loss = payload.max_daily_loss
        if payload.max_order_value is not None:
            row.max_order_value = payload.max_order_value
        if payload.max_trades_per_day is not None:
            row.max_trades_per_day = payload.max_trades_per_day
    await db.commit()
    await db.refresh(row)
    return _out(row)


@admin_router.post("/{approval_id}/approve")
async def approve_live_approval(approval_id: UUID, payload: LiveApprovalDecisionIn | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return success_response(await _decision(db, approval_id, current_user, "APPROVED", payload), "Live approval approved")


@admin_router.post("/{approval_id}/reject")
async def reject_live_approval(approval_id: UUID, payload: LiveApprovalDecisionIn | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    if payload is None or not str(payload.notes or "").strip():
        raise HTTPException(status_code=400, detail="Reject notes are required.")
    return success_response(await _decision(db, approval_id, current_user, "REJECTED", payload), "Live approval rejected")


@admin_router.post("/{approval_id}/revoke")
async def revoke_live_approval(approval_id: UUID, payload: LiveApprovalDecisionIn | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return success_response(await _decision(db, approval_id, current_user, "REVOKED", payload), "Live approval revoked")
