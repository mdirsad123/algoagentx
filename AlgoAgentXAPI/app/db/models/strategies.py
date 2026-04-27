from sqlalchemy import Boolean, Column, String, Text, DateTime, ForeignKey
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
