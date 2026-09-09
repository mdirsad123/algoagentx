from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

ALERT_TYPES = {"CROSSING_UP", "CROSSING_DOWN", "ENTERING_ZONE", "LEAVING_ZONE"}
TRIGGER_MODES = {"ONCE", "RECURRING"}
ALERT_STATUSES = {"ACTIVE", "DISABLED", "COMPLETED", "EXPIRED", "DELETED"}


class AlertBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(default="MT5", min_length=2, max_length=50)
    broker_account_id: UUID | None = None
    alert_type: str
    target_price: Decimal | None = None
    zone_low: Decimal | None = None
    zone_high: Decimal | None = None
    trigger_mode: str = "ONCE"
    cooldown_seconds: int = Field(default=60, ge=0, le=86400)
    rearm_distance: Decimal = Field(default=Decimal("0"), ge=0)
    rearm_type: str = "DISTANCE_AND_COOLDOWN"
    expires_at: datetime | None = None
    telegram_enabled: bool = True
    browser_enabled: bool = False
    whatsapp_enabled: bool = False
    metadata: dict[str, Any] | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str):
        # MT5 broker symbols may be case-sensitive and commonly include suffixes
        # such as XAUUSDm, XAUUSD.x or XAUUSD.a. Preserve the exact broker name.
        return value.strip()

    @field_validator("provider", "alert_type", "trigger_mode", "rearm_type")
    @classmethod
    def normalize_text(cls, value: str):
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_condition(self):
        if self.alert_type not in ALERT_TYPES:
            raise ValueError(f"Invalid alert_type. Allowed: {sorted(ALERT_TYPES)}")
        if self.trigger_mode not in TRIGGER_MODES:
            raise ValueError(f"Invalid trigger_mode. Allowed: {sorted(TRIGGER_MODES)}")
        if self.alert_type in {"CROSSING_UP", "CROSSING_DOWN"}:
            if self.target_price is None:
                raise ValueError("target_price is required for crossing alerts")
            self.zone_low = None
            self.zone_high = None
        else:
            if self.zone_low is None or self.zone_high is None:
                raise ValueError("zone_low and zone_high are required for zone alerts")
            if self.zone_low >= self.zone_high:
                raise ValueError("zone_low must be less than zone_high")
            self.target_price = None
        if self.browser_enabled or self.whatsapp_enabled:
            raise ValueError("Browser and WhatsApp channels are not enabled in Phase 1")
        return self


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    symbol: str | None = None
    provider: str | None = None
    broker_account_id: UUID | None = None
    alert_type: str | None = None
    target_price: Decimal | None = None
    zone_low: Decimal | None = None
    zone_high: Decimal | None = None
    trigger_mode: str | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0, le=86400)
    rearm_distance: Decimal | None = Field(default=None, ge=0)
    rearm_type: str | None = None
    expires_at: datetime | None = None
    telegram_enabled: bool | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_optional_symbol(cls, value: str | None):
        return value.strip() if isinstance(value, str) else value

    @field_validator("provider", "alert_type", "trigger_mode", "rearm_type")
    @classmethod
    def normalize_optional_text(cls, value: str | None):
        return value.strip().upper() if isinstance(value, str) else value


class AlertOut(BaseModel):
    id: UUID
    user_id: UUID
    broker_account_id: UUID | None = None
    symbol: str
    provider: str
    alert_type: str
    target_price: Decimal | None = None
    zone_low: Decimal | None = None
    zone_high: Decimal | None = None
    status: str
    runtime_state: str
    trigger_mode: str
    cooldown_seconds: int
    rearm_distance: Decimal
    rearm_type: str
    expires_at: datetime | None = None
    telegram_enabled: bool
    browser_enabled: bool
    whatsapp_enabled: bool
    last_price: Decimal | None = None
    last_market_timestamp: datetime | None = None
    last_triggered_at: datetime | None = None
    rearm_eligible_at: datetime | None = None
    trigger_count: int
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_json")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class AlertEventOut(BaseModel):
    id: UUID
    alert_id: UUID
    user_id: UUID
    symbol: str
    provider: str
    condition_type: str
    trigger_price: Decimal
    previous_price: Decimal | None = None
    market_timestamp: datetime | None = None
    server_received_at: datetime
    condition_detected_at: datetime
    notification_queued_at: datetime | None = None
    notification_sent_at: datetime | None = None
    notification_response_at: datetime | None = None
    telegram_status: str
    feed_to_server_latency_ms: int | None = None
    evaluation_latency_ms: int | None = None
    notification_api_latency_ms: int | None = None
    total_internal_latency_ms: int | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class TelegramChannelIn(BaseModel):
    chat_id: str = Field(..., min_length=1, max_length=255)
    enabled: bool = True


class TelegramChannelOut(BaseModel):
    configured: bool
    chat_id: str | None = None
    enabled: bool = False
    verified: bool = False
    using_global_fallback: bool = False


class AlertTestNotificationIn(BaseModel):
    chat_id: str | None = None


class MT5QuoteIn(BaseModel):
    symbol: str
    bid: Decimal | None = None
    ask: Decimal | None = None
    last: Decimal | None = None
    market_timestamp: datetime | None = None
    raw: dict[str, Any] | None = None

    @model_validator(mode="after")
    def ensure_price(self):
        if self.last is None and self.bid is None and self.ask is None:
            raise ValueError("At least one of last, bid or ask is required")
        return self


class MT5QuoteBatchIn(BaseModel):
    quotes: list[MT5QuoteIn] = Field(default_factory=list, max_length=500)
