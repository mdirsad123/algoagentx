from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, DECIMAL, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..base import Base
from enum import Enum as PyEnum


class CreditTransactionType(PyEnum):
    DEBIT = "debit"
    CREDIT = "credit"
    REFUND = "refund"


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(String, primary_key=True)  # UUID as string
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    transaction_type = Column(Enum(CreditTransactionType), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    balance_after = Column(DECIMAL(10, 2), nullable=False)
    description = Column(Text)
    
    # Reference to related entities
    backtest_id = Column(String, ForeignKey("performance_metrics.id"), nullable=True)
    job_id = Column(String, ForeignKey("job_status.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="credit_transactions")
    backtest = relationship("PerformanceMetric", backref="credit_transactions", foreign_keys=[backtest_id])
    job = relationship("JobStatus", backref="credit_transactions", foreign_keys=[job_id])
