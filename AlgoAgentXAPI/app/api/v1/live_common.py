from __future__ import annotations

import json
from typing import Any, Iterable, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import BrokerAccount, Strategy, StrategyDeployment


def user_id_from(current_user: dict) -> UUID:
    return UUID(str(current_user["user_id"]))


def is_admin(current_user: dict) -> bool:
    return str(current_user.get("role") or "").lower() == "admin"


def dump_schema(schema_obj: Any) -> dict[str, Any]:
    if hasattr(schema_obj, "model_dump"):
        return schema_obj.model_dump(mode="json")
    return json.loads(schema_obj.json())


def dump_list(schema_cls: Any, rows: Iterable[Any]) -> list[dict[str, Any]]:
    return [dump_schema(schema_cls.model_validate(row)) for row in rows]


def dump_one(schema_cls: Any, row: Any) -> dict[str, Any]:
    return dump_schema(schema_cls.model_validate(row))


def update_from_payload(row: Any, payload: Any, exclude: Optional[set[str]] = None) -> Any:
    exclude = exclude or set()
    values = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)
    for key, value in values.items():
        if key in exclude:
            continue
        setattr(row, key, value)
    return row


async def get_deployment_or_404(
    db: AsyncSession,
    deployment_id: UUID,
    current_user: dict,
) -> StrategyDeployment:
    stmt = select(StrategyDeployment).where(StrategyDeployment.id == deployment_id)
    if not is_admin(current_user):
        stmt = stmt.where(StrategyDeployment.user_id == user_id_from(current_user))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")
    return row


async def get_broker_account_or_404(
    db: AsyncSession,
    broker_account_id: UUID,
    current_user: dict,
) -> BrokerAccount:
    stmt = select(BrokerAccount).where(BrokerAccount.id == broker_account_id)
    if not is_admin(current_user):
        stmt = stmt.where(BrokerAccount.user_id == user_id_from(current_user))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker account not found")
    return row


async def get_published_strategy_or_400(db: AsyncSession, strategy_id: str) -> Strategy:
    row = (await db.execute(select(Strategy).where(Strategy.id == strategy_id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    if str(getattr(row, "visibility", "") or "").upper() != "PUBLIC":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published strategies can be deployed",
        )
    return row


async def get_deployable_strategy_or_400(db: AsyncSession, strategy_id: str, mode: str | None) -> Strategy:
    strategy = await get_published_strategy_or_400(db, strategy_id)
    normalized_mode = str(mode or "PAPER").upper()
    block_live_mode(normalized_mode)

    if normalized_mode == "PAPER" and not bool(getattr(strategy, "is_deployable_paper", False)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is not enabled for PAPER deployment. Ask admin to enable Paper Deployment in Deployment Gate.",
        )
    if normalized_mode == "DEMO" and not bool(getattr(strategy, "is_deployable_demo", False)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy is not enabled for MT5 DEMO deployment. Ask admin to enable Demo Deployment in Deployment Gate.",
        )
    return strategy


def block_live_mode(mode: str | None) -> None:
    if str(mode or "").upper() == "LIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Live trading is disabled until final production review.",
        )
