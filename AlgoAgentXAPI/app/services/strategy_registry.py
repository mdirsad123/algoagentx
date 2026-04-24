from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from strategies.ema_crossover import EMACrossover
from strategies.rsi_strategy import RSIStrategy
from strategies.smc_strategy import SMCStrategy
from strategies.stock_burner_ema_9_20 import StockBurnerEMA920
from strategies.trend_continuation_tce_adam import TrendContinuationTCE
from strategies.simple_trendline import SimpleTrendlineStrategy


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
}


def _normalize(value: str | None) -> str:
    return " ".join((value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def resolve_strategy(strategy_id: str | None, strategy_name: str | None, db_parameters: Dict[str, Any] | None = None) -> Tuple[Any, Dict[str, Any], str]:
    normalized_id = _normalize(strategy_id)
    normalized_name = _normalize(strategy_name)
    haystack = f"{normalized_id} {normalized_name}".strip()

    key = None
    if "trendline" in haystack:
        key = "simple_trendline"
    elif "stock burner" in haystack or ("ema" in haystack and "200" in haystack):
        key = "stock_burner_ema_920"
    elif "tce" in haystack or "trend continuation" in haystack:
        key = "trend_continuation_tce"
    elif "smc" in haystack or "smart money" in haystack:
        key = "smc_strategy"
    elif "ema" in haystack and "rsi" in haystack:
        key = "ema_crossover"
    elif normalized_id in _REGISTRY:
        key = normalized_id
    elif "rsi" in haystack:
        key = "rsi_strategy"
    elif "ema" in haystack:
        key = "ema_crossover"

    if key is None:
        available = ", ".join(entry.canonical_name for entry in _REGISTRY.values())
        raise ValueError(f"No executable strategy mapping found for '{strategy_name or strategy_id}'. Available engine strategies: {available}")

    entry = _REGISTRY[key]
    params = dict(entry.default_params)
    if isinstance(db_parameters, dict):
        for k, v in db_parameters.items():
            if isinstance(v, (str, int, float, bool)):
                params[k] = v
    return entry.strategy_class, params, entry.canonical_name
