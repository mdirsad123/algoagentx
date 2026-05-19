from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any, Optional
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import BrokerAccount, Instrument, Strategy, StrategyDeployment, StrategyRuntimePreset, LiveMarketCandle
from ..brokers.factory import get_broker_code
from ..trading.risk_engine import calculate_position_size
from ..trading.runtime_config_service import deep_merge_runtime_config, resolve_runtime_config, validate_runtime_config
from .pnl_service import to_decimal
from .capital_service import get_effective_trading_capital
from ..trading.guardrails import validate_instrument_spec, MAX_BACKTEST_RISK_PERCENT, RISK_ENGINE_VERSION
from ..live_trading.live_sl_tp_service import calculate_live_entry_plan

logger = logging.getLogger(__name__)

LOT_STYLE_MODES = {"LOTS"}
QTY_STYLE_MODES = {"SHARES", "UNITS", "CONTRACTS"}


def _float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except Exception:
        return default


def _dec(value: Any, default: str = "0") -> Decimal:
    return to_decimal(value, default)


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


async def _safe_capital_snapshot(db: AsyncSession, deployment: StrategyDeployment | None):
    """Resolve broker effective capital without allowing readiness/risk preview to crash.

    Broker account metadata can be incomplete during agent reconnects. In that case
    order preview must fall back to deployment/runtime capital and return a clean
    validation response instead of a Python NameError/AttributeError.
    """
    if deployment is None:
        return None
    try:
        broker_account = None
        broker_account_id = getattr(deployment, "broker_account_id", None)
        if broker_account_id:
            broker_account = (
                await db.execute(select(BrokerAccount).where(BrokerAccount.id == broker_account_id))
            ).scalar_one_or_none()
        return get_effective_trading_capital(deployment, broker_account)
    except Exception as exc:  # pragma: no cover - defensive readiness guard
        logger.warning(
            "LIVE_ORDER_PREVIEW_CAPITAL_SNAPSHOT_FALLBACK deployment_id=%s error=%s",
            getattr(deployment, "id", None),
            exc,
        )
        return None


def _snapshot_capital_value(capital_snapshot: Any, risk_cfg: dict[str, Any] | None = None, default: float = 0) -> float:
    if capital_snapshot is not None:
        resolved = _float(getattr(capital_snapshot, "effective_capital", None), None)
        if resolved is not None and resolved > 0:
            return resolved
    risk_cfg = risk_cfg or {}
    resolved = _float(risk_cfg.get("initial_capital"), None)
    if resolved is not None and resolved > 0:
        return resolved
    return default


def _snapshot_capital_source(capital_snapshot: Any) -> str:
    if capital_snapshot is not None:
        return str(getattr(capital_snapshot, "effective_capital_source", None) or "BROKER_OR_DEPLOYMENT_CAPITAL")
    return "RUNTIME_CONFIG"


BROKER_CAPITAL_SOURCES = {"BROKER_EQUITY", "BROKER_BALANCE", "BROKER_FREE_MARGIN"}
FALLBACK_CAPITAL_SOURCES = {"FALLBACK_DEPLOYMENT_CAPITAL", "RUNTIME_CONFIG", "UNKNOWN"}


def _is_broker_auto_execution(deployment: StrategyDeployment | None, preview_mode: str | None) -> bool:
    if deployment is None:
        return False
    if str(getattr(deployment, "mode", "") or "").upper() not in {"DEMO", "LIVE"}:
        return False
    # Only the explicit MANUAL preview endpoint may use fallback capital as a warning.
    # Runner execution, readiness auto preview, dry test, and demo micro order must
    # not size broker orders from default/deployment capital when broker capital is absent.
    return str(preview_mode or "").upper() != "MANUAL"


def _is_broker_preview(deployment: StrategyDeployment | None) -> bool:
    if deployment is None:
        return False
    return str(getattr(deployment, "mode", "") or "").upper() in {"DEMO", "LIVE"}


def _capital_warning_or_error(deployment: StrategyDeployment | None, capital_snapshot: Any, preview_mode: str | None) -> tuple[bool, str | None]:
    source = _snapshot_capital_source(capital_snapshot)
    value = _snapshot_capital_value(capital_snapshot, default=0)
    if not _is_broker_preview(deployment):
        return False, None
    if source in BROKER_CAPITAL_SOURCES and value > 0:
        return False, None
    message = "Broker capital is unavailable. Sync broker account before live order sizing."
    if _is_broker_auto_execution(deployment, preview_mode):
        return True, message
    return False, message




def _as_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalized_sl_mode(value: Any) -> str | None:
    if value in (None, ""):
        return None
    mode = str(value).strip().upper().replace(" ", "_")
    aliases = {
        "FIXED": "FIXED_PERCENT",
        "FIXED_PRICE_RISK": "FIXED_PERCENT",
        "FIXED_PRICE_RISK_PCT": "FIXED_PERCENT",
        "FIXED_PERCENT_SL": "FIXED_PERCENT",
        "STRATEGY": "STRATEGY_SUGGESTED",
        "STRATEGY_SUGGESTED_SL": "STRATEGY_SUGGESTED",
    }
    return aliases.get(mode, mode)


