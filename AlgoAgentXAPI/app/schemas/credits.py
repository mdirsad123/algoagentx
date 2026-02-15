from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum as PyEnum


class CreditTransactionType(PyEnum):
    DEBIT = "debit"
    CREDIT = "credit"
    REFUND = "refund"


class CreditTransactionBase(BaseModel):
    user_id: str
    transaction_type: CreditTransactionType
    amount: float
    description: Optional[str] = None
    backtest_id: Optional[str] = None
    job_id: Optional[str] = None


class CreditTransactionCreate(CreditTransactionBase):
    pass


class CreditTransaction(CreditTransactionBase):
    id: str
    balance_after: float
    created_at: datetime

    class Config:
        from_attributes = True


class CreditCostPreview(BaseModel):
    start_date: str
    end_date: str
    timeframe: Optional[str] = None
    months: int
    base_cost: int
    base_cost_reason: str
    timeframe_bonus: int
    timeframe_reason: str
    total_cost: int


class CreditBalance(BaseModel):
    user_id: str
    current_balance: float
    last_updated: str


class CreditSummary(BaseModel):
    user_id: str
    credit_balance: float
    included_remaining: int
    plan_name: str
    next_reset_date: Optional[str] = None
    total_transactions: int
    transaction_counts: Dict[str, int]
    last_updated: str


class InsufficientCreditsError(BaseModel):
    code: str = "INSUFFICIENT_CREDITS"
    message: str = "Insufficient credits for backtest"
    needed: int
    balance: float