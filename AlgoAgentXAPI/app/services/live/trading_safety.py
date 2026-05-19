from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.models import BrokerAccount, LiveOrder, LiveSignal, LiveTradeLog, PlatformTradingSettings, StrategyDeployment

LIVE_DISABLED_MESSAGE = "Live trading requires connected broker approval and safety checks."


@dataclass
class SafetyDecision:
    allowed: bool
    reason: Optional[str] = None


def _broker_code(row: BrokerAccount | None) -> str:
    return str((getattr(row, "broker_code", None) or getattr(row, "broker_name", None) or "")).upper()

def _selected_ctrader_account(row: BrokerAccount | None) -> dict | None:
    meta = getattr(row, "metadata_json", None) or {}
    selected = meta.get("ctrader_selected_account") if isinstance(meta, dict) else None
    return selected if isinstance(selected, dict) else None


async def get_platform_trading_settings(db: AsyncSession) -> PlatformTradingSettings:
    row = (await db.execute(select(PlatformTradingSettings).limit(1))).scalar_one_or_none()
    if row is not None:
        return row
    row = PlatformTradingSettings(
        paper_trading_enabled=True,
        demo_trading_enabled=True,
        live_trading_enabled=False,
        global_kill_switch=False,
        broker_auto_sync_enabled=True,
        min_broker_sync_interval_seconds=5,
        default_broker_sync_interval_seconds=10,
        max_broker_sync_interval_seconds=300,
    )
    db.add(row)
    await db.flush()
    return row


def day_start_utc() -> datetime:
    return datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)


async def write_live_log(db: AsyncSession, deployment: StrategyDeployment, event_type: str, message: str, level: str = "INFO", metadata: Optional[dict] = None) -> None:
    db.add(LiveTradeLog(
        deployment_id=deployment.id,
        user_id=deployment.user_id,
        event_type=event_type,
        level=level,
        message=message,
        metadata_json=metadata or {},
    ))


async def check_platform_mode_allowed(db: AsyncSession, mode: str) -> SafetyDecision:
    settings = await get_platform_trading_settings(db)
    mode = (mode or "").upper()
    if settings.global_kill_switch:
        return SafetyDecision(False, "Global kill switch is ON. Trading execution is paused for all deployments.")
    # LIVE is not globally blocked here. Provider-specific LIVE switches and approval checks run in the approval/execution gate.
    if mode == "PAPER" and not settings.paper_trading_enabled:
        return SafetyDecision(False, "Paper trading is disabled by platform trading settings.")
    if mode == "DEMO" and not settings.demo_trading_enabled:
        return SafetyDecision(False, "Demo trading is disabled by platform trading settings.")
    return SafetyDecision(True)


async def check_global_order_limits(db: AsyncSession, deployment: StrategyDeployment) -> SafetyDecision:
    settings = await get_platform_trading_settings(db)
    if deployment.mode != "DEMO":
        return SafetyDecision(True)
    start = day_start_utc()
    active_statuses = ["FILLED", "PLACED", "PENDING", "PENDING_DEMO"]
    if settings.max_global_demo_orders_per_day is not None:
        global_count = int((await db.execute(
            select(func.count(LiveOrder.id)).where(LiveOrder.created_at >= start, LiveOrder.status.in_(active_statuses))
        )).scalar() or 0)
        if global_count >= int(settings.max_global_demo_orders_per_day):
            return SafetyDecision(False, "Global demo daily order limit reached.")
    if settings.max_user_demo_orders_per_day is not None:
        user_count = int((await db.execute(
            select(func.count(LiveOrder.id)).where(LiveOrder.user_id == deployment.user_id, LiveOrder.created_at >= start, LiveOrder.status.in_(active_statuses))
        )).scalar() or 0)
        if user_count >= int(settings.max_user_demo_orders_per_day):
            return SafetyDecision(False, "User demo daily order limit reached.")
    return SafetyDecision(True)


async def check_execution_safety(db: AsyncSession, deployment: StrategyDeployment, signal: Optional[LiveSignal] = None) -> SafetyDecision:
    mode_check = await check_platform_mode_allowed(db, deployment.mode)
    if not mode_check.allowed:
        return mode_check
    if deployment.status != "RUNNING":
        return SafetyDecision(False, f"Deployment is {deployment.status}")
    if not deployment.auto_trade_enabled:
        return SafetyDecision(False, "Auto trade is disabled")
    if deployment.mode in {"DEMO", "LIVE"}:
        if not deployment.broker_account_id:
            return SafetyDecision(False, f"{deployment.mode} execution requires a connected broker account.")
        broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
        if broker is None or str(broker.status or "").upper() != "CONNECTED":
            return SafetyDecision(False, f"{deployment.mode} execution requires broker account status CONNECTED.")
        if _broker_code(broker) in {"CTRADER", "CTRADER_API"}:
            if deployment.mode == "DEMO" and not bool(getattr(settings, "ctrader_demo_trading_enabled", True)):
                return SafetyDecision(False, "cTrader demo auto trading is disabled by platform configuration.")
            if deployment.mode == "LIVE" and not bool(getattr(settings, "ctrader_live_trading_enabled", False)):
                return SafetyDecision(False, "cTrader LIVE execution is disabled by platform configuration.")
            selected = _selected_ctrader_account(broker)
            if not selected:
                return SafetyDecision(False, "cTrader account selection required before broker deployment can trade.")
            account_mode = str(selected.get("account_type") or broker.mode or "").upper()
            if account_mode and account_mode != deployment.mode:
                return SafetyDecision(False, f"cTrader selected account is not {deployment.mode}.")
    limits = await check_global_order_limits(db, deployment)
    if not limits.allowed:
        return limits
    if signal is not None:
        duplicate = (await db.execute(
            select(LiveOrder.id)
            .join(LiveSignal, LiveSignal.id == LiveOrder.signal_id)
            .where(
                LiveOrder.deployment_id == deployment.id,
                LiveSignal.candle_time == signal.candle_time,
                LiveSignal.signal_type == signal.signal_type,
                LiveSignal.source == signal.source,
                LiveOrder.status.in_(["FILLED", "PLACED", "PENDING", "PENDING_DEMO"]),
            )
            .limit(1)
        )).scalar_one_or_none()
        if duplicate is not None:
            return SafetyDecision(False, "Duplicate signal already executed")
    return SafetyDecision(True)


async def mark_heartbeat(db: AsyncSession, deployment: StrategyDeployment) -> None:
    deployment.last_heartbeat_at = datetime.now(timezone.utc)
