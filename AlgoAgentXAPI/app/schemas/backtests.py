from pydantic import BaseModel
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal
from typing import Optional, List


class PerformanceMetricBase(BaseModel):
    user_id: int
    strategy_id: str
    instrument_id: int
    timeframe: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    final_capital: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    calmar_ratio: Optional[Decimal] = None
    win_rate: Optional[Decimal] = None
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    losing_trades: Optional[int] = None
    status: str


class PerformanceMetricCreate(PerformanceMetricBase):
    pass


class PerformanceMetric(PerformanceMetricBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BacktestRunRequest(BaseModel):
    strategy_id: str
    instrument_id: int
    timeframe: str
    start_date: date
    end_date: date
    capital: Decimal
    save_result: bool = False


class TradeData(BaseModel):
    entry_time: datetime
    exit_time: Optional[datetime]
    side: str
    quantity: int
    entry_price: Decimal
    exit_price: Optional[Decimal]
    pnl: Optional[Decimal]
    exit_type: Optional[str]


class EquityPoint(BaseModel):
    timestamp: datetime
    equity: Decimal


class BacktestRunResponse(BaseModel):
    # Metadata
    backtest_id: Optional[UUID] = None  # Only if saved
    strategy_name: str
    instrument_symbol: str
    timeframe: str
    start_date: date
    end_date: date

    # Metrics
    initial_capital: Decimal
    final_capital: Decimal
    net_profit: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Decimal
    win_rate: Decimal
    total_trades: int

    # Chart data optimized for frontend
    trades: List[TradeData]
    equity_curve: List[EquityPoint]

    # Status
    saved: bool
