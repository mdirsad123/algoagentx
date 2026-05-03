from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

BROKER_MODES = {"PAPER", "DEMO", "LIVE"}
BROKER_STATUSES = {"CONNECTED", "DISCONNECTED", "EXPIRED", "ERROR"}
DEPLOYMENT_STATUSES = {"DRAFT", "RUNNING", "PAUSED", "STOPPED", "ERROR"}
SIGNAL_SOURCES = {"TRADINGVIEW", "ENGINE", "MANUAL"}
SIGNAL_TYPES = {"BUY", "SELL", "EXIT", "HOLD"}
POSITION_SIDES = {"LONG", "SHORT"}
ORDER_SIDES = {"BUY", "SELL"}
ORDER_TYPES = {"MARKET", "LIMIT", "SL", "TARGET"}
ORDER_STATUSES = {"PENDING", "PLACED", "FILLED", "REJECTED", "CANCELLED", "ERROR"}
POSITION_STATUSES = {"OPEN", "CLOSED", "ERROR"}
LOG_LEVELS = {"INFO", "WARNING", "ERROR"}


def _upper(value: Optional[str]) -> Optional[str]:
    return value.upper().strip() if isinstance(value, str) else value


class LiveBaseModel(BaseModel):
    class Config:
        from_attributes = True
        orm_mode = True



class BrokerProviderBase(LiveBaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=255)
    market_type: str = Field(default="MULTI", max_length=50)
    auth_type: str = Field(default="PASSWORD", max_length=50)
    supports_paper: bool = True
    supports_demo: bool = False
    supports_live: bool = False
    supports_market_data: bool = False
    supports_orders: bool = False
    supports_websocket: bool = False
    is_enabled: bool = True
    admin_notes: Optional[str] = None
    config_schema: Optional[dict[str, Any]] = None

    @field_validator("code", "market_type", "auth_type")
    @classmethod
    def normalize_provider_enums(cls, value: str):
        return _upper(value) or value


class BrokerProviderCreate(BrokerProviderBase):
    pass


