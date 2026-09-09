import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import Base

MONEY = Numeric(20, 8)
PCT = Numeric(18, 10)


class FundedLiveState(Base):
    __tablename__ = "funded_live_states"
    __table_args__ = (
        UniqueConstraint("deployment_id", name="uq_funded_live_states_deployment"),
        Index("idx_funded_live_states_status", "guard_status"),
        Index("idx_funded_live_states_rule_date", "rule_date"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="CASCADE"), nullable=False)
    guard_status = Column(String(40), nullable=False, server_default="NOT_INITIALIZED")
    guard_reason = Column(Text, nullable=True)
    rule_date = Column(Date, nullable=True)
    rule_timezone = Column(String(100), nullable=False, server_default="UTC")
    daily_reset_time = Column(String(8), nullable=False, server_default="00:00")
    initial_account_size = Column(MONEY, nullable=False)
    phase_number = Column(Integer, nullable=True)
    phase_start_balance = Column(MONEY, nullable=True)
    phase_start_equity = Column(MONEY, nullable=True)
    day_start_balance = Column(MONEY, nullable=True)
    day_start_equity = Column(MONEY, nullable=True)
    high_water_balance = Column(MONEY, nullable=True)
    high_water_equity = Column(MONEY, nullable=True)
    last_balance = Column(MONEY, nullable=True)
    last_equity = Column(MONEY, nullable=True)
    last_free_margin = Column(MONEY, nullable=True)
    daily_floor = Column(MONEY, nullable=True)
    max_loss_floor = Column(MONEY, nullable=True)
    remaining_daily_capacity = Column(MONEY, nullable=True)
    remaining_max_capacity = Column(MONEY, nullable=True)
    account_return_pct = Column(PCT, nullable=False, server_default="0")
    selected_risk_tier_name = Column(String(120), nullable=True)
    selected_risk_tier_sort_order = Column(Integer, nullable=True)
    requested_risk_pct = Column(PCT, nullable=True)
    requested_risk_amount = Column(MONEY, nullable=True)
    effective_risk_pct = Column(PCT, nullable=True)
    effective_risk_amount = Column(MONEY, nullable=True)
    limiting_rule = Column(String(80), nullable=True)
    trading_days = Column(Integer, nullable=False, server_default="0")
    qualifying_days = Column(Integer, nullable=False, server_default="0")
    target_balance = Column(MONEY, nullable=True)
    target_progress_pct = Column(PCT, nullable=True)
    target_reached_at = Column(DateTime(timezone=True), nullable=True)
    payout_eligible_at = Column(DateTime(timezone=True), nullable=True)
    payout_ready_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    last_evaluated_at = Column(DateTime(timezone=True), nullable=True)
    warning_state_json = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    deployment = relationship("StrategyDeployment", lazy="joined")


class FundedLiveDailySnapshot(Base):
    __tablename__ = "funded_live_daily_snapshots"
    __table_args__ = (
        UniqueConstraint("deployment_id", "rule_date", name="uq_funded_live_daily_deployment_date"),
        Index("idx_funded_live_daily_deployment_date", "deployment_id", "rule_date"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="CASCADE"), nullable=False)
    rule_date = Column(Date, nullable=False)
    start_balance = Column(MONEY, nullable=False)
    start_equity = Column(MONEY, nullable=False)
    end_balance = Column(MONEY, nullable=True)
    end_equity = Column(MONEY, nullable=True)
    peak_balance = Column(MONEY, nullable=True)
    peak_equity = Column(MONEY, nullable=True)
    low_equity = Column(MONEY, nullable=True)
    day_realized_pnl = Column(MONEY, nullable=False, server_default="0")
    day_unrealized_pnl = Column(MONEY, nullable=False, server_default="0")
    day_total_pnl = Column(MONEY, nullable=False, server_default="0")
    daily_drawdown_amount = Column(MONEY, nullable=False, server_default="0")
    daily_drawdown_pct = Column(PCT, nullable=False, server_default="0")
    trades_count = Column(Integer, nullable=False, server_default="0")
    winning_trades = Column(Integer, nullable=False, server_default="0")
    losing_trades = Column(Integer, nullable=False, server_default="0")
    qualifying_day = Column(Boolean, nullable=False, server_default="false")
    qualifying_profit_threshold = Column(MONEY, nullable=True)
    consistency_pct = Column(PCT, nullable=True)
    state = Column(String(40), nullable=False, server_default="RUNNING")
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class FundedLiveEvent(Base):
    __tablename__ = "funded_live_events"
    __table_args__ = (
        Index("idx_funded_live_events_deployment_time", "deployment_id", "event_timestamp"),
        Index("idx_funded_live_events_type", "event_type"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="CASCADE"), nullable=False)
    event_timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    event_type = Column(String(80), nullable=False)
    severity = Column(String(20), nullable=False, server_default="INFO")
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FundedLiveRiskDecision(Base):
    __tablename__ = "funded_live_risk_decisions"
    __table_args__ = (
        Index("idx_funded_live_risk_deployment_time", "deployment_id", "evaluated_at"),
        Index("idx_funded_live_risk_signal", "signal_id"),
        Index("idx_funded_live_risk_order", "order_id"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="CASCADE"), nullable=False)
    signal_id = Column(PG_UUID(as_uuid=True), ForeignKey("live_signals.id", ondelete="SET NULL"), nullable=True)
    order_id = Column(PG_UUID(as_uuid=True), ForeignKey("live_orders.id", ondelete="SET NULL"), nullable=True)
    evaluated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    balance = Column(MONEY, nullable=True)
    equity = Column(MONEY, nullable=True)
    daily_floor = Column(MONEY, nullable=True)
    max_floor = Column(MONEY, nullable=True)
    remaining_daily_capacity = Column(MONEY, nullable=True)
    remaining_max_capacity = Column(MONEY, nullable=True)
    risk_mode = Column(String(20), nullable=True)
    risk_tier = Column(String(120), nullable=True)
    requested_risk_pct = Column(PCT, nullable=True)
    requested_risk_amount = Column(MONEY, nullable=True)
    effective_risk_pct = Column(PCT, nullable=True)
    effective_risk_amount = Column(MONEY, nullable=True)
    limiting_rule = Column(String(80), nullable=True)
    allowed = Column(Boolean, nullable=False, server_default="false")
    reason = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
