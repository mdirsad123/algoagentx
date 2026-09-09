from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..base import Base


class PriceAlert(Base):
    __tablename__ = "price_alerts"
    __table_args__ = (
        Index("idx_price_alerts_lookup", "provider", "symbol", "status"),
        Index("idx_price_alerts_user_status", "user_id", "status"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_account_id = Column(PG_UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    symbol = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=False, server_default="MT5", index=True)
    alert_type = Column(String(40), nullable=False)
    target_price = Column(Numeric(24, 10), nullable=True)
    zone_low = Column(Numeric(24, 10), nullable=True)
    zone_high = Column(Numeric(24, 10), nullable=True)
    direction = Column(String(20), nullable=True)
    status = Column(String(30), nullable=False, server_default="ACTIVE", index=True)
    runtime_state = Column(String(30), nullable=False, server_default="ARMED", index=True)
    trigger_mode = Column(String(20), nullable=False, server_default="ONCE")
    cooldown_seconds = Column(Integer, nullable=False, server_default="60")
    rearm_distance = Column(Numeric(24, 10), nullable=False, server_default="0")
    rearm_type = Column(String(40), nullable=False, server_default="DISTANCE_AND_COOLDOWN")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    telegram_enabled = Column(Boolean, nullable=False, server_default="true")
    browser_enabled = Column(Boolean, nullable=False, server_default="false")
    whatsapp_enabled = Column(Boolean, nullable=False, server_default="false")
    last_price = Column(Numeric(24, 10), nullable=True)
    last_market_timestamp = Column(DateTime(timezone=True), nullable=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    rearm_eligible_at = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(Integer, nullable=False, server_default="0")
    trigger_sequence = Column(Integer, nullable=False, server_default="0")
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", lazy="joined")
    broker_account = relationship("BrokerAccount", lazy="joined")


class AlertEvent(Base):
    __tablename__ = "alert_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_alert_events_idempotency_key"),
        Index("idx_alert_events_user_created", "user_id", "created_at"),
        Index("idx_alert_events_alert_created", "alert_id", "created_at"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(PG_UUID(as_uuid=True), ForeignKey("price_alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    condition_type = Column(String(40), nullable=False)
    trigger_price = Column(Numeric(24, 10), nullable=False)
    previous_price = Column(Numeric(24, 10), nullable=True)
    market_timestamp = Column(DateTime(timezone=True), nullable=True)
    server_received_at = Column(DateTime(timezone=True), nullable=False)
    condition_detected_at = Column(DateTime(timezone=True), nullable=False)
    notification_queued_at = Column(DateTime(timezone=True), nullable=True)
    notification_sent_at = Column(DateTime(timezone=True), nullable=True)
    notification_response_at = Column(DateTime(timezone=True), nullable=True)
    telegram_status = Column(String(30), nullable=False, server_default="PENDING")
    browser_status = Column(String(30), nullable=False, server_default="DISABLED")
    whatsapp_status = Column(String(30), nullable=False, server_default="DISABLED")
    feed_to_server_latency_ms = Column(Integer, nullable=True)
    evaluation_latency_ms = Column(Integer, nullable=True)
    notification_api_latency_ms = Column(Integer, nullable=True)
    total_internal_latency_ms = Column(Integer, nullable=True)
    idempotency_key = Column(String(255), nullable=False)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    alert = relationship("PriceAlert", lazy="joined")


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint("alert_event_id", "channel", name="uq_alert_delivery_event_channel"),
        Index("idx_notification_deliveries_due", "status", "next_attempt_at"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_event_id = Column(PG_UUID(as_uuid=True), ForeignKey("alert_events.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False, server_default="PENDING", index=True)
    attempt = Column(Integer, nullable=False, server_default="0")
    requested_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)
    response_code = Column(Integer, nullable=True)
    provider_message_id = Column(String(255), nullable=True)
    error = Column(Text, nullable=True)
    response_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    event = relationship("AlertEvent", lazy="joined")


class UserNotificationChannel(Base):
    __tablename__ = "user_notification_channels"
    __table_args__ = (
        UniqueConstraint("user_id", "channel", name="uq_user_notification_channel"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(30), nullable=False)
    external_recipient_id = Column(String(255), nullable=False)
    enabled = Column(Boolean, nullable=False, server_default="true")
    verified = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AlertFeedHealth(Base):
    __tablename__ = "alert_feed_health"
    __table_args__ = (
        UniqueConstraint("provider", "broker_account_id", name="uq_alert_feed_health_provider_account"),
        Index("idx_alert_feed_health_provider_account", "provider", "broker_account_id"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False, index=True)
    broker_account_id = Column(PG_UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=True, index=True)
    status = Column(String(30), nullable=False, server_default="DISCONNECTED")
    last_tick_at = Column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    last_reconnect_at = Column(DateTime(timezone=True), nullable=True)
    connection_error = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
