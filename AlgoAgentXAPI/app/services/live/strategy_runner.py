from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import LiveOrder, LiveSignal, LiveTradeLog, Strategy, StrategyDeployment
from ..strategy_registry import resolve_strategy
from .execution_engine import execute_signal
from .mt5_candle_service import get_latest_closed_candles, refresh_deployment_candles
from .pnl_service import to_decimal


@dataclass
class StrategyRunnerResult:
    success: bool
    deployment_id: str
    latest_candle_time: str | None
    signal: str | None
    executed: bool
    order_id: str | None
    signal_id: str | None
    duplicate: bool
    message: str
    latest_runner_log: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "deployment_id": self.deployment_id,
            "latest_candle_time": self.latest_candle_time,
            "signal": self.signal,
            "executed": self.executed,
            "order_id": self.order_id,
            "signal_id": self.signal_id,
            "duplicate": self.duplicate,
            "message": self.message,
            "latest_runner_log": self.latest_runner_log,
        }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


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
    if str(getattr(strategy, "visibility", "") or "").upper() != "PUBLIC":
        raise HTTPException(status_code=400, detail="Only published strategies can run live")
    mode = (mode or "PAPER").upper()
    if mode == "LIVE":
        raise HTTPException(status_code=400, detail="Live trading is disabled until final production review.")
    if mode == "PAPER" and not bool(getattr(strategy, "is_deployable_paper", False)):
        raise HTTPException(status_code=400, detail="Strategy is not enabled for PAPER deployment")
    if mode == "DEMO" and not bool(getattr(strategy, "is_deployable_demo", False)):
        raise HTTPException(status_code=400, detail="Strategy is not enabled for MT5 DEMO deployment")


