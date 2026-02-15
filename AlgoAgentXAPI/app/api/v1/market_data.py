from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime
from ...core.dependencies import get_db
from ...schemas import TimeframeResponse, MarketDataRangeResponse
from ...db.models import MarketData, Instrument

router = APIRouter()


@router.get("/timeframes", response_model=List[TimeframeResponse])
async def get_timeframes(
    instrument_id: Optional[int] = Query(None, description="Filter by instrument ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get distinct timeframes from market_data table.
    
    Optionally filter by instrument_id.
    """
    try:
        # Build query
        query = select(MarketData.timeframe).distinct()
        
        if instrument_id is not None:
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
            
            query = query.where(MarketData.instrument_id == instrument_id)
        
        # Execute query
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