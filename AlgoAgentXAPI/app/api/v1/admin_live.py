from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_admin_user, get_db
from ...db.models import (
    AdminLiveAction,
    BrokerAccount,
    BrokerOrderEvent,
    LiveEquityPoint,
    LiveOrder,
    LivePosition,
    LiveSignal,
    LiveTradeLog,
    Strategy,
    StrategyDeployment,
    User,
)
from ...schemas.live_trading import BrokerOrderEventOut, LiveEquityPointOut, LiveOrderOut, LivePositionOut, LiveSignalOut, LiveTradeLogOut
from ...utils.api_response import success_response
from ...services.live.strategy_runner import run_strategy_for_deployment
from ...services.live.compatibility_service import run_live_compatibility_check, compatibility_failed
from ...services.live.broker_sync_service import clamp_live_sync_interval, sync_deployment_broker_state
from ...services.live.trading_safety import get_platform_trading_settings
from .live_common import dump_list, dump_one

router = APIRouter()


class AdminLiveActionRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=2000)
    metadata_json: Optional[dict[str, Any]] = None


class AdminRunStrategyRequest(BaseModel):
    execute: bool = True


class LiveSyncSettingsIn(BaseModel):
    interval_seconds: Optional[int] = Field(default=None, ge=1, le=3600)


class AdminLiveActionOut(BaseModel):
    id: UUID
    admin_user_id: UUID
    deployment_id: UUID
    action: str
    reason: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True


