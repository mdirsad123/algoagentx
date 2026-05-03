import datetime
import inspect
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    from app.services.trading.risk_engine import calculate_position_size
    from app.services.trading.pnl_engine import calculate_trade_pnl
    from app.services.trading.sl_tp_engine import calculate_sl_tp, enrich_sl_tp_indicators
    from app.services.trading.guardrails import RISK_ENGINE_VERSION, PNL_ENGINE_VERSION
except Exception:  # pragma: no cover - keeps legacy isolated script usage safe
    calculate_position_size = None
    calculate_trade_pnl = None
    calculate_sl_tp = None
    enrich_sl_tp_indicators = None
    RISK_ENGINE_VERSION = "legacy"
    PNL_ENGINE_VERSION = "legacy"


@dataclass
class BacktestParams:
    market: str = "FOREX"
    trade_mode: str = "intraday"
    rr_ratio: float = 2.0
    initial_capital: float = 100000.0
    capital_risk_pct: float = 0.01
    price_risk_pct: float = 0.002
    use_strategy_sl_tp: bool = True
    runtime_config: Optional[Dict[str, Any]] = None
    instrument_spec: Optional[Dict[str, Any]] = None


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

    account_currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    asset_class: Optional[str] = None
    quantity_mode: Optional[str] = None
    lot_size: Optional[float] = None
    actual_risk_amount: Optional[float] = None
    risk_ticks: Optional[float] = None
    risk_pips: Optional[float] = None
    reward_ticks: Optional[float] = None
    expected_reward_amount: Optional[float] = None
    sl_mode: Optional[str] = None
    position_size_mode: Optional[str] = None
    runtime_config_snapshot: Optional[Dict[str, Any]] = field(default=None)
    instrument_spec_snapshot: Optional[Dict[str, Any]] = field(default=None)
    sizing_status: Optional[str] = None
    sizing_rejected_reason: Optional[str] = None
    lifecycle_events: List[Dict[str, Any]] = field(default_factory=list)


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
    account_currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    quantity_mode: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    rejected_trade_count: int = 0
    rejection_reasons: Dict[str, int] = field(default_factory=dict)


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


def _normalize_side(position: int) -> str:
    return "BUY" if int(position) == 1 else "SELL"


def _legacy_instrument_spec(backtest_params: BacktestParams) -> Dict[str, Any]:
    return {
        "quantity_mode": "SHARES",
        "account_currency": "INR" if str(backtest_params.market).upper() == "INDIA" else "USD",
        "currency_symbol": "₹" if str(backtest_params.market).upper() == "INDIA" else "$",
        "tick_size": 0.01,
        "tick_value_per_lot": 0,
        "pip_size": 0.01,
        "min_quantity": 1,
        "quantity_step": 1,
        "asset_class": str(backtest_params.market).upper(),
    }


def _calculate_legacy_sl_tp(entry_price: float, position: int, signal_row: pd.Series, backtest_params: BacktestParams) -> tuple[float, float]:
    strategy_sl = _safe_float(signal_row.get("strategy_stop_loss"), None)
    if backtest_params.use_strategy_sl_tp and strategy_sl is not None and strategy_sl > 0:
        stop_loss = strategy_sl
    else:
        stop_loss = entry_price * (1 - backtest_params.price_risk_pct) if position == 1 else entry_price * (1 + backtest_params.price_risk_pct)
    risk_per_unit = abs(entry_price - stop_loss)
    strategy_target = _safe_float(signal_row.get("strategy_target"), None)
    if backtest_params.use_strategy_sl_tp and strategy_target is not None and strategy_target > 0:
        valid_target = (position == 1 and strategy_target > entry_price) or (position == -1 and strategy_target < entry_price)
        target = strategy_target if valid_target else None
    else:
        target = None
    if target is None:
        target = entry_price + (risk_per_unit * backtest_params.rr_ratio) if position == 1 else entry_price - (risk_per_unit * backtest_params.rr_ratio)
    return float(stop_loss), float(target)



