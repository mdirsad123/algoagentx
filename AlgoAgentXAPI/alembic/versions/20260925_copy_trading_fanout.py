"""add copy trading fan-out settings

Revision ID: 20260925_copy_trading_fanout
Revises: 20260921_live_event_pipeline
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "20260925_copy_trading_fanout"
down_revision = "20260921_live_event_pipeline"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("strategy_deployments", sa.Column("copy_trading_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("strategy_deployments", sa.Column("copy_broker_account_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.create_index("idx_strategy_deployments_copy_trading_enabled", "strategy_deployments", ["copy_trading_enabled"], unique=False)

def downgrade():
    op.drop_index("idx_strategy_deployments_copy_trading_enabled", table_name="strategy_deployments")
    op.drop_column("strategy_deployments", "copy_broker_account_ids")
    op.drop_column("strategy_deployments", "copy_trading_enabled")
