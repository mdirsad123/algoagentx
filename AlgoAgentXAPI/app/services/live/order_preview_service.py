from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import Instrument, Strategy, StrategyDeployment, StrategyRuntimePreset
from ..brokers.factory import get_broker_code
from ..trading.risk_engine import calculate_position_size
from ..trading.runtime_config_service import deep_merge_runtime_config, resolve_runtime_config, validate_runtime_config
from .pnl_service import to_decimal
from ..trading.guardrails import validate_instrument_spec, MAX_BACKTEST_RISK_PERCENT, RISK_ENGINE_VERSION

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
    data["quantity_mode"] = str(data.get("quantity_mode") or "SHARES").upper()
    data["account_currency"] = data.get("account_currency")
    data["currency_symbol"] = data.get("currency_symbol") or ("₹" if data.get("account_currency") == "INR" else "$" if data.get("account_currency") == "USD" else None)
    data["pip_size"] = data.get("pip_size") or data.get("tick_size")
    return data


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
    if deployment is not None:
        deployment_override = {
            "risk": {
                "initial_capital": _float(getattr(deployment, "capital", None), 100000),
                "risk_percent": _float(getattr(deployment, "risk_per_trade", None), 0.01),
                "position_size_mode": "FIXED_QUANTITY" if str(getattr(deployment, "quantity_mode", "") or "").upper() == "FIXED_QTY" else "RISK_BASED",
                "fixed_quantity": _float(getattr(deployment, "fixed_quantity", None), None),
                "max_lot_cap": _float(getattr(deployment, "mt5_demo_max_lot", None), None),
                "max_quantity_cap": _float(getattr(deployment, "max_quantity", None), None),
            },
            "sl_tp": {
                "rr_ratio": _float(getattr(deployment, "rr_ratio", None), 2),
                "fixed_price_risk_pct": _float(getattr(deployment, "price_risk_pct", None), 0.002),
                "sl_mode": "FIXED_PERCENT",
            },
            "execution": {
                "allow_short": bool(getattr(deployment, "allow_short", True)),
                "max_trades_per_day": getattr(deployment, "max_trades_per_day", None),
                "max_open_positions": getattr(deployment, "max_open_positions", None),
                "square_off_time": getattr(deployment, "square_off_time", None) or "15:15",
            },
        }
    merged_override = deep_merge_runtime_config(deployment_override, user_override or {})
    return resolve_runtime_config(strategy=strategy, instrument=instrument, user_override=merged_override, strategy_preset=preset)


def _derive_sl_tp(side: str, entry_price: Decimal, stop_loss: Decimal | None, runtime_config: dict[str, Any]) -> tuple[Decimal | None, Decimal | None, str | None]:
    sl_tp = runtime_config.get("sl_tp") or {}
    rr = _dec(sl_tp.get("rr_ratio"), "2")
    if stop_loss is None or stop_loss <= 0:
        pct = _dec(sl_tp.get("fixed_price_risk_pct"), "0.002")
        if pct <= 0:
            return None, None, "stop_loss is required or fixed_price_risk_pct must be greater than 0."
        stop_loss = entry_price * (Decimal("1") - pct) if side == "BUY" else entry_price * (Decimal("1") + pct)
    if side == "BUY" and stop_loss >= entry_price:
        return stop_loss, None, "BUY stop_loss must be below entry_price."
    if side == "SELL" and stop_loss <= entry_price:
        return stop_loss, None, "SELL stop_loss must be above entry_price."
    risk_distance = abs(entry_price - stop_loss)
    target = entry_price + risk_distance * rr if side == "BUY" else entry_price - risk_distance * rr
    return stop_loss, target, None


