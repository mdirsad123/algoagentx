from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from ..base import Base


class UserCredit(Base):
    __tablename__ = "user_credits"

    user_id = Column(String(36), primary_key=True)  # String to handle both UUID and Integer
    balance = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())