def _event(event_type: str, candle_time: Any, *, old_sl: Any = None, new_sl: Any = None, reason: str | None = None, price: Any = None, r_value: Any = None, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "event_type": event_type,
        "candle_time": pd.Timestamp(candle_time).isoformat() if candle_time is not None else None,
        "old_sl": _safe_float(old_sl, None),
        "new_sl": _safe_float(new_sl, None),
        "reason": reason,
        "price": _safe_float(price, None),
        "r_value": _safe_float(r_value, None),
    }
    if extra:
        payload.update(extra)
    return payload


def _favourable_r(position: int, entry_price: float, high: float, low: float, initial_risk_points: float) -> float:
    if initial_risk_points <= 0:
        return 0.0
    favourable_move = (float(high) - float(entry_price)) if position == 1 else (float(entry_price) - float(low))
    return max(0.0, float(favourable_move) / float(initial_risk_points))


def _move_stop_if_tighter(position: int, current_sl: float, candidate_sl: Optional[float]) -> Optional[float]:
    if candidate_sl is None:
        return None
    candidate = float(candidate_sl)
    current = float(current_sl)
    if position == 1 and candidate > current:
        return candidate
    if position == -1 and candidate < current:
        return candidate
    return None


def _trailing_stop_candidate(df: pd.DataFrame, index: int, position: int, row: pd.Series, runtime_config: Dict[str, Any], initial_risk_points: float) -> Optional[float]:
    tm_cfg = runtime_config.get("trade_management") or {}
    sl_cfg = runtime_config.get("sl_tp") or {}
    tm_cfg = runtime_config.get("trade_management") or {}
    mode = str(tm_cfg.get("trailing_mode") or "ATR_TRAIL").upper()
    close = _safe_float(row.get("Close"), None)
    if close is None:
        return None
    if mode == "EMA20_TRAIL":
        ema = _safe_float(row.get("_aax_ema20"), None)
        return ema
    if mode == "SWING_TRAIL":
        lookback = max(1, int(tm_cfg.get("trailing_swing_lookback") or sl_cfg.get("swing_lookback") or 5))
        start = max(0, int(index) - lookback + 1)
        window = df.iloc[start : int(index) + 1]
        return _safe_float(window["Low"].min() if position == 1 else window["High"].max(), None)
    # ATR_TRAIL default. Fallback to initial risk distance if ATR is unavailable.
    atr = _safe_float(row.get("_aax_atr"), None)
    multiplier = float(tm_cfg.get("trail_atr_multiplier") or 1.0)
    distance = (atr * multiplier) if atr and atr > 0 else float(initial_risk_points)
    return (close - distance) if position == 1 else (close + distance)


def _partial_size(value: float | None, percent: float) -> float | None:
    if value is None:
        return None
    pct = max(0.0, min(1.0, float(percent or 0)))
    return float(value) * pct

def _build_summary(trades: List[Trade], equity_curve: List[float], final_capital: float, initial_capital: float, instrument_spec: dict[str, Any]) -> dict[str, Any]:
    pnls = [float(t.pnl or 0) for t in trades]
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = sum(p for p in pnls if p < 0)
    lot_sizes = [float(t.lot_size) for t in trades if t.lot_size is not None]
    quantities = [float(t.quantity) for t in trades if t.quantity is not None]
    actual_risks = [float(t.actual_risk_amount or t.risk_amount or 0) for t in trades if (t.actual_risk_amount or t.risk_amount)]
    return {
        "account_currency": instrument_spec.get("account_currency"),
        "currency_symbol": instrument_spec.get("currency_symbol"),
        "quantity_mode": instrument_spec.get("quantity_mode"),
        "total_trades": len(trades),
        "net_pnl": float(final_capital - initial_capital),
        "gross_profit": float(gross_profit),
        "gross_loss": float(gross_loss),
        "avg_actual_risk": float(sum(actual_risks) / len(actual_risks)) if actual_risks else 0.0,
        "avg_lot_size": float(sum(lot_sizes) / len(lot_sizes)) if lot_sizes else None,
        "avg_quantity": float(sum(quantities) / len(quantities)) if quantities else None,
    }


