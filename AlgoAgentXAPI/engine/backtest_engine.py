import datetime
import inspect
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class BacktestParams:
    market: str = "FOREX"
    trade_mode: str = "intraday"
    rr_ratio: float = 2.0
    initial_capital: float = 100000.0
    capital_risk_pct: float = 0.01
    price_risk_pct: float = 0.002
    use_strategy_sl_tp: bool = True


@dataclass
class Trade:
    entry_datetime: datetime.datetime
    exit_datetime: datetime.datetime
    direction: str
    entry_price: float
    exit_price: float
    stop_loss: float
    target: float
    quantity: float
    pnl: float
    result: str
    capital_after_trade: float
    exit_reason: str
    risk_points: float = 0.0
    reward_points: float = 0.0
    rr_ratio: float = 0.0
    risk_amount: float = 0.0
    reward_amount: float = 0.0
    r_multiple: float = 0.0
    signal_reason: Optional[str] = None


@dataclass
class BacktestResult:
    trades: List[Trade]
    equity_curve: List[float]
    final_capital: float
    total_return: float
    total_trades: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float


def _filter_strategy_params(strategy_class: Any, strategy_params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        signature = inspect.signature(strategy_class.__init__)
        if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()):
            return dict(strategy_params or {})
        allowed = {
            name
            for name, param in signature.parameters.items()
            if name not in {"self", "df"}
            and param.kind in {inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY}
        }
        return {key: value for key, value in (strategy_params or {}).items() if key in allowed}
    except (TypeError, ValueError):
        return dict(strategy_params or {})


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def run_backtest_engine(
    market_data: pd.DataFrame,
    strategy_class: Any,
    strategy_params: Optional[Dict[str, Any]] = None,
    backtest_params: Optional[BacktestParams] = None,
) -> BacktestResult:
    """
    Forex / Gold / BTC safe backtest engine.

    Execution model:
    - Strategy creates Position on the signal candle after candle close.
    - Engine enters on the NEXT candle open.
    - Opposite signal exits on the NEXT candle open after opposite signal confirmation.
    - No Indian EOD/session logic.
    - No max-bars forced exit.
    - Exits only by SL / TARGET / OPPOSITE_SIGNAL.
    """
    if backtest_params is None:
        backtest_params = BacktestParams()
    if strategy_params is None:
        strategy_params = {}

    df = market_data.copy()
    required_columns = ["Date", "Open", "High", "Low", "Close"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"market_data missing required column: {col}")

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    for col in ["Open", "High", "Low", "Close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Date", "Open", "High", "Low", "Close"]).reset_index(drop=True)

    filtered_params = _filter_strategy_params(strategy_class, strategy_params)
    strategy = strategy_class(df, **filtered_params)
    df = strategy.generate().copy()

    if "Position" not in df.columns:
        raise ValueError("Strategy must return a DataFrame with Position column.")

    capital = float(backtest_params.initial_capital)
    equity_curve = [capital]
    trades: List[Trade] = []

    position = 0
    entry_price: Optional[float] = None
    entry_dt = None
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    quantity = 0.0
    entry_signal_reason: Optional[str] = None

    # i is current execution candle. signal_row is previous candle, already closed.
    for i in range(1, len(df)):
        row = df.iloc[i]
        signal_row = df.iloc[i - 1]

        current_dt = row["Date"]
        signal = int(signal_row.get("Position", 0) or 0)

        open_price = float(row["Open"])
        high = float(row["High"])
        low = float(row["Low"])

        # -----------------------------
        # EXIT first, so opposite signal closes current position at current open.
        # -----------------------------
        if position != 0 and entry_price is not None and stop_loss is not None and target is not None:
            exit_price = None
            reason = None

            if signal == -position:
                exit_price = open_price
                reason = "OPPOSITE_SIGNAL"

            if exit_price is None:
                if position == 1:
                    if low <= stop_loss:
                        exit_price = stop_loss
                        reason = "SL"
                    elif high >= target:
                        exit_price = target
                        reason = "TARGET"
                elif position == -1:
                    if high >= stop_loss:
                        exit_price = stop_loss
                        reason = "SL"
                    elif low <= target:
                        exit_price = target
                        reason = "TARGET"

            if exit_price is not None:
                pnl = (float(exit_price) - float(entry_price)) * position * quantity
                risk_points = abs(float(entry_price) - float(stop_loss))
                reward_points = abs(float(target) - float(entry_price))
                rr_ratio = (reward_points / risk_points) if risk_points > 0 else 0.0
                risk_amount = risk_points * float(quantity)
                reward_amount = reward_points * float(quantity)
                r_multiple = (float(pnl) / risk_amount) if risk_amount > 0 else 0.0
                capital += pnl
                trades.append(
                    Trade(
                        entry_datetime=entry_dt,
                        exit_datetime=current_dt,
                        direction="LONG" if position == 1 else "SHORT",
                        entry_price=float(entry_price),
                        exit_price=float(exit_price),
                        stop_loss=float(stop_loss),
                        target=float(target),
                        quantity=float(quantity),
                        pnl=float(pnl),
                        result="WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN",
                        capital_after_trade=float(capital),
                        exit_reason=str(reason),
                        risk_points=float(risk_points),
                        reward_points=float(reward_points),
                        rr_ratio=float(rr_ratio),
                        risk_amount=float(risk_amount),
                        reward_amount=float(reward_amount),
                        r_multiple=float(r_multiple),
                        signal_reason=entry_signal_reason,
                    )
                )
                position = 0
                entry_price = None
                entry_dt = None
                stop_loss = None
                target = None
                quantity = 0.0
                entry_signal_reason = None

        # -----------------------------
        # ENTRY after exit. Previous candle signal => current candle open.
        # -----------------------------
        if position == 0 and signal != 0:
            position = signal
            entry_price = open_price
            entry_dt = current_dt

            strategy_sl = _safe_float(signal_row.get("strategy_stop_loss"), None)
            if backtest_params.use_strategy_sl_tp and strategy_sl is not None and strategy_sl > 0:
                stop_loss = strategy_sl
            else:
                stop_loss = entry_price * (1 - backtest_params.price_risk_pct) if position == 1 else entry_price * (1 + backtest_params.price_risk_pct)

            raw_reason = signal_row.get("signal_reason") if "signal_reason" in signal_row.index else None
            entry_signal_reason = None if raw_reason is None or pd.isna(raw_reason) else str(raw_reason)

            if (position == 1 and stop_loss >= entry_price) or (position == -1 and stop_loss <= entry_price):
                position = 0
                entry_price = None
                entry_dt = None
                stop_loss = None
                target = None
                quantity = 0.0
                equity_curve.append(capital)
                continue

            risk_per_unit = abs(entry_price - stop_loss)
            if risk_per_unit <= 0:
                position = 0
                entry_price = None
                entry_dt = None
                stop_loss = None
                target = None
                quantity = 0.0
                equity_curve.append(capital)
                continue

            strategy_target = _safe_float(signal_row.get("strategy_target"), None)
            if backtest_params.use_strategy_sl_tp and strategy_target is not None and strategy_target > 0:
                valid_target = (position == 1 and strategy_target > entry_price) or (position == -1 and strategy_target < entry_price)
                target = strategy_target if valid_target else None
            else:
                target = None
            if target is None:
                target = entry_price + (risk_per_unit * backtest_params.rr_ratio) if position == 1 else entry_price - (risk_per_unit * backtest_params.rr_ratio)

            risk_amount = capital * backtest_params.capital_risk_pct
            quantity = risk_amount / risk_per_unit

        equity_curve.append(capital)

    wins = [trade for trade in trades if trade.pnl > 0]
    win_rate = len(wins) / len(trades) if trades else 0.0

    equity_series = pd.Series(equity_curve)
    if len(equity_series) > 0:
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = float(drawdown.min())
    else:
        max_drawdown = 0.0

    if len(equity_curve) > 1:
        returns = pd.Series(equity_curve).pct_change().dropna()
        sharpe_ratio = float((returns.mean() / returns.std()) * (252 ** 0.5)) if len(returns) > 1 and returns.std() != 0 else 0.0
    else:
        sharpe_ratio = 0.0

    total_return = (capital - float(backtest_params.initial_capital)) / float(backtest_params.initial_capital)

    return BacktestResult(
        trades=trades,
        equity_curve=equity_curve,
        final_capital=float(capital),
        total_return=float(total_return),
        total_trades=len(trades),
        win_rate=float(win_rate),
        max_drawdown=float(max_drawdown),
        sharpe_ratio=float(sharpe_ratio),
    )
