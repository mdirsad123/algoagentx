"""Immutable strategy revisions and append-only state. MANUAL APPROVAL ONLY.

No existing strategy, deployment, candle, order or checkpoint row is changed.
Application rollback retains these tables; downgrade intentionally refuses loss.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20261111_live_registry_state"
down_revision = "20261109_universal_incremental"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "live_strategy_revisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("strategy_id", sa.String(64), sa.ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.String(128), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("entrypoint", sa.String(255)),
        sa.Column("interface_version", sa.Integer()),
        sa.Column("contract_status", sa.String(20), nullable=False),
        sa.Column("contract_report", JSONB(), nullable=False),
        sa.Column("dependencies", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("strategy_id", "source_sha256", "version", name="uq_live_strategy_revision_source"),
        sa.CheckConstraint("contract_status IN ('declared', 'unsupported')", name="ck_live_revision_contract"),
    )
    op.create_table(
        "live_strategy_runtimes",
        sa.Column("deployment_id", UUID(as_uuid=True), sa.ForeignKey("strategy_deployments.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("revision_id", UUID(as_uuid=True), sa.ForeignKey("live_strategy_revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("configuration", JSONB(), nullable=False),
        sa.Column("state_schema_version", sa.Integer(), nullable=False),
        sa.Column("generation", sa.BigInteger(), nullable=False),
        sa.Column("checkpoint_sequence", sa.BigInteger(), nullable=False),
        sa.Column("candle_open", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("generation > 0 AND checkpoint_sequence >= 0", name="ck_live_runtime_sequence"),
        sa.CheckConstraint("status IN ('pending', 'ready', 'blocked')", name="ck_live_runtime_status"),
        sa.CheckConstraint("state_schema_version > 0", name="ck_live_runtime_schema"),
    )
    op.create_table(
        "live_strategy_checkpoint_history",
        sa.Column("deployment_id", UUID(as_uuid=True), sa.ForeignKey("strategy_deployments.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("generation", sa.BigInteger(), primary_key=True),
        sa.Column("sequence", sa.BigInteger(), primary_key=True),
        sa.Column("revision_id", UUID(as_uuid=True), sa.ForeignKey("live_strategy_revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("candle_open", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("deployment_id", "generation", "candle_open", name="uq_live_checkpoint_candle"),
        sa.CheckConstraint("generation > 0 AND sequence > 0", name="ck_live_checkpoint_sequence"),
    )
    op.execute("""
        CREATE FUNCTION reject_live_strategy_history_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Live strategy revisions and checkpoint history are immutable';
        END;
        $$
    """)
    for table in ("live_strategy_revisions", "live_strategy_checkpoint_history"):
        op.execute(f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} "
                   "FOR EACH ROW EXECUTE FUNCTION reject_live_strategy_history_mutation()")


def downgrade():
    raise RuntimeError("Preserve registry/state history. Roll back application only; do not drop these tables.")