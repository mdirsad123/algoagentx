from pydantic import BaseModel
from typing import Optional


class InstrumentBase(BaseModel):
    symbol: str
    exchange: str
    market: str
    instrument_type: Optional[str] = None
    tick_size: Optional[float] = None
    lot_size: Optional[int] = None


class Instrument(InstrumentBase):
    id: int

    class Config:
        from_attributes = True