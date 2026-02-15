from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from ..base import Base
import uuid


class ScreenerRuns(Base):
    __tablename__ = "screener_runs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_type = Column(String(20), nullable=False)  # NEWS / ANNOUNCEMENTS
    status = Column(String(20), nullable=False)   # RUNNING / SUCCESS / FAILED
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)