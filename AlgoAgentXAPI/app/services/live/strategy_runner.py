from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


def _validate_strategy_gate(strategy: Strategy, mode: str) -> None:
    visibility = str(getattr(strategy, "visibility", "") or "").upper()
    if visibility != "PUBLIC":
        raise HTTPException(status_code=400, detail="Only published strategies can run live")
    mode = (mode or "PAPER").upper()
    if mode == "LIVE":
        raise HTTPException(status_code=400, detail="Live trading is disabled until final production review.")
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


def _extract_latest_signal(result_df: pd.DataFrame) -> str:
    if result_df is None or result_df.empty:
        return "HOLD"
    latest = result_df.iloc[-1]
    for column in ("signal", "Signal", "SIGNAL", "position", "Position", "POSITION"):
        if column in result_df.columns:
            return _normalize_signal_value(latest[column])
    return "HOLD"


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
    if status != "RUNNING":
        final = "REJECTED"
        return {"success": False, "deployment_id": str(deployment.id), "steps": steps, "final_action": final, "message": "Deployment must be RUNNING for full dry test."}
    if mode == "LIVE":
        step("LIVE gate", "FAIL", "LIVE mode remains locked until final production review.")
        return {"success": False, "deployment_id": str(deployment.id), "steps": steps, "final_action": "REJECTED", "message": "LIVE mode is blocked."}

    strategy = (await db.execute(select(Strategy).where(Strategy.id == deployment.strategy_id))).scalar_one_or_none()
    if strategy is None:
        step("Loaded strategy", "FAIL", "Strategy not found.")
        return {"success": False, "deployment_id": str(deployment.id), "steps": steps, "final_action": "REJECTED", "message": "Strategy not found."}
    _validate_strategy_gate(strategy, mode)
    step("Loaded strategy", "PASS", f"Strategy {strategy.name} is deployable for {mode}.")

    if mode == "DEMO":
        try:
            await refresh_deployment_candles(db, deployment.id, count=300)
            step("Refreshed broker candles", "PASS", "Latest broker candles refreshed for DEMO dry test.")
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
    signal_type = _extract_latest_signal(generated)
    step("Strategy generated signal", "PASS", f"{canonical_name} generated {signal_type}.", {"signal": signal_type})
    if signal_type == "HOLD":
        step("Final simulated action", "PASS", "HOLD - no order would be placed.")
        return {"success": True, "deployment_id": str(deployment.id), "strategy_name": canonical_name, "latest_candle_time": latest_candle_time.isoformat(), "signal": signal_type, "steps": steps, "final_action": "HOLD", "message": "Full dry test completed: HOLD."}

    duplicate = await _find_duplicate_engine_signal(db, deployment.id, latest_candle_time, signal_type, strategy_id=deployment.strategy_id, symbol=latest_symbol, timeframe=deployment.timeframe)
    step("Duplicate signal check", "WARNING" if duplicate else "PASS", "Duplicate signal ignored." if duplicate else "No duplicate signal found.", {"duplicate_signal_id": str(duplicate.id) if duplicate else None})
    if duplicate:
        step("Final simulated action", "WARNING", "Duplicate signal would be ignored.")
        return {"success": True, "deployment_id": str(deployment.id), "strategy_name": canonical_name, "latest_candle_time": latest_candle_time.isoformat(), "signal": signal_type, "steps": steps, "duplicate": True, "final_action": "REJECTED", "message": "Duplicate signal would be ignored."}

    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none() if deployment.broker_account_id else None
    broker_code = get_broker_code(broker) if broker is not None else ("PAPER" if mode == "PAPER" else "MT5")
    preview = await build_live_order_preview(db, deployment=deployment, broker_code=broker_code, symbol=latest_symbol, side=signal_type, preview_mode="AUTO_LATEST_PRICE", strict_instrument=mode in {"DEMO", "LIVE"})
    entry_plan = preview.get("entry_plan") or {}
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

    final_action = "WOULD_PLACE_PAPER_ORDER" if mode == "PAPER" else "WOULD_PLACE_DEMO_ORDER"
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
        await _log(db, deployment, "RUNNER_STARTED", "Strategy runner started", metadata={"execute": execute})
        mode = str(deployment.mode or "PAPER").upper()
        status = str(deployment.status or "").upper()
        if status != "RUNNING":
            raise HTTPException(status_code=400, detail=f"Deployment not RUNNING. Current status is {deployment.status}.")
        if mode == "LIVE":
            raise HTTPException(status_code=400, detail="Live trading is disabled until final production review.")
        if mode not in {"PAPER", "DEMO"}:
            raise HTTPException(status_code=400, detail="Strategy runner supports PAPER and DEMO modes only")

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

        if mode == "DEMO":
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

        signal_type = _extract_latest_signal(generated)
        side = "LONG" if signal_type == "BUY" else "SHORT" if signal_type == "SELL" else None
        await _log(
            db,
            deployment,
            "RUNNER_SIGNAL_GENERATED",
            f"{canonical_name} generated {signal_type} on latest closed candle",
            metadata={"signal_type": signal_type, "latest_candle_time": latest_candle_time.isoformat(), "price": str(latest_close), "symbol": latest_symbol},
        )

        duplicate = await _find_duplicate_engine_signal(db, deployment.id, latest_candle_time, signal_type, strategy_id=deployment.strategy_id, symbol=latest_symbol, timeframe=deployment.timeframe)
        if duplicate is not None:
            deployment.last_heartbeat_at = datetime.now(timezone.utc)
            latest_log_message = "Duplicate signal ignored"
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
            reason=f"Strategy runner: {canonical_name}",
            raw_payload={
                "runner": "live_market_candles",
                "strategy_id": strategy.id,
                "strategy_name": strategy.name,
                "canonical_strategy": canonical_name,
                "execute_requested": execute,
                "latest_candle_time": latest_candle_time.isoformat(),
                "resolved_symbol": latest_symbol,
            },
            status="RECEIVED",
        )
        db.add(signal)
        await db.flush()
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
