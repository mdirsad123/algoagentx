from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from uuid import UUID

from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...db.models import BrokerAccount, LiveOrder, MT5Agent, MT5AgentCommand
from ...schemas.mt5_agent import MT5AgentCommandOut, MT5AgentCommandResultIn, MT5AgentHeartbeatIn, MT5AgentOrderResultIn, MT5AgentOut, MT5AgentRegisterIn, MT5AgentRegisterOut
from ...utils.api_response import success_response
from .live_common import get_broker_account_or_404, user_id_from

router = APIRouter()


def _agent_download_zip_path() -> Path:
    # app/api/v1/mt5_agent.py -> app/api/v1 -> app/api -> app -> project root
    return Path(__file__).resolve().parents[3] / "storage" / "downloads" / "AlgoAgentXMT5Agent.zip"


@router.get("/download")
async def download_mt5_agent():
    zip_path = _agent_download_zip_path()
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="AlgoAgentX MT5 Agent package is not available yet. Please ask admin to rebuild the API package.")
    return FileResponse(
        path=str(zip_path),
        filename="AlgoAgentXMT5Agent.zip",
        media_type="application/zip",
    )



def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _extract_token(payload_token: str | None = None, authorization: str | None = None) -> str:
    if payload_token:
        return payload_token.strip()
    if authorization:
        text = authorization.strip()
        if text.lower().startswith("bearer "):
            return text[7:].strip()
        return text
    return ""


async def _agent_from_token(db: AsyncSession, token: str) -> MT5Agent:
    if not token:
        raise HTTPException(status_code=401, detail="Missing MT5 agent token")
    row = (await db.execute(select(MT5Agent).where(MT5Agent.agent_token_hash == _hash_token(token)))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid MT5 agent token")
    return row


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_mt5_agent(payload: MT5AgentRegisterIn, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    account = await get_broker_account_or_404(db, payload.broker_account_id, current_user)
    if str(account.broker_code or account.broker_name or "").upper() != "MT5":
        raise HTTPException(status_code=400, detail="Agent token can only be generated for MT5 broker accounts")
    token = "aax_mt5_" + secrets.token_urlsafe(40)
    token_hash = _hash_token(token)
    existing = (await db.execute(select(MT5Agent).where(MT5Agent.broker_account_id == account.id).order_by(MT5Agent.created_at.desc()))).scalars().first()
    if existing:
        existing.agent_token_hash = token_hash
        existing.status = "DISCONNECTED"
        existing.trading_mode = payload.trading_mode
        existing.terminal_status = "WAITING_FOR_AGENT"
        agent = existing
    else:
        agent = MT5Agent(user_id=user_id_from(current_user), broker_account_id=account.id, agent_token_hash=token_hash, status="DISCONNECTED", terminal_status="WAITING_FOR_AGENT", trading_mode=payload.trading_mode)
        db.add(agent)
    meta = account.metadata_json or {}
    account.metadata_json = {**meta, "mt5_agent": {"status": "TOKEN_GENERATED", "last_token_generated_at": datetime.now(timezone.utc).isoformat(), "message": "Agent token generated. Copy it into AlgoAgentX MT5 Agent."}}
    await db.commit()
    await db.refresh(agent)
    await db.refresh(account)
    return success_response(MT5AgentRegisterOut(agent=MT5AgentOut.model_validate(agent), agent_token=token, message="Copy this token now. It is shown only once.").model_dump(mode="json"), "MT5 Agent token generated")


@router.get("/broker-account/{broker_account_id}/status")
async def get_agent_status(broker_account_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    account = await get_broker_account_or_404(db, broker_account_id, current_user)
    row = (await db.execute(select(MT5Agent).where(MT5Agent.broker_account_id == account.id).order_by(MT5Agent.last_heartbeat_at.desc().nullslast(), MT5Agent.created_at.desc()))).scalars().first()
    if not row:
        return success_response(None, "No MT5 Agent registered yet")
    return success_response(MT5AgentOut.model_validate(row).model_dump(mode="json"))


@router.post("/heartbeat")
async def heartbeat(payload: MT5AgentHeartbeatIn, authorization: str | None = Header(default=None), db: AsyncSession = Depends(get_db)):
    token = _extract_token(payload.agent_token, authorization)
    agent = await _agent_from_token(db, token)
    now = datetime.now(timezone.utc)
    agent.last_heartbeat_at = now
    agent.status = "CONNECTED" if payload.terminal_connected else "DISCONNECTED"
    agent.terminal_status = payload.terminal_status or ("CONNECTED" if payload.terminal_connected else "NOT_CONNECTED")
    account_login = payload.mt5_account_login or payload.account_login
    trading_allowed = payload.trading_allowed if payload.trading_allowed is not None else payload.algo_trading_enabled
    agent.mt5_account_login = account_login or agent.mt5_account_login
    agent.server_name = payload.server_name or agent.server_name
    agent.balance = payload.balance
    agent.equity = payload.equity
    agent.currency = payload.currency or agent.currency
    agent.algo_trading_enabled = trading_allowed
    agent.agent_version = payload.agent_version or agent.agent_version
    agent.metadata_json = {**(agent.metadata_json or {}), **(payload.metadata or {}), "last_heartbeat_at": now.isoformat()}
    account = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == agent.broker_account_id))).scalar_one_or_none()
    if account:
        account.status = "CONNECTED" if payload.terminal_connected else "DISCONNECTED"
        account.last_connected_at = now if payload.terminal_connected else account.last_connected_at
        account.login_id = account_login or account.login_id
        account.server_name = payload.server_name or account.server_name
        account.metadata_json = {**(account.metadata_json or {}), "mt5_agent": {"agent_id": str(agent.id), "status": agent.status, "terminal_status": agent.terminal_status, "last_heartbeat_at": now.isoformat(), "balance": str(agent.balance) if agent.balance is not None else None, "equity": str(agent.equity) if agent.equity is not None else None, "currency": agent.currency, "algo_trading_enabled": agent.algo_trading_enabled, "agent_version": agent.agent_version}}
    await db.commit()
    return success_response({"status": agent.status, "terminal_status": agent.terminal_status, "last_heartbeat_at": now.isoformat()}, "Heartbeat accepted")


