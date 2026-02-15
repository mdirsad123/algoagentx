from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional


class SignalBase(BaseModel):
    instrument_id: int
    signal_type: str
    confidence: Optional[float] = None
    metadata: Optional[dict] = None


class SignalCreate(SignalBase):
    pass


class Signal(SignalBase):
    id: UUID
    backtest_id: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True