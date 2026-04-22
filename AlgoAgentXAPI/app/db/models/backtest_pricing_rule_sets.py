from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from ..base import Base
import uuid


class BacktestPricingRuleSet(Base):
    __tablename__ = "backtest_pricing_rule_sets"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    version = Column(String(40), nullable=False, default="v1")
    description = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, default=False)
    is_locked = Column(Boolean, nullable=False, default=False)

    base_cost = Column(Numeric(10, 2), nullable=False, default=2)
    range_days_step = Column(Integer, nullable=False, default=30)
    min_credit_charge = Column(Integer, nullable=False, default=1)
    max_credit_charge = Column(Integer, nullable=True)

    # rule json payloads
    # [{"max_days": 30, "multiplier": 1.0}, ... , {"max_days": null, "multiplier": 2.0}]
    date_range_buckets = Column(JSON, nullable=False)
    # [{"max_minutes": 15, "multiplier": 1.5}, ... , {"max_minutes": null, "multiplier": 0.8}]
    timeframe_multipliers = Column(JSON, nullable=False)

    # optional extensions (kept disabled in v1 unless admin enables)
    strategy_complexity_enabled = Column(Boolean, nullable=False, default=False)
    strategy_complexity_step = Column(Numeric(10, 4), nullable=False, default=0)
    strategy_complexity_cap = Column(Numeric(10, 4), nullable=False, default=0)

    plan_discounts = Column(JSON, nullable=True)  # {"PRO": 0.05, "PREMIUM": 0.10}

    created_by = Column(String(36), nullable=True)
    updated_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
