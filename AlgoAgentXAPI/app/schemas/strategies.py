from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StrategyBase(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[dict] = None


class StrategyCreate(StrategyBase):
    pass


class Strategy(StrategyBase):
    id: str
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class StrategyTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str = "active"  # active/inactive
    win_rate: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    total_trades: Optional[int] = None
    max_drawdown: Optional[float] = None
    profit_factor: Optional[float] = None
    last_updated: datetime

    class Config:
        from_attributes = True


class StrategyMyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str = "active"  # active/inactive
    win_rate: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    total_trades: Optional[int] = None
    max_drawdown: Optional[float] = None
    profit_factor: Optional[float] = None
    last_updated: datetime

    class Config:
        from_attributes = True