def _dec(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None:
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _admin_id(current_user: dict) -> UUID:
    return UUID(str(current_user["user_id"]))


def _strategy_safe(row: Strategy | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "visibility": getattr(row, "visibility", None),
        "created_by": str(getattr(row, "created_by", None)) if getattr(row, "created_by", None) else None,
        "published_by": str(getattr(row, "published_by", None)) if getattr(row, "published_by", None) else None,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _user_safe(row: User | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": str(row.id),
        "email": row.email,
        "fullname": row.fullname,
        "mobile": row.mobile,
        "role": row.role,
        "created_at": row.created_at,
    }


def _broker_safe(row: BrokerAccount | None) -> dict[str, Any] | None:
    if not row:
        return None
    meta = row.metadata_json or {}
    last_test = meta.get("last_test") if isinstance(meta, dict) else {}
    last_test = last_test if isinstance(last_test, dict) else {}
    return {
        "id": str(row.id),
        "broker_account_id": str(row.id),
        "broker_name": row.broker_name,
        "account_label": row.account_label,
        "mode": row.mode,
        "status": row.status,
        "login_id": row.login_id,
        "server_name": row.server_name,
        "balance": last_test.get("balance"),
        "equity": last_test.get("equity"),
        "currency": last_test.get("currency"),
        "last_connected_at": row.last_connected_at,
        "safe_message": meta.get("safe_message") if isinstance(meta, dict) else None,
    }


def _deployment_safe(row: StrategyDeployment) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "user_id": str(row.user_id),
        "strategy_id": row.strategy_id,
        "broker_account_id": str(row.broker_account_id) if row.broker_account_id else None,
        "instrument": row.instrument,
        "timeframe": row.timeframe,
        "mode": row.mode,
        "status": row.status,
        "capital": row.capital,
        "risk_per_trade": row.risk_per_trade,
        "rr_ratio": row.rr_ratio,
        "price_risk_pct": row.price_risk_pct,
        "max_daily_loss": row.max_daily_loss,
        "max_trades_per_day": row.max_trades_per_day,
        "max_open_positions": row.max_open_positions,
        "allow_short": row.allow_short,
        "auto_trade_enabled": row.auto_trade_enabled,
        "auto_runner_enabled": getattr(row, "auto_runner_enabled", False),
        "last_runner_at": getattr(row, "last_runner_at", None),
        "last_processed_candle_time": getattr(row, "last_processed_candle_time", None),
        "last_broker_sync_at": getattr(row, "last_broker_sync_at", None),
        "live_sync_enabled": getattr(row, "live_sync_enabled", False),
        "live_sync_interval_seconds": getattr(row, "live_sync_interval_seconds", 10),
        "last_live_sync_at": getattr(row, "last_live_sync_at", None),
        "live_sync_error_count": getattr(row, "live_sync_error_count", 0),
        "live_sync_last_error": getattr(row, "live_sync_last_error", None),
        "live_approved": getattr(row, "live_approved", False),
        "live_approved_at": getattr(row, "live_approved_at", None),
        "runner_error_count": getattr(row, "runner_error_count", 0),
        "runner_last_error": getattr(row, "runner_last_error", None),
        "last_signal_at": row.last_signal_at,
        "last_heartbeat_at": row.last_heartbeat_at,
        "heartbeat_stale": bool(row.last_heartbeat_at and (datetime.now(timezone.utc) - row.last_heartbeat_at).total_seconds() > 180),
        "started_at": row.started_at,
        "stopped_at": row.stopped_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _today_start() -> datetime:
    return datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)


async def _deployment_metrics(db: AsyncSession, deployment_id: UUID) -> dict[str, Any]:
    day_start = _today_start()
    realized = _dec((await db.execute(select(func.coalesce(func.sum(LivePosition.realized_pnl), 0)).where(LivePosition.deployment_id == deployment_id))).scalar())
    unrealized = _dec((await db.execute(select(func.coalesce(func.sum(LivePosition.unrealized_pnl), 0)).where(LivePosition.deployment_id == deployment_id, LivePosition.status == "OPEN"))).scalar())
    today_pnl = _dec((await db.execute(select(func.coalesce(func.sum(LivePosition.realized_pnl), 0)).where(LivePosition.deployment_id == deployment_id, LivePosition.closed_at >= day_start))).scalar())
    open_positions = int((await db.execute(select(func.count(LivePosition.id)).where(LivePosition.deployment_id == deployment_id, LivePosition.status == "OPEN"))).scalar() or 0)
    orders_today = int((await db.execute(select(func.count(LiveOrder.id)).where(LiveOrder.deployment_id == deployment_id, LiveOrder.created_at >= day_start))).scalar() or 0)
    signals_today = int((await db.execute(select(func.count(LiveSignal.id)).where(LiveSignal.deployment_id == deployment_id, LiveSignal.created_at >= day_start))).scalar() or 0)
    total_orders = int((await db.execute(select(func.count(LiveOrder.id)).where(LiveOrder.deployment_id == deployment_id))).scalar() or 0)
    total_signals = int((await db.execute(select(func.count(LiveSignal.id)).where(LiveSignal.deployment_id == deployment_id))).scalar() or 0)
    latest_equity = (await db.execute(select(LiveEquityPoint.equity).where(LiveEquityPoint.deployment_id == deployment_id).order_by(LiveEquityPoint.timestamp.desc()).limit(1))).scalar_one_or_none()
    return {
        "realized_pnl": realized,
        "unrealized_pnl": unrealized,
        "today_pnl": today_pnl,
        "open_positions_count": open_positions,
        "open_positions": open_positions,
        "orders_today": orders_today,
        "orders_count_today": orders_today,
        "signals_today": signals_today,
        "signals_count_today": signals_today,
        "total_orders": total_orders,
        "total_signals": total_signals,
        "equity": _dec(latest_equity, "0"),
    }


async def _detail_summary(db: AsyncSession, deployment_id: UUID) -> dict[str, Any]:
    row = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Deployment not found")
    user = (await db.execute(select(User).where(User.id == row.user_id))).scalar_one_or_none()
    strategy = (await db.execute(select(Strategy).where(Strategy.id == row.strategy_id))).scalar_one_or_none()
    broker = None
    if row.broker_account_id:
        broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == row.broker_account_id))).scalar_one_or_none()

    metrics = await _deployment_metrics(db, row.id)
    metrics["capital"] = row.capital
    broker_data = _broker_safe(broker)
    metrics["currency"] = broker_data.get("currency") if isinstance(broker_data, dict) else None

    open_positions = (await db.execute(select(LivePosition).where(LivePosition.deployment_id == row.id, LivePosition.status == "OPEN").order_by(LivePosition.opened_at.desc()).limit(50))).scalars().all()
    recent_signals = (await db.execute(select(LiveSignal).where(LiveSignal.deployment_id == row.id).order_by(LiveSignal.created_at.desc()).limit(50))).scalars().all()
    recent_orders = (await db.execute(select(LiveOrder).where(LiveOrder.deployment_id == row.id).order_by(LiveOrder.created_at.desc()).limit(50))).scalars().all()
    recent_logs = (await db.execute(select(LiveTradeLog).where(LiveTradeLog.deployment_id == row.id).order_by(LiveTradeLog.created_at.desc()).limit(80))).scalars().all()
    recent_equity = (await db.execute(select(LiveEquityPoint).where(LiveEquityPoint.deployment_id == row.id).order_by(LiveEquityPoint.timestamp.desc()).limit(80))).scalars().all()
    audit_actions = (await db.execute(select(AdminLiveAction).where(AdminLiveAction.deployment_id == row.id).order_by(AdminLiveAction.created_at.desc()).limit(80))).scalars().all()
    broker_events = (await db.execute(select(BrokerOrderEvent).where(BrokerOrderEvent.deployment_id == row.id).order_by(BrokerOrderEvent.created_at.desc()).limit(80))).scalars().all()

    return {
        "deployment": _deployment_safe(row),
        "user": _user_safe(user),
        "strategy": _strategy_safe(strategy),
        "broker": broker_data,
        "metrics": metrics,
        "open_positions": dump_list(LivePositionOut, open_positions),
        "recent_signals": dump_list(LiveSignalOut, recent_signals),
        "recent_orders": dump_list(LiveOrderOut, recent_orders),
        "recent_logs": dump_list(LiveTradeLogOut, recent_logs),
        "recent_equity_points": dump_list(LiveEquityPointOut, recent_equity),
        "admin_audit_actions": dump_list(AdminLiveActionOut, audit_actions),
        "recent_broker_events": dump_list(BrokerOrderEventOut, broker_events),
    }


