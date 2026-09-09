from decimal import Decimal
from typing import Iterable

from .consistency import consistency_percentage


def _d(value) -> Decimal:
    return Decimal(str(value))


def static_initial_balance_floor(initial_balance, drawdown_pct) -> Decimal:
    return _d(initial_balance) * (Decimal("1") - _d(drawdown_pct))


def start_of_day_balance_floor(start_of_day_balance, drawdown_pct) -> Decimal:
    return _d(start_of_day_balance) * (Decimal("1") - _d(drawdown_pct))


def start_of_day_equity_floor(start_of_day_equity, drawdown_pct) -> Decimal:
    return _d(start_of_day_equity) * (Decimal("1") - _d(drawdown_pct))


def trailing_floor(high_water_value, drawdown_pct) -> Decimal:
    return _d(high_water_value) * (Decimal("1") - _d(drawdown_pct))


def qualifying_profit_threshold(account_size, minimum_profit_pct) -> Decimal:
    return _d(account_size) * _d(minimum_profit_pct)


def qualifies_trading_day(*, day_closed_profit, trades_count, account_size, mode, minimum_profit_pct=None) -> bool:
    normalized = str(mode or "ANY_TRADE_DAY").upper()
    if normalized == "ANY_TRADE_DAY":
        return int(trades_count or 0) > 0
    if normalized == "MIN_PROFIT_DAY":
        if minimum_profit_pct is None:
            raise ValueError("minimum_profit_pct is required for MIN_PROFIT_DAY")
        return _d(day_closed_profit) >= qualifying_profit_threshold(account_size, minimum_profit_pct)
    raise ValueError(f"Unsupported qualifying day mode: {mode}")


def calculate_daily_floor(mode, *, initial_balance, start_balance, start_equity, drawdown_pct) -> Decimal:
    normalized = str(mode).upper()
    if normalized == "STATIC_INITIAL_BALANCE":
        # Daily drawdown resets each funded trading day. In this mode the
        # *allowance amount* is fixed from the initial account size, while the
        # day's floor is anchored to start-of-day equity. Example: $5,000 and
        # 5% => a fixed $250 daily allowance. If the next day starts at $4,900,
        # that day's floor is $4,650 rather than permanently remaining $4,750.
        allowance = _d(initial_balance) * _d(drawdown_pct)
        return _d(start_equity) - allowance
    if normalized == "START_OF_DAY_BALANCE":
        return start_of_day_balance_floor(start_balance, drawdown_pct)
    if normalized == "START_OF_DAY_EQUITY":
        return start_of_day_equity_floor(start_equity, drawdown_pct)
    raise ValueError(f"Unsupported daily drawdown mode: {mode}")


def calculate_max_loss_floor(mode, *, initial_balance, high_water_balance, high_water_equity, drawdown_pct) -> Decimal:
    normalized = str(mode).upper()
    if normalized == "STATIC_INITIAL_BALANCE":
        return static_initial_balance_floor(initial_balance, drawdown_pct)
    if normalized == "TRAILING_BALANCE":
        return trailing_floor(high_water_balance, drawdown_pct)
    if normalized in {"TRAILING_EQUITY", "HIGH_WATER_MARK"}:
        return trailing_floor(high_water_equity, drawdown_pct)
    raise ValueError(f"Unsupported maximum drawdown mode: {mode}")


def remaining_loss_capacity(current_equity, floor) -> Decimal:
    return max(Decimal("0"), _d(current_equity) - _d(floor))


def evaluate_consistency(best_profitable_day, daily_profits: Iterable, maximum_percentage):
    total_positive = sum((_d(x) for x in daily_profits if _d(x) > 0), Decimal("0"))
    pct = consistency_percentage(best_profitable_day, total_positive)
    return {"consistency_pct": pct, "total_positive_profit": total_positive, "satisfied": pct <= _d(maximum_percentage)}
