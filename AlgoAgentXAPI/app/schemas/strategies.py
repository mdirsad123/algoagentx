from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrategyBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    parameters: Optional[dict[str, Any]] = None
    visibility: Optional[str] = "PRIVATE"


class StrategyCreate(StrategyBase):
    created_by: Optional[str] = None


class StrategyResponse(StrategyBase):
    id: str
    created_by: Optional[str] = None
    source_request_id: Optional[str] = None
    published_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    strategy_type: Optional[str] = None
    market: Optional[str] = None
    timeframe: Optional[str] = None

    winRate: Optional[float] = None
    sharpeRatio: Optional[float] = None
    totalTrades: Optional[int] = None
    maxDrawdown: Optional[float] = None
    profitFactor: Optional[float] = None
    creatorName: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# backward-compatible names used by app/schemas/__init__.py
Strategy = StrategyResponse
StrategyTemplateResponse = StrategyResponse
StrategyMyResponse = StrategyResponse