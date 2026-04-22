from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class PerformanceMetricBase(BaseModel):
    user_id: str
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
    profit_factor: Optional[Decimal] = None
    status: str = "completed"


class PerformanceMetricCreate(PerformanceMetricBase):
    pass


class PerformanceMetric(PerformanceMetricBase):
    id: str
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
    capital: Decimal = Field(..., gt=0)
    save_result: bool = True


class BacktestCostPreviewRequest(BaseModel):
    strategy_id: Optional[str] = None
    instrument_id: Optional[int] = None
    timeframe: str
    start_date: date
    end_date: date
    capital: Optional[Decimal] = None


class TradeData(BaseModel):
    entry_time: datetime
    exit_time: Optional[datetime] = None
    side: str
    quantity: int
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    exit_type: Optional[str] = None


class EquityPoint(BaseModel):
    timestamp: datetime
    equity: Decimal


class BacktestRunResponse(BaseModel):
    backtest_id: Optional[str] = None
    strategy_name: str
    instrument_symbol: str
    timeframe: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    final_capital: Decimal
    net_profit: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Decimal
    win_rate: Decimal
    total_trades: int
    profit_factor: Optional[Decimal] = None
    trades: List[TradeData]
    equity_curve: List[EquityPoint]
    saved: bool


class BacktestHistoryItem(BaseModel):
    id: str
    strategy_id: Optional[str] = None
    strategy_name: Optional[str] = None
    instrument_id: Optional[int] = None
    instrument_symbol: Optional[str] = None
    timeframe: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    initial_capital: Optional[Decimal] = None
    final_capital: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    win_rate: Optional[Decimal] = None
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    losing_trades: Optional[int] = None
    credit_cost: Optional[float] = None
    debit_transaction_id: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BacktestPagination(BaseModel):
    page: int
    page_size: int
    total_count: int
    total_pages: int


class BacktestHistoryResponse(BaseModel):
    backtests: List[BacktestHistoryItem]
    pagination: BacktestPagination


class BacktestDetailResponse(BaseModel):
    summary: BacktestHistoryItem
    trades: List[dict[str, Any]]
    equity_curve: List[dict[str, Any]]
    pnl_calendar: List[dict[str, Any]]
