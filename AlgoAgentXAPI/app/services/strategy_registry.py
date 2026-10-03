from __future__ import annotations

from dataclasses import dataclass
import inspect
from typing import Any, Dict, Tuple

from strategies.ema_crossover import EMACrossover
from strategies.rsi_strategy import RSIStrategy
from strategies.smc_strategy import SMCStrategy
from strategies.stock_burner_ema_9_20 import StockBurnerEMA920
from strategies.trend_continuation_tce_adam import TrendContinuationTCE
from strategies.simple_trendline import SimpleTrendlineStrategy
from strategies.every_two_candle_color_demo import EveryTwoCandleColorDemoStrategy
from strategies.every_candle_color_live_latency_test import EveryCandleColorLiveLatencyTestStrategy
from strategies.xauusd_5m_resistance_rejection_v1 import XAUUSD5MResistanceRejectionV1
from strategies.xauusd_5m_resistance_rejection_v3_5 import XAUUSD5MSupplyDemandRejectionV35CandidateA
from strategies.xauusd_5m_trend_breakout_v1_37 import XAUUSD5MTrendBreakoutV137


@dataclass(frozen=True)
class StrategyRegistryEntry:
    strategy_class: Any
    default_params: Dict[str, Any]
    canonical_name: str


_REGISTRY: dict[str, StrategyRegistryEntry] = {
    "ema_crossover": StrategyRegistryEntry(EMACrossover, {"rr_ratio": 2.0}, "EMA Crossover"),
    "rsi_strategy": StrategyRegistryEntry(RSIStrategy, {"period": 14, "buy_level": 30, "sell_level": 70}, "RSI Strategy"),
    "smc_strategy": StrategyRegistryEntry(SMCStrategy, {"rr_ratio": 2.0}, "SMC Strategy"),
    "stock_burner_ema_920": StrategyRegistryEntry(StockBurnerEMA920, {"rr_ratio": 2.0}, "Stock Burner EMA 9/20"),
    "trend_continuation_tce": StrategyRegistryEntry(TrendContinuationTCE, {"rr_ratio": 2.0}, "Trend Continuation TCE"),
    "simple_trendline": StrategyRegistryEntry(SimpleTrendlineStrategy, {"lookback": 3, "breakout_buffer": 0.0}, "Simple Trendline Strategy"),
    "xauusd_5m_resistance_rejection_v1": StrategyRegistryEntry(
        XAUUSD5MResistanceRejectionV1,
        {"entry_confirmation": "BREAK_REJECTION_LOW", "sl_mode": "REJECTION_HIGH", "tp_mode": "FIXED_RR", "minimum_rr": 1.5, "target_rr": 2.0, "debug_mode": False},
        "XAUUSD 5M Resistance Rejection V1",
    ),
    "xauusd_5m_resistance_rejection_v3_5": StrategyRegistryEntry(
        XAUUSD5MSupplyDemandRejectionV35CandidateA,
        {},
        "XAUUSD 5M Resistance Rejection V3.5",
    ),
    "xauusd_5m_trend_breakout_v1_37": StrategyRegistryEntry(
        XAUUSD5MTrendBreakoutV137,
        {},
        "Trend-Following Breakout V1.37",
    ),
    "every_two_candle_color_demo": StrategyRegistryEntry(
        EveryTwoCandleColorDemoStrategy,
        {"signal_every_n_candles": 2, "warmup_bars": 2, "signal_latest_candle": True},
        "Every 2 Candle Color Demo Strategy",
    ),
    "every_candle_color_live_latency_test": StrategyRegistryEntry(
        EveryCandleColorLiveLatencyTestStrategy,
        {"warmup_bars": 2, "doji_side": "BUY"},
        "Every Candle Color Live Latency Test Strategy",
    ),
}


