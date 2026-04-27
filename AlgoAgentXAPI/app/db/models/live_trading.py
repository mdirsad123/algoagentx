from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import Base


class BrokerAccount(Base):
    __tablename__ = "broker_accounts"
    __table_args__ = (
        Index("idx_broker_accounts_user_status", "user_id", "status"),
        Index("idx_broker_accounts_user_mode", "user_id", "mode"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_name = Column(String(50), nullable=False, server_default="MT5")
    account_label = Column(String(255), nullable=False)
    mode = Column(String(20), nullable=False, server_default="DEMO", index=True)
    status = Column(String(30), nullable=False, server_default="DISCONNECTED", index=True)
    server_name = Column(String(255), nullable=True)
    login_id = Column(String(255), nullable=True)
    encrypted_password = Column(Text, nullable=True)
    encrypted_token = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=False, server_default="{}")
    last_connected_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", lazy="joined")


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


class PlatformTradingSettings(Base):
    __tablename__ = "platform_trading_settings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    paper_trading_enabled = Column(Boolean, nullable=False, server_default="true")
    demo_trading_enabled = Column(Boolean, nullable=False, server_default="true")
    live_trading_enabled = Column(Boolean, nullable=False, server_default="false")
    global_kill_switch = Column(Boolean, nullable=False, server_default="false")
    max_global_demo_orders_per_day = Column(Integer, nullable=True)
    max_user_demo_orders_per_day = Column(Integer, nullable=True)
    updated_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    updated_by_user = relationship("User", lazy="joined")
