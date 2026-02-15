from sqlalchemy import Column, String, JSON, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..base import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    parameters = Column(JSON)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
