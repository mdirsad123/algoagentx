from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...db.models import BrokerAccount
from ...schemas.live_trading import BrokerAccountCreate, BrokerAccountOut, BrokerAccountUpdate
from ...services.brokers.factory import get_broker_adapter
from ...utils.api_response import success_response
from .live_common import dump_list, dump_one, get_broker_account_or_404, is_admin, update_from_payload, user_id_from

router = APIRouter()


def _connection_payload(result) -> dict:
    return {
        "connected": bool(result.connected),
        "message": result.message,
        "account_login": result.account_login,
        "server": result.server,
        "balance": str(result.balance) if result.balance is not None else None,
        "equity": str(result.equity) if result.equity is not None else None,
        "currency": result.currency,
        "raw": result.raw,
    }


@router.get("")
async def list_broker_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    stmt = select(BrokerAccount).order_by(BrokerAccount.created_at.desc())
    if not is_admin(current_user):
        stmt = stmt.where(BrokerAccount.user_id == user_id_from(current_user))
    rows = (await db.execute(stmt)).scalars().all()
    return success_response(dump_list(BrokerAccountOut, rows))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_broker_account(
    payload: BrokerAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    values = payload.model_dump()
    values["broker_name"] = (values.get("broker_name") or "MT5").upper()
    if values.get("mode") == "LIVE":
        values["mode"] = "DEMO"
    values["status"] = values.get("status") or "DISCONNECTED"
    row = BrokerAccount(user_id=user_id_from(current_user), **values)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(BrokerAccountOut, row), "Broker account created")


@router.get("/{broker_account_id}")
async def get_broker_account(
    broker_account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    return success_response(dump_one(BrokerAccountOut, row))


@router.patch("/{broker_account_id}")
async def update_broker_account(
    broker_account_id: UUID,
    payload: BrokerAccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    values = payload.model_dump(exclude_unset=True)
    if values.get("encrypted_password") in {None, ""}:
        values.pop("encrypted_password", None)
    if values.get("encrypted_token") in {None, ""}:
        values.pop("encrypted_token", None)
    for key, value in values.items():
        setattr(row, key, value)
    if row.mode == "LIVE":
        row.mode = "DEMO"
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(BrokerAccountOut, row), "Broker account updated")


@router.delete("/{broker_account_id}")
async def delete_broker_account(
    broker_account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    await db.delete(row)
    await db.commit()
    return success_response({"id": str(broker_account_id)}, "Broker account deleted")


@router.post("/{broker_account_id}/test")
async def test_broker_connection(
    broker_account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    adapter = get_broker_adapter(row)
    result = await adapter.test_connection()
    row.status = "CONNECTED" if result.connected else "ERROR"
    row.last_connected_at = datetime.now(timezone.utc) if result.connected else row.last_connected_at
    existing_meta = row.metadata_json or {}
    row.metadata_json = {
        **existing_meta,
        "last_test": _connection_payload(result),
        "provider": row.broker_name,
        "safe_message": result.message,
    }
    await db.commit()
    await db.refresh(row)
    return success_response({"broker_account": dump_one(BrokerAccountOut, row), "connection": _connection_payload(result)}, "Broker connection tested")


@router.get("/{broker_account_id}/account-info")
async def get_broker_account_info(
    broker_account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    adapter = get_broker_adapter(row)
    info = await adapter.get_account_info()
    return success_response(info)


@router.get("/{broker_account_id}/positions")
async def get_broker_positions(
    broker_account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await get_broker_account_or_404(db, broker_account_id, current_user)
    adapter = get_broker_adapter(row)
    positions = await adapter.get_positions()
    return success_response(positions)
