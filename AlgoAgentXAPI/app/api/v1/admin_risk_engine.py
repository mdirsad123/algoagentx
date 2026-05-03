from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.models import Instrument
from ...services.trading.risk_engine import calculate_position_size
from ...utils.api_response import success_response


router = APIRouter()


class RiskEnginePreviewRequest(BaseModel):
    instrument_id: int = Field(..., ge=1)
    entry_price: float
    stop_loss: float
    capital: float = Field(..., gt=0)
    risk_percent: float = Field(..., gt=0)
    side: Optional[str] = "BUY"
    position_size_mode: str = "RISK_BASED"
    fixed_lot: Optional[float] = None
    fixed_quantity: Optional[float] = None
    max_lot_cap: Optional[float] = None
    max_quantity_cap: Optional[float] = None


def _num(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _instrument_spec(row: Instrument) -> dict[str, Any]:
    fields = [
        "symbol",
        "name",
        "asset_class",
        "base_currency",
        "quote_currency",
        "account_currency",
        "currency_symbol",
        "price_unit_name",
        "quantity_mode",
        "contract_size",
        "tick_size",
        "tick_value_per_lot",
        "pip_size",
        "min_quantity",
        "max_quantity",
        "quantity_step",
        "min_lot",
        "max_lot",
        "lot_step",
        "price_precision",
        "quantity_precision",
        "broker_symbol",
    ]
    return {field: _num(getattr(row, field, None)) for field in fields}


@router.post("/preview")
async def preview_risk_engine(
    payload: RiskEnginePreviewRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    instrument = await db.get(Instrument, payload.instrument_id)
    if not instrument:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")

    spec = _instrument_spec(instrument)
    result = calculate_position_size(
        entry_price=payload.entry_price,
        stop_loss=payload.stop_loss,
        capital=payload.capital,
        risk_percent=payload.risk_percent,
        instrument_spec=spec,
        position_size_mode=payload.position_size_mode,
        fixed_lot=payload.fixed_lot,
        fixed_quantity=payload.fixed_quantity,
        max_lot_cap=payload.max_lot_cap,
        max_quantity_cap=payload.max_quantity_cap,
        side=payload.side,
    )
    return success_response({"instrument": spec, "calculation": result})