class BrokerProviderUpdate(LiveBaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    market_type: Optional[str] = None
    auth_type: Optional[str] = None
    supports_paper: Optional[bool] = None
    supports_demo: Optional[bool] = None
    supports_live: Optional[bool] = None
    supports_market_data: Optional[bool] = None
    supports_orders: Optional[bool] = None
    supports_websocket: Optional[bool] = None
    is_enabled: Optional[bool] = None
    admin_notes: Optional[str] = None
    config_schema: Optional[dict[str, Any]] = None

    @field_validator("code", "market_type", "auth_type")
    @classmethod
    def normalize_provider_update_enums(cls, value: Optional[str]):
        return _upper(value) if value is not None else value


class BrokerProviderOut(BrokerProviderBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

class UpstoxBrokerAccountCreate(LiveBaseModel):
    account_label: str = Field(default="Upstox India", min_length=2, max_length=255)
    client_id: str = Field(..., min_length=5, max_length=255)
    client_secret: str = Field(..., min_length=5, max_length=2000)
    redirect_uri: str = Field(default="http://localhost:8000/api/v1/broker-accounts/upstox/callback", min_length=10, max_length=1000)
    redirect_after: str = Field(default="/brokers", max_length=500)


class UpstoxConnectUrlOut(LiveBaseModel):
    auth_url: str
    state: str
    broker_account_id: Optional[UUID] = None


class BrokerOAuthStateOut(LiveBaseModel):
    id: UUID
    user_id: UUID
    broker_provider_code: str
    broker_account_id: Optional[UUID] = None
    state: str
    redirect_after: Optional[str] = None
    expires_at: datetime
    consumed_at: Optional[datetime] = None
    created_at: datetime


class BrokerAccountCreate(LiveBaseModel):
    broker_provider_id: Optional[UUID] = None
    broker_name: str = Field(default="MT5", max_length=50)
    broker_code: Optional[str] = None
    auth_type: Optional[str] = None
    account_label: str = Field(..., min_length=2, max_length=255)
    mode: str = Field(default="DEMO")
    status: str = Field(default="DISCONNECTED")
    server_name: Optional[str] = None
    login_id: Optional[str] = None
    oauth_client_id: Optional[str] = None
    encrypted_client_secret: Optional[str] = None
    oauth_redirect_uri: Optional[str] = None
    encrypted_password: Optional[str] = None
    encrypted_token: Optional[str] = None
    encrypted_refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("mode", "status")
    @classmethod
    def normalize_enums(cls, value: str, info):
        value = _upper(value)
        allowed = BROKER_MODES if info.field_name == "mode" else BROKER_STATUSES
        if value not in allowed:
            raise ValueError(f"Invalid {info.field_name}. Allowed: {sorted(allowed)}")
        return value


class BrokerAccountUpdate(LiveBaseModel):
    broker_provider_id: Optional[UUID] = None
    broker_name: Optional[str] = None
    broker_code: Optional[str] = None
    auth_type: Optional[str] = None
    account_label: Optional[str] = None
    mode: Optional[str] = None
    status: Optional[str] = None
    server_name: Optional[str] = None
    login_id: Optional[str] = None
    oauth_client_id: Optional[str] = None
    encrypted_client_secret: Optional[str] = None
    oauth_redirect_uri: Optional[str] = None
    encrypted_password: Optional[str] = None
    encrypted_token: Optional[str] = None
    encrypted_refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    metadata_json: Optional[dict[str, Any]] = None
    last_connected_at: Optional[datetime] = None

    @field_validator("mode", "status")
    @classmethod
    def normalize_enums(cls, value: Optional[str], info):
        if value is None:
            return value
        value = _upper(value)
        allowed = BROKER_MODES if info.field_name == "mode" else BROKER_STATUSES
        if value not in allowed:
            raise ValueError(f"Invalid {info.field_name}. Allowed: {sorted(allowed)}")
        return value


class BrokerAccountOut(LiveBaseModel):
    id: UUID
    user_id: UUID
    broker_provider_id: Optional[UUID] = None
    broker_name: str
    broker_code: Optional[str] = None
    auth_type: Optional[str] = None
    account_label: str
    mode: str
    status: str
    server_name: Optional[str] = None
    login_id: Optional[str] = None
    oauth_client_id: Optional[str] = None
    oauth_redirect_uri: Optional[str] = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    token_expires_at: Optional[datetime] = None
    last_connected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class StrategyDeploymentCreate(LiveBaseModel):
    strategy_id: str
    broker_account_id: Optional[UUID] = None
    name: str = Field(..., min_length=2, max_length=255)
    instrument: str = Field(..., min_length=1, max_length=100)
    broker_symbol: Optional[str] = None
    instrument_key: Optional[str] = None
    exchange: Optional[str] = None
    segment: Optional[str] = None
    timeframe: str = Field(..., min_length=1, max_length=50)
    mode: str = Field(default="PAPER")
    capital: Decimal = Decimal("100000")
    risk_per_trade: Decimal = Decimal("0.01")
    rr_ratio: Decimal = Decimal("2")
    price_risk_pct: Decimal = Decimal("0.002")
    max_daily_loss: Decimal = Decimal("5000")
    max_trades_per_day: int = 10
    max_open_positions: int = 1
    allow_short: bool = True
    auto_trade_enabled: bool = False
    auto_runner_enabled: bool = False
    mt5_demo_max_lot: Optional[Decimal] = None
    product_type: str = "MIS"
    order_variety: str = "REGULAR"
    quantity_mode: str = "RISK_BASED"
    fixed_quantity: Optional[Decimal] = None
    max_quantity: Optional[Decimal] = None
    max_order_value: Optional[Decimal] = None
    square_off_time: Optional[str] = None
    upstox_order_confirmed: bool = False
    tradingview_secret: Optional[str] = None

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str):
        value = _upper(value)
        if value not in BROKER_MODES:
            raise ValueError(f"Invalid mode. Allowed: {sorted(BROKER_MODES)}")
        return value


class StrategyDeploymentUpdate(LiveBaseModel):
    broker_account_id: Optional[UUID] = None
    name: Optional[str] = None
    instrument: Optional[str] = None
    broker_symbol: Optional[str] = None
    instrument_key: Optional[str] = None
    exchange: Optional[str] = None
    segment: Optional[str] = None
    timeframe: Optional[str] = None
    mode: Optional[str] = None
    status: Optional[str] = None
    capital: Optional[Decimal] = None
    risk_per_trade: Optional[Decimal] = None
    rr_ratio: Optional[Decimal] = None
    price_risk_pct: Optional[Decimal] = None
    max_daily_loss: Optional[Decimal] = None
    max_trades_per_day: Optional[int] = None
    max_open_positions: Optional[int] = None
    allow_short: Optional[bool] = None
    auto_trade_enabled: Optional[bool] = None
    auto_runner_enabled: Optional[bool] = None
    mt5_demo_max_lot: Optional[Decimal] = None
    product_type: Optional[str] = None
    order_variety: Optional[str] = None
    quantity_mode: Optional[str] = None
    fixed_quantity: Optional[Decimal] = None
    max_quantity: Optional[Decimal] = None
    max_order_value: Optional[Decimal] = None
    square_off_time: Optional[str] = None
    upstox_order_confirmed: Optional[bool] = None
    tradingview_secret: Optional[str] = None

    @field_validator("mode", "status")
    @classmethod
    def normalize_enums(cls, value: Optional[str], info):
        if value is None:
            return value
        value = _upper(value)
        allowed = BROKER_MODES if info.field_name == "mode" else DEPLOYMENT_STATUSES
        if value not in allowed:
            raise ValueError(f"Invalid {info.field_name}. Allowed: {sorted(allowed)}")
        return value


class StrategyDeploymentOut(LiveBaseModel):
    id: UUID
    user_id: UUID
    strategy_id: str
    broker_account_id: Optional[UUID] = None
    name: str
    instrument: str
    broker_symbol: Optional[str] = None
    instrument_key: Optional[str] = None
    exchange: Optional[str] = None
    segment: Optional[str] = None
    timeframe: str
    mode: str
    status: str
    capital: Decimal
    risk_per_trade: Decimal
    rr_ratio: Decimal
    price_risk_pct: Decimal
    max_daily_loss: Decimal
    max_trades_per_day: int
    max_open_positions: int
    allow_short: bool
    auto_trade_enabled: bool
    auto_runner_enabled: bool = False
    last_runner_at: Optional[datetime] = None
    last_processed_candle_time: Optional[datetime] = None
    last_broker_sync_at: Optional[datetime] = None
    live_sync_enabled: bool = False
    live_sync_interval_seconds: int = 10
    last_live_sync_at: Optional[datetime] = None
    live_sync_error_count: int = 0
    live_sync_last_error: Optional[str] = None
    live_approved: bool = False
    live_approved_at: Optional[datetime] = None
    runner_error_count: int = 0
    runner_last_error: Optional[str] = None
    mt5_demo_max_lot: Optional[Decimal] = None
    product_type: Optional[str] = "MIS"
    order_variety: Optional[str] = "REGULAR"
    quantity_mode: Optional[str] = "RISK_BASED"
    fixed_quantity: Optional[Decimal] = None
    max_quantity: Optional[Decimal] = None
    max_order_value: Optional[Decimal] = None
    square_off_time: Optional[str] = None
    upstox_order_confirmed: Optional[bool] = False
    tradingview_secret: Optional[str] = None
    webhook_url: str = "/api/v1/webhooks/tradingview"
    example_payload: dict[str, Any] = Field(default_factory=dict)
    last_signal_at: Optional[datetime] = None
    last_heartbeat_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class LiveSignalCreate(LiveBaseModel):
    deployment_id: UUID
    source: str = "MANUAL"
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    signal_type: str
    side: Optional[str] = None
    price: Optional[Decimal] = None
    candle_time: Optional[datetime] = None
    confidence: Optional[Decimal] = None
    reason: Optional[str] = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source", "signal_type", "side")
    @classmethod
    def normalize_enums(cls, value: Optional[str], info):
        if value is None:
            return value
        value = _upper(value)
        allowed_map = {"source": SIGNAL_SOURCES, "signal_type": SIGNAL_TYPES, "side": POSITION_SIDES}
        allowed = allowed_map[info.field_name]
        if value not in allowed:
            raise ValueError(f"Invalid {info.field_name}. Allowed: {sorted(allowed)}")
        return value


class LiveSignalOut(LiveBaseModel):
    id: UUID
    deployment_id: UUID
    user_id: UUID
    strategy_id: str
    source: str
    symbol: str
    timeframe: str
    signal_type: str
    side: Optional[str] = None
    price: Optional[Decimal] = None
    candle_time: Optional[datetime] = None
    confidence: Optional[Decimal] = None
    reason: Optional[str] = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    status: str
    rejection_reason: Optional[str] = None
    created_at: datetime


class BrokerOrderEventOut(LiveBaseModel):
    id: UUID
    broker_provider_code: str
    broker_account_id: Optional[UUID] = None
    deployment_id: Optional[UUID] = None
    broker_order_id: Optional[str] = None
    event_type: str
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    processed: bool = False
    created_at: datetime


class LiveOrderOut(LiveBaseModel):
    id: UUID
    deployment_id: UUID
    signal_id: Optional[UUID] = None
    user_id: UUID
    broker_account_id: Optional[UUID] = None
    broker_order_id: Optional[str] = None
    symbol: str
    side: str
    order_type: str
    qty: Decimal
    entry_price: Optional[Decimal] = None
    executed_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    target: Optional[Decimal] = None
    status: str
    error_message: Optional[str] = None
    raw_response: Optional[dict[str, Any]] = None
    quantity_mode: Optional[str] = None
    requested_lot: Optional[Decimal] = None
    final_lot: Optional[Decimal] = None
    requested_quantity: Optional[Decimal] = None
    final_quantity: Optional[Decimal] = None
    risk_amount: Optional[Decimal] = None
    actual_risk: Optional[Decimal] = None
    instrument_spec_snapshot: Optional[dict[str, Any]] = None
    runtime_config_snapshot: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class LivePositionOut(LiveBaseModel):
    id: UUID
    deployment_id: UUID
    user_id: UUID
    broker_account_id: Optional[UUID] = None
    symbol: str
    side: str
    qty: Decimal
    avg_entry_price: Decimal
    current_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    target: Optional[Decimal] = None
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class LiveTradeLogOut(LiveBaseModel):
    id: UUID
    deployment_id: UUID
    user_id: UUID
    event_type: str
    level: str
    message: str
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime


class LiveEquityPointOut(LiveBaseModel):
    id: UUID
    deployment_id: UUID
    user_id: UUID
    timestamp: datetime
    equity: Decimal
    balance: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    created_at: datetime


class ManualDeploymentSignalIn(LiveBaseModel):
    signal_type: Optional[str] = None
    signal: Optional[str] = None
    price: Decimal
    reason: Optional[str] = "Manual signal test"
    candle_time: Optional[datetime] = None

    @model_validator(mode="after")
    def normalize_signal_field(self):
        value = _upper(self.signal_type or self.signal)
        if value not in SIGNAL_TYPES:
            raise ValueError(f"Invalid signal. Allowed: {sorted(SIGNAL_TYPES)}")
        self.signal_type = value
        self.signal = value
        return self


class LiveDeploymentSummaryOut(LiveBaseModel):
    status: str
    mode: str
    today_pnl: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    open_positions_count: int
    orders_count_today: int
    signals_count_today: int
    equity: Decimal


class LiveMarketCandleOut(LiveBaseModel):
    id: UUID
    deployment_id: Optional[UUID] = None
    broker_account_id: Optional[UUID] = None
    symbol: str
    timeframe: str
    candle_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[Decimal] = None
    source: str = "MT5"
    is_closed: bool = True
    created_at: datetime
    updated_at: datetime


class LiveCandleSnapshotOut(LiveBaseModel):
    source: str = "MT5"
    symbol: str
    timeframe: str
    stored_count: int = 0
    latest_candle_time: Optional[datetime] = None
    latest_close: Optional[Decimal] = None
    candles: list[dict[str, Any]] = Field(default_factory=list)

class RunStrategyOnceIn(LiveBaseModel):
    execute: bool = True


class RunStrategyOnceOut(LiveBaseModel):
    success: bool
    deployment_id: str
    strategy_name: Optional[str] = None
    latest_candle_time: Optional[datetime] = None
    signal: Optional[str] = None
    executed: bool = False
    order_id: Optional[str] = None
    broker_order_id: Optional[str] = None
    signal_id: Optional[str] = None
    duplicate: bool = False
    message: str
    latest_runner_log: Optional[str] = None
    order_status: Optional[str] = None
    error_message: Optional[str] = None
    symbol: Optional[str] = None
