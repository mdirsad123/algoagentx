from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


def _parse_backtest_date(value):
    """Accept HTML yyyy-mm-dd plus legacy dd-mm-yyyy/dd/mm/yyyy payloads safely."""
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        raw = value.strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return value


class BacktestAdvancedFilters(BaseModel):
    enabled: bool = False
    days_of_week: List[str] = Field(default_factory=list)
    session: str = "ALL"
    custom_start_time: Optional[str] = None
    custom_end_time: Optional[str] = None
    timezone: str = "Asia/Kolkata"

    @field_validator("days_of_week", mode="before")
    @classmethod
    def normalize_days(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value.upper()]
        if isinstance(value, list):
            return [str(day).upper() for day in value if str(day or "").strip()]
        return value

    @field_validator("session", mode="before")
    @classmethod
    def normalize_session(cls, value):
        return str(value or "ALL").upper()


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
    instrument_id: Optional[int] = None
    instrument_symbol: Optional[str] = None
    symbol: Optional[str] = None
    timeframe: str
    timeframe_id: Optional[int] = None
    start_date: date
    end_date: date
    capital: Decimal = Field(..., gt=0)
    save_result: bool = True
    advanced_filters: Optional[BacktestAdvancedFilters] = None
    runtime_config: Optional[dict[str, Any]] = None
    strategy_preset_id: Optional[str] = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_date_inputs(cls, value):
        return _parse_backtest_date(value)


class BacktestCostPreviewRequest(BaseModel):
    strategy_id: Optional[str] = None
    instrument_id: Optional[int] = None
    timeframe: str
    start_date: date
    end_date: date
    capital: Optional[Decimal] = None
    advanced_filters: Optional[BacktestAdvancedFilters] = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_date_inputs(cls, value):
        return _parse_backtest_date(value)


class TradeData(BaseModel):
    entry_time: datetime
    exit_time: Optional[datetime] = None
    side: str
    quantity: int
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    exit_type: Optional[str] = None
    stop_loss: Optional[Decimal] = None
    target: Optional[Decimal] = None
    risk_points: Optional[Decimal] = None
    reward_points: Optional[Decimal] = None
    rr_ratio: Optional[Decimal] = None
    risk_amount: Optional[Decimal] = None
    reward_amount: Optional[Decimal] = None
    r_multiple: Optional[Decimal] = None
    signal_reason: Optional[str] = None


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
    advanced_filters: Optional[dict[str, Any]] = None
    filter_summary: Optional[str] = None
    candles_before_filter: Optional[int] = None
    candles_after_filter: Optional[int] = None
    filter_reduction_pct: Optional[float] = None
    runtime_config_snapshot: Optional[dict[str, Any]] = None
    instrument_spec_snapshot: Optional[dict[str, Any]] = None
    runtime_summary: Optional[str] = None


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
