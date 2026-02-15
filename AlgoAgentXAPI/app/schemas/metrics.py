from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from typing import Optional


class MetricBase(BaseModel):
    backtest_id: UUID
    name: str
    value: Optional[Decimal] = None


class MetricCreate(MetricBase):
    pass


class Metric(MetricBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True