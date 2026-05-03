from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


ALLOWED_QUANTITY_MODES = {"SHARES", "LOTS", "UNITS", "CONTRACTS"}


class AssetClassOut(BaseModel):
    id: int
    code: str
    label: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TimeframeOut(BaseModel):
    id: int
    code: str
    label: str
    minutes: Optional[int] = None
    is_intraday: bool = False
    is_active: bool = True
    display_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class InstrumentBase(BaseModel):
    symbol: Optional[str] = None
    name: Optional[str] = None
    exchange: Optional[str] = "GLOBAL"
    market: Optional[str] = None
    instrument_type: Optional[str] = None
    asset_class: Optional[str] = None
    base_currency: Optional[str] = None
    quote_currency: Optional[str] = None
    account_currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    price_unit_name: Optional[str] = None
    quantity_mode: Optional[str] = None
    contract_size: Optional[float] = None
    tick_size: Optional[float] = None
    tick_value_per_lot: Optional[float] = None
    pip_size: Optional[float] = None
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    quantity_step: Optional[float] = None
    min_lot: Optional[float] = None
    max_lot: Optional[float] = None
    lot_step: Optional[float] = None
    lot_size: Optional[int] = None
    price_precision: Optional[int] = None
    quantity_precision: Optional[int] = None
    broker_symbol: Optional[str] = None
    is_tradeable_backtest: Optional[bool] = True
    is_tradeable_live: Optional[bool] = False
    is_active: Optional[bool] = True

    @field_validator("symbol", "asset_class", "quantity_mode", "account_currency", "base_currency", "quote_currency", mode="before")
    @classmethod
    def upper_clean(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value.upper() if value else None
        return value

    @field_validator("quantity_mode")
    @classmethod
    def validate_quantity_mode(cls, value):
        if value and value not in ALLOWED_QUANTITY_MODES:
            raise ValueError(f"quantity_mode must be one of {sorted(ALLOWED_QUANTITY_MODES)}")
        return value


class InstrumentCreate(InstrumentBase):
    symbol: str = Field(..., min_length=1)
    name: Optional[str] = None


class InstrumentUpdate(InstrumentBase):
    pass


class InstrumentOut(InstrumentBase):
    id: int
    symbol: str
    exchange: Optional[str] = None
    market: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