def _get_nested(mapping: Any, *path: str) -> Any:
    cur = mapping
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _deployment_sl_tp_override(deployment: StrategyDeployment) -> dict[str, Any]:
    """Return deployment-level SL/TP overrides without forcing the SL mode.

    The previous live preview implementation always wrote
    ``sl_tp.sl_mode = FIXED_PERCENT``. That made AUTO live execution ignore a
    strategy/default runtime config of STRATEGY_SUGGESTED and produced very wide
    fixed-percent SL/TP. This helper only includes sl_mode when it was explicitly
    stored on the deployment/settings payload.
    """
    override: dict[str, Any] = {
        "rr_ratio": _float(getattr(deployment, "rr_ratio", None), 2),
        "fixed_price_risk_pct": _float(getattr(deployment, "price_risk_pct", None), 0.002),
    }

    candidates: list[Any] = [
        getattr(deployment, "sl_mode", None),
        _get_nested(getattr(deployment, "runtime_config", None), "sl_tp", "sl_mode"),
        _get_nested(getattr(deployment, "runtime_config_snapshot", None), "sl_tp", "sl_mode"),
        _get_nested(getattr(deployment, "settings_json", None), "sl_tp", "sl_mode"),
        _get_nested(getattr(deployment, "config_json", None), "sl_tp", "sl_mode"),
    ]
    for candidate in candidates:
        mode = _normalized_sl_mode(candidate)
        if mode:
            override["sl_mode"] = mode
            break
    return override


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def _instrument_spec(row: Instrument) -> dict[str, Any]:
    keys = [
        "id", "symbol", "name", "asset_class", "base_currency", "quote_currency", "account_currency",
        "currency_symbol", "price_unit_name", "quantity_mode", "contract_size", "tick_size",
        "tick_value_per_lot", "pip_size", "min_quantity", "max_quantity", "quantity_step",
        "min_lot", "max_lot", "lot_step", "price_precision", "quantity_precision", "broker_symbol",
        "is_tradeable_live", "is_active",
    ]
    data = {key: _plain(getattr(row, key, None)) for key in keys}
    if data.get("quantity_mode"):
        data["quantity_mode"] = str(data.get("quantity_mode")).upper()
    data["account_currency"] = data.get("account_currency")
    if data.get("currency_symbol") is None and data.get("account_currency"):
        data["currency_symbol"] = "₹" if data.get("account_currency") == "INR" else "$" if data.get("account_currency") == "USD" else None
    data["pip_size"] = data.get("pip_size") or data.get("tick_size")
    data["source"] = "Instrument Master"
    return data


def _missing_instrument_fields(spec: dict[str, Any] | None, *, live: bool = True) -> list[str]:
    spec = spec or {}
    missing: list[str] = []

    def add(field: str) -> None:
        if field not in missing:
            missing.append(field)

    def blank(value: Any) -> bool:
        return value is None or value == ""

    if not spec:
        return ["instrument_master_record", "account_currency", "quantity_mode", "broker_symbol", "tick_size", "is_tradeable_live", "min_step_size"]

    mode = str(spec.get("quantity_mode") or "").upper()
    if blank(spec.get("account_currency")):
        add("account_currency")
    if blank(spec.get("quantity_mode")) or mode not in {"LOTS", "SHARES", "UNITS", "CONTRACTS"}:
        add("quantity_mode")
    if blank(spec.get("broker_symbol")):
        add("broker_symbol")
    if _float(spec.get("tick_size"), None) is None or float(_float(spec.get("tick_size"), 0) or 0) <= 0:
        add("tick_size")
    if live and spec.get("is_tradeable_live") is not True:
        add("is_tradeable_live")

    if mode == "LOTS":
        if _float(spec.get("tick_value_per_lot"), None) is None or float(_float(spec.get("tick_value_per_lot"), 0) or 0) <= 0:
            add("tick_value_per_lot")
        if _float(spec.get("lot_step"), None) is None or float(_float(spec.get("lot_step"), 0) or 0) <= 0:
            add("lot_step")
        if _float(spec.get("min_lot"), None) is None or float(_float(spec.get("min_lot"), 0) or 0) <= 0:
            add("min_lot")
    elif mode in {"SHARES", "UNITS", "CONTRACTS"}:
        if _float(spec.get("quantity_step"), None) is None or float(_float(spec.get("quantity_step"), 0) or 0) <= 0:
            add("quantity_step")
        if _float(spec.get("min_quantity"), None) is None or float(_float(spec.get("min_quantity"), 0) or 0) <= 0:
            add("min_quantity")
    else:
        add("min_step_size")
    return missing


