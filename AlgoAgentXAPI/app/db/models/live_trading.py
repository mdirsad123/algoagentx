from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import Base


class BrokerProvider(Base):
    __tablename__ = "broker_providers"
    __table_args__ = (
        UniqueConstraint("code", name="uq_broker_providers_code"),
        Index("idx_broker_providers_enabled", "is_enabled"),
        Index("idx_broker_providers_market", "market_type"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    market_type = Column(String(50), nullable=False, server_default="MULTI")
    auth_type = Column(String(50), nullable=False, server_default="PASSWORD")
    supports_paper = Column(Boolean, nullable=False, server_default="true")
    supports_demo = Column(Boolean, nullable=False, server_default="false")
    supports_live = Column(Boolean, nullable=False, server_default="false")
    supports_market_data = Column(Boolean, nullable=False, server_default="false")
    supports_orders = Column(Boolean, nullable=False, server_default="false")
    supports_websocket = Column(Boolean, nullable=False, server_default="false")
    is_enabled = Column(Boolean, nullable=False, server_default="true", index=True)
    admin_notes = Column(Text, nullable=True)
    config_schema = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class BrokerOAuthState(Base):
    __tablename__ = "broker_oauth_states"
    __table_args__ = (
        UniqueConstraint("state", name="uq_broker_oauth_states_state"),
        Index("idx_broker_oauth_states_user_provider", "user_id", "broker_provider_code"),
        Index("idx_broker_oauth_states_account", "broker_account_id"),
        Index("idx_broker_oauth_states_expires", "expires_at"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_provider_code = Column(String(50), nullable=False, index=True)
    broker_account_id = Column(PG_UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=True, index=True)
    state = Column(String(255), nullable=False, unique=True, index=True)
    redirect_after = Column(String(500), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", lazy="joined")
    broker_account = relationship("BrokerAccount", lazy="joined")


class BrokerAccount(Base):
    __tablename__ = "broker_accounts"
    __table_args__ = (
        Index("idx_broker_accounts_user_status", "user_id", "status"),
        Index("idx_broker_accounts_user_mode", "user_id", "mode"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_provider_id = Column(PG_UUID(as_uuid=True), ForeignKey("broker_providers.id", ondelete="SET NULL"), nullable=True, index=True)
    broker_name = Column(String(50), nullable=False, server_default="MT5")
    broker_code = Column(String(50), nullable=True, index=True)
    auth_type = Column(String(50), nullable=True)
    account_label = Column(String(255), nullable=False)
    mode = Column(String(20), nullable=False, server_default="DEMO", index=True)
    status = Column(String(30), nullable=False, server_default="DISCONNECTED", index=True)
    server_name = Column(String(255), nullable=True)
    login_id = Column(String(255), nullable=True)
    oauth_client_id = Column(String(255), nullable=True)
    encrypted_client_secret = Column(Text, nullable=True)
    oauth_redirect_uri = Column(String(1000), nullable=True)
    encrypted_password = Column(Text, nullable=True)
    encrypted_token = Column(Text, nullable=True)
    encrypted_refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(JSONB, nullable=False, server_default="{}")
    last_connected_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", lazy="joined")
    broker_provider = relationship("BrokerProvider", lazy="joined")


class BrokerInstrument(Base):
    __tablename__ = "broker_instruments"
    __table_args__ = (
        UniqueConstraint("broker_provider_code", "instrument_key", name="uq_broker_instruments_provider_key"),
        Index("idx_broker_instruments_provider_symbol", "broker_provider_code", "trading_symbol"),
        Index("idx_broker_instruments_search", "broker_provider_code", "exchange", "segment"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    broker_provider_code = Column(String(50), nullable=False, index=True)
    exchange = Column(String(50), nullable=True, index=True)
    trading_symbol = Column(String(100), nullable=False, index=True)
    instrument_key = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    segment = Column(String(80), nullable=True, index=True)
    lot_size = Column(Integer, nullable=True)
    tick_size = Column(Numeric(18, 8), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class StrategyDeployment(Base):
    __tablename__ = "strategy_deployments"
    __table_args__ = (
        Index("idx_strategy_deployments_user_status", "user_id", "status"),
        Index("idx_strategy_deployments_strategy", "strategy_id"),
        Index("idx_strategy_deployments_broker", "broker_account_id"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id = Column(String(64), ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False, index=True)
    broker_account_id = Column(PG_UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    instrument = Column(String(100), nullable=False, index=True)
    broker_symbol = Column(String(255), nullable=True, index=True)
    instrument_key = Column(String(255), nullable=True, index=True)
    exchange = Column(String(50), nullable=True)
    segment = Column(String(80), nullable=True)
    timeframe = Column(String(50), nullable=False)
    mode = Column(String(20), nullable=False, server_default="PAPER", index=True)
    status = Column(String(30), nullable=False, server_default="DRAFT", index=True)
    capital = Column(Numeric(18, 4), nullable=False, server_default="100000")
    risk_per_trade = Column(Numeric(10, 6), nullable=False, server_default="0.01")
    rr_ratio = Column(Numeric(10, 4), nullable=False, server_default="2")
    price_risk_pct = Column(Numeric(10, 6), nullable=False, server_default="0.002")
    max_daily_loss = Column(Numeric(18, 4), nullable=False, server_default="5000")
    max_trades_per_day = Column(Integer, nullable=False, server_default="10")
    max_open_positions = Column(Integer, nullable=False, server_default="1")
    allow_short = Column(Boolean, nullable=False, server_default="true")
    auto_trade_enabled = Column(Boolean, nullable=False, server_default="false")
    auto_runner_enabled = Column(Boolean, nullable=False, server_default="false", index=True)
    last_runner_at = Column(DateTime(timezone=True), nullable=True)
    last_processed_candle_time = Column(DateTime(timezone=True), nullable=True)
    last_broker_sync_at = Column(DateTime(timezone=True), nullable=True)
    live_sync_enabled = Column(Boolean, nullable=False, server_default="false", index=True)
    live_sync_interval_seconds = Column(Integer, nullable=False, server_default="10")
    last_live_sync_at = Column(DateTime(timezone=True), nullable=True)
    live_sync_error_count = Column(Integer, nullable=False, server_default="0")
    live_sync_last_error = Column(Text, nullable=True)
    live_approved = Column(Boolean, nullable=False, server_default="false", index=True)
    live_approved_at = Column(DateTime(timezone=True), nullable=True)
    runner_error_count = Column(Integer, nullable=False, server_default="0")
    runner_last_error = Column(Text, nullable=True)
    mt5_demo_max_lot = Column(Numeric(18, 8), nullable=True)
    product_type = Column(String(30), nullable=False, server_default="MIS")
    order_variety = Column(String(30), nullable=False, server_default="REGULAR")
    quantity_mode = Column(String(30), nullable=False, server_default="RISK_BASED")
    fixed_quantity = Column(Numeric(18, 8), nullable=True)
    max_quantity = Column(Numeric(18, 8), nullable=True)
    max_order_value = Column(Numeric(18, 4), nullable=True)
    square_off_time = Column(String(20), nullable=True)
    upstox_order_confirmed = Column(Boolean, nullable=False, server_default="false")
    tradingview_secret = Column(String(255), nullable=True)
    last_signal_at = Column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", lazy="joined")
    strategy = relationship("Strategy", lazy="joined")
    broker_account = relationship("BrokerAccount", lazy="joined")

    @property
    def webhook_url(self) -> str:
        return "/api/v1/webhooks/tradingview"

    @property
    def example_payload(self) -> dict:
        return {
            "secret": self.tradingview_secret or "USER_DEPLOYMENT_SECRET",
            "deployment_id": str(self.id) if self.id else "DEPLOYMENT_ID",
            "symbol": "{{ticker}}",
            "timeframe": "{{interval}}",
            "signal": "BUY",
            "price": "{{close}}",
            "time": "{{time}}",
            "reason": "TradingView alert",
        }


class LiveSignal(Base):
    __tablename__ = "live_signals"
    __table_args__ = (
        Index("idx_live_signals_deployment_created", "deployment_id", "created_at"),
        Index("idx_live_signals_user_created", "user_id", "created_at"),
        Index("idx_live_signals_status", "status"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_id = Column(String(64), ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False, index=True)
    source = Column(String(30), nullable=False, server_default="MANUAL")
    symbol = Column(String(100), nullable=False, index=True)
    timeframe = Column(String(50), nullable=False)
    signal_type = Column(String(20), nullable=False)
    side = Column(String(20), nullable=True)
    price = Column(Numeric(18, 8), nullable=True)
    candle_time = Column(DateTime(timezone=True), nullable=True)
    confidence = Column(Numeric(10, 6), nullable=True)
    reason = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=False, server_default="{}")
    status = Column(String(30), nullable=False, server_default="RECEIVED", index=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    deployment = relationship("StrategyDeployment", lazy="joined")


class BrokerOrderEvent(Base):
    __tablename__ = "broker_order_events"
    __table_args__ = (
        Index("idx_broker_order_events_provider_created", "broker_provider_code", "created_at"),
        Index("idx_broker_order_events_deployment_created", "deployment_id", "created_at"),
        Index("idx_broker_order_events_order", "broker_order_id"),
        Index("idx_broker_order_events_processed", "processed"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    broker_provider_code = Column(String(50), nullable=False, index=True)
    broker_account_id = Column(PG_UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="SET NULL"), nullable=True, index=True)
    broker_order_id = Column(String(255), nullable=True, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    raw_payload = Column(JSONB, nullable=False, server_default="{}")
    processed = Column(Boolean, nullable=False, server_default="false", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    broker_account = relationship("BrokerAccount", lazy="joined")
    deployment = relationship("StrategyDeployment", lazy="joined")


class LiveOrder(Base):
    __tablename__ = "live_orders"
    __table_args__ = (
        Index("idx_live_orders_deployment_created", "deployment_id", "created_at"),
        Index("idx_live_orders_user_status", "user_id", "status"),
        Index("idx_live_orders_signal", "signal_id"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="CASCADE"), nullable=False, index=True)
    signal_id = Column(PG_UUID(as_uuid=True), ForeignKey("live_signals.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_account_id = Column(PG_UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    broker_order_id = Column(String(255), nullable=True)
    symbol = Column(String(100), nullable=False, index=True)
    side = Column(String(20), nullable=False)
    order_type = Column(String(30), nullable=False, server_default="MARKET")
    qty = Column(Numeric(18, 8), nullable=False)
    entry_price = Column(Numeric(18, 8), nullable=True)
    executed_price = Column(Numeric(18, 8), nullable=True)
    stop_loss = Column(Numeric(18, 8), nullable=True)
    target = Column(Numeric(18, 8), nullable=True)
    status = Column(String(30), nullable=False, server_default="PENDING", index=True)
    error_message = Column(Text, nullable=True)
    raw_response = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class LivePosition(Base):
    __tablename__ = "live_positions"
    __table_args__ = (
        Index("idx_live_positions_deployment_status", "deployment_id", "status"),
        Index("idx_live_positions_user_status", "user_id", "status"),
        Index("idx_live_positions_symbol", "symbol"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_account_id = Column(PG_UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    symbol = Column(String(100), nullable=False, index=True)
    side = Column(String(20), nullable=False)
    qty = Column(Numeric(18, 8), nullable=False)
    avg_entry_price = Column(Numeric(18, 8), nullable=False)
    current_price = Column(Numeric(18, 8), nullable=True)
    stop_loss = Column(Numeric(18, 8), nullable=True)
    target = Column(Numeric(18, 8), nullable=True)
    unrealized_pnl = Column(Numeric(18, 4), nullable=False, server_default="0")
    realized_pnl = Column(Numeric(18, 4), nullable=False, server_default="0")
    status = Column(String(30), nullable=False, server_default="OPEN", index=True)
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class LiveTradeLog(Base):
    __tablename__ = "live_trade_logs"
    __table_args__ = (
        Index("idx_live_trade_logs_deployment_created", "deployment_id", "created_at"),
        Index("idx_live_trade_logs_user_created", "user_id", "created_at"),
        Index("idx_live_trade_logs_level", "level"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    level = Column(String(20), nullable=False, server_default="INFO", index=True)
    message = Column(Text, nullable=False)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LiveEquityPoint(Base):
    __tablename__ = "live_equity_points"
    __table_args__ = (
        Index("idx_live_equity_points_deployment_timestamp", "deployment_id", "timestamp"),
        Index("idx_live_equity_points_user_timestamp", "user_id", "timestamp"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    equity = Column(Numeric(18, 4), nullable=False)
    balance = Column(Numeric(18, 4), nullable=True)
    unrealized_pnl = Column(Numeric(18, 4), nullable=True)
    realized_pnl = Column(Numeric(18, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LiveMarketCandle(Base):
    __tablename__ = "live_market_candles"
    __table_args__ = (
        UniqueConstraint("deployment_id", "symbol", "timeframe", "candle_time", name="uq_live_market_candles_dep_symbol_tf_time"),
        Index("idx_live_market_candles_deployment_time", "deployment_id", "candle_time"),
        Index("idx_live_market_candles_symbol_tf_time", "symbol", "timeframe", "candle_time"),
        Index("idx_live_market_candles_broker_time", "broker_account_id", "candle_time"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="CASCADE"), nullable=True, index=True)
    broker_account_id = Column(PG_UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    symbol = Column(String(100), nullable=False, index=True)
    timeframe = Column(String(50), nullable=False, index=True)
    candle_time = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Numeric(18, 8), nullable=False)
    high = Column(Numeric(18, 8), nullable=False)
    low = Column(Numeric(18, 8), nullable=False)
    close = Column(Numeric(18, 8), nullable=False)
    volume = Column(Numeric(18, 8), nullable=True)
    source = Column(String(30), nullable=False, server_default="MT5")
    is_closed = Column(Boolean, nullable=False, server_default="true")
    raw_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    deployment = relationship("StrategyDeployment", lazy="joined")
    broker_account = relationship("BrokerAccount", lazy="joined")


class AdminLiveAction(Base):
    __tablename__ = "admin_live_actions"
    __table_args__ = (
        Index("idx_admin_live_actions_deployment_created", "deployment_id", "created_at"),
        Index("idx_admin_live_actions_admin_created", "admin_user_id", "created_at"),
        Index("idx_admin_live_actions_action", "action"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    admin_user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(80), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    admin_user = relationship("User", lazy="joined")
    deployment = relationship("StrategyDeployment", lazy="joined")


class LiveTradingApproval(Base):
    __tablename__ = "live_trading_approvals"
    __table_args__ = (
        Index("idx_live_trading_approvals_user_status", "user_id", "status"),
        Index("idx_live_trading_approvals_broker_status", "broker_account_id", "status"),
        Index("idx_live_trading_approvals_created", "created_at"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_account_id = Column(PG_UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    approved_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(30), nullable=False, server_default="PENDING", index=True)
    approved_markets = Column(JSONB, nullable=True)
    max_daily_loss = Column(Numeric(18, 4), nullable=True)
    max_order_value = Column(Numeric(18, 4), nullable=True)
    max_trades_per_day = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    risk_disclaimer_accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    broker_account = relationship("BrokerAccount", lazy="joined")
    approver = relationship("User", foreign_keys=[approved_by], lazy="joined")


class PlatformTradingSettings(Base):
    __tablename__ = "platform_trading_settings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    paper_trading_enabled = Column(Boolean, nullable=False, server_default="true")
    demo_trading_enabled = Column(Boolean, nullable=False, server_default="true")
    live_trading_enabled = Column(Boolean, nullable=False, server_default="false")
    global_kill_switch = Column(Boolean, nullable=False, server_default="false")
    max_global_demo_orders_per_day = Column(Integer, nullable=True)
    max_user_demo_orders_per_day = Column(Integer, nullable=True)
    upstox_order_execution_enabled = Column(Boolean, nullable=False, server_default="false")
    broker_auto_sync_enabled = Column(Boolean, nullable=False, server_default="true")
    min_broker_sync_interval_seconds = Column(Integer, nullable=False, server_default="5")
    default_broker_sync_interval_seconds = Column(Integer, nullable=False, server_default="10")
    max_broker_sync_interval_seconds = Column(Integer, nullable=False, server_default="300")
    updated_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    updated_by_user = relationship("User", lazy="joined")
