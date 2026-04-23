from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from ..base import Base


class UserCredit(Base):
    __tablename__ = "user_credits"

    user_id = Column(PG_UUID(as_uuid=True), primary_key=True)
    balance = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