def _instrument_not_ready_payload(symbol: str | None, side: str, spec: dict[str, Any] | None, missing_fields: list[str]) -> dict[str, Any]:
    sym = str(symbol or "Selected instrument").strip().upper() or "Selected instrument"
    message = f"{sym} is not ready for live trading. Configure account currency, quantity mode, broker symbol, min/step size, and live enabled in Market Master."
    return {
        "validation_status": "REJECTED",
        "status": "REJECTED",
        "reason": "Instrument not ready",
        "rejected_reason": message,
        "instrument_not_ready_message": message,
        "missing_fields": missing_fields,
        "symbol": symbol,
        "side": side,
        "instrument_spec_snapshot": spec or {"symbol": symbol, "source": "Missing"},
    }


async def find_live_instrument_spec(db: AsyncSession, *, instrument_id: int | None = None, symbol: str | None = None) -> tuple[Instrument | None, dict[str, Any] | None]:
    row = None
    if instrument_id:
        row = (await db.execute(select(Instrument).where(Instrument.id == instrument_id))).scalar_one_or_none()
    if row is None and symbol:
        sym = str(symbol).strip().upper()
        row = (await db.execute(select(Instrument).where(Instrument.symbol == sym))).scalar_one_or_none()
        if row is None:
            # MT5 often uses suffixes such as XAUUSDm. Prefer exact prefix fallback only when active/live master exists.
            all_rows = (await db.execute(select(Instrument).where(Instrument.is_active.is_(True)))).scalars().all()
            for item in all_rows:
                item_sym = str(getattr(item, "symbol", "") or "").upper()
                broker_sym = str(getattr(item, "broker_symbol", "") or "").upper()
                if item_sym and (sym.startswith(item_sym) or item_sym.startswith(sym) or sym == broker_sym):
                    row = item
                    break
    return row, (_instrument_spec(row) if row is not None else None)


async def resolve_live_runtime_config(
    db: AsyncSession,
    deployment: StrategyDeployment | None = None,
    instrument: Instrument | None = None,
    user_override: dict[str, Any] | None = None,
    strategy_id: str | None = None,
    strategy_preset_id: str | None = None,
) -> dict[str, Any]:
    strategy = None
    if deployment is not None:
        strategy = getattr(deployment, "strategy", None)
        strategy_id = strategy_id or str(deployment.strategy_id)
    if strategy is None and strategy_id:
        strategy = (await db.execute(select(Strategy).where(Strategy.id == str(strategy_id)))).scalar_one_or_none()

    preset = None
    if strategy_preset_id:
        preset = (await db.execute(select(StrategyRuntimePreset).where(StrategyRuntimePreset.id == str(strategy_preset_id), StrategyRuntimePreset.is_active.is_(True)))).scalar_one_or_none()
    elif strategy is not None:
        preset = (await db.execute(select(StrategyRuntimePreset).where(StrategyRuntimePreset.strategy_id == strategy.id, StrategyRuntimePreset.is_default.is_(True), StrategyRuntimePreset.is_active.is_(True)))).scalar_one_or_none()

    deployment_override: dict[str, Any] = {}
    capital_snapshot = await _safe_capital_snapshot(db, deployment) if deployment is not None else None
    if deployment is not None:
        quantity_mode_value = str(getattr(deployment, "quantity_mode", "") or "RISK_BASED").upper()
        position_size_mode = "RISK_BASED"
        fixed_lot_value = None
        if quantity_mode_value in {"FIXED_QTY", "FIXED_QUANTITY"}:
            position_size_mode = "FIXED_QUANTITY"
        elif quantity_mode_value in {"FIXED_LOT", "FIXED_LOTS", "LOT", "LOTS"}:
            # Use fixed lot only when explicitly selected on the deployment/runtime settings.
            # mt5_demo_max_lot is a safety cap, not an automatic fixed-lot override.
            position_size_mode = "FIXED_LOT"
            fixed_lot_value = _float(getattr(deployment, "fixed_lot", None), None) or _float(getattr(deployment, "lot_size", None), None)

        deployment_override = {
            "risk": {
                "initial_capital": _snapshot_capital_value(capital_snapshot, default=0),
                "risk_percent": _float(getattr(deployment, "risk_per_trade", None), 0.01),
                "position_size_mode": position_size_mode,
                "fixed_lot": fixed_lot_value,
                "fixed_quantity": _float(getattr(deployment, "fixed_quantity", None), None),
                "max_lot_cap": _float(getattr(deployment, "mt5_demo_max_lot", None), None),
                "max_quantity_cap": _float(getattr(deployment, "max_quantity", None), None),
            },
            "sl_tp": _deployment_sl_tp_override(deployment),
            "execution": {
                "allow_short": bool(getattr(deployment, "allow_short", True)),
                "max_trades_per_day": getattr(deployment, "max_trades_per_day", None),
                "max_open_positions": getattr(deployment, "max_open_positions", None),
                "square_off_time": getattr(deployment, "square_off_time", None) or "15:15",
            },
        }
    merged_override = deep_merge_runtime_config(deployment_override, user_override or {})
    return resolve_runtime_config(strategy=strategy, instrument=instrument, user_override=merged_override, strategy_preset=preset)


