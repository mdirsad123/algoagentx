from sqlalchemy import Column, String, JSON, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..base import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    parameters = Column(JSON)
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
