"""Ordered equity events and durable backtest ownership (no history deletion).

Existing events receive sequence zero. Deploy only after old backtest writers
have drained. A short lock timeout prevents blocking a busy production table.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261106_backtest_reliability"
down_revision = "20261031_market_gap_publish"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column("equity_curve", sa.Column("event_sequence", sa.Integer(), nullable=False, server_default="0"))
    op.drop_constraint("equity_curve_pkey", "equity_curve", type_="primary")
    op.create_primary_key("equity_curve_pkey", "equity_curve", ["backtest_id", "timestamp", "event_sequence"])
    op.create_check_constraint("ck_equity_event_sequence_nonnegative", "equity_curve", "event_sequence >= 0")
    op.create_table(
        "backtest_execution",
        sa.Column("job_id", sa.String(), sa.ForeignKey("job_status.id"), primary_key=True),
        sa.Column("fence", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("owner", sa.String(128)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stage", sa.String(64), nullable=False, server_default="queued"),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("telemetry", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("attempts >= 0 AND max_attempts > 0", name="ck_backtest_attempts"),
    )


def downgrade():
    # A downgrade must never destroy same-timestamp history or recovery evidence.
    op.execute("SET LOCAL lock_timeout = '5s'")
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM equity_curve WHERE event_sequence <> 0)")).scalar():
        raise RuntimeError("Cannot downgrade: ordered equity events exist; retain schema and roll back application only")
    if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM backtest_execution)")).scalar():
        raise RuntimeError("Cannot downgrade: durable execution records exist; retain schema")
    op.drop_table("backtest_execution")
    op.drop_constraint("equity_curve_pkey", "equity_curve", type_="primary")
    op.drop_constraint("ck_equity_event_sequence_nonnegative", "equity_curve", type_="check")
    op.drop_column("equity_curve", "event_sequence")
    op.create_primary_key("equity_curve_pkey", "equity_curve", ["backtest_id", "timestamp"])