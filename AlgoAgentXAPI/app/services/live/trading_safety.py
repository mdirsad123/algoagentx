from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import BrokerAccount, LiveOrder, LiveSignal, LiveTradeLog, PlatformTradingSettings, StrategyDeployment

LIVE_DISABLED_MESSAGE = "Live trading is disabled until final production review."


@dataclass
class SafetyDecision:
    allowed: bool
    reason: Optional[str] = None


async def get_platform_trading_settings(db: AsyncSession) -> PlatformTradingSettings:
    row = (await db.execute(select(PlatformTradingSettings).limit(1))).scalar_one_or_none()
    if row is not None:
        return row
    row = PlatformTradingSettings(
        paper_trading_enabled=True,
        demo_trading_enabled=True,
        live_trading_enabled=False,
        global_kill_switch=False,
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
    if mode == "LIVE":
        return SafetyDecision(False, LIVE_DISABLED_MESSAGE)
    if mode == "PAPER" and not settings.paper_trading_enabled:
        return SafetyDecision(False, "Paper trading is disabled by platform trading settings.")
    if mode == "DEMO" and not settings.demo_trading_enabled:
        return SafetyDecision(False, "MT5 demo trading is disabled by platform trading settings.")
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
            return SafetyDecision(False, "Global MT5 demo daily order limit reached.")
    if settings.max_user_demo_orders_per_day is not None:
        user_count = int((await db.execute(
            select(func.count(LiveOrder.id)).where(LiveOrder.user_id == deployment.user_id, LiveOrder.created_at >= start, LiveOrder.status.in_(active_statuses))
        )).scalar() or 0)
        if user_count >= int(settings.max_user_demo_orders_per_day):
            return SafetyDecision(False, "User MT5 demo daily order limit reached.")
    return SafetyDecision(True)


async def check_execution_safety(db: AsyncSession, deployment: StrategyDeployment, signal: Optional[LiveSignal] = None) -> SafetyDecision:
    mode_check = await check_platform_mode_allowed(db, deployment.mode)
    if not mode_check.allowed:
        return mode_check
    if deployment.status != "RUNNING":
        return SafetyDecision(False, f"Deployment is {deployment.status}")
    if not deployment.auto_trade_enabled:
        return SafetyDecision(False, "Auto trade is disabled")
    if deployment.mode == "DEMO":
        if not deployment.broker_account_id:
            return SafetyDecision(False, "DEMO execution requires an MT5 demo broker account.")
        broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
        if broker is None or broker.status != "CONNECTED":
            return SafetyDecision(False, "DEMO execution requires broker account status CONNECTED.")
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
