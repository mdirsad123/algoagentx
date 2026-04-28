from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import BrokerAccount, LiveOrder, LiveTradingApproval, LiveTradeLog, PlatformTradingSettings, Strategy, StrategyDeployment
from .pnl_service import to_decimal
from .trading_safety import LIVE_DISABLED_MESSAGE, day_start_utc, get_platform_trading_settings
from ..brokers.factory import get_broker_code


@dataclass
class LiveGateDecision:
    allowed: bool
    reason: str | None = None
    approval: LiveTradingApproval | None = None


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).upper() for v in value]
    return []


async def find_active_live_approval(db: AsyncSession, user_id: UUID, broker_account_id: UUID | None = None) -> LiveTradingApproval | None:
    stmt = select(LiveTradingApproval).where(
        LiveTradingApproval.user_id == user_id,
        LiveTradingApproval.status == "APPROVED",
        LiveTradingApproval.risk_disclaimer_accepted_at.is_not(None),
    ).order_by(LiveTradingApproval.updated_at.desc())
    rows = list((await db.execute(stmt)).scalars().all())
    if broker_account_id:
        exact = next((r for r in rows if str(r.broker_account_id) == str(broker_account_id)), None)
        if exact:
            return exact
    return next((r for r in rows if r.broker_account_id is None), rows[0] if rows else None)


async def write_live_approval_audit(db: AsyncSession, deployment: StrategyDeployment | None, user_id: UUID, event_type: str, message: str, level: str = "INFO", metadata: dict[str, Any] | None = None) -> None:
    if deployment is not None:
        db.add(LiveTradeLog(
            deployment_id=deployment.id,
            user_id=user_id,
            event_type=event_type,
            level=level,
            message=message,
            metadata_json=metadata or {},
        ))


async def check_live_execution_gate(db: AsyncSession, deployment: StrategyDeployment, estimated_order_value: Decimal | None = None) -> LiveGateDecision:
    if deployment.mode != "LIVE":
        return LiveGateDecision(True)

    settings: PlatformTradingSettings = await get_platform_trading_settings(db)
    if settings.global_kill_switch:
        return LiveGateDecision(False, "Global kill switch is ON. Live execution is blocked.")
    if not settings.live_trading_enabled:
        return LiveGateDecision(False, LIVE_DISABLED_MESSAGE + " and admin approval.")
    if not getattr(deployment, "live_approved", False):
        return LiveGateDecision(False, "Live trading is disabled until final production review and admin approval.")
    if not deployment.broker_account_id:
        return LiveGateDecision(False, "Live trading requires a LIVE broker account.")

    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None or broker.status != "CONNECTED":
        return LiveGateDecision(False, "Live trading requires a connected LIVE broker account.")
    if str(broker.mode or "").upper() != "LIVE":
        return LiveGateDecision(False, "Live trading requires broker account mode LIVE.")
    provider = broker.broker_provider
    if provider is not None and not bool(getattr(provider, "supports_live", False)):
        return LiveGateDecision(False, "Selected broker provider is not enabled for LIVE execution.")

    strategy = (await db.execute(select(Strategy).where(Strategy.id == deployment.strategy_id))).scalar_one_or_none()
    if strategy is not None and not bool(getattr(strategy, "is_live_approved", False)):
        return LiveGateDecision(False, "Strategy must be live approved before LIVE execution.")

    approval = await find_active_live_approval(db, deployment.user_id, deployment.broker_account_id)
    if approval is None:
        return LiveGateDecision(False, "Live trading is disabled until final production review and admin approval.")

    markets = _as_list(approval.approved_markets)
    requested_market = str(deployment.segment or deployment.exchange or deployment.instrument or "").upper()
    if markets and requested_market and not any(m in requested_market or requested_market in m for m in markets):
        return LiveGateDecision(False, "Deployment market is not included in the live approval.", approval)

    if approval.max_order_value is not None and estimated_order_value is not None and estimated_order_value > to_decimal(approval.max_order_value):
        return LiveGateDecision(False, "Order value exceeds approved live trading limit.", approval)

    start = day_start_utc()
    filled_statuses = ["FILLED", "PLACED", "PENDING"]
    if approval.max_trades_per_day is not None:
        count = int((await db.execute(select(func.count(LiveOrder.id)).where(LiveOrder.user_id == deployment.user_id, LiveOrder.created_at >= start, LiveOrder.status.in_(filled_statuses)))).scalar() or 0)
        if count >= int(approval.max_trades_per_day):
            return LiveGateDecision(False, "Approved max trades per day reached.", approval)

    if approval.max_daily_loss is not None:
        # Conservative: use existing local closed/open PnL rows where available.
        from ...db.models import LivePosition
        today_pnl = to_decimal((await db.execute(select(func.coalesce(func.sum(LivePosition.realized_pnl + LivePosition.unrealized_pnl), 0)).where(LivePosition.user_id == deployment.user_id))).scalar())
        if today_pnl < 0 and abs(today_pnl) >= to_decimal(approval.max_daily_loss):
            return LiveGateDecision(False, "Approved max daily loss reached.", approval)

    return LiveGateDecision(True, approval=approval)