@router.get("/commands")
async def poll_commands(authorization: str | None = Header(default=None), db: AsyncSession = Depends(get_db)):
    agent = await _agent_from_token(db, _extract_token(None, authorization))
    rows = (await db.execute(select(MT5AgentCommand).where(MT5AgentCommand.agent_id == agent.id, MT5AgentCommand.status == "PENDING").order_by(MT5AgentCommand.created_at.asc()).limit(10))).scalars().all()
    now = datetime.now(timezone.utc)
    for row in rows:
        row.status = "SENT"
        row.picked_up_at = now
    await db.commit()
    return success_response([MT5AgentCommandOut.model_validate(row).model_dump(mode="json") for row in rows])


async def _store_command_result(payload: MT5AgentCommandResultIn, authorization: str | None, db: AsyncSession) -> dict[str, str]:
    agent = await _agent_from_token(db, _extract_token(payload.agent_token, authorization))
    cmd = (await db.execute(
        select(MT5AgentCommand).where(MT5AgentCommand.id == payload.command_id, MT5AgentCommand.agent_id == agent.id)
    )).scalar_one_or_none()
    if not cmd:
        raise HTTPException(status_code=404, detail="MT5 agent command not found")

    requested_status = str(payload.status or "").upper().strip()
    if payload.success:
        cmd.status = "COMPLETED" if requested_status not in {"ERROR", "TIMEOUT"} else requested_status
        cmd.error_message = None
    else:
        cmd.status = requested_status if requested_status in {"ERROR", "TIMEOUT"} else "ERROR"
        cmd.error_message = payload.message or f"MT5 {cmd.command_type} command failed"
    cmd.result_payload = payload.model_dump(mode="json")
    cmd.completed_at = datetime.now(timezone.utc)

    if cmd.command_type == "PLACE_ORDER":
        raw_payload = cmd.request_payload if isinstance(cmd.request_payload, dict) else {}
        client_order_id = raw_payload.get("client_order_id") or raw_payload.get("idempotency_key")
        live_order = None
        if client_order_id:
            live_order = (await db.execute(select(LiveOrder).where(LiveOrder.client_order_id == client_order_id))).scalar_one_or_none()
        if live_order is None:
            live_order = (await db.execute(select(LiveOrder).where(LiveOrder.broker_order_id == str(cmd.id)))).scalar_one_or_none()
        if live_order is not None:
            raw_result = payload.raw_response or {}
            old_raw = live_order.raw_response if isinstance(live_order.raw_response, dict) else {}
            if payload.broker_order_id:
                live_order.broker_order_id = str(payload.broker_order_id)
            if payload.executed_price is not None:
                live_order.executed_price = payload.executed_price
            live_order.status = "FILLED" if payload.success else "ERROR"
            live_order.error_message = None if payload.success else (payload.message or cmd.error_message)
            live_order.raw_response = {
                **old_raw,
                "agent_command_id": str(cmd.id),
                "client_order_id": client_order_id,
                "mt5_order_result": raw_result,
                "mt5_order_message": payload.message,
            }

    await db.commit()
    return {"command_id": str(cmd.id), "status": cmd.status}


@router.post("/command-result")
async def command_result(payload: MT5AgentCommandResultIn, authorization: str | None = Header(default=None), db: AsyncSession = Depends(get_db)):
    data = await _store_command_result(payload, authorization, db)
    return success_response(data, "Command result accepted")


@router.post("/order-result")
async def order_result(payload: MT5AgentOrderResultIn, authorization: str | None = Header(default=None), db: AsyncSession = Depends(get_db)):
    data = await _store_command_result(payload, authorization, db)
    return success_response(data, "Order result accepted")
