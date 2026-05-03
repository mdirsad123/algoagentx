from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_current_user, get_db
from ...db.models import AssetClass, Instrument, Timeframe
from ...schemas.market_master import InstrumentCreate, InstrumentUpdate
from ...utils.api_response import success_response

router = APIRouter()
admin_router = APIRouter()


def _num(value: Any):
    if isinstance(value, Decimal):
        return float(value)
    return value


def instrument_to_dict(row: Instrument) -> dict[str, Any]:
    fields = [
        "id", "symbol", "name", "exchange", "market", "instrument_type", "asset_class",
        "base_currency", "quote_currency", "account_currency", "currency_symbol",
        "price_unit_name", "quantity_mode", "contract_size", "tick_size",
        "tick_value_per_lot", "pip_size", "min_quantity", "max_quantity",
        "quantity_step", "min_lot", "max_lot", "lot_step", "lot_size",
        "price_precision", "quantity_precision", "broker_symbol", "is_tradeable_backtest",
        "is_tradeable_live", "is_active", "created_at", "updated_at",
    ]
    data = {field: _num(getattr(row, field, None)) for field in fields}
    for dt_field in ("created_at", "updated_at"):
        if data.get(dt_field) is not None and hasattr(data[dt_field], "isoformat"):
            data[dt_field] = data[dt_field].isoformat()
    return data


def asset_class_to_dict(row: AssetClass) -> dict[str, Any]:
    return {
        "id": row.id,
        "code": row.code,
        "label": row.label,
        "description": row.description,
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def timeframe_to_dict(row: Timeframe) -> dict[str, Any]:
    return {
        "id": row.id,
        "code": row.code,
        "label": row.label,
        "minutes": row.minutes,
        "is_intraday": row.is_intraday,
        "is_active": row.is_active,
        "display_order": row.display_order,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@admin_router.get("/asset-classes")
async def admin_asset_classes(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    rows = (await db.execute(select(AssetClass).order_by(AssetClass.code.asc()))).scalars().all()
    return success_response([asset_class_to_dict(row) for row in rows])


@admin_router.get("/timeframes")
async def admin_timeframes(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    rows = (await db.execute(select(Timeframe).order_by(Timeframe.display_order.asc(), Timeframe.id.asc()))).scalars().all()
    return success_response([timeframe_to_dict(row) for row in rows])


@admin_router.get("/instruments")
async def admin_instruments(
    search: str | None = Query(default=None),
    active_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    stmt = select(Instrument)
    if active_only:
        stmt = stmt.where(Instrument.is_active.is_(True))
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where((Instrument.symbol.ilike(term)) | (Instrument.name.ilike(term)) | (Instrument.asset_class.ilike(term)))
    rows = (await db.execute(stmt.order_by(Instrument.symbol.asc()))).scalars().all()
    return success_response([instrument_to_dict(row) for row in rows])


@admin_router.get("/instruments/{instrument_id}")
async def admin_instrument_detail(
    instrument_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    row = await db.get(Instrument, instrument_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")
    return success_response(instrument_to_dict(row))


@admin_router.post("/instruments", status_code=status.HTTP_201_CREATED)
async def admin_create_instrument(
    payload: InstrumentCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    exists = (await db.execute(select(Instrument).where(func.upper(Instrument.symbol) == payload.symbol.upper()))).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Instrument symbol already exists")
    values = payload.model_dump(exclude_unset=True)
    values["symbol"] = payload.symbol.upper()
    values["exchange"] = values.get("exchange") or "GLOBAL"
    values["market"] = values.get("market") or values.get("asset_class") or "GLOBAL"
    values["instrument_type"] = values.get("instrument_type") or values.get("asset_class")
    row = Instrument(**values)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(instrument_to_dict(row))


@admin_router.patch("/instruments/{instrument_id}")
async def admin_update_instrument(
    instrument_id: int,
    payload: InstrumentUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    row = await db.get(Instrument, instrument_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")
    values = payload.model_dump(exclude_unset=True)
    if "symbol" in values and values["symbol"]:
        values["symbol"] = values["symbol"].upper()
    for key, value in values.items():
        if hasattr(row, key):
            setattr(row, key, value)
    if not row.market:
        row.market = row.asset_class or "GLOBAL"
    if not row.instrument_type:
        row.instrument_type = row.asset_class
    await db.commit()
    await db.refresh(row)
    return success_response(instrument_to_dict(row))


@router.get("/timeframes")
async def user_timeframes(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(Timeframe)
            .where(Timeframe.is_active.is_(True))
            .order_by(Timeframe.display_order.asc(), Timeframe.id.asc())
        )
    ).scalars().all()
    return success_response([timeframe_to_dict(row) for row in rows])


@router.get("/instruments")
async def user_instruments(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(Instrument)
            .where(Instrument.is_active.is_(True))
            .order_by(Instrument.symbol.asc())
        )
    ).scalars().all()
    return success_response([instrument_to_dict(row) for row in rows])