async def _latest_candles(db: AsyncSession, deployment: StrategyDeployment | None, symbol: str | None, timeframe: str | None, limit: int = 120) -> list[LiveMarketCandle]:
    stmt = select(LiveMarketCandle).order_by(LiveMarketCandle.candle_time.desc()).limit(limit)
    if deployment is not None:
        stmt = stmt.where(LiveMarketCandle.deployment_id == deployment.id)
    else:
        if symbol:
            stmt = stmt.where(func.upper(LiveMarketCandle.symbol) == str(symbol).upper())
        if timeframe:
            stmt = stmt.where(LiveMarketCandle.timeframe == timeframe)
    rows = list((await db.execute(stmt)).scalars().all())
    rows.reverse()
    return rows


def _normalize_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def _timeframe_stale_seconds(timeframe: str | None) -> int:
    tf = str(timeframe or "").strip().upper()
    mapping = {"M1": 60, "1M": 60, "M5": 300, "5M": 300, "M15": 900, "15M": 900, "M30": 1800, "30M": 1800, "H1": 3600, "1H": 3600, "D1": 86400, "1D": 86400}
    return mapping.get(tf, 900) * 6


def _latest_price_sanity_warnings(deployment: StrategyDeployment | None, candle: LiveMarketCandle | None, instrument_spec: dict[str, Any] | None, price: Decimal) -> list[str]:
    warnings: list[str] = []
    if candle is None:
        return warnings
    candle_symbol = _normalize_symbol(getattr(candle, "symbol", None))
    deploy_symbol = _normalize_symbol(getattr(deployment, "instrument", None) if deployment else None)
    broker_symbol = _normalize_symbol(getattr(deployment, "broker_symbol", None) if deployment else None) or _normalize_symbol((instrument_spec or {}).get("broker_symbol"))
    allowed = {x for x in [deploy_symbol, broker_symbol, _normalize_symbol((instrument_spec or {}).get("symbol"))] if x}
    if candle_symbol and allowed and candle_symbol not in allowed:
        warnings.append(f"Latest candle symbol {candle_symbol} does not match selected deployment symbol {deploy_symbol or broker_symbol}. Confirm broker symbol and candle source.")
    if price <= 0:
        warnings.append("Latest price is not positive. Refresh candles before preview/execution.")
    candle_time = getattr(candle, "candle_time", None)
    if isinstance(candle_time, datetime):
        ct = candle_time if candle_time.tzinfo else candle_time.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ct).total_seconds()
        stale_after = _timeframe_stale_seconds(getattr(deployment, "timeframe", None) if deployment else None)
        if age > stale_after:
            warnings.append("Latest candle looks stale for this timeframe. Refresh candles before auto trading.")
    asset = _normalize_symbol((instrument_spec or {}).get("asset_class"))
    sym = deploy_symbol or broker_symbol or candle_symbol
    if (asset == "METAL" or sym.startswith("XAUUSD")) and price > 0 and (price < Decimal("1000") or price > Decimal("10000")):
        warnings.append("Latest price looks unusual for XAUUSD. Confirm broker symbol and market data source.")
    return warnings


def _atr(candles: list[LiveMarketCandle], period: int) -> Decimal | None:
    if len(candles) < period + 1:
        return None
    trs: list[Decimal] = []
    recent = candles[-(period + 1):]
    for prev, cur in zip(recent, recent[1:]):
        high = _dec(getattr(cur, "high", None), "0")
        low = _dec(getattr(cur, "low", None), "0")
        prev_close = _dec(getattr(prev, "close", None), "0")
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    if not trs:
        return None
    return sum(trs, Decimal("0")) / Decimal(len(trs))