def _broker_order_payload_preview(
    *, broker_code: str | None, symbol: str, instrument_key: str | None, side: str, price: Decimal, stop_loss: Decimal | None, target: Decimal | None,
    qty_value: Decimal, quantity_mode: str, deployment: StrategyDeployment | None = None,
) -> dict[str, Any]:
    code = (broker_code or "PAPER").upper()
    if code == "MT5" or quantity_mode in LOT_STYLE_MODES:
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
            "note": "MT5 uses volume = final_lot_size. Never send share quantity as volume.",
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
    runtime_config: dict[str, Any] | None = None,
    strategy_id: str | None = None,
    strategy_preset_id: str | None = None,
    strict_instrument: bool = True,
) -> dict[str, Any]:
    side = str(side or "BUY").upper()
    if side not in {"BUY", "SELL"}:
        return {"validation_status": "REJECTED", "rejected_reason": "side must be BUY or SELL."}

    resolved_symbol = symbol or (getattr(deployment, "instrument", None) if deployment else None)
    instrument_row, instrument_spec = await find_live_instrument_spec(db, instrument_id=instrument_id, symbol=resolved_symbol)
    if instrument_spec is None:
        reason = "Instrument spec missing. Configure Instrument Master before live/demo order sizing."
        return {"validation_status": "REJECTED", "status": "REJECTED", "rejected_reason": reason, "symbol": resolved_symbol, "side": side}

    spec_validation = validate_instrument_spec(instrument_spec, live=True)
    if not spec_validation.get("valid"):
        return {
            "validation_status": "REJECTED",
            "status": "REJECTED",
            "rejected_reason": " ".join(spec_validation.get("errors") or []),
            "symbol": resolved_symbol,
            "side": side,
            "instrument_spec_snapshot": instrument_spec,
        }

    entry = _dec(entry_price if entry_price is not None else 0, "0")
    if entry <= 0:
        return {"validation_status": "REJECTED", "status": "REJECTED", "rejected_reason": "entry_price or market price is required.", "symbol": resolved_symbol, "side": side, "instrument_spec_snapshot": instrument_spec}

    config = await resolve_live_runtime_config(db, deployment=deployment, instrument=instrument_row, user_override=runtime_config or {}, strategy_id=strategy_id, strategy_preset_id=strategy_preset_id)
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

    if stop_loss in (None, ""):
        return {
            "validation_status": "REJECTED",
            "status": "REJECTED",
            "rejected_reason": "Stop loss is required for live/demo order sizing.",
            "symbol": resolved_symbol,
            "side": side,
            "entry_price": float(entry),
            "runtime_config_snapshot": config,
            "instrument_spec_snapshot": instrument_spec,
        }

    sl, target, sl_error = _derive_sl_tp(side, entry, _dec(stop_loss, "0") if stop_loss not in (None, "") else None, config)
    if sl_error:
        return {"validation_status": "REJECTED", "status": "REJECTED", "rejected_reason": sl_error, "symbol": resolved_symbol, "side": side, "entry_price": float(entry), "stop_loss": float(sl) if sl is not None else None, "runtime_config_snapshot": config, "instrument_spec_snapshot": instrument_spec}

    size = calculate_position_size(
        entry_price=float(entry),
        stop_loss=float(sl),
        capital=float(risk_cfg.get("initial_capital") or 0),
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
    final_lot = _dec(size.get("final_lot_size"), "0") if size.get("final_lot_size") is not None else None
    final_qty = _dec(size.get("final_quantity"), "0") if size.get("final_quantity") is not None else None
    qty_value = final_lot if quantity_mode in LOT_STYLE_MODES else final_qty

    if size.get("status") != "OK" or qty_value is None or qty_value <= 0:
        return {
            "validation_status": "REJECTED",
            "status": "REJECTED",
            "rejected_reason": size.get("rejected_reason") or "Risk engine rejected order size.",
            "symbol": resolved_symbol,
            "side": side,
            "entry_price": float(entry),
            "stop_loss": float(sl) if sl is not None else None,
            "target": float(target) if target is not None else None,
            "quantity_mode": quantity_mode,
            "risk_engine": size,
            "runtime_config_snapshot": config,
            "instrument_spec_snapshot": instrument_spec,
        }

    if quantity_mode in LOT_STYLE_MODES:
        step = _dec(instrument_spec.get("lot_step"), "0.01")
        min_v = _dec(instrument_spec.get("min_lot"), "0.01")
        max_v = _dec(instrument_spec.get("max_lot"), "100")
        capped = min(max(qty_value, min_v), max_v)
        qty_value = _floor_to_step(capped, step)
        final_lot = qty_value
    else:
        step = _dec(instrument_spec.get("quantity_step"), "1")
        min_v = _dec(instrument_spec.get("min_quantity"), "1")
        max_v = _dec(instrument_spec.get("max_quantity"), "999999999")
        capped = min(max(qty_value, min_v), max_v)
        qty_value = _floor_to_step(capped, step).quantize(Decimal("1"), rounding=ROUND_DOWN)
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
        "final_lot": float(final_lot) if final_lot is not None else None,
        "requested_quantity": size.get("raw_quantity"),
        "final_quantity": float(final_qty) if final_qty is not None else None,
        "risk_amount": size.get("risk_amount"),
        "actual_risk": size.get("actual_risk_amount"),
        "risk_engine": size,
        "risk_engine_version": RISK_ENGINE_VERSION,
        "instrument_spec_snapshot": instrument_spec,
        "runtime_config_snapshot": config,
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
        "stop_loss": float(sl) if sl is not None else None,
        "target": float(target) if target is not None else None,
        "account_currency": instrument_spec.get("account_currency"),
        "currency_symbol": instrument_spec.get("currency_symbol"),
        "asset_class": instrument_spec.get("asset_class"),
        "runtime_config_snapshot": config,
        "instrument_spec_snapshot": instrument_spec,
        "risk_engine": size,
        "risk_engine_version": RISK_ENGINE_VERSION,
        "risk_metadata": risk_metadata,
        "broker_order_payload_preview": order_payload,
    }
