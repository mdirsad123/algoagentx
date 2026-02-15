from .users import User, UserCreate, UserLogin, UserUpdate
from .strategies import Strategy, StrategyCreate, StrategyTemplateResponse, StrategyMyResponse
from .backtests import (
    PerformanceMetric, PerformanceMetricCreate, PerformanceMetricBase,
    BacktestRunRequest, BacktestRunResponse, TradeData, EquityPoint
)
from .signals import Signal, SignalCreate
from .metrics import Metric, MetricCreate
from .instruments import Instrument
from .market_data import TimeframeResponse, MarketDataRangeResponse
from .notifications import NotificationCreate, NotificationResponse, NotificationUpdate, MarkReadRequest, MarkAllReadRequest
from .strategy_requests import (
    StrategyRequestCreate,
    StrategyRequestUpdate,
    StrategyRequestAdminUpdate,
    StrategyRequestResponse,
    StrategyRequestListResponse
)
from .screener import (
    ScreenerNewsBase, ScreenerNewsCreate, ScreenerNewsResponse,
    ScreenerAnnouncementsBase, ScreenerAnnouncementsCreate, ScreenerAnnouncementsResponse,
    ScreenerRunsBase, ScreenerRunsCreate, ScreenerRunsResponse
)

# Alias for backward compatibility
Backtest = PerformanceMetric
BacktestCreate = PerformanceMetricCreate

__all__ = [
    "User", "UserCreate", "UserLogin", "UserUpdate",
    "Strategy", "StrategyCreate",
    "PerformanceMetric", "PerformanceMetricCreate", "PerformanceMetricBase",
    "BacktestRunRequest", "BacktestRunResponse", "TradeData", "EquityPoint",
    "Backtest", "BacktestCreate",  # Aliases for backward compatibility
    "Signal", "SignalCreate",
    "Metric", "MetricCreate",
    "Instrument",
    "TimeframeResponse", "MarketDataRangeResponse",
    "NotificationCreate", "NotificationResponse", "NotificationUpdate", "MarkReadRequest", "MarkAllReadRequest",
    "StrategyRequestCreate",
    "StrategyRequestUpdate",
    "StrategyRequestAdminUpdate",
    "StrategyRequestResponse",
    "StrategyRequestListResponse",
    "ScreenerNewsBase", "ScreenerNewsCreate", "ScreenerNewsResponse",
    "ScreenerAnnouncementsBase", "ScreenerAnnouncementsCreate", "ScreenerAnnouncementsResponse",
    "ScreenerRunsBase", "ScreenerRunsCreate", "ScreenerRunsResponse",
]
