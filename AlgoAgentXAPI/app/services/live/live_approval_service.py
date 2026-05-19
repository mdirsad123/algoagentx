from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.models import BrokerAccount, LiveOrder, LiveTradingApproval, LiveTradeLog, PlatformTradingSettings, Strategy, StrategyDeployment
from .pnl_service import to_decimal
from .trading_safety import day_start_utc, get_platform_trading_settings
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
        return next((r for r in rows if str(r.broker_account_id) == str(broker_account_id)), None)
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


def _broker_mode_matches_deployment(broker: BrokerAccount, mode: str) -> bool:
    requested = str(mode or "PAPER").upper()
    broker_mode = str(getattr(broker, "mode", "") or "").upper()
    if requested == broker_mode:
        return True
    meta = getattr(broker, "metadata_json", None) or {}
    if isinstance(meta, dict):
        selected_mt5 = meta.get("selected_account") or meta.get("mt5_selected_account") or meta.get("account_info") or meta.get("last_test") or {}
        if isinstance(selected_mt5, dict):
            account_mode = str(selected_mt5.get("mode") or selected_mt5.get("account_type") or selected_mt5.get("trading_mode") or "").upper()
            if requested == "LIVE" and account_mode in {"LIVE", "REAL"}:
                return True
            if requested == "DEMO" and account_mode == "DEMO":
                return True
        selected_ctrader = meta.get("ctrader_selected_account")
        if isinstance(selected_ctrader, dict):
            account_mode = str(selected_ctrader.get("account_type") or "").upper()
            if requested == account_mode:
                return True
    return False


def _approval_market_allowed(approval: LiveTradingApproval, instrument: str | None = None, exchange: str | None = None, segment: str | None = None, broker_symbol: str | None = None, instrument_key: str | None = None) -> bool:
    """Return whether an approval covers the requested instrument/market.

    Current product rule: broker approval unlocks the broker account for DEMO/LIVE.
    approved_markets is informational by default and only becomes restrictive when
    LIVE_APPROVAL_STRICT_MARKET_SCOPE=true. ALL/ANY/* always allow everything.
    """
    markets = _as_list(approval.approved_markets)
    if not markets or any(m in {"ALL", "ANY", "*"} for m in markets):
        return True
    if not bool(getattr(settings, "live_approval_strict_market_scope", False)):
        return True
    requested = [str(v or "").upper() for v in [instrument, exchange, segment, broker_symbol, instrument_key] if str(v or "").strip()]
    if not requested:
        return True
    return any(m in r or r in m for m in markets for r in requested)


async def check_broker_deployment_approval(
    db: AsyncSession,
    user_id: UUID,
    broker_account_id: UUID | None,
    mode: str,
    instrument: str | None = None,
    exchange: str | None = None,
    segment: str | None = None,
    broker_symbol: str | None = None,
    instrument_key: str | None = None,
) -> LiveTradingApproval | None:
    normalized_mode = str(mode or "PAPER").upper()
    if normalized_mode == "PAPER":
        return None
    if broker_account_id is None:
        raise HTTPException(status_code=400, detail=f"{normalized_mode} deployment requires a connected broker account.")

    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == broker_account_id, BrokerAccount.user_id == user_id))).scalar_one_or_none()
    if broker is None:
        raise HTTPException(status_code=404, detail="Broker account not found")
    if str(broker.status or "").upper() != "CONNECTED":
        raise HTTPException(status_code=400, detail=f"{normalized_mode} deployment requires broker account status CONNECTED.")
    if not _broker_mode_matches_deployment(broker, normalized_mode):
        raise HTTPException(status_code=400, detail=f"Selected broker account is not a {normalized_mode} account.")
    broker_code = get_broker_code(broker)
    if broker_code in {"CTRADER", "CTRADER_API"}:
        if normalized_mode == "DEMO" and not bool(getattr(settings, "ctrader_demo_trading_enabled", True)):
            raise HTTPException(status_code=400, detail="cTrader demo auto trading is disabled by platform configuration.")
        if normalized_mode == "LIVE" and not bool(getattr(settings, "ctrader_live_trading_enabled", False)):
            raise HTTPException(status_code=400, detail="cTrader LIVE execution is disabled by platform configuration.")

    approval = await find_active_live_approval(db, user_id, broker_account_id)
    if approval is None or str(approval.status or "").upper() != "APPROVED" or approval.risk_disclaimer_accepted_at is None:
        raise HTTPException(status_code=400, detail=f"This broker account is not approved for {normalized_mode} deployment. Please request approval first.")
    if not _approval_market_allowed(approval, instrument, exchange, segment, broker_symbol, instrument_key):
        raise HTTPException(status_code=400, detail=f"This broker account approval does not include the selected market/instrument for {normalized_mode} deployment.")
    return approval


