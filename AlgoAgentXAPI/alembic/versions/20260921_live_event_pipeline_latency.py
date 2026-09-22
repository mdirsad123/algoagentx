"""event-driven live pipeline latency trace

Revision ID: 20260921_live_event_pipeline
Revises: remove_live_trading_approvals_table, 20260910_alert_approach_phase2a,
         20260421_billing_schema_contract_compat
Create Date: 2026-09-21

The three-parent down revision intentionally merges the repository's existing
Alembic heads before applying this additive live-trading migration.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260921_live_event_pipeline"
down_revision = (
    "remove_live_trading_approvals_table",
    "20260910_alert_approach_phase2a",
    "20260421_billing_schema_contract_compat",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("live_signals", sa.Column("trace_id", sa.String(length=160), nullable=True))
    op.create_index("ix_live_signals_trace_id", "live_signals", ["trace_id"], unique=False)
    op.add_column("live_orders", sa.Column("trace_id", sa.String(length=160), nullable=True))
    op.create_index("ix_live_orders_trace_id", "live_orders", ["trace_id"], unique=False)

    op.create_table(
        "live_execution_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("trace_id", sa.String(length=160), nullable=False),
        sa.Column("deployment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("broker_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("candle_open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_close_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=50), server_default="CTRADER", nullable=False),
        sa.Column("environment", sa.String(length=20), nullable=True),
        sa.Column("symbol", sa.String(length=100), nullable=False),
        sa.Column("timeframe", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="STARTED", nullable=False),
        sa.Column("signal_type", sa.String(length=20), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("t0_expected_close_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("t1_broker_event_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t2_candle_normalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t3_candle_db_commit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t4_redis_event_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t5_strategy_event_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t6_strategy_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t7_strategy_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t8_signal_persisted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t9_execution_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t10_risk_checks_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t11_order_request_queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t12_order_request_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t13_broker_order_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t14_broker_fill_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t15_local_order_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t16_local_position_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("t17_ui_event_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("perf_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["broker_account_id"], ["broker_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deployment_id"], ["strategy_deployments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["live_orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["live_signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deployment_id", "candle_open_time", name="uq_live_execution_trace_deployment_candle"),
        sa.UniqueConstraint("trace_id", name="uq_live_execution_traces_trace_id"),
    )
    op.create_index("idx_live_execution_traces_deployment_created", "live_execution_traces", ["deployment_id", "created_at"], unique=False)
    op.create_index("idx_live_execution_traces_deployment_close", "live_execution_traces", ["deployment_id", "expected_close_at"], unique=False)
    op.create_index("idx_live_execution_traces_status", "live_execution_traces", ["status"], unique=False)
    op.create_table(
        "live_broker_order_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("client_order_id", sa.String(length=50), nullable=False),
        sa.Column("deployment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("broker_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="RESERVED", nullable=False),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["deployment_id"], ["strategy_deployments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["broker_account_id"], ["broker_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_live_broker_order_intents_key"),
    )
    op.create_index("idx_live_broker_order_intents_deployment_created", "live_broker_order_intents", ["deployment_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_live_broker_order_intents_deployment_created", table_name="live_broker_order_intents")
    op.drop_table("live_broker_order_intents")
    op.drop_index("idx_live_execution_traces_status", table_name="live_execution_traces")
    op.drop_index("idx_live_execution_traces_deployment_close", table_name="live_execution_traces")
    op.drop_index("idx_live_execution_traces_deployment_created", table_name="live_execution_traces")
    op.drop_table("live_execution_traces")
    op.drop_index("ix_live_orders_trace_id", table_name="live_orders")
    op.drop_column("live_orders", "trace_id")
    op.drop_index("ix_live_signals_trace_id", table_name="live_signals")
    op.drop_column("live_signals", "trace_id")
