from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TimeframeResponse(BaseModel):
    """Response schema for distinct timeframes"""
    timeframe: str


class MarketDataRangeResponse(BaseModel):
    """Response schema for market data range information"""
    min_timestamp: datetime
    max_timestamp: datetime
    candle_count: int