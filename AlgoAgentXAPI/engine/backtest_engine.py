import pandas as pd
import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# ================================
# MARKET SESSION CONFIG
# ================================
MARKET_CONFIG = {
    "INDIA": {
        "timezone": "Asia/Kolkata",
        "session_start": datetime.time(9, 15),
        "session_end": datetime.time(15, 30),
        "entry_cutoff": datetime.time(15, 15),
        "force_exit": True,
    },
    "CRYPTO": {
        "timezone": "UTC",
        "session_start": None,
        "session_end": None,
        "entry_cutoff": None,
        "force_exit": False,
    },
    "FOREX": {
        "timezone": "UTC",
        "session_start": None,
        "session_end": None,
        "entry_cutoff": None,
        "force_exit": False,
    },
}

@dataclass
class BacktestParams:
    market: str = "INDIA"
    trade_mode: str = "intraday"
    rr_ratio: float = 2.0
    initial_capital: float = 100000.0
    capital_risk_pct: float = 0.01
    price_risk_pct: float = 0.002
    max_bars_in_trade: int = 6

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

def run_backtest_engine(
    market_data: pd.DataFrame,
    strategy_class: Any,
    strategy_params: Optional[Dict[str, Any]] = None,
    backtest_params: Optional[BacktestParams] = None
) -> BacktestResult:
    """
    Pure function backtest engine.

    Args:
        market_data: DataFrame with columns [Date, Open, High, Low, Close, Volume]
        strategy_class: Strategy class with generate() method
        strategy_params: Dict of params for strategy
        backtest_params: BacktestParams dataclass

    Returns:
        BacktestResult with trades, equity_curve, and metrics
    """
    if backtest_params is None:
        backtest_params = BacktestParams()

    if strategy_params is None:
        strategy_params = {}

    df = market_data.copy()
    df["Date"] = pd.to_datetime(df["Date"])

    # Initialize strategy
    strategy = strategy_class(df, **strategy_params)
    df = strategy.generate().copy()

    capital = backtest_params.initial_capital
    equity_curve = [capital]
    trades = []

    position = 0
    entry_price = None
    entry_dt = None
    stop_loss = None
    target = None
    quantity = 0
    bars_held = 0

    market_cfg = MARKET_CONFIG[backtest_params.market]

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev_row = df.iloc[i - 1]

        signal = row.get("Position", 0)
        current_dt = row["Date"]
        prev_dt = prev_row["Date"]

        current_time = current_dt.time()
        current_date = current_dt.date()
        prev_date = prev_dt.date()

        # ================================
        # ENTRY LOGIC
        # ================================
        if position == 0 and signal != 0:
            # Entry cutoff for Indian intraday/scalp
            if (
                backtest_params.market == "INDIA"
                and backtest_params.trade_mode in ["scalp", "intraday"]
                and current_time >= market_cfg["entry_cutoff"]
            ):
                equity_curve.append(capital)
                continue

            position = signal
            entry_price = row["Open"]
            entry_dt = current_dt
            bars_held = 0

            risk_amount = capital * backtest_params.capital_risk_pct

            if position == 1:
                stop_loss = entry_price * (1 - backtest_params.price_risk_pct)
                target = entry_price * (1 + backtest_params.price_risk_pct * backtest_params.rr_ratio)
            else:
                stop_loss = entry_price * (1 + backtest_params.price_risk_pct)
                target = entry_price * (1 - backtest_params.price_risk_pct * backtest_params.rr_ratio)

            risk_per_unit = abs(entry_price - stop_loss)
            quantity = risk_amount / risk_per_unit if risk_per_unit > 0 else 0

        # ================================
        # EXIT LOGIC
        # ================================
        elif position != 0:
            bars_held += 1
            exit_price = None
            reason = None

            # SL / TARGET
            if position == 1:
                if row["Low"] <= stop_loss:
                    exit_price = stop_loss
                    reason = "SL"
                elif row["High"] >= target:
                    exit_price = target
                    reason = "TARGET"
            else:
                if row["High"] >= stop_loss:
                    exit_price = stop_loss
                    reason = "SL"
                elif row["Low"] <= target:
                    exit_price = target
                    reason = "TARGET"

            # Forced EOD exit (Indian market)
            if (
                exit_price is None
                and backtest_params.market == "INDIA"
                and backtest_params.trade_mode in ["scalp", "intraday"]
                and current_time >= market_cfg["entry_cutoff"]
            ):
                exit_price = row["Close"]
                reason = "FORCED_EOD_EXIT"

            # Swing / overnight protection
            if (
                exit_price is None
                and backtest_params.trade_mode in ["scalp", "intraday"]
                and current_date != prev_date
            ):
                exit_price = prev_row["Close"]
                reason = "EOD_EXIT"

            # Opposite signal
            if exit_price is None and signal == -position:
                exit_price = row["Open"]
                reason = "OPPOSITE_SIGNAL"

            if exit_price is not None:
                pnl = (exit_price - entry_price) * position * quantity
                capital += pnl

                trade = Trade(
                    entry_datetime=entry_dt,
                    exit_datetime=current_dt,
                    direction="LONG" if position == 1 else "SHORT",
                    entry_price=entry_price,
                    exit_price=exit_price,
                    stop_loss=stop_loss,
                    target=target,
                    quantity=quantity,
                    pnl=pnl,
                    result="WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN",
                    capital_after_trade=capital,
                    exit_reason=reason,
                )
                trades.append(trade)

                position = 0
                entry_price = None
                stop_loss = None
                target = None
                quantity = 0
                bars_held = 0

        equity_curve.append(capital)

    # Calculate metrics
    if len(trades) > 0:
        wins = [t for t in trades if t.pnl > 0]
        win_rate = len(wins) / len(trades)
    else:
        win_rate = 0.0

    # Max drawdown
    equity_series = pd.Series(equity_curve)
    rolling_max = equity_series.cummax()
    drawdown = (equity_series - rolling_max) / rolling_max
    max_drawdown = drawdown.min()

    # Sharpe ratio (annualized)
    if len(equity_curve) > 1:
        returns = pd.Series(equity_curve).pct_change().dropna()
        if returns.std() != 0:
            sharpe_ratio = (returns.mean() / returns.std()) * (252 ** 0.5)
        else:
            sharpe_ratio = 0.0
    else:
        sharpe_ratio = 0.0

    total_return = (capital - backtest_params.initial_capital) / backtest_params.initial_capital

    return BacktestResult(
        trades=trades,
        equity_curve=equity_curve,
        final_capital=capital,
        total_return=total_return,
        total_trades=len(trades),
        win_rate=win_rate,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
    )
