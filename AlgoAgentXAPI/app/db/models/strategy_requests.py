from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..base import Base


class StrategyRequest(Base):
    __tablename__ = "strategy_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False, index=True)
    strategy_type = Column(String(255), nullable=True)
    market = Column(String(255), nullable=True)
    timeframe = Column(String(255), nullable=True)
    indicators = Column(JSONB, nullable=True)

    entry_rules = Column(Text, nullable=False)
    exit_rules = Column(Text, nullable=False)
    risk_rules = Column(Text, nullable=False)
    confirmation_rules = Column(Text, nullable=True)
    invalidation_rules = Column(Text, nullable=True)
    trade_management_rules = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    user_update_notes = Column(Text, nullable=True)
    clarification_submitted_at = Column(DateTime(timezone=True), nullable=True)
    last_user_update_at = Column(DateTime(timezone=True), nullable=True)
    parent_strategy_id = Column(String(64), ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True, index=True)
    parent_request_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_requests.id", ondelete="SET NULL"), nullable=True, index=True)
    request_kind = Column(String(50), nullable=False, server_default="NEW")
    refinement_notes = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, server_default="UNDER_DEVELOPMENT", index=True)
    admin_notes = Column(Text, nullable=True)

    assigned_to = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    deployed_strategy_id = Column(
        String(64),
        ForeignKey("strategies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    attachments = relationship("StrategyRequestAttachment", back_populates="request", cascade="all, delete-orphan", order_by="StrategyRequestAttachment.sort_order")


class StrategyRequestAttachment(Base):
    __tablename__ = "strategy_request_attachments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    request_id = Column(PG_UUID(as_uuid=True), ForeignKey("strategy_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=True)
    file_path = Column(Text, nullable=False)
    public_url = Column(Text, nullable=True)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sort_order = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    request = relationship("StrategyRequest", back_populates="attachments")
    user = relationship("User", lazy="joined")