from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
import math
import hashlib
from uuid import UUID

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from ...db.models import BrokerAccount, LiveOrder, LiveSignal, LiveTradeLog, Strategy, StrategyDeployment
from ..strategy_registry import resolve_strategy
from .execution_engine import execute_signal
from .order_preview_service import build_live_order_preview
from ..brokers.factory import get_broker_code
from .broker_candle_service import get_latest_closed_candles, refresh_deployment_candles
from .pnl_service import to_decimal
from ..live_trading.paper_position_manager import process_paper_positions_for_deployment


@dataclass
class StrategyRunnerResult:
    success: bool
    deployment_id: str
    strategy_name: str | None
    latest_candle_time: str | None
    signal: str | None
    executed: bool
    order_id: str | None
    broker_order_id: str | None
    signal_id: str | None
    duplicate: bool
    message: str
    latest_runner_log: str | None = None
    order_status: str | None = None
    error_message: str | None = None
    symbol: str | None = None
    entry_plan: dict[str, Any] | None = None
    risk_preview: dict[str, Any] | None = None
    final_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "deployment_id": self.deployment_id,
            "strategy_name": self.strategy_name,
            "latest_candle_time": self.latest_candle_time,
            "signal": self.signal,
            "executed": self.executed,
            "order_id": self.order_id,
            "broker_order_id": self.broker_order_id,
            "signal_id": self.signal_id,
            "duplicate": self.duplicate,
            "message": self.message,
            "latest_runner_log": self.latest_runner_log,
            "order_status": self.order_status,
            "error_message": self.error_message,
            "symbol": self.symbol,
            "entry_plan": self.entry_plan,
            "risk_preview": self.risk_preview,
            "final_action": self.final_action,
        }


