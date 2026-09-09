"""real-time price alerting phase 1

Revision ID: 20260909_real_time_alerting_phase1
Revises: 20260903_funded_live_trading_guard
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260909_real_time_alerting_phase1"
down_revision = "20260903_funded_live_trading_guard"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "price_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("broker_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("symbol", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="MT5"),
        sa.Column("alert_type", sa.String(40), nullable=False),
        sa.Column("target_price", sa.Numeric(24, 10), nullable=True),
        sa.Column("zone_low", sa.Numeric(24, 10), nullable=True),
        sa.Column("zone_high", sa.Numeric(24, 10), nullable=True),
        sa.Column("direction", sa.String(20), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("runtime_state", sa.String(30), nullable=False, server_default="ARMED"),
        sa.Column("trigger_mode", sa.String(20), nullable=False, server_default="ONCE"),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("rearm_distance", sa.Numeric(24, 10), nullable=False, server_default="0"),
        sa.Column("rearm_type", sa.String(40), nullable=False, server_default="DISTANCE_AND_COOLDOWN"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("browser_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_price", sa.Numeric(24, 10), nullable=True),
        sa.Column("last_market_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rearm_eligible_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trigger_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_price_alerts_lookup", "price_alerts", ["provider", "symbol", "status"])
    op.create_index("idx_price_alerts_user_status", "price_alerts", ["user_id", "status"])
    op.create_index("ix_price_alerts_broker_account_id", "price_alerts", ["broker_account_id"])

    op.create_table(
        "alert_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("price_alerts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("condition_type", sa.String(40), nullable=False),
        sa.Column("trigger_price", sa.Numeric(24, 10), nullable=False),
        sa.Column("previous_price", sa.Numeric(24, 10), nullable=True),
        sa.Column("market_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("condition_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notification_queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notification_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notification_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("browser_status", sa.String(30), nullable=False, server_default="DISABLED"),
        sa.Column("whatsapp_status", sa.String(30), nullable=False, server_default="DISABLED"),
        sa.Column("feed_to_server_latency_ms", sa.Integer(), nullable=True),
        sa.Column("evaluation_latency_ms", sa.Integer(), nullable=True),
        sa.Column("notification_api_latency_ms", sa.Integer(), nullable=True),
        sa.Column("total_internal_latency_ms", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("idempotency_key", name="uq_alert_events_idempotency_key"),
    )
    op.create_index("idx_alert_events_user_created", "alert_events", ["user_id", "created_at"])
    op.create_index("idx_alert_events_alert_created", "alert_events", ["alert_id", "created_at"])

    op.create_table(
        "notification_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("alert_event_id", "channel", name="uq_alert_delivery_event_channel"),
    )
    op.create_index("idx_notification_deliveries_due", "notification_deliveries", ["status", "next_attempt_at"])

    op.create_table(
        "user_notification_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("external_recipient_id", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "channel", name="uq_user_notification_channel"),
    )

    op.create_table(
        "alert_feed_health",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("broker_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="DISCONNECTED"),
        sa.Column("last_tick_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reconnect_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connection_error", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "broker_account_id", name="uq_alert_feed_health_provider_account"),
    )
    op.create_index("idx_alert_feed_health_provider_account", "alert_feed_health", ["provider", "broker_account_id"])


def downgrade():
    op.drop_table("alert_feed_health")
    op.drop_table("user_notification_channels")
    op.drop_table("notification_deliveries")
    op.drop_table("alert_events")
    op.drop_table("price_alerts")
