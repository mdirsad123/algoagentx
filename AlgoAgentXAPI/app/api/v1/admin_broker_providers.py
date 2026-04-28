from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.models import BrokerProvider
from ...schemas.live_trading import BrokerProviderCreate, BrokerProviderOut, BrokerProviderUpdate
from ...utils.api_response import success_response
from .live_common import dump_list, dump_one

router = APIRouter()


async def _provider_or_404(db: AsyncSession, provider_id: UUID) -> BrokerProvider:
    row = (await db.execute(select(BrokerProvider).where(BrokerProvider.id == provider_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker provider not found")
    return row


@router.get("")
async def list_broker_providers(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    rows = (await db.execute(select(BrokerProvider).order_by(BrokerProvider.code.asc()))).scalars().all()
    return success_response(dump_list(BrokerProviderOut, rows))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_broker_provider(
    payload: BrokerProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    values = payload.model_dump()
    values["code"] = str(values.get("code") or "").upper().strip()
    exists = (await db.execute(select(BrokerProvider).where(BrokerProvider.code == values["code"]))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Broker provider code already exists")
    row = BrokerProvider(**values)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(BrokerProviderOut, row), "Broker provider created")


@router.patch("/{provider_id}")
async def update_broker_provider(
    provider_id: UUID,
    payload: BrokerProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    row = await _provider_or_404(db, provider_id)
    values = payload.model_dump(exclude_unset=True)
    if "code" in values and values["code"]:
        values["code"] = str(values["code"]).upper().strip()
    for key, value in values.items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(BrokerProviderOut, row), "Broker provider updated")


@router.post("/{provider_id}/enable")
async def enable_broker_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    row = await _provider_or_404(db, provider_id)
    row.is_enabled = True
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(BrokerProviderOut, row), "Broker provider enabled")


@router.post("/{provider_id}/disable")
async def disable_broker_provider(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    row = await _provider_or_404(db, provider_id)
    row.is_enabled = False
    await db.commit()
    await db.refresh(row)
    return success_response(dump_one(BrokerProviderOut, row), "Broker provider disabled")