def _normalize_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _deployment_lock_key(deployment_id: UUID) -> int:
    """Stable signed 64-bit key for PostgreSQL advisory transaction locks."""
    digest = hashlib.sha256(str(deployment_id).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


async def _log(
    db: AsyncSession,
    deployment: StrategyDeployment,
    event_type: str,
    message: str,
    level: str = "INFO",
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    db.add(
        LiveTradeLog(
            deployment_id=deployment.id,
            user_id=deployment.user_id,
            event_type=event_type,
            level=level,
            message=message,
            metadata_json=metadata or {},
        )
    )


def _preview_cap_applied(preview: dict[str, Any] | None) -> bool:
    preview = preview or {}
    risk_metadata = preview.get("risk_metadata") if isinstance(preview.get("risk_metadata"), dict) else {}
    risk_engine = preview.get("risk_engine") if isinstance(preview.get("risk_engine"), dict) else {}
    raw_lot = _safe_float(risk_metadata.get("raw_lot") or risk_metadata.get("requested_lot") or risk_engine.get("raw_lot_size"))
    final_lot = _safe_float(risk_metadata.get("final_lot") or preview.get("final_lot_size") or risk_engine.get("final_lot_size"))
    max_lot = _safe_float(risk_metadata.get("max_lot_cap") or risk_engine.get("max_lot_cap"))
    raw_qty = _safe_float(risk_metadata.get("raw_quantity") or risk_metadata.get("requested_quantity") or risk_engine.get("raw_quantity"))
    final_qty = _safe_float(risk_metadata.get("final_quantity") or preview.get("final_quantity") or risk_engine.get("final_quantity"))
    max_qty = _safe_float(risk_metadata.get("max_quantity_cap") or risk_engine.get("max_quantity_cap"))
    if raw_lot is not None and final_lot is not None and max_lot is not None and raw_lot > final_lot and final_lot <= max_lot:
        return True
    if raw_qty is not None and final_qty is not None and max_qty is not None and raw_qty > final_qty and final_qty <= max_qty:
        return True
    return False


def _broker_payload_ok(preview: dict[str, Any] | None) -> bool:
    preview = preview or {}
    payload = preview.get("broker_payload_preview") or preview.get("broker_order_payload_preview")
    if not isinstance(payload, dict) or not payload.get("side") or not payload.get("symbol"):
        return False
    has_size = payload.get("volume") not in (None, "", 0) or payload.get("quantity") not in (None, "", 0)
    return bool(has_size and payload.get("sl") is not None and payload.get("tp") is not None)


async def _log_live_engine_qa_preview(
    db: AsyncSession,
    deployment: StrategyDeployment,
    *,
    signal_id: str | None = None,
    signal_type: str | None = None,
    signal_payload: dict[str, Any] | None = None,
    preview: dict[str, Any] | None = None,
    context: str = "runner",
) -> None:
    """Write final end-to-end QA pass logs for strategy output, SL/TP, risk and broker payload.

    These logs make the demo strategy and real Support/Resistance strategy easy to
    verify without changing the execution architecture. FAIL/WARNING states are
    already represented by the normal preview/readiness logs; these PASS events are
    emitted only when each contract stage is satisfied.
    """
    signal_payload = signal_payload or {}
    preview = preview or {}
    base = {
        "context": context,
        "signal_id": signal_id,
        "signal_type": signal_type or signal_payload.get("signal_type"),
        "strategy_stop_loss": signal_payload.get("strategy_stop_loss") or preview.get("strategy_stop_loss"),
        "strategy_target": signal_payload.get("strategy_target") or preview.get("strategy_target"),
    }
    await _log(db, deployment, "LIVE_ENGINE_QA_SIGNAL_CONTRACT_PASS", "Live engine signal contract validated", metadata={**base, "signal_reason": signal_payload.get("signal_reason")})

    entry_plan = preview.get("entry_plan") if isinstance(preview.get("entry_plan"), dict) else {}
    if entry_plan.get("status") == "OK" and preview.get("stop_loss") is not None and preview.get("target") is not None:
        await _log(
            db,
            deployment,
            "LIVE_ENGINE_QA_SLTP_PASS",
            "Live engine SL/TP contract validated",
            metadata={
                **base,
                "entry_price": preview.get("entry_price"),
                "final_stop_loss": preview.get("stop_loss"),
                "final_target": preview.get("target"),
                "sl_mode": entry_plan.get("sl_mode"),
                "stop_loss_source": entry_plan.get("stop_loss_source"),
                "target_source": entry_plan.get("target_source"),
                "risk_points": entry_plan.get("risk_points"),
                "reward_points": entry_plan.get("reward_points"),
                "rr_ratio": entry_plan.get("rr_ratio"),
            },
        )

    if str(preview.get("validation_status") or preview.get("status") or "").upper() == "OK":
        risk_metadata = preview.get("risk_metadata") if isinstance(preview.get("risk_metadata"), dict) else {}
        await _log(
            db,
            deployment,
            "LIVE_ENGINE_QA_RISK_PASS",
            "Live engine risk sizing validated",
            metadata={
                **base,
                "effective_capital": risk_metadata.get("effective_capital") or preview.get("effective_capital"),
                "effective_capital_source": risk_metadata.get("effective_capital_source") or preview.get("effective_capital_source"),
                "risk_percent": risk_metadata.get("risk_percent"),
                "risk_amount": risk_metadata.get("risk_amount") or preview.get("risk_amount"),
                "position_size_mode": risk_metadata.get("position_size_mode"),
                "raw_lot": risk_metadata.get("raw_lot"),
                "final_lot": risk_metadata.get("final_lot") or preview.get("final_lot_size"),
                "raw_quantity": risk_metadata.get("raw_quantity"),
                "final_quantity": risk_metadata.get("final_quantity") or preview.get("final_quantity"),
                "max_lot_cap": risk_metadata.get("max_lot_cap"),
                "cap_applied": _preview_cap_applied(preview),
            },
        )
        if _broker_payload_ok(preview):
            await _log(
                db,
                deployment,
                "LIVE_ENGINE_QA_BROKER_PAYLOAD_PASS",
                "Live engine broker payload validated",
                metadata={
                    **base,
                    "broker_payload_preview": preview.get("broker_payload_preview") or preview.get("broker_order_payload_preview"),
                    "cap_applied": _preview_cap_applied(preview),
                },
            )


def _validate_strategy_gate(strategy: Strategy, mode: str) -> None:
    visibility = str(getattr(strategy, "visibility", "") or "").upper()
    if visibility != "PUBLIC":
        raise HTTPException(status_code=400, detail="Only published strategies can run live")
    mode = (mode or "PAPER").upper()
    if mode == "LIVE" and not bool(getattr(strategy, "is_live_approved", False)):
        raise HTTPException(status_code=400, detail="Strategy is not enabled for LIVE deployment")
    if mode == "PAPER" and not bool(getattr(strategy, "is_deployable_paper", False)):
        raise HTTPException(status_code=400, detail="Strategy is not enabled for PAPER deployment")
    if mode == "DEMO" and not bool(getattr(strategy, "is_deployable_demo", False)):
        raise HTTPException(status_code=400, detail="Strategy is not enabled for MT5 DEMO deployment")


def _candles_to_dataframe(candles: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    # get_latest_closed_candles returns newest first. Strategies expect ascending time.
    for candle in reversed(candles):
        rows.append(
            {
                "Date": _normalize_dt(candle.get("candle_time")),
                "Open": float(to_decimal(candle.get("open"))),
                "High": float(to_decimal(candle.get("high"))),
                "Low": float(to_decimal(candle.get("low"))),
                "Close": float(to_decimal(candle.get("close"))),
                "Volume": float(to_decimal(candle.get("volume"), "0")),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Date").reset_index(drop=True)
    return df


def _normalize_signal_value(raw_value: Any) -> str:
    if raw_value is None:
        return "HOLD"
    try:
        numeric = int(float(raw_value))
        if numeric > 0:
            return "BUY"
        if numeric < 0:
            return "SELL"
        return "HOLD"
    except Exception:
        text = str(raw_value or "").strip().upper()
        if text in {"BUY", "LONG", "BULL", "1", "+1"}:
            return "BUY"
        if text in {"SELL", "SHORT", "BEAR", "-1"}:
            return "SELL"
        if text in {"EXIT", "CLOSE", "CLOSE_LONG", "CLOSE_SHORT", "FLAT"}:
            return "EXIT"
        return "HOLD"




def _json_safe_value(value: Any) -> Any:
    """Convert pandas/numpy/scalar values into JSON-safe Python values."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, (int, bool, str)):
        text = value.strip() if isinstance(value, str) else value
        if text == "":
            return None
        return text
    if isinstance(value, dict):
        return {str(k): _json_safe_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe_value(v) for v in value]
    return str(value)


def _safe_float(value: Any) -> float | None:
    value = _json_safe_value(value)
    if value is None:
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _first_present(row: Any, columns: tuple[str, ...]) -> Any:
    for column in columns:
        try:
            if column in row.index:
                value = row[column]
                if _json_safe_value(value) is not None:
                    return value
        except Exception:
            continue
    return None


def _safe_row_dict(row: Any) -> dict[str, Any]:
    try:
        raw = row.to_dict()
    except Exception:
        raw = {}
    return {str(k): _json_safe_value(v) for k, v in raw.items()}


def extract_latest_signal_payload(generated_df: pd.DataFrame) -> dict[str, Any]:
    """Extract the live runner contract from the latest generated strategy row.

    Live-compatible strategies may return signal/Position plus strategy_stop_loss,
    strategy_target, helper risk/reward columns and signal_reason.  This helper
    intentionally reads only the latest closed-candle row, mirroring the live
    runner decision point.
    """
    if generated_df is None or generated_df.empty:
        return {
            "signal_type": "HOLD",
            "strategy_stop_loss": None,
            "strategy_target": None,
            "strategy_risk_points": None,
            "strategy_reward_points": None,
            "signal_reason": None,
            "source_row": {},
        }

    latest = generated_df.iloc[-1]
    signal_raw = _first_present(latest, ("signal", "Signal", "SIGNAL", "position", "Position", "POSITION"))
    signal_type = _normalize_signal_value(signal_raw)
    stop_loss = _safe_float(_first_present(latest, ("strategy_stop_loss", "stop_loss", "sl", "SL")))
    target = _safe_float(_first_present(latest, ("strategy_target", "target", "take_profit", "tp", "TP")))
    risk_points = _safe_float(_first_present(latest, ("strategy_risk_points", "risk_points", "risk", "risk_distance")))
    reward_points = _safe_float(_first_present(latest, ("strategy_reward_points", "reward_points", "reward", "reward_distance")))
    reason_value = _json_safe_value(_first_present(latest, ("signal_reason", "reason", "Reason", "SIGNAL_REASON")))
    signal_reason = str(reason_value) if reason_value is not None else None

    return {
        "signal_type": signal_type,
        "strategy_stop_loss": stop_loss,
        "strategy_target": target,
        "strategy_risk_points": risk_points,
        "strategy_reward_points": reward_points,
        "signal_reason": signal_reason,
        "source_row": _safe_row_dict(latest),
    }


def _extract_latest_signal(result_df: pd.DataFrame) -> str:
    return str(extract_latest_signal_payload(result_df).get("signal_type") or "HOLD")


def _run_strategy_generate(strategy_instance: Any) -> pd.DataFrame:
    for method_name in ("generate", "generate_signals", "run"):
        method = getattr(strategy_instance, method_name, None)
        if callable(method):
            generated = method()
            if isinstance(generated, pd.DataFrame):
                return generated
    df = getattr(strategy_instance, "df", None)
    if isinstance(df, pd.DataFrame):
        return df
    raise ValueError("Strategy did not return a valid DataFrame")


async def _find_duplicate_engine_signal(
    db: AsyncSession,
    deployment_id: UUID,
    candle_time: datetime,
    signal_type: str,
    *,
    strategy_id: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
) -> LiveSignal | None:
    stmt = select(LiveSignal).where(
        LiveSignal.deployment_id == deployment_id,
        LiveSignal.source == "ENGINE",
        LiveSignal.candle_time == candle_time,
        LiveSignal.signal_type == signal_type,
    )
    if strategy_id:
        stmt = stmt.where(LiveSignal.strategy_id == strategy_id)
    if symbol:
        stmt = stmt.where(LiveSignal.symbol == symbol)
    if timeframe:
        stmt = stmt.where(LiveSignal.timeframe == timeframe)
    return (await db.execute(stmt.order_by(LiveSignal.created_at.desc()).limit(1))).scalar_one_or_none()


def _message_for_result(signal_type: str, execute: bool, auto_trade: bool, order: Optional[LiveOrder], duplicate: bool = False) -> str:
    if duplicate:
        return "Duplicate signal ignored"
    if signal_type == "HOLD":
        return "Strategy generated HOLD, no order placed"
    if not execute:
        return f"Dry run completed; strategy generated {signal_type}, no order placed"
    if not auto_trade:
        return "Auto trade disabled; signal saved without order"
    if order is None:
        return f"Strategy generated {signal_type}, but no order was placed"
    if order.status in {"FILLED", "PLACED"}:
        return f"Strategy generated {signal_type} and MT5 demo order placed" if order.broker_order_id else f"Strategy generated {signal_type} and paper order placed"
    if order.status == "ERROR":
        return f"MT5 order failed: {order.error_message or 'Check execution logs'}"
    return f"Strategy generated {signal_type}; order status {order.status}"


async def run_full_dry_test_for_deployment(db: AsyncSession, deployment_id: UUID) -> dict[str, Any]:
    """Run one complete live runner cycle without placing an order or saving a signal."""
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")

    steps: list[dict[str, Any]] = []

    def step(name: str, status: str, message: str, data: dict[str, Any] | None = None) -> None:
        steps.append({"name": name, "status": status, "message": message, "data": data or {}})

    mode = str(deployment.mode or "PAPER").upper()
    status = str(deployment.status or "").upper()
    step("Loaded deployment", "PASS" if status == "RUNNING" else "FAIL", f"Deployment is {deployment.status} in {mode} mode.")
    await _log(db, deployment, "LIVE_ENGINE_QA_STARTED", "Live engine final QA dry test started", metadata={"context": "full_dry_test", "mode": mode, "status": status})
    if status != "RUNNING":
        final = "REJECTED"
        return {"success": False, "deployment_id": str(deployment.id), "steps": steps, "final_action": final, "message": "Deployment must be RUNNING for full dry test."}
    if mode not in {"DEMO", "LIVE"}:
        step("Broker mode", "FAIL", "Full dry test is available for broker DEMO/LIVE deployments only.")
        return {"success": False, "deployment_id": str(deployment.id), "steps": steps, "final_action": "REJECTED", "message": "Create a DEMO or LIVE broker deployment for full dry test."}

    strategy = (await db.execute(select(Strategy).where(Strategy.id == deployment.strategy_id))).scalar_one_or_none()
    if strategy is None:
        step("Loaded strategy", "FAIL", "Strategy not found.")
        return {"success": False, "deployment_id": str(deployment.id), "steps": steps, "final_action": "REJECTED", "message": "Strategy not found."}
    _validate_strategy_gate(strategy, mode)
    step("Loaded strategy", "PASS", f"Strategy {strategy.name} is deployable for {mode}.")

    if mode in {"DEMO", "LIVE"}:
        try:
            await refresh_deployment_candles(db, deployment.id, count=300)
            step("Refreshed broker candles", "PASS", f"Latest broker candles refreshed for {mode} dry test.")
        except Exception as exc:
            step("Refreshed broker candles", "WARNING", f"Could not refresh broker candles: {str(exc)[:180]}")

    candles = await get_latest_closed_candles(db, deployment.id, limit=300)
    if len(candles) < 20:
        step("Loaded candles", "FAIL", f"Only {len(candles)} closed candles found. Refresh candles first.")
        return {"success": False, "deployment_id": str(deployment.id), "steps": steps, "final_action": "REJECTED", "message": "Not enough live candles."}
    latest_candle = candles[0]
    latest_candle_time = _normalize_dt(latest_candle.get("candle_time"))
    latest_close = to_decimal(latest_candle.get("close"))
    latest_symbol = str(latest_candle.get("symbol") or deployment.instrument)
    step("Loaded candles", "PASS", f"Loaded {len(candles)} candles. Latest close {latest_close} at {latest_candle_time}.", {"latest_candle_time": latest_candle_time.isoformat(), "latest_price": float(latest_close), "symbol": latest_symbol})

    df = _candles_to_dataframe(candles)
    strategy_params = strategy.parameters if isinstance(strategy.parameters, dict) else {}
    strategy_class, params, canonical_name = resolve_strategy(strategy.id, strategy.name, strategy_params)
    generated = _run_strategy_generate(strategy_class(df, **params))
    signal_payload = extract_latest_signal_payload(generated)
    signal_type = str(signal_payload.get("signal_type") or "HOLD")
    step("Strategy generated signal", "PASS", f"{canonical_name} generated {signal_type}.", {"signal": signal_type, "signal_reason": signal_payload.get("signal_reason")})
    has_strategy_sltp = signal_payload.get("strategy_stop_loss") is not None and signal_payload.get("strategy_target") is not None
    if signal_type in {"BUY", "SELL"}:
        step(
            "Extracted strategy SL/TP",
            "PASS" if has_strategy_sltp else "WARNING",
            "Strategy provided SL/TP on the latest signal row." if has_strategy_sltp else "Strategy generated BUY/SELL but did not provide strategy SL/TP. Runtime fallback may be used in later execution phases.",
            {
                "strategy_stop_loss": signal_payload.get("strategy_stop_loss"),
                "strategy_target": signal_payload.get("strategy_target"),
                "strategy_risk_points": signal_payload.get("strategy_risk_points"),
                "strategy_reward_points": signal_payload.get("strategy_reward_points"),
                "signal_reason": signal_payload.get("signal_reason"),
            },
        )
    else:
        step("Extracted strategy SL/TP", "PASS", "HOLD/EXIT does not require strategy SL/TP for this dry test.", {"signal": signal_type})
    await _log(
        db,
        deployment,
        "RUNNER_STRATEGY_OUTPUT_EXTRACTED",
        "Strategy output extracted from latest closed candle",
        metadata={
            "signal_type": signal_type,
            "strategy_stop_loss": signal_payload.get("strategy_stop_loss"),
            "strategy_target": signal_payload.get("strategy_target"),
            "signal_reason": signal_payload.get("signal_reason"),
        },
    )
    from .compatibility_service import run_live_compatibility_check
    compatibility = await run_live_compatibility_check(db, deployment.id)
    compatibility_status = str(compatibility.get("status") or "FAIL").upper()
    step(
        "Live Compatibility",
        "PASS" if compatibility_status == "PASS" else "WARNING" if compatibility_status == "WARNING" else "FAIL",
        compatibility.get("summary") or "Live compatibility checked.",
        {"checks": compatibility.get("checks", [])},
    )
    if compatibility_status == "FAIL":
        step("Final simulated action", "FAIL", "Compatibility failed. Fix failed checks before live auto execution.")
        await db.commit()
        return {"success": False, "deployment_id": str(deployment.id), "strategy_name": canonical_name, "latest_candle_time": latest_candle_time.isoformat(), "signal": signal_type, "steps": steps, "final_action": "REJECTED", "message": "Full dry test rejected: live compatibility failed.", "compatibility": compatibility}

    if signal_type == "HOLD":
        step("Final simulated action", "PASS", "HOLD - no order would be placed.")
        await db.commit()
        return {"success": True, "deployment_id": str(deployment.id), "strategy_name": canonical_name, "latest_candle_time": latest_candle_time.isoformat(), "signal": signal_type, "steps": steps, "final_action": "HOLD", "message": "Full dry test completed: HOLD.", "compatibility": compatibility}

    duplicate = await _find_duplicate_engine_signal(db, deployment.id, latest_candle_time, signal_type, strategy_id=deployment.strategy_id, symbol=latest_symbol, timeframe=deployment.timeframe)
    step("Duplicate signal check", "WARNING" if duplicate else "PASS", "Duplicate signal ignored." if duplicate else "No duplicate signal found.", {"duplicate_signal_id": str(duplicate.id) if duplicate else None})
    if duplicate:
        step("Final simulated action", "WARNING", "Duplicate signal would be ignored.")
        await db.commit()
        return {"success": True, "deployment_id": str(deployment.id), "strategy_name": canonical_name, "latest_candle_time": latest_candle_time.isoformat(), "signal": signal_type, "steps": steps, "duplicate": True, "final_action": "REJECTED", "message": "Duplicate signal would be ignored."}

    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none() if deployment.broker_account_id else None
    broker_code = get_broker_code(broker) if broker is not None else ("PAPER" if mode == "PAPER" else "MT5")
    preview = await build_live_order_preview(
        db,
        deployment=deployment,
        broker_code=broker_code,
        symbol=latest_symbol,
        side=signal_type,
        stop_loss=signal_payload.get("strategy_stop_loss"),
        strategy_target=signal_payload.get("strategy_target"),
        preview_mode="AUTO_LATEST_PRICE",
        strict_instrument=mode in {"DEMO", "LIVE"},
    )
    entry_plan = preview.get("entry_plan") or {}
    await _log_live_engine_qa_preview(db, deployment, signal_type=signal_type, signal_payload=signal_payload, preview=preview, context="full_dry_test")
    preview_ok = str(preview.get("validation_status") or preview.get("status") or "").upper() == "OK"
    step("Calculated SL/TP", "PASS" if entry_plan.get("status") == "OK" else "FAIL", "SL/TP calculated." if entry_plan.get("status") == "OK" else str(preview.get("rejected_reason") or "SL/TP calculation failed."), entry_plan)
    step("Calculated lot/qty", "PASS" if preview_ok else "FAIL", "Risk preview passed." if preview_ok else str(preview.get("rejected_reason") or "Risk preview rejected."), {"quantity_mode": preview.get("quantity_mode"), "lot": preview.get("final_lot_size"), "quantity": preview.get("final_quantity"), "risk": preview.get("actual_risk_amount"), "payload": preview.get("broker_payload_preview")})
    if preview.get("latest_price_warnings"):
        step("Latest price sanity", "WARNING", "; ".join(preview.get("latest_price_warnings") or []))
    else:
        step("Latest price sanity", "PASS", "Latest candle price passed sanity checks.")

    if not preview_ok:
        step("Final simulated action", "FAIL", "Signal would be rejected before order placement.")
        return {"success": False, "deployment_id": str(deployment.id), "strategy_name": canonical_name, "latest_candle_time": latest_candle_time.isoformat(), "signal": signal_type, "steps": steps, "entry_plan": entry_plan, "risk_preview": preview, "final_action": "REJECTED", "message": preview.get("rejected_reason") or "Full dry test rejected."}

    final_action = "WOULD_PLACE_LIVE_ORDER" if mode == "LIVE" else "WOULD_PLACE_DEMO_ORDER"
    step("Safety checks", "PASS", "No real order placed. Safety/risk preview passed for this simulated cycle.")
    step("Final simulated action", "PASS", final_action.replace("_", " "))
    await _log(db, deployment, "RUNNER_FULL_DRY_TEST", f"Full dry test completed: {final_action}", metadata={"signal": signal_type, "entry_plan": entry_plan, "risk_preview": {k: preview.get(k) for k in ["quantity_mode", "final_lot_size", "final_quantity", "actual_risk_amount", "broker_payload_preview"]}})
    await db.commit()
    return {"success": True, "deployment_id": str(deployment.id), "strategy_name": canonical_name, "latest_candle_time": latest_candle_time.isoformat(), "signal": signal_type, "steps": steps, "entry_plan": entry_plan, "risk_preview": preview, "final_action": final_action, "message": f"Full dry test completed: {final_action.replace('_', ' ').title()}"}


async def run_strategy_for_deployment(db: AsyncSession, deployment_id: UUID, execute: bool = True) -> dict[str, Any]:
    deployment = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")

    latest_log_message: str | None = None
    canonical_name: str | None = None
    latest_candle_time: datetime | None = None
    latest_symbol: str | None = None

    try:
        lock_key = _deployment_lock_key(deployment.id)
        locked = (await db.execute(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock_key})).scalar()
        if not locked:
            latest_log_message = "Another runner is already processing this deployment."
            await _log(db, deployment, "RUNNER_LOCK_SKIPPED", latest_log_message, "WARNING", {"deployment_id": str(deployment.id)})
            await db.commit()
            return StrategyRunnerResult(
                success=True,
                deployment_id=str(deployment.id),
                strategy_name=None,
                latest_candle_time=None,
                signal=None,
                executed=False,
                order_id=None,
                broker_order_id=None,
                signal_id=None,
                duplicate=True,
                message=latest_log_message,
                latest_runner_log=latest_log_message,
                final_action="LOCK_SKIPPED",
            ).to_dict()

        await _log(db, deployment, "RUNNER_STARTED", "Strategy runner started", metadata={"execute": execute})
        await _log(db, deployment, "LIVE_ENGINE_QA_STARTED", "Live engine final QA runner cycle started", metadata={"context": "runner", "execute": execute})
        mode = str(deployment.mode or "PAPER").upper()
        status = str(deployment.status or "").upper()
        if status != "RUNNING":
            raise HTTPException(status_code=400, detail=f"Deployment not RUNNING. Current status is {deployment.status}.")
        if mode not in {"PAPER", "DEMO", "LIVE"}:
            raise HTTPException(status_code=400, detail="Strategy runner supports PAPER, DEMO, and LIVE modes")

        if mode == "PAPER":
            try:
                await process_paper_positions_for_deployment(db, deployment.id)
                await _log(db, deployment, "PAPER_POSITION_MANAGER_UPDATED", "Paper positions checked before strategy runner cycle")
            except Exception as exc:
                await _log(db, deployment, "PAPER_POSITION_MANAGER_ERROR", f"Paper position manager failed: {exc}", "WARNING")

        strategy = (await db.execute(select(Strategy).where(Strategy.id == deployment.strategy_id))).scalar_one_or_none()
        if strategy is None:
            raise HTTPException(status_code=404, detail="Strategy not found")
        _validate_strategy_gate(strategy, mode)

        if mode in {"DEMO", "LIVE"}:
            await _log(db, deployment, "RUNNER_CANDLE_REFRESH_STARTED", "Refreshing latest broker closed candles before strategy run")
            await refresh_deployment_candles(db, deployment.id, count=300)

        candles = await get_latest_closed_candles(db, deployment.id, limit=300)
        if len(candles) < 20:
            raise HTTPException(status_code=400, detail="Not enough live candle data to run strategy. Refresh candles first.")

        latest_candle = candles[0]
        latest_candle_time = _normalize_dt(latest_candle.get("candle_time"))
        latest_close = to_decimal(latest_candle.get("close"))
        latest_symbol = str(latest_candle.get("symbol") or deployment.instrument)
        df = _candles_to_dataframe(candles)
        await _log(
            db,
            deployment,
            "RUNNER_CANDLES_LOADED",
            f"Loaded {len(df)} closed candles for strategy run",
            metadata={"latest_candle_time": latest_candle_time.isoformat(), "symbol": latest_symbol},
        )

        strategy_params = strategy.parameters if isinstance(strategy.parameters, dict) else {}
        strategy_class, params, canonical_name = resolve_strategy(strategy.id, strategy.name, strategy_params)
        strategy_instance = strategy_class(df, **params)
        generated = _run_strategy_generate(strategy_instance)
        if generated is None or not isinstance(generated, pd.DataFrame) or generated.empty:
            raise HTTPException(status_code=400, detail="Strategy did not return a valid DataFrame")

        signal_payload = extract_latest_signal_payload(generated)
        signal_type = str(signal_payload.get("signal_type") or "HOLD")
        side = "LONG" if signal_type == "BUY" else "SHORT" if signal_type == "SELL" else None
        output_metadata = {
            "signal_type": signal_type,
            "strategy_stop_loss": signal_payload.get("strategy_stop_loss"),
            "strategy_target": signal_payload.get("strategy_target"),
            "strategy_risk_points": signal_payload.get("strategy_risk_points"),
            "strategy_reward_points": signal_payload.get("strategy_reward_points"),
            "signal_reason": signal_payload.get("signal_reason"),
            "latest_candle_time": latest_candle_time.isoformat(),
            "price": str(latest_close),
            "symbol": latest_symbol,
        }
        await _log(
            db,
            deployment,
            "RUNNER_STRATEGY_OUTPUT_EXTRACTED",
            "Strategy output extracted from latest closed candle",
            metadata={k: output_metadata.get(k) for k in ["signal_type", "strategy_stop_loss", "strategy_target", "signal_reason"]},
        )
        await _log(
            db,
            deployment,
            "RUNNER_SIGNAL_GENERATED",
            f"{canonical_name} generated {signal_type} on latest closed candle",
            metadata=output_metadata,
        )
        await _log(db, deployment, "LIVE_ENGINE_QA_SIGNAL_CONTRACT_PASS", "Live engine signal contract validated", metadata=output_metadata)

        # Do not persist HOLD noise into live_signals. HOLD is a heartbeat/result,
        # not a tradeable signal. Persist only BUY/SELL/EXIT so Recent Signals and
        # signal counts stay useful for trading decisions.
        if signal_type == "HOLD":
            deployment.last_heartbeat_at = datetime.now(timezone.utc)
            latest_log_message = "HOLD - no tradeable signal, not saved"
            await _log(
                db,
                deployment,
                "RUNNER_HOLD_IGNORED",
                latest_log_message,
                metadata={"latest_candle_time": latest_candle_time.isoformat(), "price": str(latest_close), "symbol": latest_symbol, "strategy_output": output_metadata},
            )
            await db.commit()
            return StrategyRunnerResult(
                success=True,
                deployment_id=str(deployment.id),
                strategy_name=canonical_name or getattr(strategy, "name", None),
                latest_candle_time=latest_candle_time.isoformat(),
                signal=signal_type,
                executed=False,
                order_id=None,
                broker_order_id=None,
                signal_id=None,
                duplicate=False,
                message=latest_log_message,
                latest_runner_log=latest_log_message,
                symbol=latest_symbol,
                final_action="HOLD_IGNORED",
            ).to_dict()

        duplicate = await _find_duplicate_engine_signal(db, deployment.id, latest_candle_time, signal_type, strategy_id=deployment.strategy_id, symbol=latest_symbol, timeframe=deployment.timeframe)
        if duplicate is not None:
            deployment.last_heartbeat_at = datetime.now(timezone.utc)
            latest_log_message = "Duplicate tradeable signal ignored"
            await _log(
                db,
                deployment,
                "RUNNER_DUPLICATE_IGNORED",
                latest_log_message,
                "WARNING",
                {"existing_signal_id": str(duplicate.id), "signal_type": signal_type, "latest_candle_time": latest_candle_time.isoformat()},
            )
            await db.commit()
            return StrategyRunnerResult(
                success=True,
                deployment_id=str(deployment.id),
                strategy_name=canonical_name or getattr(strategy, "name", None),
                latest_candle_time=latest_candle_time.isoformat(),
                signal=signal_type,
                executed=False,
                order_id=None,
                broker_order_id=None,
                signal_id=str(duplicate.id),
                duplicate=True,
                message=latest_log_message,
                latest_runner_log=latest_log_message,
                symbol=latest_symbol,
            ).to_dict()

        signal = LiveSignal(
            deployment_id=deployment.id,
            user_id=deployment.user_id,
            strategy_id=deployment.strategy_id,
            source="ENGINE",
            symbol=latest_symbol,
            timeframe=deployment.timeframe,
            signal_type=signal_type,
            side=side,
            price=latest_close,
            candle_time=latest_candle_time,
            confidence=None,
            reason=signal_payload.get("signal_reason") or f"Strategy runner: {canonical_name}",
            raw_payload={
                "runner": "live_market_candles",
                "strategy_id": strategy.id,
                "strategy_name": strategy.name,
                "canonical_strategy": canonical_name,
                "execute_requested": execute,
                "latest_candle_time": latest_candle_time.isoformat(),
                "resolved_symbol": latest_symbol,
                "strategy_stop_loss": signal_payload.get("strategy_stop_loss"),
                "strategy_target": signal_payload.get("strategy_target"),
                "strategy_risk_points": signal_payload.get("strategy_risk_points"),
                "strategy_reward_points": signal_payload.get("strategy_reward_points"),
                "signal_reason": signal_payload.get("signal_reason"),
                "source_row": signal_payload.get("source_row") or {},
            },
            status="RECEIVED",
        )
        try:
            async with db.begin_nested():
                db.add(signal)
                await db.flush()
        except IntegrityError:
            duplicate = await _find_duplicate_engine_signal(db, deployment.id, latest_candle_time, signal_type, strategy_id=deployment.strategy_id, symbol=latest_symbol, timeframe=deployment.timeframe)
            deployment.last_heartbeat_at = datetime.now(timezone.utc)
            latest_log_message = "Duplicate tradeable signal blocked by DB idempotency guard"
            await _log(
                db,
                deployment,
                "DUPLICATE_SIGNAL_BLOCKED",
                latest_log_message,
                "WARNING",
                {"existing_signal_id": str(duplicate.id) if duplicate else None, "signal_type": signal_type, "latest_candle_time": latest_candle_time.isoformat()},
            )
            await db.commit()
            return StrategyRunnerResult(
                success=True,
                deployment_id=str(deployment.id),
                strategy_name=canonical_name or getattr(strategy, "name", None),
                latest_candle_time=latest_candle_time.isoformat(),
                signal=signal_type,
                executed=False,
                order_id=None,
                broker_order_id=None,
                signal_id=str(duplicate.id) if duplicate else None,
                duplicate=True,
                message=latest_log_message,
                latest_runner_log=latest_log_message,
                symbol=latest_symbol,
                final_action="DUPLICATE_SIGNAL_BLOCKED",
            ).to_dict()

        deployment.last_signal_at = datetime.now(timezone.utc)
        deployment.last_heartbeat_at = datetime.now(timezone.utc)
        await _log(db, deployment, "RUNNER_SIGNAL_SAVED", f"ENGINE {signal_type} signal saved", metadata={"signal_id": str(signal.id)})

        order: Optional[LiveOrder] = None
        executed = False
        if not execute:
            signal.status = "ACCEPTED"
            latest_log_message = _message_for_result(signal_type, execute, bool(deployment.auto_trade_enabled), None)
            await _log(db, deployment, "RUNNER_DRY_RUN_COMPLETED", latest_log_message, metadata={"signal_id": str(signal.id)})
        elif not deployment.auto_trade_enabled:
            signal.status = "ACCEPTED"
            latest_log_message = _message_for_result(signal_type, execute, False, None)
            await _log(db, deployment, "RUNNER_EXECUTION_SKIPPED", latest_log_message, "WARNING", {"signal_id": str(signal.id)})
        else:
            order = await execute_signal(db, deployment, signal)
            executed = bool(order and signal.status == "EXECUTED" and order.status in {"FILLED", "PLACED"})
            latest_log_message = signal.rejection_reason or _message_for_result(signal_type, execute, True, order)
            await _log(
                db,
                deployment,
                "RUNNER_COMPLETED",
                latest_log_message,
                "ERROR" if order is not None and order.status == "ERROR" else "INFO",
                {"signal_id": str(signal.id), "order_id": str(order.id) if order else None, "executed": executed},
            )

        await db.commit()
        await db.refresh(signal)
        if order is not None:
            await db.refresh(order)

        return StrategyRunnerResult(
            success=True,
            deployment_id=str(deployment.id),
            strategy_name=canonical_name or getattr(strategy, "name", None),
            latest_candle_time=latest_candle_time.isoformat(),
            signal=signal_type,
            executed=executed,
            order_id=str(order.id) if order else None,
            broker_order_id=order.broker_order_id if order else None,
            signal_id=str(signal.id),
            duplicate=False,
            message=latest_log_message or "Strategy runner completed",
            latest_runner_log=latest_log_message,
            order_status=order.status if order else None,
            error_message=order.error_message if order else signal.rejection_reason,
            symbol=latest_symbol,
        ).to_dict()

    except HTTPException as exc:
        latest_log_message = str(exc.detail)
        await _log(db, deployment, "RUNNER_ERROR", latest_log_message, "ERROR", {"deployment_id": str(deployment.id)})
        await db.commit()
        raise
    except Exception as exc:
        latest_log_message = f"Strategy runner failed: {exc.__class__.__name__}: {str(exc)[:240]}"
        await _log(db, deployment, "RUNNER_ERROR", latest_log_message, "ERROR", {"deployment_id": str(deployment.id)})
        await db.commit()
        raise HTTPException(status_code=400, detail="Strategy runner failed. Check execution logs for details.") from exc
