import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import Base

MONEY = Numeric(20, 8)
PCT = Numeric(18, 10)


class FundedAccountProfile(Base):
    __tablename__ = "funded_account_profiles"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    provider_name = Column(String(255), nullable=True)
    challenge_type = Column(String(40), nullable=False, index=True)
    account_size = Column(MONEY, nullable=False)
    account_currency = Column(String(12), nullable=False, server_default="USD")
    is_template = Column(Boolean, nullable=False, server_default="false", index=True)
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
    description = Column(Text, nullable=True)
    payout_config = Column(JSONB, nullable=True)
    rules_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    phases = relationship("FundedAccountPhase", cascade="all, delete-orphan", back_populates="profile", order_by="FundedAccountPhase.sequence")
    risk_tiers = relationship("FundedRiskTier", cascade="all, delete-orphan", back_populates="profile", order_by="FundedRiskTier.sort_order")

    __table_args__ = (
        Index("ix_funded_profiles_user_active", "user_id", "is_active"),
        Index("ix_funded_profiles_template_active", "is_template", "is_active"),
    )


class FundedAccountPhase(Base):
    __tablename__ = "funded_account_phases"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey("funded_account_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    phase_number = Column(Integer, nullable=False)
    phase_name = Column(String(120), nullable=False)
    profit_target_pct = Column(PCT, nullable=True)
    daily_drawdown_pct = Column(PCT, nullable=False)
    daily_drawdown_mode = Column(String(40), nullable=False)
    max_drawdown_pct = Column(PCT, nullable=False)
    max_drawdown_mode = Column(String(40), nullable=False)
    minimum_trading_days = Column(Integer, nullable=False, server_default="0")
    minimum_qualifying_day_profit_pct = Column(PCT, nullable=True)
    qualifying_day_mode = Column(String(30), nullable=False, server_default="ANY_TRADE_DAY")
    profit_target_required = Column(Boolean, nullable=False, server_default="true")
    reset_balance_after_pass = Column(Boolean, nullable=False, server_default="false")
    sequence = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    profile = relationship("FundedAccountProfile", back_populates="phases")

    __table_args__ = (
        UniqueConstraint("profile_id", "phase_number", name="uq_funded_phase_profile_number"),
        UniqueConstraint("profile_id", "sequence", name="uq_funded_phase_profile_sequence"),
    )


class FundedRiskTier(Base):
    __tablename__ = "funded_risk_tiers"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey("funded_account_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    sort_order = Column(Integer, nullable=False)
    min_account_return_pct = Column(PCT, nullable=True)
    max_account_return_pct = Column(PCT, nullable=True)
    risk_percent = Column(PCT, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    profile = relationship("FundedAccountProfile", back_populates="risk_tiers")

    __table_args__ = (UniqueConstraint("profile_id", "sort_order", name="uq_funded_risk_tier_order"),)


class FundedBacktestRun(Base):
    __tablename__ = "funded_backtest_runs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id = Column(PG_UUID(as_uuid=True), ForeignKey("funded_account_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)
    strategy_id = Column(String(64), ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False, index=True)
    timeframe = Column(String(30), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_capital = Column(MONEY, nullable=False)
    final_balance = Column(MONEY, nullable=True)
    final_equity = Column(MONEY, nullable=True)
    status = Column(String(40), nullable=False, server_default="PENDING", index=True)
    current_phase = Column(Integer, nullable=True)
    passed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    payout_eligible_at = Column(DateTime(timezone=True), nullable=True)
    calendar_days = Column(Integer, nullable=False, server_default="0")
    trading_days = Column(Integer, nullable=False, server_default="0")
    qualifying_days = Column(Integer, nullable=False, server_default="0")
    runtime_config_snapshot = Column(JSONB, nullable=False)
    instrument_spec_snapshot = Column(JSONB, nullable=False)
    funded_profile_snapshot = Column(JSONB, nullable=False)
    risk_plan_snapshot = Column(JSONB, nullable=False)
    summary_json = Column(JSONB, nullable=True)
    rule_engine_version = Column(String(40), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_funded_runs_user_created", "user_id", "created_at"),)


class FundedBacktestPhase(Base):
    __tablename__ = "funded_backtest_phases"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    funded_backtest_id = Column(PG_UUID(as_uuid=True), ForeignKey("funded_backtest_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    phase_number = Column(Integer, nullable=False)
    phase_name = Column(String(120), nullable=False)
    starting_at = Column(DateTime(timezone=True), nullable=True)
    ending_at = Column(DateTime(timezone=True), nullable=True)
    starting_balance = Column(MONEY, nullable=False)
    ending_balance = Column(MONEY, nullable=True)
    target_pct = Column(PCT, nullable=True)
    target_amount = Column(MONEY, nullable=True)
    target_reached = Column(Boolean, nullable=False, server_default="false")
    maximum_drawdown = Column(MONEY, nullable=True)
    worst_daily_drawdown = Column(MONEY, nullable=True)
    trading_days = Column(Integer, nullable=False, server_default="0")
    qualifying_days = Column(Integer, nullable=False, server_default="0")
    phase_status = Column(String(40), nullable=False, server_default="PENDING")
    passed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("funded_backtest_id", "phase_number", name="uq_funded_run_phase_number"),)


class FundedBacktestTrade(Base):
    __tablename__ = "funded_backtest_trades"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    funded_backtest_id = Column(PG_UUID(as_uuid=True), ForeignKey("funded_backtest_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    funded_phase_id = Column(PG_UUID(as_uuid=True), ForeignKey("funded_backtest_phases.id", ondelete="CASCADE"), nullable=True, index=True)
    source_trade_id = Column(String(64), nullable=True, index=True)
    trade_number = Column(Integer, nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False, index=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    side = Column(String(12), nullable=False)
    entry_price = Column(MONEY, nullable=False)
    exit_price = Column(MONEY, nullable=True)
    stop_loss = Column(MONEY, nullable=True)
    target = Column(MONEY, nullable=True)
    rr_ratio = Column(PCT, nullable=True)
    exit_type = Column(String(50), nullable=True)
    balance_before_trade = Column(MONEY, nullable=False)
    equity_before_trade = Column(MONEY, nullable=False)
    account_return_pct_before_trade = Column(PCT, nullable=False)
    selected_risk_tier_id = Column(PG_UUID(as_uuid=True), nullable=True)
    selected_risk_tier_name = Column(String(120), nullable=True)
    requested_risk_pct = Column(PCT, nullable=False)
    effective_risk_pct = Column(PCT, nullable=False)
    requested_risk_amount = Column(MONEY, nullable=False)
    actual_risk_amount = Column(MONEY, nullable=True)
    quantity_mode = Column(String(30), nullable=True)
    calculated_lot_size = Column(MONEY, nullable=True)
    calculated_quantity = Column(MONEY, nullable=True)
    pnl = Column(MONEY, nullable=True)
    r_multiple = Column(PCT, nullable=True)
    balance_after_trade = Column(MONEY, nullable=True)
    equity_after_trade = Column(MONEY, nullable=True)
    daily_pnl_after_trade = Column(MONEY, nullable=True)
    daily_dd_pct_used = Column(PCT, nullable=True)
    max_dd_pct_used = Column(PCT, nullable=True)
    qualifying_day_state = Column(String(40), nullable=True)
    consistency_contribution = Column(PCT, nullable=True)
    rule_event = Column(String(80), nullable=True)
    account_state_after_trade = Column(String(40), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("funded_backtest_id", "trade_number", name="uq_funded_trade_number"),)


class FundedBacktestDailySnapshot(Base):
    __tablename__ = "funded_backtest_daily_snapshots"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    funded_backtest_id = Column(PG_UUID(as_uuid=True), ForeignKey("funded_backtest_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    funded_phase_id = Column(PG_UUID(as_uuid=True), ForeignKey("funded_backtest_phases.id", ondelete="CASCADE"), nullable=True, index=True)
    trading_date = Column(Date, nullable=False)
    start_balance = Column(MONEY, nullable=False)
    start_equity = Column(MONEY, nullable=False)
    end_balance = Column(MONEY, nullable=False)
    end_equity = Column(MONEY, nullable=False)
    day_pnl = Column(MONEY, nullable=False)
    day_return_pct = Column(PCT, nullable=False)
    peak_equity = Column(MONEY, nullable=True)
    low_equity = Column(MONEY, nullable=True)
    daily_drawdown_amount = Column(MONEY, nullable=True)
    daily_drawdown_pct = Column(PCT, nullable=True)
    trades_count = Column(Integer, nullable=False, server_default="0")
    winning_trades = Column(Integer, nullable=False, server_default="0")
    losing_trades = Column(Integer, nullable=False, server_default="0")
    qualifying_day = Column(Boolean, nullable=False, server_default="false")
    qualifying_profit_threshold = Column(MONEY, nullable=True)
    consistency_pct = Column(PCT, nullable=True)
    state = Column(String(40), nullable=True)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("funded_backtest_id", "trading_date", name="uq_funded_daily_snapshot_date"),)


class FundedBacktestEvent(Base):
    __tablename__ = "funded_backtest_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    funded_backtest_id = Column(PG_UUID(as_uuid=True), ForeignKey("funded_backtest_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    funded_phase_id = Column(PG_UUID(as_uuid=True), ForeignKey("funded_backtest_phases.id", ondelete="CASCADE"), nullable=True, index=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    event_title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (Index("ix_funded_events_run_time", "funded_backtest_id", "event_timestamp"),)