async def _write_admin_action(
    db: AsyncSession,
    *,
    admin_user_id: UUID,
    deployment: StrategyDeployment,
    action: str,
    reason: str | None,
    metadata_json: dict[str, Any] | None = None,
) -> None:
    db.add(AdminLiveAction(
        admin_user_id=admin_user_id,
        deployment_id=deployment.id,
        action=action,
        reason=reason,
        metadata_json=metadata_json or {},
    ))
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=f"ADMIN_{action}",
        level="WARNING" if action in {"FORCE_PAUSE", "FORCE_STOP", "DISABLE_AUTO_TRADE"} else "INFO",
        message=f"Admin action {action.replace('_', ' ').lower()}" + (f": {reason}" if reason else ""),
        metadata_json={"admin_user_id": str(admin_user_id), "reason": reason, **(metadata_json or {})},
    ))


@router.get("/deployments")
async def list_admin_live_deployments(
    status: Optional[str] = Query(default=None),
    mode: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    strategy_id: Optional[str] = Query(default=None),
    broker: Optional[str] = Query(default=None),
    instrument: Optional[str] = Query(default=None),
    timeframe: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    stmt = select(StrategyDeployment).order_by(StrategyDeployment.created_at.desc())
    if status:
        stmt = stmt.where(StrategyDeployment.status == status.upper())
    if mode:
        stmt = stmt.where(StrategyDeployment.mode == mode.upper())
    if user_id:
        stmt = stmt.where(StrategyDeployment.user_id == UUID(str(user_id)))
    if strategy_id:
        stmt = stmt.where(StrategyDeployment.strategy_id == strategy_id)
    if instrument:
        stmt = stmt.where(StrategyDeployment.instrument.ilike(f"%{instrument}%"))
    if timeframe:
        stmt = stmt.where(StrategyDeployment.timeframe == timeframe)

    rows = list((await db.execute(stmt)).scalars().all())
    if broker:
        broker_lower = broker.lower()
        filtered = []
        for row in rows:
            b = row.broker_account
            if b and (broker_lower in (b.broker_name or "").lower() or broker_lower in (b.account_label or "").lower()):
                filtered.append(row)
        rows = filtered

    result = []
    totals = {
        "total_deployments": len(rows),
        "running": 0,
        "paused": 0,
        "error": 0,
        "open_positions": 0,
        "today_total_pnl": Decimal("0"),
        "signals_today": 0,
        "orders_today": 0,
    }
    for row in rows:
        user = row.user
        strategy = row.strategy
        broker_row = row.broker_account
        metrics = await _deployment_metrics(db, row.id)
        totals["running"] += 1 if row.status == "RUNNING" else 0
        totals["paused"] += 1 if row.status == "PAUSED" else 0
        totals["error"] += 1 if row.status == "ERROR" else 0
        totals["open_positions"] += int(metrics["open_positions_count"] or 0)
        totals["today_total_pnl"] += _dec(metrics["today_pnl"])
        totals["signals_today"] += int(metrics["signals_today"] or 0)
        totals["orders_today"] += int(metrics["orders_today"] or 0)
        result.append({
            "deployment_id": str(row.id),
            "deployment_name": row.name,
            "user_id": str(row.user_id),
            "user_name": getattr(user, "fullname", None),
            "user_email": getattr(user, "email", None),
            "strategy_id": row.strategy_id,
            "strategy_name": getattr(strategy, "name", None) or row.strategy_id,
            "broker_account_id": str(row.broker_account_id) if row.broker_account_id else None,
            "broker_name": getattr(broker_row, "account_label", None) or getattr(broker_row, "broker_name", None),
            "broker_status": getattr(broker_row, "status", None),
            "instrument": row.instrument,
            "timeframe": row.timeframe,
            "mode": row.mode,
            "status": row.status,
            "auto_trade_enabled": row.auto_trade_enabled,
            "auto_runner_enabled": getattr(row, "auto_runner_enabled", False),
            "last_runner_at": getattr(row, "last_runner_at", None),
            "last_processed_candle_time": getattr(row, "last_processed_candle_time", None),
        "last_broker_sync_at": getattr(row, "last_broker_sync_at", None),
            "live_sync_enabled": getattr(row, "live_sync_enabled", False),
            "live_sync_interval_seconds": getattr(row, "live_sync_interval_seconds", 10),
            "last_live_sync_at": getattr(row, "last_live_sync_at", None),
            "live_sync_error_count": getattr(row, "live_sync_error_count", 0),
            "live_sync_last_error": getattr(row, "live_sync_last_error", None),
            "live_approved": getattr(row, "live_approved", False),
            "live_approved_at": getattr(row, "live_approved_at", None),
            "runner_error_count": getattr(row, "runner_error_count", 0),
            "runner_last_error": getattr(row, "runner_last_error", None),
            "runner_stale": bool(getattr(row, "auto_runner_enabled", False) and row.status == "RUNNING" and (not getattr(row, "last_runner_at", None) or (datetime.now(timezone.utc) - row.last_runner_at).total_seconds() > 180)),
            "last_signal_at": row.last_signal_at,
            "last_heartbeat_at": row.last_heartbeat_at,
            "heartbeat_stale": bool(row.last_heartbeat_at and (datetime.now(timezone.utc) - row.last_heartbeat_at).total_seconds() > 180),
            "open_positions_count": metrics["open_positions_count"],
            "today_pnl": metrics["today_pnl"],
            "signals_today": metrics["signals_today"],
            "orders_today": metrics["orders_today"],
        })

    settings = await get_platform_trading_settings(db)
    return success_response({"summary": totals, "rows": result, "settings": {"paper_trading_enabled": settings.paper_trading_enabled, "demo_trading_enabled": settings.demo_trading_enabled, "live_trading_enabled": settings.live_trading_enabled, "global_kill_switch": settings.global_kill_switch, "broker_auto_sync_enabled": getattr(settings, "broker_auto_sync_enabled", True), "min_broker_sync_interval_seconds": getattr(settings, "min_broker_sync_interval_seconds", 5), "default_broker_sync_interval_seconds": getattr(settings, "default_broker_sync_interval_seconds", 10), "max_broker_sync_interval_seconds": getattr(settings, "max_broker_sync_interval_seconds", 300), "max_global_demo_orders_per_day": settings.max_global_demo_orders_per_day, "max_user_demo_orders_per_day": settings.max_user_demo_orders_per_day}})


@router.get("/deployments/{deployment_id}")
async def get_admin_live_deployment_detail(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    return success_response(await _detail_summary(db, deployment_id))


@router.post("/deployments/{deployment_id}/sync-broker")
async def admin_sync_deployment_broker(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    try:
        result = await sync_deployment_broker_state(db, deployment_id)
        detail = await _detail_summary(db, deployment_id)
        return success_response({"sync": result, "detail": detail}, "Broker sync completed")
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


async def _set_admin_live_sync(db: AsyncSession, deployment_id: UUID, enabled: bool, interval_seconds: int | None, current_user: dict) -> dict[str, Any]:
    row = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Deployment not found")
    settings = await get_platform_trading_settings(db)
    row.live_sync_interval_seconds = clamp_live_sync_interval(settings, interval_seconds or getattr(row, "live_sync_interval_seconds", None))
    row.live_sync_enabled = enabled
    if enabled:
        row.live_sync_error_count = 0
        row.live_sync_last_error = None
    await _write_admin_action(db, admin_user_id=_admin_id(current_user), deployment=row, action="ENABLE_LIVE_SYNC" if enabled else "DISABLE_LIVE_SYNC", reason=None, metadata_json={"interval_seconds": row.live_sync_interval_seconds})
    await db.commit()
    return await _detail_summary(db, deployment_id)


@router.post("/deployments/{deployment_id}/live-sync/enable")
async def admin_enable_live_sync(deployment_id: UUID, payload: LiveSyncSettingsIn | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return success_response(await _set_admin_live_sync(db, deployment_id, True, payload.interval_seconds if payload else None, current_user), "Live broker auto-sync enabled")


@router.post("/deployments/{deployment_id}/live-sync/disable")
async def admin_disable_live_sync(deployment_id: UUID, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return success_response(await _set_admin_live_sync(db, deployment_id, False, None, current_user), "Live broker auto-sync disabled")


@router.patch("/deployments/{deployment_id}/live-sync/settings")
async def admin_update_live_sync_settings(deployment_id: UUID, payload: LiveSyncSettingsIn, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    row = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Deployment not found")
    settings = await get_platform_trading_settings(db)
    row.live_sync_interval_seconds = clamp_live_sync_interval(settings, payload.interval_seconds)
    await _write_admin_action(db, admin_user_id=_admin_id(current_user), deployment=row, action="CHANGE_LIVE_SYNC_INTERVAL", reason=None, metadata_json={"interval_seconds": row.live_sync_interval_seconds})
    await db.commit()
    return success_response(await _detail_summary(db, deployment_id), "Live broker auto-sync interval updated")


@router.post("/deployments/{deployment_id}/run-strategy-once")
async def admin_run_live_strategy_once(deployment_id: UUID, payload: AdminRunStrategyRequest | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    result = await run_strategy_for_deployment(db, deployment_id, execute=(payload.execute if payload else True))
    return success_response({"runner": result, "detail": await _detail_summary(db, deployment_id)}, result.get("message") or "Strategy runner completed")

async def _control_action(
    deployment_id: UUID,
    payload: AdminLiveActionRequest,
    db: AsyncSession,
    current_user: dict,
    action: str,
) -> dict[str, Any]:
    row = (await db.execute(select(StrategyDeployment).where(StrategyDeployment.id == deployment_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if action == "FORCE_PAUSE":
        row.status = "PAUSED"
    elif action == "FORCE_STOP":
        row.status = "STOPPED"
        row.stopped_at = datetime.now(timezone.utc)
    elif action == "DISABLE_AUTO_TRADE":
        row.auto_trade_enabled = False
    elif action == "ENABLE_AUTO_TRADE":
        compatibility = await run_live_compatibility_check(db, row.id)
        if compatibility_failed(compatibility):
            failing = [c for c in compatibility.get("checks", []) if c.get("status") == "FAIL"]
            detail = failing[0].get("message") if failing else "Live compatibility check failed. Fix compatibility before enabling Auto Trade."
            raise HTTPException(status_code=400, detail=detail)
        row.auto_trade_enabled = True
    else:
        raise HTTPException(status_code=400, detail="Unsupported admin action")
    await _write_admin_action(db, admin_user_id=_admin_id(current_user), deployment=row, action=action, reason=payload.reason, metadata_json=payload.metadata_json)
    await db.commit()
    return await _detail_summary(db, deployment_id)


@router.post("/deployments/{deployment_id}/force-pause")
async def force_pause_deployment(deployment_id: UUID, payload: AdminLiveActionRequest | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return success_response(await _control_action(deployment_id, payload or AdminLiveActionRequest(), db, current_user, "FORCE_PAUSE"), "Deployment force paused")


@router.post("/deployments/{deployment_id}/force-stop")
async def force_stop_deployment(deployment_id: UUID, payload: AdminLiveActionRequest | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return success_response(await _control_action(deployment_id, payload or AdminLiveActionRequest(), db, current_user, "FORCE_STOP"), "Deployment force stopped")


@router.post("/deployments/{deployment_id}/disable-auto-trade")
async def disable_auto_trade(deployment_id: UUID, payload: AdminLiveActionRequest | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return success_response(await _control_action(deployment_id, payload or AdminLiveActionRequest(), db, current_user, "DISABLE_AUTO_TRADE"), "Auto trade disabled")


@router.post("/deployments/{deployment_id}/enable-auto-trade")
async def enable_auto_trade(deployment_id: UUID, payload: AdminLiveActionRequest | None = None, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_admin_user)):
    return success_response(await _control_action(deployment_id, payload or AdminLiveActionRequest(), db, current_user, "ENABLE_AUTO_TRADE"), "Auto trade enabled")
