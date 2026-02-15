from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from ..base import Base


class JobStatus(Base):
    __tablename__ = "job_status"

    id = Column(String, primary_key=True)  # UUID as string
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    job_type = Column(String, nullable=False)  # 'backtest', 'strategy_test', etc.
    status = Column(String, nullable=False)  # 'pending', 'running', 'completed', 'failed', 'retry'
    progress = Column(Integer, default=0)  # 0-100
    message = Column(Text)  # Status message or error details
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Job-specific data stored as JSON
    job_data = Column(Text)  # JSON string with job parameters
    result_data = Column(Text)  # JSON string with job results
    
    # Credit transaction tracking
    debit_txn_id = Column(String, ForeignKey("credit_transactions.id"), nullable=True)
