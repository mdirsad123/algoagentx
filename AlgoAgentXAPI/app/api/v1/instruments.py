from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_db
from ...db.models import Instrument
from ...utils.api_response import success_response

router = APIRouter()


@router.get("/")
async def get_instruments(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Instrument).order_by(Instrument.symbol.asc()))).scalars().all()
    data = [{
        "id": row.id,
        "symbol": row.symbol,
        "exchange": row.exchange,
        "market": row.market,
        "instrument_type": row.instrument_type,
        "tick_size": float(row.tick_size) if row.tick_size is not None else None,
        "lot_size": row.lot_size,
    } for row in rows]
    return success_response(data, "No data found" if not data else None)
