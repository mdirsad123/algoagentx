from sqlalchemy import Boolean, Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..base import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String(64), primary_key=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    parameters = Column(JSONB, nullable=True, default=dict)

    default_runtime_config = Column(JSONB, nullable=True)
    runtime_config_schema = Column(JSONB, nullable=True)
    supports_runtime_config = Column(Boolean, nullable=False, server_default="true", index=True)
    config_version = Column(Integer, nullable=False, server_default="1")


    created_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    visibility = Column(String(16), nullable=False, server_default="PRIVATE", index=True)

    source_request_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("strategy_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    published_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lifecycle_status = Column(String(40), nullable=False, server_default="DRAFT", index=True)
    is_deployable_paper = Column(Boolean, nullable=False, server_default="false", index=True)
    is_deployable_demo = Column(Boolean, nullable=False, server_default="false", index=True)
    is_live_approved = Column(Boolean, nullable=False, server_default="false", index=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    sandbox_passed_at = Column(DateTime(timezone=True), nullable=True)
    paper_enabled_at = Column(DateTime(timezone=True), nullable=True)
    demo_enabled_at = Column(DateTime(timezone=True), nullable=True)
    live_approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    creator = relationship("User", foreign_keys=[created_by], lazy="joined")


class StrategyRuntimePreset(Base):
    __tablename__ = "strategy_runtime_presets"

    id = Column(String(64), primary_key=True)
    strategy_id = Column(String(64), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    config_json = Column(JSONB, nullable=False, default=dict)
    risk_label = Column(String(100), nullable=True)
    is_default = Column(Boolean, nullable=False, server_default="false", index=True)
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
    created_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    strategy = relationship("Strategy", lazy="joined")