def _candles_to_dataframe(candles: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
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


def _extract_latest_signal(result_df: pd.DataFrame) -> str:
    if result_df is None or result_df.empty:
        return "HOLD"
    latest = result_df.iloc[-1]
    raw_value = None
    for column in ("signal", "Signal", "position", "Position"):
        if column in result_df.columns:
            raw_value = latest[column]
            break
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
        if text in {"BUY", "LONG", "1"}:
            return "BUY"
        if text in {"SELL", "SHORT", "-1"}:
            return "SELL"
        if text == "EXIT":
            return "EXIT"
        return "HOLD"


async def _find_duplicate_engine_signal(
    db: AsyncSession,
    deployment_id: UUID,
    candle_time: datetime,
    signal_type: str,
) -> LiveSignal | None:
    return (
        await db.execute(
            select(LiveSignal)
            .where(
                LiveSignal.deployment_id == deployment_id,
                LiveSignal.source == "ENGINE",
                LiveSignal.candle_time == candle_time,
                LiveSignal.signal_type == signal_type,
            )
            .order_by(LiveSignal.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def run_strategy_for_deployment(db: AsyncSession, deployment_id: UUID, execute: bool = True) -> dict[str, Any]:
    deployment = (
        await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))
    ).scalar_one_or_none()
    if deployment is None:
        raise HTTPException(status_code=404, detail="Deployment not found")

    latest_log_message: str | None = None

    try:
        await _log(db, deployment, "RUNNER_STARTED", "Strategy runner started", metadata={"execute": execute})
        if deployment.status != "RUNNING":
            raise HTTPException(status_code=400, detail=f"Deployment is {deployment.status}. Start deployment before running strategy.")
        if deployment.mode == "LIVE":
            raise HTTPException(status_code=400, detail="Live trading is disabled until final production review.")

        strategy = (
            await db.execute(select(Strategy).where(Strategy.id == deployment.strategy_id))
        ).scalar_one_or_none()
        if strategy is None:
            raise HTTPException(status_code=404, detail="Strategy not found")
        _validate_strategy_gate(strategy, deployment.mode)

        if deployment.mode == "DEMO":
            await _log(db, deployment, "RUNNER_CANDLE_REFRESH_STARTED", "Refreshing latest MT5 candles before strategy run")
            await refresh_deployment_candles(db, deployment.id, count=300)

        candles = await get_latest_closed_candles(db, deployment.id, limit=300)
        if len(candles) < 20:
            raise HTTPException(status_code=400, detail="Not enough live candle data to run strategy. Refresh candles first.")

        latest_candle = candles[0]
        latest_candle_time = _normalize_dt(latest_candle.get("candle_time"))
        latest_close = to_decimal(latest_candle.get("close"))
        df = _candles_to_dataframe(candles)
        await _log(db, deployment, "RUNNER_CANDLES_LOADED", f"Loaded {len(df)} closed candles for strategy run", metadata={"latest_candle_time": latest_candle_time.isoformat()})

        strategy_params = strategy.parameters if isinstance(strategy.parameters, dict) else {}
        strategy_class, params, canonical_name = resolve_strategy(strategy.id, strategy.name, strategy_params)
        strategy_instance = strategy_class(df, **params)
        generated = strategy_instance.generate()
        if generated is None or not isinstance(generated, pd.DataFrame) or generated.empty:
            raise HTTPException(status_code=400, detail="Strategy did not return a valid DataFrame")

        signal_type = _extract_latest_signal(generated)
        side = "LONG" if signal_type == "BUY" else "SHORT" if signal_type == "SELL" else None
        await _log(db, deployment, "RUNNER_SIGNAL_GENERATED", f"{canonical_name} generated {signal_type} on latest closed candle", metadata={"signal_type": signal_type, "latest_candle_time": latest_candle_time.isoformat(), "price": str(latest_close)})

        duplicate = await _find_duplicate_engine_signal(db, deployment.id, latest_candle_time, signal_type)
        if duplicate is not None:
            deployment.last_heartbeat_at = datetime.now(timezone.utc)
            latest_log_message = "Duplicate ENGINE signal ignored for latest candle"
            await _log(db, deployment, "RUNNER_DUPLICATE_IGNORED", latest_log_message, "WARNING", {"existing_signal_id": str(duplicate.id), "signal_type": signal_type, "latest_candle_time": latest_candle_time.isoformat()})
            await db.commit()
            return StrategyRunnerResult(
                success=True,
                deployment_id=str(deployment.id),
                latest_candle_time=latest_candle_time.isoformat(),
                signal=signal_type,
                executed=False,
                order_id=None,
                signal_id=str(duplicate.id),
                duplicate=True,
                message=latest_log_message,
                latest_runner_log=latest_log_message,
            ).to_dict()

        signal = LiveSignal(
            deployment_id=deployment.id,
            user_id=deployment.user_id,
            strategy_id=deployment.strategy_id,
            source="ENGINE",
            symbol=deployment.instrument,
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
            latest_log_message = "Dry run completed; signal saved without execution"
            await _log(db, deployment, "RUNNER_DRY_RUN_COMPLETED", latest_log_message, metadata={"signal_id": str(signal.id)})
        elif not deployment.auto_trade_enabled:
            signal.status = "ACCEPTED"
            latest_log_message = "Auto trade is disabled; ENGINE signal saved without execution"
            await _log(db, deployment, "RUNNER_EXECUTION_SKIPPED", latest_log_message, "WARNING", {"signal_id": str(signal.id)})
        else:
            order = await execute_signal(db, deployment, signal)
            executed = bool(order and signal.status == "EXECUTED")
            latest_log_message = signal.rejection_reason or ("Strategy executed successfully" if executed else f"Strategy signal {signal.status.lower()}")
            await _log(db, deployment, "RUNNER_COMPLETED", latest_log_message, metadata={"signal_id": str(signal.id), "order_id": str(order.id) if order else None, "executed": executed})

        await db.commit()
        await db.refresh(signal)
        if order is not None:
            await db.refresh(order)

        return StrategyRunnerResult(
            success=True,
            deployment_id=str(deployment.id),
            latest_candle_time=latest_candle_time.isoformat(),
            signal=signal_type,
            executed=executed,
            order_id=str(order.id) if order else None,
            signal_id=str(signal.id),
            duplicate=False,
            message=latest_log_message or "Strategy runner completed",
            latest_runner_log=latest_log_message,
        ).to_dict()

    except HTTPException as exc:
        latest_log_message = str(exc.detail)
        await _log(db, deployment, "RUNNER_ERROR", latest_log_message, "ERROR")
        await db.commit()
        raise
    except Exception as exc:
        latest_log_message = f"Strategy runner failed: {exc.__class__.__name__}: {str(exc)[:240]}"
        await _log(db, deployment, "RUNNER_ERROR", latest_log_message, "ERROR")
        await db.commit()
        raise HTTPException(status_code=400, detail="Strategy runner failed. Check execution logs for details.") from exc
