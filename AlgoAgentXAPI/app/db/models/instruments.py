from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from ..base import Base


class AssetClass(Base):
    __tablename__ = "asset_classes"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False, unique=True, index=True)
    label = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Timeframe(Base):
    __tablename__ = "timeframes"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False, unique=True, index=True)
    label = Column(String, nullable=False)
    minutes = Column(Integer, nullable=True)
    is_intraday = Column(Boolean, nullable=False, server_default="false")
    is_active = Column(Boolean, nullable=False, server_default="true")
    display_order = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    exchange = Column(String, nullable=False, server_default="GLOBAL")
    market = Column(String, nullable=False, server_default="GLOBAL")
    instrument_type = Column(String)
    lot_size = Column(Integer)

    asset_class = Column(String, nullable=True, index=True)
    base_currency = Column(String, nullable=True)
    quote_currency = Column(String, nullable=True)
    account_currency = Column(String, nullable=True)
    currency_symbol = Column(String, nullable=True)
    price_unit_name = Column(String, nullable=True)
    quantity_mode = Column(String, nullable=True)
    contract_size = Column(Numeric(20, 6), nullable=True)
    tick_size = Column(Numeric(20, 8), nullable=True)
    tick_value_per_lot = Column(Numeric(20, 8), nullable=True)
    pip_size = Column(Numeric(20, 8), nullable=True)
    min_quantity = Column(Numeric(20, 6), nullable=True)
    max_quantity = Column(Numeric(20, 6), nullable=True)
    quantity_step = Column(Numeric(20, 6), nullable=True)
    min_lot = Column(Numeric(20, 6), nullable=True)
    max_lot = Column(Numeric(20, 6), nullable=True)
    lot_step = Column(Numeric(20, 6), nullable=True)
    price_precision = Column(Integer, nullable=True)
    quantity_precision = Column(Integer, nullable=True)
    broker_symbol = Column(String, nullable=True)
    is_tradeable_backtest = Column(Boolean, nullable=False, server_default="true")
    is_tradeable_live = Column(Boolean, nullable=False, server_default="false")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