def enforce_approval_limits(approval: LiveTradingApproval | None, values: dict[str, Any]) -> None:
    if approval is None:
        return
    if approval.max_daily_loss is not None and values.get("max_daily_loss") is not None and to_decimal(values.get("max_daily_loss")) > to_decimal(approval.max_daily_loss):
        raise HTTPException(status_code=400, detail=f"Max daily loss exceeds approved limit ({approval.max_daily_loss}).")
    if approval.max_trades_per_day is not None and values.get("max_trades_per_day") is not None and int(values.get("max_trades_per_day") or 0) > int(approval.max_trades_per_day):
        raise HTTPException(status_code=400, detail=f"Max trades per day exceeds approved limit ({approval.max_trades_per_day}).")
    if approval.max_order_value is not None and values.get("max_order_value") is not None and to_decimal(values.get("max_order_value")) > to_decimal(approval.max_order_value):
        raise HTTPException(status_code=400, detail=f"Max order value exceeds approved limit ({approval.max_order_value}).")


async def check_live_execution_gate(db: AsyncSession, deployment: StrategyDeployment, estimated_order_value: Decimal | None = None) -> LiveGateDecision:
    if str(deployment.mode or "").upper() != "LIVE":
        return LiveGateDecision(True)

    platform_settings: PlatformTradingSettings = await get_platform_trading_settings(db)
    if platform_settings.global_kill_switch:
        return LiveGateDecision(False, "Global kill switch is ON. Live execution is blocked.")
    if not deployment.broker_account_id:
        return LiveGateDecision(False, "Live trading requires a LIVE broker account.")

    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker is None or str(broker.status or "").upper() != "CONNECTED":
        return LiveGateDecision(False, "Live trading requires a connected LIVE broker account.")
    if not _broker_mode_matches_deployment(broker, "LIVE"):
        return LiveGateDecision(False, "Live trading requires broker account mode LIVE.")
    if get_broker_code(broker) in {"CTRADER", "CTRADER_API"} and not bool(getattr(settings, "ctrader_live_trading_enabled", False)):
        return LiveGateDecision(False, "cTrader LIVE execution is disabled by platform configuration.")
    provider = broker.broker_provider
    if provider is not None and not bool(getattr(provider, "supports_live", False)) and get_broker_code(broker) not in {"MT5", "MT5_AGENT", "CTRADER", "CTRADER_API"}:
        return LiveGateDecision(False, "Selected broker provider is not enabled for LIVE execution.")

    strategy = (await db.execute(select(Strategy).where(Strategy.id == deployment.strategy_id))).scalar_one_or_none()
    if strategy is not None and not bool(getattr(strategy, "is_live_approved", False)):
        return LiveGateDecision(False, "Strategy must be live approved before LIVE execution.")

    approval = await find_active_live_approval(db, deployment.user_id, deployment.broker_account_id)
    if approval is None or approval.risk_disclaimer_accepted_at is None:
        return LiveGateDecision(False, "This broker account is not approved for LIVE deployment. Please request approval first.")

    if not _approval_market_allowed(approval, deployment.instrument, deployment.exchange, deployment.segment, deployment.broker_symbol, deployment.instrument_key):
        return LiveGateDecision(False, "Deployment market is not included in the live approval because strict market scope is enabled.", approval)

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
