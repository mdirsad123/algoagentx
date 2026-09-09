from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime
from ...core.dependencies import get_db
from ...schemas import TimeframeResponse, MarketDataRangeResponse
from ...db.models import MarketData, Instrument, Timeframe

router = APIRouter()


@router.get("/timeframes", response_model=List[TimeframeResponse])
async def get_timeframes(
    instrument_id: Optional[int] = Query(None, description="Filter by instrument ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get active timeframes from the master timeframes table.

    instrument_id is accepted for backward compatibility; if the master table is
    empty, the endpoint falls back to existing market_data rows.
    """
    try:
        if instrument_id is not None:
            instrument_result = await db.execute(
                select(Instrument).where(Instrument.id == instrument_id)
            )
            instrument = instrument_result.scalar_one_or_none()
            if not instrument:
                raise HTTPException(
                    status_code=404,
                    detail=f"Instrument with ID {instrument_id} not found"
                )

        result = await db.execute(
            select(Timeframe.code)
            .where(Timeframe.is_active.is_(True))
            .order_by(Timeframe.display_order.asc(), Timeframe.id.asc())
        )
        timeframes = result.scalars().all()

        if not timeframes:
            query = select(MarketData.timeframe).where(MarketData.timeframe.is_not(None)).distinct().order_by(MarketData.timeframe.asc())
            if instrument_id is not None:
                query = query.where(MarketData.instrument_id == instrument_id)
            result = await db.execute(query)
            timeframes = result.scalars().all()
        
        # Return as list of TimeframeResponse objects
        return [{"timeframe": tf} for tf in timeframes]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve timeframes: {str(e)}"
        )


@router.get("/range", response_model=MarketDataRangeResponse)
async def get_market_data_range(
    instrument_id: int = Query(..., description="Instrument ID"),
    timeframe: str = Query(..., description="Timeframe (e.g., 5m, 15m, 1h, 1d)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get min/max timestamp and candle count for specified instrument and timeframe.
    """
    try:
        # Verify instrument exists
        instrument_result = await db.execute(
            select(Instrument).where(Instrument.id == instrument_id)
        )
        instrument = instrument_result.scalar_one_or_none()
        if not instrument:
            raise HTTPException(
                status_code=404, 
                detail=f"Instrument with ID {instrument_id} not found"
            )
        
        # Query for min/max timestamps and count
        query = select(
            func.min(MarketData.timestamp).label('min_timestamp'),
            func.max(MarketData.timestamp).label('max_timestamp'),
            func.count(MarketData.timestamp).label('candle_count')
        ).where(
            MarketData.instrument_id == instrument_id,
            MarketData.timeframe == timeframe
        )
        
        result = await db.execute(query)
        row = result.first()
        
        if not row or row.min_timestamp is None:
            raise HTTPException(
                status_code=404,
                detail=f"No market data found for instrument {instrument_id} with timeframe {timeframe}"
            )
        
        return {
            "min_timestamp": row.min_timestamp,
            "max_timestamp": row.max_timestamp,
            "candle_count": row.candle_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve market data range: {str(e)}"
        )