def _normalize(value: str | None) -> str:
    return " ".join((value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def _filter_init_params(strategy_class: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        signature = inspect.signature(strategy_class.__init__)
    except (TypeError, ValueError):
        return dict(params)

    parameters = signature.parameters
    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()):
        return dict(params)

    allowed = {
        name
        for name, param in parameters.items()
        if name not in {"self", "df"}
        and param.kind in {inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY}
    }
    return {key: value for key, value in params.items() if key in allowed}


def resolve_strategy(strategy_id: str | None, strategy_name: str | None, db_parameters: Dict[str, Any] | None = None) -> Tuple[Any, Dict[str, Any], str]:
    db_params = db_parameters if isinstance(db_parameters, dict) else {}
    source_code = str(db_params.get("source_code") or "").strip()
    engine_mode = str(db_params.get("engine_mode") or "").strip().upper()

    # DB-attached source code is authoritative. Admin-created, duplicated, and
    # versioned strategies must execute the exact code stored on that Strategy
    # row in both backtest and live trading. Never silently fall back to a
    # similarly named static strategy (for example V3.5 -> V1).
    if source_code:
        from .dynamic_strategy_loader import build_dynamic_strategy_entry

        try:
            return build_dynamic_strategy_entry(strategy_id, strategy_name, db_params)
        except ValueError as exc:
            raise ValueError(
                f"Dynamic strategy source for '{strategy_name or strategy_id}' could not be loaded: {exc}. "
                "Static fallback is disabled when source_code is attached."
            ) from exc

    if engine_mode == "DYNAMIC_DB":
        raise ValueError(
            f"Strategy '{strategy_name or strategy_id}' is marked DYNAMIC_DB but has no source_code. "
            "Save the strategy source again before backtest/live deployment."
        )

    normalized_id = _normalize(strategy_id)
    normalized_name = _normalize(strategy_name)
    haystack = f"{normalized_id} {normalized_name}".strip()

    # Exact static mappings first. Versioned strategies only use a static class
    # when that exact version is explicitly registered.
    exact_static_names = {
        _normalize(entry.canonical_name): key
        for key, entry in _REGISTRY.items()
    }
    key = None
    if normalized_id in _REGISTRY:
        key = normalized_id
    elif normalized_name in exact_static_names:
        key = exact_static_names[normalized_name]
    elif (
        "every candle" in haystack
        or "live latency test" in haystack
        or ("latency" in haystack and "candle color" in haystack)
    ):
        key = "every_candle_color_live_latency_test"
    elif (
        "every 2 candle" in haystack
        or "every two candle" in haystack
        or "candle color demo" in haystack
        or "colour demo" in haystack
        or "color demo" in haystack
        or "demo test" in haystack
    ):
        key = "every_two_candle_color_demo"
    elif "trendline" in haystack:
        key = "simple_trendline"
    elif (
        "stock burner" in haystack
        or "ema 9/20" in haystack
        or "ema 9 20" in haystack
        or "9/20" in haystack
        or ("ema" in haystack and "920" in haystack)
        or ("ema" in haystack and "9" in haystack and "20" in haystack)
        or ("ema" in haystack and "trend momentum" in haystack)
        or ("ema" in haystack and "200" in haystack)
    ):
        key = "stock_burner_ema_920"
    elif "tce" in haystack or "trend continuation" in haystack:
        key = "trend_continuation_tce"
    elif "smc" in haystack or "smart money" in haystack:
        key = "smc_strategy"
    elif "ema" in haystack and "rsi" in haystack:
        key = "ema_crossover"
    elif "rsi" in haystack:
        key = "rsi_strategy"
    elif "ema" in haystack:
        key = "ema_crossover"

    if key is None:
        available = ", ".join(entry.canonical_name for entry in _REGISTRY.values())
        raise ValueError(
            f"No executable strategy mapping found for '{strategy_name or strategy_id}'. "
            f"Available static engine strategies: {available}. "
            "Admin/custom versions must include source_code and execute through DYNAMIC_DB."
        )

    entry = _REGISTRY[key]
    params = dict(entry.default_params)
    if isinstance(db_parameters, dict):
        for k, v in db_parameters.items():
            if isinstance(v, (str, int, float, bool)):
                params[k] = v
    params = _filter_init_params(entry.strategy_class, params)
    return entry.strategy_class, params, entry.canonical_name

