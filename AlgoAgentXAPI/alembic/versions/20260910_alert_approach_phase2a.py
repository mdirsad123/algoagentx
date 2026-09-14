"""approaching level and zone alerts phase 2a

Revision ID: 20260910_alert_approach_phase2a
Revises: 20260909_real_time_alerting_phase1
Create Date: 2026-09-10
"""
from alembic import op
import sqlalchemy as sa

revision = "20260910_alert_approach_phase2a"
down_revision = "20260909_real_time_alerting_phase1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("price_alerts", sa.Column("approach_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("price_alerts", sa.Column("approach_distance", sa.Numeric(24, 10), nullable=True))
    op.add_column("price_alerts", sa.Column("approach_state", sa.String(30), nullable=False, server_default="DISABLED"))
    op.add_column("price_alerts", sa.Column("last_approach_triggered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("price_alerts", sa.Column("approach_trigger_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("price_alerts", "approach_trigger_count")
    op.drop_column("price_alerts", "last_approach_triggered_at")
    op.drop_column("price_alerts", "approach_state")
    op.drop_column("price_alerts", "approach_distance")
    op.drop_column("price_alerts", "approach_enabled")