def _derive_sl_tp_from_candles(side: str, entry_price: Decimal, stop_loss: Decimal | None, runtime_config: dict[str, Any], candles: list[LiveMarketCandle] | None = None) -> tuple[Decimal | None, Decimal | None, str | None]:
    sl_tp = runtime_config.get("sl_tp") or {}
    rr = _dec(sl_tp.get("rr_ratio"), "2")
    sl_mode = _normalized_sl_mode(sl_tp.get("sl_mode")) or "FIXED_PERCENT"
    if stop_loss is None or stop_loss <= 0:
        if sl_mode == "ATR":
            period = int(_float(sl_tp.get("atr_period"), 14) or 14)
            multiplier = _dec(sl_tp.get("atr_multiplier"), "2")
            atr_value = _atr(candles or [], period)
            if atr_value is None or atr_value <= 0:
                return None, None, "Stop loss could not be calculated because ATR needs more candles. Try Fixed Percent SL or refresh candles."
            distance = atr_value * multiplier
            stop_loss = entry_price - distance if side == "BUY" else entry_price + distance
        elif sl_mode == "SWING":
            lookback = int(_float(sl_tp.get("swing_lookback"), 10) or 10)
            if len(candles or []) < lookback:
                return None, None, "Stop loss could not be calculated because Swing SL needs more candles. Try Fixed Percent SL or refresh candles."
            recent = (candles or [])[-lookback:]
            stop_loss = min(_dec(c.low, "0") for c in recent) if side == "BUY" else max(_dec(c.high, "0") for c in recent)
        else:
            pct = _dec(sl_tp.get("fixed_price_risk_pct"), "0.002")
            if pct <= 0:
                return None, None, "Stop loss could not be calculated. Fixed Percent SL must be greater than 0."
            stop_loss = entry_price * (Decimal("1") - pct) if side == "BUY" else entry_price * (Decimal("1") + pct)
    if side == "BUY" and stop_loss >= entry_price:
        return stop_loss, None, "BUY stop loss must be below entry price."
    if side == "SELL" and stop_loss <= entry_price:
        return stop_loss, None, "SELL stop loss must be above entry price."
    risk_distance = abs(entry_price - stop_loss)
    target = entry_price + risk_distance * rr if side == "BUY" else entry_price - risk_distance * rr
    if side == "BUY" and target <= entry_price:
        return stop_loss, target, "BUY target must be above entry price."
    if side == "SELL" and target >= entry_price:
        return stop_loss, target, "SELL target must be below entry price."
    return stop_loss, target, None


def _broker_order_payload_preview(
    *, broker_code: str | None, symbol: str, instrument_key: str | None, side: str, price: Decimal, stop_loss: Decimal | None, target: Decimal | None,
    qty_value: Decimal, quantity_mode: str, deployment: StrategyDeployment | None = None,
) -> dict[str, Any]:
    code = (broker_code or "PAPER").upper()
    if code in {"MT5", "CTRADER", "CTRADER_API"} or quantity_mode in LOT_STYLE_MODES:
        return {
            "broker": code,
            "symbol": symbol,
            "side": side,
            "order_type": "MARKET",
            "volume": float(qty_value),
            "price": float(price),
            "sl": float(stop_loss) if stop_loss is not None else None,
            "tp": float(target) if target is not None else None,
            "comment": "AlgoAgentX Demo",
            "note": "MT5/cTrader use volume = final_lot_size. Never send share quantity as volume.",
        }
    return {
        "broker": code,
        "symbol": symbol,
        "instrument_key": instrument_key or symbol,
        "side": side,
        "order_type": "MARKET",
        "quantity": int(qty_value),
        "price": float(price),
        "product_type": getattr(deployment, "product_type", "MIS") if deployment else "MIS",
        "order_variety": getattr(deployment, "order_variety", "REGULAR") if deployment else "REGULAR",
        "note": "Indian broker uses integer share/contract quantity, not MT5 lot volume.",
    }


