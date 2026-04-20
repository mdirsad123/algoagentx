from sqlalchemy import Column, String, Text, DateTime, ForeignKey
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
    notes = Column(Text, nullable=True)

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