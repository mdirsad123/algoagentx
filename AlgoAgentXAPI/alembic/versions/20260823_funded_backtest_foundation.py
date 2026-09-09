"""Add funded account backtest domain foundation.

Revision ID: 20260823_funded_backtest_foundation
Revises: current three repository heads
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260823_funded_backtest_foundation"
down_revision: Union[str, Sequence[str], None] = (
    "20260421_billing_schema_contract_compat",
    "add_market_data_index",
    "remove_live_trading_approvals_table",
)
branch_labels = None
depends_on = None

MONEY = sa.Numeric(20, 8)
PCT = sa.Numeric(18, 10)
UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    op.create_table(
        "funded_account_profiles",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider_name", sa.String(255), nullable=True),
        sa.Column("challenge_type", sa.String(40), nullable=False),
        sa.Column("account_size", MONEY, nullable=False),
        sa.Column("account_currency", sa.String(12), nullable=False, server_default="USD"),
        sa.Column("is_template", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("payout_config", JSONB, nullable=True),
        sa.Column("rules_json", JSONB, nullable=True),
        *timestamps(),
    )
    op.create_index("ix_funded_account_profiles_user_id", "funded_account_profiles", ["user_id"])
    op.create_index("ix_funded_account_profiles_challenge_type", "funded_account_profiles", ["challenge_type"])
    op.create_index("ix_funded_profiles_user_active", "funded_account_profiles", ["user_id", "is_active"])
    op.create_index("ix_funded_profiles_template_active", "funded_account_profiles", ["is_template", "is_active"])

    op.create_table(
        "funded_account_phases",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("profile_id", UUID, sa.ForeignKey("funded_account_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase_number", sa.Integer(), nullable=False),
        sa.Column("phase_name", sa.String(120), nullable=False),
        sa.Column("profit_target_pct", PCT, nullable=True),
        sa.Column("daily_drawdown_pct", PCT, nullable=False),
        sa.Column("daily_drawdown_mode", sa.String(40), nullable=False),
        sa.Column("max_drawdown_pct", PCT, nullable=False),
        sa.Column("max_drawdown_mode", sa.String(40), nullable=False),
        sa.Column("minimum_trading_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("minimum_qualifying_day_profit_pct", PCT, nullable=True),
        sa.Column("qualifying_day_mode", sa.String(30), nullable=False, server_default="ANY_TRADE_DAY"),
        sa.Column("profit_target_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reset_balance_after_pass", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sequence", sa.Integer(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("profile_id", "phase_number", name="uq_funded_phase_profile_number"),
        sa.UniqueConstraint("profile_id", "sequence", name="uq_funded_phase_profile_sequence"),
    )
    op.create_index("ix_funded_account_phases_profile_id", "funded_account_phases", ["profile_id"])

    op.create_table(
        "funded_risk_tiers",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("profile_id", UUID, sa.ForeignKey("funded_account_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("min_account_return_pct", PCT, nullable=True),
        sa.Column("max_account_return_pct", PCT, nullable=True),
        sa.Column("risk_percent", PCT, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *timestamps(),
        sa.UniqueConstraint("profile_id", "sort_order", name="uq_funded_risk_tier_order"),
    )
    op.create_index("ix_funded_risk_tiers_profile_id", "funded_risk_tiers", ["profile_id"])

    op.create_table(
        "funded_backtest_runs",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", UUID, sa.ForeignKey("funded_account_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("strategy_id", sa.String(64), sa.ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("instrument_id", sa.Integer(), sa.ForeignKey("instruments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("timeframe", sa.String(30), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("initial_capital", MONEY, nullable=False),
        sa.Column("final_balance", MONEY, nullable=True),
        sa.Column("final_equity", MONEY, nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="PENDING"),
        sa.Column("current_phase", sa.Integer(), nullable=True),
        sa.Column("passed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("payout_eligible_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calendar_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trading_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qualifying_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("runtime_config_snapshot", JSONB, nullable=False),
        sa.Column("instrument_spec_snapshot", JSONB, nullable=False),
        sa.Column("funded_profile_snapshot", JSONB, nullable=False),
        sa.Column("risk_plan_snapshot", JSONB, nullable=False),
        sa.Column("summary_json", JSONB, nullable=True),
        sa.Column("rule_engine_version", sa.String(40), nullable=False),
        *timestamps(),
    )
    for col in ("user_id", "profile_id", "strategy_id", "instrument_id", "status", "created_at"):
        op.create_index(f"ix_funded_backtest_runs_{col}", "funded_backtest_runs", [col])
    op.create_index("ix_funded_runs_user_created", "funded_backtest_runs", ["user_id", "created_at"])

    op.create_table(
        "funded_backtest_phases",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("funded_backtest_id", UUID, sa.ForeignKey("funded_backtest_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase_number", sa.Integer(), nullable=False), sa.Column("phase_name", sa.String(120), nullable=False),
        sa.Column("starting_at", sa.DateTime(timezone=True)), sa.Column("ending_at", sa.DateTime(timezone=True)),
        sa.Column("starting_balance", MONEY, nullable=False), sa.Column("ending_balance", MONEY),
        sa.Column("target_pct", PCT), sa.Column("target_amount", MONEY),
        sa.Column("target_reached", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("maximum_drawdown", MONEY), sa.Column("worst_daily_drawdown", MONEY),
        sa.Column("trading_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qualifying_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("phase_status", sa.String(40), nullable=False, server_default="PENDING"),
        sa.Column("passed_at", sa.DateTime(timezone=True)), sa.Column("failed_at", sa.DateTime(timezone=True)),
        sa.Column("failure_reason", sa.Text()), *timestamps(),
        sa.UniqueConstraint("funded_backtest_id", "phase_number", name="uq_funded_run_phase_number"),
    )
    op.create_index("ix_funded_backtest_phases_funded_backtest_id", "funded_backtest_phases", ["funded_backtest_id"])

    op.create_table(
        "funded_backtest_trades",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("funded_backtest_id", UUID, sa.ForeignKey("funded_backtest_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("funded_phase_id", UUID, sa.ForeignKey("funded_backtest_phases.id", ondelete="CASCADE")),
        sa.Column("source_trade_id", sa.String(64)), sa.Column("trade_number", sa.Integer(), nullable=False),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False), sa.Column("exit_time", sa.DateTime(timezone=True)),
        sa.Column("side", sa.String(12), nullable=False), sa.Column("entry_price", MONEY, nullable=False),
        sa.Column("exit_price", MONEY), sa.Column("stop_loss", MONEY), sa.Column("target", MONEY), sa.Column("rr_ratio", PCT), sa.Column("exit_type", sa.String(50)),
        sa.Column("balance_before_trade", MONEY, nullable=False), sa.Column("equity_before_trade", MONEY, nullable=False),
        sa.Column("account_return_pct_before_trade", PCT, nullable=False), sa.Column("selected_risk_tier_id", UUID), sa.Column("selected_risk_tier_name", sa.String(120)),
        sa.Column("requested_risk_pct", PCT, nullable=False), sa.Column("effective_risk_pct", PCT, nullable=False),
        sa.Column("requested_risk_amount", MONEY, nullable=False), sa.Column("actual_risk_amount", MONEY),
        sa.Column("quantity_mode", sa.String(30)), sa.Column("calculated_lot_size", MONEY), sa.Column("calculated_quantity", MONEY),
        sa.Column("pnl", MONEY), sa.Column("r_multiple", PCT), sa.Column("balance_after_trade", MONEY), sa.Column("equity_after_trade", MONEY),
        sa.Column("daily_pnl_after_trade", MONEY), sa.Column("daily_dd_pct_used", PCT), sa.Column("max_dd_pct_used", PCT),
        sa.Column("qualifying_day_state", sa.String(40)), sa.Column("consistency_contribution", PCT), sa.Column("rule_event", sa.String(80)),
        sa.Column("account_state_after_trade", sa.String(40)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("funded_backtest_id", "trade_number", name="uq_funded_trade_number"),
    )
    for col in ("funded_backtest_id", "funded_phase_id", "source_trade_id", "entry_time"):
        op.create_index(f"ix_funded_backtest_trades_{col}", "funded_backtest_trades", [col])

    op.create_table(
        "funded_backtest_daily_snapshots",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("funded_backtest_id", UUID, sa.ForeignKey("funded_backtest_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("funded_phase_id", UUID, sa.ForeignKey("funded_backtest_phases.id", ondelete="CASCADE")),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("start_balance", MONEY, nullable=False), sa.Column("start_equity", MONEY, nullable=False), sa.Column("end_balance", MONEY, nullable=False), sa.Column("end_equity", MONEY, nullable=False),
        sa.Column("day_pnl", MONEY, nullable=False), sa.Column("day_return_pct", PCT, nullable=False), sa.Column("peak_equity", MONEY), sa.Column("low_equity", MONEY),
        sa.Column("daily_drawdown_amount", MONEY), sa.Column("daily_drawdown_pct", PCT),
        sa.Column("trades_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("winning_trades", sa.Integer(), nullable=False, server_default="0"), sa.Column("losing_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qualifying_day", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("qualifying_profit_threshold", MONEY), sa.Column("consistency_pct", PCT),
        sa.Column("state", sa.String(40)), sa.Column("failure_reason", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("funded_backtest_id", "trading_date", name="uq_funded_daily_snapshot_date"),
    )
    op.create_index("ix_funded_backtest_daily_snapshots_funded_backtest_id", "funded_backtest_daily_snapshots", ["funded_backtest_id"])
    op.create_index("ix_funded_backtest_daily_snapshots_funded_phase_id", "funded_backtest_daily_snapshots", ["funded_phase_id"])

    op.create_table(
        "funded_backtest_events",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("funded_backtest_id", UUID, sa.ForeignKey("funded_backtest_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("funded_phase_id", UUID, sa.ForeignKey("funded_backtest_phases.id", ondelete="CASCADE")),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False), sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("event_title", sa.String(255), nullable=False), sa.Column("message", sa.Text()), sa.Column("metadata_json", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_funded_backtest_events_funded_backtest_id", "funded_backtest_events", ["funded_backtest_id"])
    op.create_index("ix_funded_backtest_events_funded_phase_id", "funded_backtest_events", ["funded_phase_id"])
    op.create_index("ix_funded_backtest_events_event_timestamp", "funded_backtest_events", ["event_timestamp"])
    op.create_index("ix_funded_backtest_events_event_type", "funded_backtest_events", ["event_type"])
    op.create_index("ix_funded_events_run_time", "funded_backtest_events", ["funded_backtest_id", "event_timestamp"])


def downgrade() -> None:
    op.drop_table("funded_backtest_events")
    op.drop_table("funded_backtest_daily_snapshots")
    op.drop_table("funded_backtest_trades")
    op.drop_table("funded_backtest_phases")
    op.drop_table("funded_backtest_runs")
    op.drop_table("funded_risk_tiers")
    op.drop_table("funded_account_phases")
    op.drop_table("funded_account_profiles")
