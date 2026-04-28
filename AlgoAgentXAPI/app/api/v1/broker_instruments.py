from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_current_user, get_db
from ...db.models import BrokerInstrument
from ...utils.api_response import success_response

router = APIRouter()


def _payload(row: BrokerInstrument) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "broker_provider_code": row.broker_provider_code,
        "exchange": row.exchange,
        "trading_symbol": row.trading_symbol,
        "instrument_key": row.instrument_key,
        "name": row.name,
        "segment": row.segment,
        "lot_size": row.lot_size,
        "tick_size": str(row.tick_size) if row.tick_size is not None else None,
        "is_active": row.is_active,
        "metadata_json": row.metadata_json or {},
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("")
async def list_broker_instruments(
    broker: str = Query(default="UPSTOX"),
    search: Optional[str] = Query(default=None),
    exchange: Optional[str] = Query(default=None),
    segment: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    provider = (broker or "UPSTOX").upper().strip()
    stmt = select(BrokerInstrument).where(BrokerInstrument.broker_provider_code == provider, BrokerInstrument.is_active.is_(True))
    if exchange:
        stmt = stmt.where(BrokerInstrument.exchange.ilike(exchange.strip()))
    if segment:
        stmt = stmt.where(BrokerInstrument.segment.ilike(segment.strip()))
    if search:
        q = f"%{search.strip()}%"
        stmt = stmt.where(or_(BrokerInstrument.trading_symbol.ilike(q), BrokerInstrument.instrument_key.ilike(q), BrokerInstrument.name.ilike(q)))
    stmt = stmt.order_by(BrokerInstrument.trading_symbol.asc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return success_response([_payload(row) for row in rows])