async def build_live_order_preview(
    db: AsyncSession,
    *,
    deployment: StrategyDeployment | None = None,
    broker_code: str | None = None,
    instrument_id: int | None = None,
    symbol: str | None = None,
    side: str = "BUY",
    entry_price: Any = None,
    stop_loss: Any = None,
    strategy_target: Any = None,
    runtime_config: dict[str, Any] | None = None,
    strategy_id: str | None = None,
    strategy_preset_id: str | None = None,
    strict_instrument: bool = True,
    preview_mode: str = "MANUAL",
) -> dict[str, Any]:
    side = str(side or "BUY").upper()
    if side not in {"BUY", "SELL"}:
        return {"validation_status": "REJECTED", "rejected_reason": "side must be BUY or SELL."}

    resolved_symbol = symbol or (getattr(deployment, "instrument", None) if deployment else None)
    instrument_row, instrument_spec = await find_live_instrument_spec(db, instrument_id=instrument_id, symbol=resolved_symbol)
    if instrument_spec is None:
        return _instrument_not_ready_payload(
            resolved_symbol,
            side,
            None,
            ["instrument_master_record", "account_currency", "quantity_mode", "broker_symbol", "tick_size", "is_tradeable_live", "min_step_size"],
        )

    missing_fields = _missing_instrument_fields(instrument_spec, live=True)
    spec_validation = validate_instrument_spec(instrument_spec, live=True)
    if missing_fields or not spec_validation.get("valid"):
        # Keep toast/banner short. Full field-level detail is rendered in the Instrument Readiness card.
        return _instrument_not_ready_payload(resolved_symbol, side, instrument_spec, missing_fields)

    candles: list[LiveMarketCandle] = []
    latest_price: Decimal | None = None
    auto_mode = str(preview_mode or "MANUAL").upper() == "AUTO_LATEST_PRICE"
    if auto_mode:
        candles = await _latest_candles(db, deployment, resolved_symbol, getattr(deployment, "timeframe", None) if deployment else None)
        if not candles:
            return {"validation_status": "REJECTED", "status": "REJECTED", "rejected_reason": "No latest candle found. Refresh candles before auto preview.", "symbol": resolved_symbol, "side": side, "instrument_spec_snapshot": instrument_spec, "mode": "AUTO_LATEST_PRICE"}
        latest_price = _dec(candles[-1].close, "0")
        entry_price = latest_price

    entry = _dec(entry_price if entry_price is not None else 0, "0")
    if entry <= 0:
        return {"validation_status": "REJECTED", "status": "REJECTED", "rejected_reason": "entry_price or latest market price is required.", "symbol": resolved_symbol, "side": side, "instrument_spec_snapshot": instrument_spec}

    config = await resolve_live_runtime_config(db, deployment=deployment, instrument=instrument_row, user_override=runtime_config or {}, strategy_id=strategy_id, strategy_preset_id=strategy_preset_id)

    # Keep an order-preview-local capital snapshot for metadata and sizing.
    # This is intentionally defined before every later reference so readiness,
    # demo micro order, and auto-runner previews never fail with NameError when
    # broker capital metadata is missing or temporarily unavailable.
    capital_snapshot = await _safe_capital_snapshot(db, deployment)
    capital_source = _snapshot_capital_source(capital_snapshot)
    effective_capital = _snapshot_capital_value(capital_snapshot, risk_cfg=None, default=0)
    capital_reject, capital_warning = _capital_warning_or_error(deployment, capital_snapshot, preview_mode)
    if capital_reject:
        return {
            "validation_status": "REJECTED",
            "status": "REJECTED",
            "rejected_reason": capital_warning,
            "symbol": resolved_symbol,
            "side": side,
            "entry_price": float(entry),
            "effective_capital": effective_capital,
            "effective_capital_source": capital_source,
            "risk_metadata": {
                "effective_capital": effective_capital,
                "effective_capital_source": capital_source,
                "capital_warning": capital_warning,
                "position_size_mode": str((config.get("risk") or {}).get("position_size_mode") or "RISK_BASED"),
            },
            "runtime_config_snapshot": config,
            "instrument_spec_snapshot": instrument_spec,
        }

    config_validation = validate_runtime_config(config)
    if not config_validation.get("valid"):
        return {
            "validation_status": "REJECTED",
            "status": "REJECTED",
            "rejected_reason": "Runtime config is invalid: " + "; ".join(config_validation.get("errors") or []),
            "symbol": resolved_symbol,
            "side": side,
            "runtime_config_snapshot": config,
            "instrument_spec_snapshot": instrument_spec,
        }

    risk_cfg = config.get("risk") or {}
    if float(risk_cfg.get("risk_percent") or 0) > MAX_BACKTEST_RISK_PERCENT:
        return {
            "validation_status": "REJECTED",
            "status": "REJECTED",
            "rejected_reason": "Risk exceeds configured max. Maximum allowed risk per trade is 10%.",
            "symbol": resolved_symbol,
            "side": side,
            "runtime_config_snapshot": config,
            "instrument_spec_snapshot": instrument_spec,
        }

    if deployment is not None and not candles:
        candles = await _latest_candles(db, deployment, resolved_symbol, getattr(deployment, "timeframe", None), limit=120)
    latest_candle = candles[-1] if candles else None
    price_warnings = _latest_price_sanity_warnings(deployment, latest_candle, instrument_spec, entry)

    strategy_stop_loss_value = _float(stop_loss, None) if stop_loss not in (None, "") else None
    strategy_target_value = _float(strategy_target, None) if strategy_target not in (None, "") else None
    strategy_sltp_received = strategy_stop_loss_value is not None or strategy_target_value is not None

    entry_plan = calculate_live_entry_plan(
        candles=candles,
        side=side,
        entry_price=entry,
        runtime_config=config,
        instrument_spec=instrument_spec,
        strategy_stop_loss=strategy_stop_loss_value,
        strategy_target=strategy_target_value,
    )
    if entry_plan.get("status") != "OK":
        return {
            "validation_status": "REJECTED",
            "status": "REJECTED",
            "rejected_reason": entry_plan.get("rejected_reason") or "Stop loss could not be calculated.",
            "symbol": resolved_symbol,
            "side": side,
            "entry_price": float(entry),
            "stop_loss": entry_plan.get("stop_loss"),
            "target": entry_plan.get("target"),
            "strategy_stop_loss": strategy_stop_loss_value,
            "strategy_target": strategy_target_value,
            "strategy_sltp_received": strategy_sltp_received,
            "latest_price_warnings": price_warnings,
            "entry_plan": entry_plan,
            "runtime_config_snapshot": config,
            "instrument_spec_snapshot": instrument_spec,
        }
    sl = _dec(entry_plan.get("stop_loss"), "0")
    target = _dec(entry_plan.get("target"), "0")

    size = calculate_position_size(
        entry_price=float(entry),
        stop_loss=float(sl),
        capital=effective_capital,
        risk_percent=float(risk_cfg.get("risk_percent") or 0),
        instrument_spec=instrument_spec,
        position_size_mode=str(risk_cfg.get("position_size_mode") or "RISK_BASED"),
        fixed_lot=risk_cfg.get("fixed_lot"),
        fixed_quantity=risk_cfg.get("fixed_quantity"),
        max_lot_cap=risk_cfg.get("max_lot_cap"),
        max_quantity_cap=risk_cfg.get("max_quantity_cap"),
        side=side,
    )
    quantity_mode = str(size.get("quantity_mode") or instrument_spec.get("quantity_mode") or "SHARES").upper()
    if (broker_code or "").upper() in {"CTRADER", "CTRADER_API"} and quantity_mode not in LOT_STYLE_MODES:
        quantity_mode = "LOTS"
    final_lot = _dec(size.get("final_lot_size"), "0") if size.get("final_lot_size") is not None else None
    final_qty = _dec(size.get("final_quantity"), "0") if size.get("final_quantity") is not None else None
    qty_value = final_lot if quantity_mode in LOT_STYLE_MODES else final_qty

    if size.get("status") != "OK" or qty_value is None or qty_value <= 0:
        rejected_risk_metadata = {
            "effective_capital": effective_capital,
            "effective_capital_source": capital_source,
            "risk_percent": float(risk_cfg.get("risk_percent") or 0),
            "risk_amount": size.get("risk_amount"),
            "position_size_mode": str(risk_cfg.get("position_size_mode") or "RISK_BASED"),
            "raw_lot": size.get("raw_lot_size"),
            "final_lot": size.get("final_lot_size"),
            "raw_quantity": size.get("raw_quantity"),
            "final_quantity": size.get("final_quantity"),
            "max_lot_cap": risk_cfg.get("max_lot_cap"),
            "max_quantity_cap": risk_cfg.get("max_quantity_cap"),
            "min_lot": instrument_spec.get("min_lot"),
            "lot_step": instrument_spec.get("lot_step"),
            "min_quantity": instrument_spec.get("min_quantity"),
            "quantity_step": instrument_spec.get("quantity_step"),
            "capital_warning": capital_warning,
        }
        return {
            "validation_status": "REJECTED",
            "status": "REJECTED",
            "rejected_reason": size.get("rejected_reason") or "Risk engine rejected order size.",
            "symbol": resolved_symbol,
            "side": side,
            "entry_price": float(entry),
            "stop_loss": float(sl) if sl is not None else None,
            "target": float(target) if target is not None else None,
            "strategy_stop_loss": strategy_stop_loss_value,
            "strategy_target": strategy_target_value,
            "strategy_sltp_received": strategy_sltp_received,
            "quantity_mode": quantity_mode,
            "risk_engine": size,
            "risk_metadata": rejected_risk_metadata,
            "effective_capital": effective_capital,
            "effective_capital_source": capital_source,
            "latest_price_warnings": price_warnings,
            "entry_plan": entry_plan,
            "runtime_config_snapshot": config,
            "instrument_spec_snapshot": instrument_spec,
        }

    if quantity_mode in LOT_STYLE_MODES:
        step = _dec(instrument_spec.get("lot_step"), "0.01")
        min_v = _dec(instrument_spec.get("min_lot"), "0.01")
        max_v = _dec(instrument_spec.get("max_lot"), "100")
        capped = min(qty_value, max_v)
        qty_value = _floor_to_step(capped, step)
        if qty_value < min_v:
            return {
                "validation_status": "REJECTED",
                "status": "REJECTED",
                "rejected_reason": "Risk-based lot is below broker minimum lot.",
                "symbol": resolved_symbol,
                "side": side,
                "entry_price": float(entry),
                "stop_loss": float(sl) if sl is not None else None,
                "target": float(target) if target is not None else None,
                "quantity_mode": quantity_mode,
                "risk_engine": size,
                "entry_plan": entry_plan,
                "runtime_config_snapshot": config,
                "instrument_spec_snapshot": instrument_spec,
            }
        final_lot = qty_value
    else:
        step = _dec(instrument_spec.get("quantity_step"), "1")
        min_v = _dec(instrument_spec.get("min_quantity"), "1")
        max_v = _dec(instrument_spec.get("max_quantity"), "999999999")
        capped = min(qty_value, max_v)
        qty_value = _floor_to_step(capped, step).quantize(Decimal("1"), rounding=ROUND_DOWN)
        if qty_value < min_v:
            return {
                "validation_status": "REJECTED",
                "status": "REJECTED",
                "rejected_reason": "Risk-based quantity is below broker minimum quantity.",
                "symbol": resolved_symbol,
                "side": side,
                "entry_price": float(entry),
                "stop_loss": float(sl) if sl is not None else None,
                "target": float(target) if target is not None else None,
                "quantity_mode": quantity_mode,
                "risk_engine": size,
                "entry_plan": entry_plan,
                "runtime_config_snapshot": config,
                "instrument_spec_snapshot": instrument_spec,
            }
        final_qty = qty_value

    order_payload = _broker_order_payload_preview(
        broker_code=broker_code,
        symbol=str(getattr(deployment, "broker_symbol", None) or instrument_spec.get("broker_symbol") or resolved_symbol),
        instrument_key=getattr(deployment, "instrument_key", None) if deployment else None,
        side=side,
        price=entry,
        stop_loss=sl,
        target=target,
        qty_value=qty_value,
        quantity_mode=quantity_mode,
        deployment=deployment,
    )

    risk_metadata = {
        "quantity_mode": quantity_mode,
        "requested_lot": size.get("raw_lot_size"),
        "raw_lot": size.get("raw_lot_size"),
        "final_lot": float(final_lot) if final_lot is not None else None,
        "requested_quantity": size.get("raw_quantity"),
        "raw_quantity": size.get("raw_quantity"),
        "final_quantity": float(final_qty) if final_qty is not None else None,
        "risk_percent": float(risk_cfg.get("risk_percent") or 0),
        "risk_amount": size.get("risk_amount"),
        "actual_risk": size.get("actual_risk_amount"),
        "risk_engine": size,
        "risk_engine_version": RISK_ENGINE_VERSION,
        "instrument_spec_snapshot": instrument_spec,
        "runtime_config_snapshot": config,
        "effective_capital": effective_capital,
        "initial_capital": _float(risk_cfg.get("initial_capital"), 0),
        "position_size_mode": str(risk_cfg.get("position_size_mode") or "RISK_BASED"),
        "effective_capital_source": capital_source,
        "capital_warning": capital_warning,
        "max_lot_cap": risk_cfg.get("max_lot_cap"),
        "max_quantity_cap": risk_cfg.get("max_quantity_cap"),
        "min_lot": instrument_spec.get("min_lot"),
        "lot_step": instrument_spec.get("lot_step"),
        "min_quantity": instrument_spec.get("min_quantity"),
        "quantity_step": instrument_spec.get("quantity_step"),
        "strategy_stop_loss": strategy_stop_loss_value,
        "strategy_target": strategy_target_value,
        "strategy_sltp_received": strategy_sltp_received,
        "preview_stop_loss": float(sl) if sl is not None else None,
        "preview_target": float(target) if target is not None else None,
    }

    return {
        "validation_status": "OK",
        "status": "OK",
        "rejected_reason": None,
        "broker": (broker_code or "PAPER").upper(),
        "symbol": resolved_symbol,
        "side": side,
        "quantity_mode": quantity_mode,
        "final_lot_size": float(final_lot) if final_lot is not None else None,
        "final_quantity": float(final_qty) if final_qty is not None else None,
        "risk_amount": size.get("risk_amount"),
        "actual_risk_amount": size.get("actual_risk_amount"),
        "entry_price": float(entry),
        "latest_price": float(latest_price or entry),
        "preview_mode": "AUTO_LATEST_PRICE" if auto_mode else "MANUAL",
        "stop_loss": float(sl) if sl is not None else None,
        "target": float(target) if target is not None else None,
        "strategy_stop_loss": strategy_stop_loss_value,
        "strategy_target": strategy_target_value,
        "strategy_sltp_received": strategy_sltp_received,
        "expected_reward_amount": (float(size.get("actual_risk_amount") or 0) * float((config.get("sl_tp") or {}).get("rr_ratio") or 0)) if size.get("actual_risk_amount") is not None else None,
        "account_currency": instrument_spec.get("account_currency"),
        "currency_symbol": instrument_spec.get("currency_symbol"),
        "asset_class": instrument_spec.get("asset_class"),
        "runtime_config_snapshot": config,
        "instrument_spec_snapshot": instrument_spec,
        "risk_engine": size,
        "risk_engine_version": RISK_ENGINE_VERSION,
        "entry_plan": entry_plan,
        "latest_price_warnings": price_warnings,
        "risk_metadata": risk_metadata,
        "effective_capital": effective_capital,
        "effective_capital_source": capital_source,
        "capital_warning": capital_warning,
        "broker_symbol": order_payload.get("symbol"),
        "broker_payload_preview": order_payload,
        "broker_order_payload_preview": order_payload,
    }