def run_backtest_engine(
    market_data: pd.DataFrame,
    strategy_class: Any,
    strategy_params: Optional[Dict[str, Any]] = None,
    backtest_params: Optional[BacktestParams] = None,
) -> BacktestResult:
    """Instrument-aware AlgoAgentX backtest engine.

    Strategy remains signal-only. The engine handles next-candle entry, SL/TP,
    risk sizing and PnL. Legacy behavior is preserved when instrument specs or
    runtime config are not provided.
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

    runtime_config = dict(backtest_params.runtime_config or {})
    risk_cfg = runtime_config.get("risk") or {}
    exec_cfg = runtime_config.get("execution") or {}
    sl_cfg = runtime_config.get("sl_tp") or {}
    tm_cfg = runtime_config.get("trade_management") or {}

    instrument_spec = dict(backtest_params.instrument_spec or {})
    warnings: List[str] = []
    rejected_trade_count = 0
    rejection_reasons: Dict[str, int] = {}

    def reject_trade(reason: str) -> None:
        nonlocal rejected_trade_count, rejection_reasons
        key = str(reason or "Unknown rejection")
        rejected_trade_count += 1
        rejection_reasons[key] = rejection_reasons.get(key, 0) + 1
    professional_mode = bool(instrument_spec and calculate_position_size and calculate_trade_pnl and calculate_sl_tp)
    if not professional_mode:
        warnings.append("Instrument spec missing. Legacy sizing used.")
        instrument_spec = _legacy_instrument_spec(backtest_params)
    else:
        instrument_spec.setdefault("quantity_mode", "SHARES")
        instrument_spec.setdefault("account_currency", risk_cfg.get("account_currency") or "USD")
        instrument_spec.setdefault("currency_symbol", "$" if instrument_spec.get("account_currency") == "USD" else "₹")

    if professional_mode and enrich_sl_tp_indicators:
        df = enrich_sl_tp_indicators(df, runtime_config)

    capital = float(backtest_params.initial_capital)
    equity_curve = [capital]
    trades: List[Trade] = []

    position = 0
    entry_price: Optional[float] = None
    entry_dt = None
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    quantity = 0.0
    lot_size: Optional[float] = None
    quantity_mode = str(instrument_spec.get("quantity_mode") or "SHARES").upper()
    entry_signal_reason: Optional[str] = None
    entry_risk_result: dict[str, Any] = {}
    entry_sl_result: dict[str, Any] = {}
    initial_stop_loss: Optional[float] = None
    initial_target: Optional[float] = None
    initial_risk_points: float = 0.0
    lifecycle_events: List[Dict[str, Any]] = []
    breakeven_moved = False
    partial_exit_done = False
    partial_pnl_total = 0.0
    original_quantity: Optional[float] = None
    original_lot_size: Optional[float] = None

    max_trades_per_day = exec_cfg.get("max_trades_per_day")
    trades_by_day: dict[Any, int] = {}
    allow_long = bool(exec_cfg.get("allow_long", True))
    allow_short = bool(exec_cfg.get("allow_short", True))
    exit_on_opposite_signal = bool(exec_cfg.get("exit_on_opposite_signal", True))

    for i in range(1, len(df)):
        row = df.iloc[i]
        signal_row = df.iloc[i - 1]

        current_dt = row["Date"]
        signal = int(signal_row.get("Position", 0) or 0)

        open_price = float(row["Open"])
        high = float(row["High"])
        low = float(row["Low"])

        if position != 0 and entry_price is not None and stop_loss is not None and target is not None:
            exit_price = None
            reason = None
            current_r = _favourable_r(position, float(entry_price), high, low, float(initial_risk_points or abs(float(entry_price) - float(initial_stop_loss or stop_loss))))

            if exit_on_opposite_signal and signal == -position:
                exit_price = open_price
                reason = "OPPOSITE_SIGNAL"

            if exit_price is None:
                if position == 1:
                    if low <= stop_loss:
                        exit_price = stop_loss
                        reason = "STOP_LOSS_HIT" if stop_loss > float(initial_stop_loss or stop_loss) else "SL"
                    elif high >= target:
                        exit_price = target
                        reason = "TAKE_PROFIT_HIT"
                elif position == -1:
                    if high >= stop_loss:
                        exit_price = stop_loss
                        reason = "STOP_LOSS_HIT" if stop_loss < float(initial_stop_loss or stop_loss) else "SL"
                    elif low <= target:
                        exit_price = target
                        reason = "TAKE_PROFIT_HIT"

            if exit_price is None and tm_cfg:
                # Breakeven: once trade reaches configured R, tighten SL to entry +/- optional offset.
                if bool(tm_cfg.get("break_even_enabled", False)) and not breakeven_moved:
                    trigger_r = float(tm_cfg.get("break_even_trigger_r") or 1.0)
                    offset_points = float(tm_cfg.get("break_even_offset_points") or 0.0)
                    if current_r >= trigger_r:
                        candidate = float(entry_price) + offset_points if position == 1 else float(entry_price) - offset_points
                        tightened = _move_stop_if_tighter(position, float(stop_loss), candidate)
                        if tightened is not None:
                            old_sl = float(stop_loss)
                            stop_loss = tightened
                            breakeven_moved = True
                            lifecycle_events.append(_event("BREAK_EVEN_MOVED", current_dt, old_sl=old_sl, new_sl=stop_loss, reason="Reached breakeven trigger R", price=open_price, r_value=current_r))

                # Partial exit: close a part of the active position at a configured R, keep the remainder running.
                if bool(tm_cfg.get("partial_exit_enabled", False)) and not partial_exit_done:
                    partial_at_r = float(tm_cfg.get("partial_exit_at_r") or 1.0)
                    partial_pct = float(tm_cfg.get("partial_exit_percent") or 0.5)
                    if current_r >= partial_at_r and 0 < partial_pct < 1:
                        partial_exit_price = float(entry_price) + (float(initial_risk_points) * partial_at_r) if position == 1 else float(entry_price) - (float(initial_risk_points) * partial_at_r)
                        partial_qty = _partial_size(quantity if quantity_mode != "LOTS" else None, partial_pct)
                        partial_lot = _partial_size(lot_size if quantity_mode == "LOTS" else None, partial_pct)
                        if professional_mode and calculate_trade_pnl:
                            partial_result = calculate_trade_pnl(
                                entry_price=float(entry_price),
                                exit_price=float(partial_exit_price),
                                side=_normalize_side(position),
                                quantity_mode=quantity_mode,
                                quantity=partial_qty if quantity_mode != "LOTS" else None,
                                lot_size=partial_lot,
                                instrument_spec=instrument_spec,
                            )
                            partial_pnl = float(partial_result.get("pnl") or 0.0) if partial_result.get("status") == "OK" else 0.0
                        else:
                            partial_pnl = (float(partial_exit_price) - float(entry_price)) * position * float(partial_qty or 0.0)
                        if partial_pnl or partial_qty or partial_lot:
                            partial_pnl_total += partial_pnl
                            capital += partial_pnl
                            if quantity_mode == "LOTS" and partial_lot is not None and lot_size is not None:
                                lot_size = max(0.0, float(lot_size) - float(partial_lot))
                            elif partial_qty is not None:
                                quantity = max(0.0, float(quantity) - float(partial_qty))
                            partial_exit_done = True
                            lifecycle_events.append(_event("PARTIAL_EXIT", current_dt, reason="Partial exit reached configured R", price=partial_exit_price, r_value=current_r, extra={"partial_exit_percent": partial_pct, "partial_pnl": partial_pnl, "remaining_quantity": quantity, "remaining_lot_size": lot_size}))

                # Trailing stop: only starts after configured R and never loosens stop.
                if bool(tm_cfg.get("trailing_enabled", False)):
                    trail_start_r = float(tm_cfg.get("trail_start_r") or 1.5)
                    if current_r >= trail_start_r:
                        candidate = _trailing_stop_candidate(df, i, position, row, runtime_config, float(initial_risk_points or 0.0))
                        tightened = _move_stop_if_tighter(position, float(stop_loss), candidate)
                        if tightened is not None:
                            old_sl = float(stop_loss)
                            stop_loss = tightened
                            lifecycle_events.append(_event("TRAILING_STOP_MOVED", current_dt, old_sl=old_sl, new_sl=stop_loss, reason=str(tm_cfg.get("trailing_mode") or "ATR_TRAIL"), price=open_price, r_value=current_r))

            if exit_price is not None:
                if professional_mode and calculate_trade_pnl:
                    pnl_result = calculate_trade_pnl(
                        entry_price=float(entry_price),
                        exit_price=float(exit_price),
                        side=_normalize_side(position),
                        quantity_mode=quantity_mode,
                        quantity=quantity if quantity_mode != "LOTS" else None,
                        lot_size=lot_size,
                        instrument_spec=instrument_spec,
                    )
                    remaining_pnl = float(pnl_result.get("pnl") or 0.0) if pnl_result.get("status") == "OK" else 0.0
                else:
                    remaining_pnl = (float(exit_price) - float(entry_price)) * position * quantity
                    pnl_result = {"ticks": None, "pips": None}
                pnl = float(partial_pnl_total) + float(remaining_pnl)

                risk_points = float(entry_risk_result.get("risk_points") or initial_risk_points or abs(float(entry_price) - float(initial_stop_loss or stop_loss)))
                reward_points = float(entry_sl_result.get("reward_points") or abs(float(target) - float(entry_price)))
                rr_ratio = (reward_points / risk_points) if risk_points > 0 else 0.0
                risk_amount = float(entry_risk_result.get("risk_amount") or risk_points * float(original_quantity or quantity or 0))
                actual_risk_amount = float(entry_risk_result.get("actual_risk_amount") or risk_amount or 0)
                expected_reward_amount = actual_risk_amount * rr_ratio if actual_risk_amount else None
                reward_amount = expected_reward_amount or (reward_points * float(original_quantity or quantity or 0))
                r_multiple = (float(pnl) / actual_risk_amount) if actual_risk_amount > 0 else 0.0
                capital += remaining_pnl
                lifecycle_events.append(_event(str(reason), current_dt, old_sl=stop_loss, new_sl=stop_loss, reason="Trade closed", price=exit_price, r_value=r_multiple, extra={"pnl": pnl, "remaining_pnl": remaining_pnl, "partial_pnl": partial_pnl_total}))
                trades.append(
                    Trade(
                        entry_datetime=entry_dt,
                        exit_datetime=current_dt,
                        direction="LONG" if position == 1 else "SHORT",
                        entry_price=float(entry_price),
                        exit_price=float(exit_price),
                        stop_loss=float(stop_loss),
                        target=float(target),
                        quantity=float(original_quantity if original_quantity is not None else quantity or 0),
                        pnl=float(pnl),
                        result="WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN",
                        capital_after_trade=float(capital),
                        exit_reason=str(reason),
                        risk_points=float(risk_points),
                        reward_points=float(reward_points),
                        rr_ratio=float(rr_ratio),
                        risk_amount=float(risk_amount),
                        reward_amount=float(reward_amount or 0),
                        r_multiple=float(r_multiple),
                        signal_reason=entry_signal_reason,
                        account_currency=instrument_spec.get("account_currency"),
                        currency_symbol=instrument_spec.get("currency_symbol"),
                        asset_class=instrument_spec.get("asset_class"),
                        quantity_mode=quantity_mode,
                        lot_size=float(original_lot_size) if original_lot_size is not None else lot_size,
                        actual_risk_amount=float(actual_risk_amount),
                        risk_ticks=entry_risk_result.get("risk_ticks"),
                        risk_pips=entry_risk_result.get("risk_pips"),
                        reward_ticks=(reward_points / float(instrument_spec.get("tick_size") or 0)) if float(instrument_spec.get("tick_size") or 0) > 0 else None,
                        expected_reward_amount=expected_reward_amount,
                        sl_mode=entry_sl_result.get("sl_mode") or sl_cfg.get("sl_mode"),
                        position_size_mode=risk_cfg.get("position_size_mode") or "RISK_BASED",
                        runtime_config_snapshot=runtime_config,
                        instrument_spec_snapshot=instrument_spec,
                        sizing_status=entry_risk_result.get("status"),
                        sizing_rejected_reason=entry_risk_result.get("rejected_reason"),
                        lifecycle_events=list(lifecycle_events),
                    )
                )
                position = 0
                entry_price = None
                entry_dt = None
                stop_loss = None
                target = None
                quantity = 0.0
                lot_size = None
                entry_signal_reason = None
                entry_risk_result = {}
                entry_sl_result = {}
                initial_stop_loss = None
                initial_target = None
                initial_risk_points = 0.0
                lifecycle_events = []
                breakeven_moved = False
                partial_exit_done = False
                partial_pnl_total = 0.0
                original_quantity = None
                original_lot_size = None

        if position == 0 and signal != 0:
            if signal == 1 and not allow_long:
                equity_curve.append(capital)
                continue
            if signal == -1 and not allow_short:
                equity_curve.append(capital)
                continue
            trade_day = pd.Timestamp(current_dt).date()
            if max_trades_per_day is not None and trades_by_day.get(trade_day, 0) >= int(max_trades_per_day):
                equity_curve.append(capital)
                continue

            pending_position = signal
            pending_entry_price = open_price

            raw_reason = signal_row.get("signal_reason") if "signal_reason" in signal_row.index else None
            pending_signal_reason = None if raw_reason is None or pd.isna(raw_reason) else str(raw_reason)

            if professional_mode and calculate_sl_tp:
                entry_sl_result = calculate_sl_tp(
                    df=df,
                    signal_index=i - 1,
                    entry_price=pending_entry_price,
                    side=_normalize_side(pending_position),
                    runtime_config=runtime_config,
                    suggested_stop_loss=_safe_float(signal_row.get("strategy_stop_loss"), None),
                    suggested_target=_safe_float(signal_row.get("strategy_target"), None),
                )
                if entry_sl_result.get("status") != "OK":
                    reject_trade(entry_sl_result.get("rejected_reason") or "SL/TP calculation rejected trade.")
                    equity_curve.append(capital)
                    continue
                pending_stop_loss = float(entry_sl_result["stop_loss"])
                pending_target = float(entry_sl_result["target"])
            else:
                pending_stop_loss, pending_target = _calculate_legacy_sl_tp(pending_entry_price, pending_position, signal_row, backtest_params)
                entry_sl_result = {
                    "status": "OK",
                    "sl_mode": "LEGACY_FIXED_PERCENT",
                    "stop_loss": pending_stop_loss,
                    "target": pending_target,
                    "risk_points": abs(pending_entry_price - pending_stop_loss),
                    "reward_points": abs(pending_target - pending_entry_price),
                    "rr_ratio": backtest_params.rr_ratio,
                }

            if (pending_position == 1 and pending_stop_loss >= pending_entry_price) or (pending_position == -1 and pending_stop_loss <= pending_entry_price):
                side_name = _normalize_side(pending_position)
                reject_trade(f"Stop loss is invalid for {side_name}. SL must be below entry for BUY and above entry for SELL.")
                equity_curve.append(capital)
                continue

            risk_per_unit = abs(pending_entry_price - pending_stop_loss)
            if risk_per_unit <= 0:
                reject_trade("Stop loss distance must be greater than 0.")
                equity_curve.append(capital)
                continue

            if professional_mode and calculate_position_size:
                entry_risk_result = calculate_position_size(
                    entry_price=pending_entry_price,
                    stop_loss=pending_stop_loss,
                    capital=capital,
                    risk_percent=float(risk_cfg.get("risk_percent") or backtest_params.capital_risk_pct),
                    instrument_spec=instrument_spec,
                    position_size_mode=str(risk_cfg.get("position_size_mode") or "RISK_BASED"),
                    fixed_lot=risk_cfg.get("fixed_lot"),
                    fixed_quantity=risk_cfg.get("fixed_quantity"),
                    max_lot_cap=risk_cfg.get("max_lot_cap"),
                    max_quantity_cap=risk_cfg.get("max_quantity_cap"),
                    side=_normalize_side(pending_position),
                )
                if entry_risk_result.get("status") != "OK":
                    reject_trade(entry_risk_result.get("rejected_reason") or "Risk engine rejected trade.")
                    equity_curve.append(capital)
                    continue
                quantity_mode = str(entry_risk_result.get("quantity_mode") or instrument_spec.get("quantity_mode") or "SHARES").upper()
                if quantity_mode == "LOTS":
                    lot_size = float(entry_risk_result.get("final_lot_size") or 0)
                    quantity = 0.0
                    if lot_size <= 0:
                        reject_trade("Calculated lot size is invalid or below minimum.")
                        equity_curve.append(capital)
                        continue
                else:
                    quantity = float(entry_risk_result.get("final_quantity") or 0)
                    lot_size = None
                    if quantity <= 0:
                        reject_trade("Calculated quantity is invalid or below minimum.")
                        equity_curve.append(capital)
                        continue
            else:
                risk_amount = capital * backtest_params.capital_risk_pct
                quantity = risk_amount / risk_per_unit
                lot_size = None
                entry_risk_result = {
                    "status": "OK",
                    "risk_amount": risk_amount,
                    "actual_risk_amount": risk_amount,
                    "quantity_mode": "SHARES",
                    "final_quantity": quantity,
                }

            position = pending_position
            entry_price = pending_entry_price
            entry_dt = current_dt
            stop_loss = pending_stop_loss
            target = pending_target
            initial_stop_loss = float(pending_stop_loss)
            initial_target = float(pending_target)
            initial_risk_points = float(entry_sl_result.get("risk_points") or abs(float(pending_entry_price) - float(pending_stop_loss)))
            original_quantity = float(quantity or 0.0) if quantity_mode != "LOTS" else None
            original_lot_size = float(lot_size or 0.0) if quantity_mode == "LOTS" else None
            lifecycle_events = [_event("ENTRY", current_dt, old_sl=None, new_sl=stop_loss, reason="Position opened", price=entry_price, r_value=0.0, extra={"target": target, "quantity": quantity, "lot_size": lot_size})]
            breakeven_moved = False
            partial_exit_done = False
            partial_pnl_total = 0.0
            entry_signal_reason = pending_signal_reason
            trades_by_day[trade_day] = trades_by_day.get(trade_day, 0) + 1

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
    summary = _build_summary(trades, equity_curve, capital, float(backtest_params.initial_capital), instrument_spec)
    summary["max_drawdown"] = max_drawdown
    summary["risk_engine_version"] = RISK_ENGINE_VERSION
    summary["pnl_engine_version"] = PNL_ENGINE_VERSION
    summary["warnings"] = warnings
    summary["rejected_trade_count"] = int(rejected_trade_count)
    summary["rejection_reasons"] = dict(rejection_reasons)

    return BacktestResult(
        trades=trades,
        equity_curve=equity_curve,
        final_capital=float(capital),
        total_return=float(total_return),
        total_trades=len(trades),
        win_rate=float(win_rate),
        max_drawdown=float(max_drawdown),
        sharpe_ratio=float(sharpe_ratio),
        account_currency=instrument_spec.get("account_currency"),
        currency_symbol=instrument_spec.get("currency_symbol"),
        quantity_mode=str(instrument_spec.get("quantity_mode") or quantity_mode).upper(),
        warnings=warnings,
        summary=summary,
        rejected_trade_count=int(rejected_trade_count),
        rejection_reasons=dict(rejection_reasons),
    )
