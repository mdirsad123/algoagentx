"""Additive universal-runtime foundation; existing deployment/history rows stay intact."""
from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.sql import func

from ..base import Base


def json_type():
    return JSON().with_variant(JSONB(), "postgresql")


class LiveStrategyRevision(Base):
    __tablename__ = "live_strategy_revisions"
    __table_args__ = (
        UniqueConstraint("strategy_id", "source_sha256", "version", name="uq_live_strategy_revision_source"),
        CheckConstraint("contract_status IN ('declared', 'unsupported')", name="ck_live_revision_contract"),
    )
    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    strategy_id = Column(String(64), ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False)
    version = Column(String(128), nullable=False)
    source_code = Column(Text, nullable=False)
    source_sha256 = Column(String(64), nullable=False)
    entrypoint = Column(String(255), nullable=True)
    interface_version = Column(Integer, nullable=True)
    contract_status = Column(String(20), nullable=False)
    contract_report = Column(json_type(), nullable=False)
    dependencies = Column(json_type(), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LiveStrategyRuntime(Base):
    __tablename__ = "live_strategy_runtimes"
    __table_args__ = (
        CheckConstraint("generation > 0 AND checkpoint_sequence >= 0", name="ck_live_runtime_sequence"),
        CheckConstraint("status IN ('pending', 'ready', 'blocked')", name="ck_live_runtime_status"),
        CheckConstraint("state_schema_version > 0", name="ck_live_runtime_schema"),
    )
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="RESTRICT"), primary_key=True)
    revision_id = Column(PG_UUID(as_uuid=True), ForeignKey("live_strategy_revisions.id", ondelete="RESTRICT"), nullable=False)
    fingerprint = Column(String(64), nullable=False)
    configuration = Column(json_type(), nullable=False)
    state_schema_version = Column(Integer, nullable=False)
    generation = Column(BigInteger, nullable=False)
    checkpoint_sequence = Column(BigInteger, nullable=False, default=0)
    candle_open = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False)
    reason = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LiveStrategyCheckpoint(Base):
    __tablename__ = "live_strategy_checkpoint_history"
    __table_args__ = (
        UniqueConstraint("deployment_id", "generation", "candle_open", name="uq_live_checkpoint_candle"),
        CheckConstraint("generation > 0 AND sequence > 0", name="ck_live_checkpoint_sequence"),
    )
    deployment_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_deployments.id", ondelete="RESTRICT"), primary_key=True)
    generation = Column(BigInteger, primary_key=True)
    sequence = Column(BigInteger, primary_key=True)
    revision_id = Column(PG_UUID(as_uuid=True), ForeignKey("live_strategy_revisions.id", ondelete="RESTRICT"), nullable=False)
    candle_open = Column(DateTime(timezone=True), nullable=False)
    payload = Column(json_type(), nullable=False)
    payload_sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())