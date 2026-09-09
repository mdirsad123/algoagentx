"""funded live trading guard and runtime state

Revision ID: 20260903_funded_live_trading_guard
Revises: 20260823_funded_backtest_foundation
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260903_funded_live_trading_guard"
down_revision = "20260823_funded_backtest_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("strategy_deployments", sa.Column("account_policy_type", sa.String(length=20), nullable=False, server_default="STANDARD"))
    op.add_column("strategy_deployments", sa.Column("funded_profile_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("strategy_deployments", sa.Column("funded_profile_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("strategy_deployments", sa.Column("funded_risk_plan_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("strategy_deployments", sa.Column("funded_risk_mode", sa.String(length=20), nullable=True))
    op.add_column("strategy_deployments", sa.Column("funded_fixed_risk_pct", sa.Numeric(18, 10), nullable=True))
    op.add_column("strategy_deployments", sa.Column("funded_safety_buffer_pct", sa.Numeric(18, 10), nullable=True, server_default="0"))
    op.add_column("strategy_deployments", sa.Column("funded_configured_max_risk_pct", sa.Numeric(18, 10), nullable=True))
    op.add_column("strategy_deployments", sa.Column("funded_phase_number", sa.Integer(), nullable=True))
    op.add_column("strategy_deployments", sa.Column("funded_attach_mode", sa.String(length=30), nullable=True))
    op.add_column("strategy_deployments", sa.Column("funded_initialization_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_foreign_key(
        "fk_strategy_deployments_funded_profile",
        "strategy_deployments", "funded_account_profiles",
        ["funded_profile_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index("ix_strategy_deployments_account_policy_type", "strategy_deployments", ["account_policy_type"])
    op.create_index("ix_strategy_deployments_funded_profile_id", "strategy_deployments", ["funded_profile_id"])

    op.create_table(
        "funded_live_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deployment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("guard_status", sa.String(40), nullable=False, server_default="NOT_INITIALIZED"),
        sa.Column("guard_reason", sa.Text(), nullable=True),
        sa.Column("rule_date", sa.Date(), nullable=True),
        sa.Column("rule_timezone", sa.String(100), nullable=False, server_default="UTC"),
        sa.Column("daily_reset_time", sa.String(8), nullable=False, server_default="00:00"),
        sa.Column("initial_account_size", sa.Numeric(20, 8), nullable=False),
        sa.Column("phase_number", sa.Integer(), nullable=True),
        sa.Column("phase_start_balance", sa.Numeric(20, 8), nullable=True),
        sa.Column("phase_start_equity", sa.Numeric(20, 8), nullable=True),
        sa.Column("day_start_balance", sa.Numeric(20, 8), nullable=True),
        sa.Column("day_start_equity", sa.Numeric(20, 8), nullable=True),
        sa.Column("high_water_balance", sa.Numeric(20, 8), nullable=True),
        sa.Column("high_water_equity", sa.Numeric(20, 8), nullable=True),
        sa.Column("last_balance", sa.Numeric(20, 8), nullable=True),
        sa.Column("last_equity", sa.Numeric(20, 8), nullable=True),
        sa.Column("last_free_margin", sa.Numeric(20, 8), nullable=True),
        sa.Column("daily_floor", sa.Numeric(20, 8), nullable=True),
        sa.Column("max_loss_floor", sa.Numeric(20, 8), nullable=True),
        sa.Column("remaining_daily_capacity", sa.Numeric(20, 8), nullable=True),
        sa.Column("remaining_max_capacity", sa.Numeric(20, 8), nullable=True),
        sa.Column("account_return_pct", sa.Numeric(18, 10), nullable=False, server_default="0"),
        sa.Column("selected_risk_tier_name", sa.String(120), nullable=True),
        sa.Column("selected_risk_tier_sort_order", sa.Integer(), nullable=True),
        sa.Column("requested_risk_pct", sa.Numeric(18, 10), nullable=True),
        sa.Column("requested_risk_amount", sa.Numeric(20, 8), nullable=True),
        sa.Column("effective_risk_pct", sa.Numeric(18, 10), nullable=True),
        sa.Column("effective_risk_amount", sa.Numeric(20, 8), nullable=True),
        sa.Column("limiting_rule", sa.String(80), nullable=True),
        sa.Column("trading_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qualifying_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_balance", sa.Numeric(20, 8), nullable=True),
        sa.Column("target_progress_pct", sa.Numeric(18, 10), nullable=True),
        sa.Column("target_reached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payout_eligible_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payout_ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("warning_state_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["deployment_id"], ["strategy_deployments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("deployment_id", name="uq_funded_live_states_deployment"),
    )
    op.create_index("idx_funded_live_states_status", "funded_live_states", ["guard_status"])
    op.create_index("idx_funded_live_states_rule_date", "funded_live_states", ["rule_date"])

    op.create_table(
        "funded_live_daily_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deployment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_date", sa.Date(), nullable=False),
        sa.Column("start_balance", sa.Numeric(20, 8), nullable=False),
        sa.Column("start_equity", sa.Numeric(20, 8), nullable=False),
        sa.Column("end_balance", sa.Numeric(20, 8), nullable=True),
        sa.Column("end_equity", sa.Numeric(20, 8), nullable=True),
        sa.Column("peak_balance", sa.Numeric(20, 8), nullable=True),
        sa.Column("peak_equity", sa.Numeric(20, 8), nullable=True),
        sa.Column("low_equity", sa.Numeric(20, 8), nullable=True),
        sa.Column("day_realized_pnl", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("day_unrealized_pnl", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("day_total_pnl", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("daily_drawdown_amount", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("daily_drawdown_pct", sa.Numeric(18, 10), nullable=False, server_default="0"),
        sa.Column("trades_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("winning_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losing_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qualifying_day", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("qualifying_profit_threshold", sa.Numeric(20, 8), nullable=True),
        sa.Column("consistency_pct", sa.Numeric(18, 10), nullable=True),
        sa.Column("state", sa.String(40), nullable=False, server_default="RUNNING"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["deployment_id"], ["strategy_deployments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("deployment_id", "rule_date", name="uq_funded_live_daily_deployment_date"),
    )
    op.create_index("idx_funded_live_daily_deployment_date", "funded_live_daily_snapshots", ["deployment_id", "rule_date"])

    op.create_table(
        "funded_live_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deployment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="INFO"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["deployment_id"], ["strategy_deployments.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_funded_live_events_deployment_time", "funded_live_events", ["deployment_id", "event_timestamp"])
    op.create_index("idx_funded_live_events_type", "funded_live_events", ["event_type"])

    op.create_table(
        "funded_live_risk_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deployment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("balance", sa.Numeric(20, 8), nullable=True),
        sa.Column("equity", sa.Numeric(20, 8), nullable=True),
        sa.Column("daily_floor", sa.Numeric(20, 8), nullable=True),
        sa.Column("max_floor", sa.Numeric(20, 8), nullable=True),
        sa.Column("remaining_daily_capacity", sa.Numeric(20, 8), nullable=True),
        sa.Column("remaining_max_capacity", sa.Numeric(20, 8), nullable=True),
        sa.Column("risk_mode", sa.String(20), nullable=True),
        sa.Column("risk_tier", sa.String(120), nullable=True),
        sa.Column("requested_risk_pct", sa.Numeric(18, 10), nullable=True),
        sa.Column("requested_risk_amount", sa.Numeric(20, 8), nullable=True),
        sa.Column("effective_risk_pct", sa.Numeric(18, 10), nullable=True),
        sa.Column("effective_risk_amount", sa.Numeric(20, 8), nullable=True),
        sa.Column("limiting_rule", sa.String(80), nullable=True),
        sa.Column("allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["deployment_id"], ["strategy_deployments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["live_signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["live_orders.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_funded_live_risk_deployment_time", "funded_live_risk_decisions", ["deployment_id", "evaluated_at"])
    op.create_index("idx_funded_live_risk_signal", "funded_live_risk_decisions", ["signal_id"])
    op.create_index("idx_funded_live_risk_order", "funded_live_risk_decisions", ["order_id"])


def downgrade():
    op.drop_index("idx_funded_live_risk_order", table_name="funded_live_risk_decisions")
    op.drop_index("idx_funded_live_risk_signal", table_name="funded_live_risk_decisions")
    op.drop_index("idx_funded_live_risk_deployment_time", table_name="funded_live_risk_decisions")
    op.drop_table("funded_live_risk_decisions")
    op.drop_index("idx_funded_live_events_type", table_name="funded_live_events")
    op.drop_index("idx_funded_live_events_deployment_time", table_name="funded_live_events")
    op.drop_table("funded_live_events")
    op.drop_index("idx_funded_live_daily_deployment_date", table_name="funded_live_daily_snapshots")
    op.drop_table("funded_live_daily_snapshots")
    op.drop_index("idx_funded_live_states_rule_date", table_name="funded_live_states")
    op.drop_index("idx_funded_live_states_status", table_name="funded_live_states")
    op.drop_table("funded_live_states")

    op.drop_index("ix_strategy_deployments_funded_profile_id", table_name="strategy_deployments")
    op.drop_index("ix_strategy_deployments_account_policy_type", table_name="strategy_deployments")
    op.drop_constraint("fk_strategy_deployments_funded_profile", "strategy_deployments", type_="foreignkey")
    for name in [
        "funded_initialization_json", "funded_attach_mode", "funded_phase_number",
        "funded_configured_max_risk_pct", "funded_safety_buffer_pct", "funded_fixed_risk_pct",
        "funded_risk_mode", "funded_risk_plan_snapshot", "funded_profile_snapshot",
        "funded_profile_id", "account_policy_type",
    ]:
        op.drop_column("strategy_deployments", name)
