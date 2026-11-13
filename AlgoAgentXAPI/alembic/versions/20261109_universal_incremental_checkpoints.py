"""Optional native incremental checkpoint storage (no existing trade data touched)."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261109_universal_incremental"
down_revision = "20261106_backtest_reliability"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "live_incremental_checkpoints",
        sa.Column("deployment_id", sa.String(64), primary_key=True),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("candle_open", sa.DateTime(timezone=True), nullable=False),
        sa.Column("candle_count", sa.BigInteger(), nullable=False),
        sa.Column("state_schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_candle", JSONB(), nullable=False),
        sa.Column("state_json", JSONB(), nullable=False),
        sa.Column("state_sha256", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    # Keep durable checkpoints across an application rollback.
    raise RuntimeError("Checkpoint data is retained. Remove manually only after exporting it.")
