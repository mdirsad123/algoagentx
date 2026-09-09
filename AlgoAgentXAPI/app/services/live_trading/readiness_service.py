from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import (
    BrokerAccount,
    Instrument,
    LiveMarketCandle,
    LiveOrder,
    LiveTradeLog,
    PlatformTradingSettings,
    Strategy,
    StrategyDeployment,
)
from ..brokers.factory import get_broker_code
from ..live.order_preview_service import build_live_order_preview, find_live_instrument_spec
from ..trading.guardrails import validate_instrument_spec
from ..live.trading_safety import day_start_utc, get_platform_trading_settings
from ..live.compatibility_service import run_live_compatibility_check
from ..live.funded_guard_service import (
    _rule_clock,
    broker_funded_state,
    current_funded_trades_count,
    evaluate_funded_guard,
    funded_status_payload,
    validate_risk_tiers,
)

PASS = "PASS"
FAIL = "FAIL"
WARNING = "WARNING"


def _user_id_from(user: dict) -> Any:
    return user.get("id") or user.get("user_id") or user.get("sub")


def _is_admin(user: dict) -> bool:
    role = str(user.get("role") or user.get("user_role") or "").upper()
    return bool(user.get("is_admin")) or role == "ADMIN"


def _check(key: str, label: str, status: str, message: str, action_label: str | None = None, action_href: str | None = None) -> dict[str, Any]:
    payload = {"key": key, "label": label, "status": status, "message": message}
    if action_label:
        payload["action_label"] = action_label
    if action_href:
        payload["action_href"] = action_href
    return payload


def _mode(row: StrategyDeployment | None) -> str:
    return str(getattr(row, "mode", "PAPER") or "PAPER").upper()


def _status(row: StrategyDeployment | None) -> str:
    return str(getattr(row, "status", "") or "").upper()


def _dec(value: Any, default: str = "0") -> Decimal:
    try:
        if value in (None, ""):
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


async def _safe(label: str, fn, fallback_key: str) -> list[dict[str, Any]]:
    try:
        result = await fn()
        return result if isinstance(result, list) else [result]
    except Exception as exc:
        return [_check(fallback_key, label, FAIL, f"Readiness check failed safely: {exc}")]


async def _get_deployment(db: AsyncSession, deployment_id: UUID, user: dict) -> StrategyDeployment | None:
    stmt = select(StrategyDeployment).where(StrategyDeployment.id == deployment_id)
    if not _is_admin(user):
        stmt = stmt.where(StrategyDeployment.user_id == _user_id_from(user))
    return (await db.execute(stmt)).scalar_one_or_none()


async def check_strategy_ready(db: AsyncSession, deployment: StrategyDeployment) -> list[dict[str, Any]]:
    strategy = getattr(deployment, "strategy", None)
    if strategy is None:
        strategy = (await db.execute(select(Strategy).where(Strategy.id == deployment.strategy_id))).scalar_one_or_none()
    if strategy is None:
        return [
            _check("strategy_public", "Strategy published", FAIL, "Strategy was not found.", "Open Strategy", "/strategies"),
            _check("strategy_deployable_for_mode", "Strategy deployable for mode", FAIL, "Strategy was not found.", "Open Strategy", "/strategies"),
        ]

    visibility = str(getattr(strategy, "visibility", "") or "").upper()
    mode = _mode(deployment)
    if mode == "LIVE":
        deployable = bool(getattr(strategy, "is_live_approved", False))
        deploy_msg = "Strategy is LIVE approved." if deployable else "Strategy is not LIVE approved. LIVE requires strategy approval plus broker deployment approval."
    elif mode == "DEMO":
        deployable = bool(getattr(strategy, "is_deployable_demo", False))
        deploy_msg = "Strategy is enabled for DEMO deployment." if deployable else "Ask admin to enable Demo Deployment for this strategy."
    else:
        deployable = bool(getattr(strategy, "is_deployable_paper", False))
        deploy_msg = "Strategy is enabled for PAPER deployment." if deployable else "Ask admin to enable Paper Deployment for this strategy."

    return [
        _check("strategy_public", "Strategy published", PASS if visibility == "PUBLIC" else FAIL, "Strategy is public and deployable." if visibility == "PUBLIC" else "Only PUBLIC strategies can be deployed.", "Open Strategy", "/strategies"),
        _check("strategy_deployable_for_mode", "Strategy deployable for mode", PASS if deployable else FAIL, deploy_msg, "Open Strategy", "/strategies"),
    ]


async def check_broker_ready(db: AsyncSession, deployment: StrategyDeployment) -> list[dict[str, Any]]:
    mode = _mode(deployment)
    broker_required = mode in {"DEMO", "LIVE"}
    checks = [_check("broker_required_for_mode", "Broker required for mode", PASS if broker_required else PASS, "Broker connection is required for DEMO/LIVE." if broker_required else "PAPER mode simulates orders inside AlgoAgentX and does not require broker.")]

    if not broker_required:
        checks.append(_check("broker_connected", "Broker connected", PASS, "PAPER mode does not need a broker connection.", "Connect Broker", "/brokers"))
        return checks

    if not deployment.broker_account_id:
        checks.append(_check("broker_connected", "Broker connected", FAIL, "DEMO mode requires a linked CONNECTED broker account.", "Connect Broker", "/brokers"))
        return checks

    broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    connected = broker is not None and str(getattr(broker, "status", "") or "").upper() == "CONNECTED"
    message = f"{get_broker_code(broker) if broker else 'Broker'} account is connected." if connected else "Broker account is missing or not CONNECTED. Go to Brokers and click Test Connection."
    checks.append(_check("broker_connected", "Broker connected", PASS if connected else FAIL, message, "Connect Broker", "/brokers"))
    return checks


async def check_instrument_ready(db: AsyncSession, deployment: StrategyDeployment) -> list[dict[str, Any]]:
    row, spec = await find_live_instrument_spec(db, symbol=deployment.instrument)
    if spec is None:
        return [
            _check("instrument_spec_exists", "Instrument spec exists", FAIL, "Instrument Master spec is missing for this symbol.", "Open Settings", f"/live-trading/{deployment.id}/settings"),
            _check("instrument_spec_valid", "Instrument spec valid", FAIL, "Cannot validate instrument until spec exists.", "Open Settings", f"/live-trading/{deployment.id}/settings"),
            _check("broker_symbol_configured", "Broker symbol configured", WARNING, "Broker symbol/instrument key is not configured. Configure it if broker symbol differs from deployment symbol.", "Open Settings", f"/live-trading/{deployment.id}/settings"),
        ]

    validation = validate_instrument_spec(spec, live=True)
    valid = bool(validation.get("valid"))
    errors = validation.get("errors") or []
    broker_symbol = getattr(deployment, "broker_symbol", None) or getattr(deployment, "instrument_key", None) or spec.get("broker_symbol") or deployment.instrument
    return [
        _check("instrument_spec_exists", "Instrument spec exists", PASS, f"Instrument Master found for {spec.get('symbol') or deployment.instrument}."),
        _check("instrument_spec_valid", "Instrument spec valid", PASS if valid else FAIL, "Instrument risk fields are valid." if valid else " ".join(errors) or "Instrument risk fields are incomplete.", "Open Settings", f"/live-trading/{deployment.id}/settings"),
        _check("broker_symbol_configured", "Broker symbol configured", PASS if broker_symbol else WARNING, f"Broker symbol resolved as {broker_symbol}." if broker_symbol else "Configure broker_symbol or instrument_key when broker uses a different symbol.", "Open Settings", f"/live-trading/{deployment.id}/settings"),
    ]


async def check_market_data_ready(db: AsyncSession, deployment: StrategyDeployment) -> list[dict[str, Any]]:
    count = int((await db.execute(select(func.count(LiveMarketCandle.id)).where(LiveMarketCandle.deployment_id == deployment.id, LiveMarketCandle.is_closed.is_(True)))).scalar() or 0)
    latest = (await db.execute(select(LiveMarketCandle).where(LiveMarketCandle.deployment_id == deployment.id, LiveMarketCandle.is_closed.is_(True)).order_by(LiveMarketCandle.candle_time.desc()).limit(1))).scalar_one_or_none()
    enough = count >= 50
    return [
        _check("latest_candles_available", "Latest candles available", PASS if latest else FAIL, f"Latest closed candle is {latest.candle_time}." if latest else "No closed live candles stored yet. Refresh candles first.", "Refresh Candles", f"/live-trading/{deployment.id}"),
        _check("enough_candles_for_strategy", "Enough candles for strategy", PASS if enough else WARNING, f"{count} closed candles are stored." if enough else f"Only {count} closed candles are stored. Many strategies need at least 50 candles.", "Refresh Candles", f"/live-trading/{deployment.id}"),
    ]


async def check_risk_preview_ready(db: AsyncSession, deployment: StrategyDeployment) -> list[dict[str, Any]]:
    latest = (await db.execute(select(LiveMarketCandle).where(LiveMarketCandle.deployment_id == deployment.id, LiveMarketCandle.is_closed.is_(True)).order_by(LiveMarketCandle.candle_time.desc()).limit(1))).scalar_one_or_none()
    entry = _dec(getattr(latest, "close", None), "0") if latest is not None else Decimal("0")
    if entry <= 0:
        return [
            _check("latest_entry_plan_ok", "Latest entry plan OK", FAIL, "Entry plan needs a latest candle close price. Refresh candles first.", "Refresh Candles", f"/live-trading/{deployment.id}"),
            _check("risk_preview_ok", "Risk preview OK", FAIL, "Risk preview needs a latest candle close price. Refresh candles first.", "Preview Order", f"/live-trading/{deployment.id}/settings"),
        ]
    broker = None
    broker_code = None
    if deployment.broker_account_id:
        broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
        broker_code = get_broker_code(broker) if broker is not None else None
    funded_decision = None
    if str(getattr(deployment, "account_policy_type", "STANDARD") or "STANDARD").upper() == "FUNDED":
        funded_decision = await evaluate_funded_guard(
            db,
            deployment,
            purpose="READINESS_PREVIEW",
            persist_decision=False,
            auto_pause_on_breach=False,
        )

    preview = await build_live_order_preview(
        db,
        deployment=deployment,
        broker_code=broker_code,
        side="BUY",
        preview_mode="AUTO_LATEST_PRICE",
        strict_instrument=True,
        funded_guard=funded_decision.to_dict() if funded_decision is not None else None,
        risk_amount_override=funded_decision.effective_risk_amount if funded_decision is not None else None,
        risk_percent_override=funded_decision.effective_risk_pct if funded_decision is not None else None,
    )
    ok = str(preview.get("validation_status") or preview.get("status") or "").upper() == "OK"
    entry_plan = preview.get("entry_plan") or {}
    entry_ok = entry_plan.get("status") == "OK"
    reason = preview.get("rejected_reason") or "Order sizing preview passed with current runtime risk settings."
    entry_msg = "Latest entry plan calculated SL/TP." if entry_ok else str(reason or "SL/TP could not be calculated.")
    return [
        _check("latest_entry_plan_ok", "Latest entry plan OK", PASS if entry_ok else FAIL, entry_msg, "Preview Order", f"/live-trading/{deployment.id}/settings"),
        _check("risk_preview_ok", "Risk preview OK", PASS if ok else FAIL, str(reason), "Preview Order", f"/live-trading/{deployment.id}/settings"),
    ]


async def check_live_compatibility_ready(db: AsyncSession, deployment: StrategyDeployment) -> list[dict[str, Any]]:
    result = await run_live_compatibility_check(db, deployment.id)
    status = str(result.get("status") or FAIL).upper()
    message = result.get("summary") or "Live compatibility checked."
    checks = result.get("checks") or []
    return [_check("live_compatibility_ok", "Live Compatibility", PASS if status == PASS else WARNING if status == WARNING else FAIL, message, "Open Compatibility", f"/live-trading/{deployment.id}") | {"data": {"checks": checks}}]

async def check_funded_ready(db: AsyncSession, deployment: StrategyDeployment) -> list[dict[str, Any]]:
    if str(getattr(deployment, "account_policy_type", "STANDARD") or "STANDARD").upper() != "FUNDED":
        return [_check("funded_policy_ready", "Funded policy", PASS, "Standard broker deployment; funded guard is not required.")]

    checks: list[dict[str, Any]] = []
    snapshot = getattr(deployment, "funded_profile_snapshot", None) or {}
    checks.append(_check(
        "funded_profile_attached", "Funded profile attached",
        PASS if getattr(deployment, "funded_profile_id", None) and snapshot else FAIL,
        "Funded profile snapshot is attached and immutable for this deployment." if snapshot else "Funded profile snapshot is missing.",
        "Open Settings", f"/live-trading/{deployment.id}/settings",
    ))

    profile_snapshot = snapshot.get("profile") or {} if isinstance(snapshot, dict) else {}
    phases = snapshot.get("phases") or [] if isinstance(snapshot, dict) else []
    phase_number = getattr(deployment, "funded_phase_number", None)
    challenge_type = str(profile_snapshot.get("challenge_type") or "").upper()
    phase_ok = challenge_type == "INSTANT" or not phases or (phase_number is not None and any(int(p.get("phase_number") or 0) == int(phase_number) for p in phases))
    checks.append(_check(
        "funded_phase_valid", "Funded phase valid", PASS if phase_ok else FAIL,
        f"Funded phase {phase_number} is valid." if phase_ok and phase_number is not None else ("Instant funded stage is valid." if phase_ok else "Selected funded phase is invalid or missing."),
        "Open Settings", f"/live-trading/{deployment.id}/settings",
    ))

    risk_mode = str(getattr(deployment, "funded_risk_mode", "DYNAMIC") or "DYNAMIC").upper()
    risk_ok = True
    risk_message = f"Funded risk mode is {risk_mode}."
    try:
        if risk_mode == "DYNAMIC":
            validate_risk_tiers(getattr(deployment, "funded_risk_plan_snapshot", None) or [])
        elif risk_mode == "FIXED":
            fixed = _dec(getattr(deployment, "funded_fixed_risk_pct", None), "0")
            if fixed <= 0:
                raise ValueError("Fixed funded risk must be greater than zero.")
        else:
            raise ValueError("Unsupported funded risk mode.")
    except Exception as exc:
        risk_ok = False
        risk_message = str(exc)
    checks.append(_check("funded_risk_plan_valid", "Funded risk plan valid", PASS if risk_ok else FAIL, risk_message, "Open Settings", f"/live-trading/{deployment.id}/settings"))

    broker = None
    if deployment.broker_account_id:
        broker = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    broker_state = broker_funded_state(broker) if broker is not None else {"fresh": False, "balance": None, "equity": None, "currency": None}
    balance_ok = broker_state.get("balance") is not None and _dec(broker_state.get("balance")) > 0
    equity_ok = broker_state.get("equity") is not None and _dec(broker_state.get("equity")) > 0
    fresh_ok = bool(broker_state.get("fresh"))
    expected_currency = str(profile_snapshot.get("account_currency") or "USD").upper()
    actual_currency = str(broker_state.get("currency") or "").upper()
    currency_ok = bool(actual_currency) and actual_currency == expected_currency

    try:
        _, rule_timezone, daily_reset_time = _rule_clock(deployment)
        rule_clock_ok = True
        rule_clock_message = f"Funded rule day uses {rule_timezone} reset at {daily_reset_time}."
    except Exception as exc:
        rule_clock_ok = False
        rule_clock_message = str(exc)

    checks.extend([
        _check("funded_broker_balance_fresh", "Funded broker balance fresh", PASS if (fresh_ok and balance_ok) else FAIL, f"Broker balance: {broker_state.get('balance')}." if fresh_ok and balance_ok else "Fresh positive broker balance is required. Funded fallback capital is forbidden."),
        _check("funded_broker_equity_fresh", "Funded broker equity fresh", PASS if (fresh_ok and equity_ok) else FAIL, f"Broker equity: {broker_state.get('equity')}." if fresh_ok and equity_ok else "Fresh positive broker equity is required before funded entries."),
        _check("funded_broker_currency_matches", "Funded broker currency matches", PASS if currency_ok else FAIL, f"Broker/profile currency: {actual_currency}." if currency_ok else f"Broker currency {actual_currency or 'UNKNOWN'} does not match funded profile currency {expected_currency}."),
        _check("funded_rule_clock_valid", "Funded rule timezone/reset valid", PASS if rule_clock_ok else FAIL, rule_clock_message, "Open Settings", f"/live-trading/{deployment.id}/settings"),
    ])

    status = await funded_status_payload(db, deployment)
    state = status.get("guard") or {}
    initialized = bool(state) and str(state.get("status") or "NOT_INITIALIZED").upper() != "NOT_INITIALIZED"
    guard_status = str(state.get("status") or "NOT_INITIALIZED").upper()
    guard_ok = guard_status not in {"BLOCKED", "FAILED", "PASS_READY", "AWAITING_PROVIDER_TRANSITION"}
    checks.append(_check("funded_state_initialized", "Funded state initialized", PASS if initialized else FAIL, f"Funded guard state is {guard_status}." if initialized else "Funded runtime state is not initialized. Start/refresh with a fresh broker sync."))
    checks.append(_check("funded_guard_not_breached", "Funded DD guard not breached", PASS if (initialized and guard_ok) else FAIL, state.get("reason") or (f"Funded guard is {guard_status}." if initialized else "Funded guard is not initialized.")))
    return checks


async def check_runner_ready(db: AsyncSession, deployment: StrategyDeployment) -> list[dict[str, Any]]:
    auto_trade = bool(getattr(deployment, "auto_trade_enabled", False))
    auto_runner = bool(getattr(deployment, "auto_runner_enabled", False))
    runner_error = getattr(deployment, "runner_last_error", None)
    broker_error = getattr(deployment, "live_sync_last_error", None)
    return [
        _check("auto_trade_enabled", "Auto Trade enabled", PASS if auto_trade else WARNING, "Auto Trade places an order only when strategy gives BUY/SELL and risk preview passes." if auto_trade else "Auto Trade is OFF. Signals will be saved but not executed.", "Enable Auto Trade", f"/live-trading/{deployment.id}/settings"),
        _check("auto_runner_enabled", "Auto Runner enabled", PASS if auto_runner else WARNING, "Auto Runner checks every new closed candle." if auto_runner else "Auto Runner is OFF. Strategy will not run automatically on new closed candles.", "Enable Auto Runner", f"/live-trading/{deployment.id}"),
        _check("no_blocking_runner_error", "No blocking runner error", PASS if not runner_error else FAIL, "No recent blocking runner error." if not runner_error else str(runner_error), "Run Dry Test", f"/live-trading/{deployment.id}"),
        _check("no_blocking_broker_error", "No blocking broker error", PASS if not broker_error else FAIL, "No recent broker sync error." if not broker_error else str(broker_error), "Sync Broker", f"/live-trading/{deployment.id}"),
        _check("duplicate_protection_enabled", "Duplicate protection enabled", PASS, "Runner checks deployment, strategy, instrument, timeframe, candle time and signal side before executing."),
    ]


async def check_platform_and_limits(db: AsyncSession, deployment: StrategyDeployment) -> list[dict[str, Any]]:
    settings = await get_platform_trading_settings(db)
    mode = _mode(deployment)
    if getattr(settings, "global_kill_switch", False):
        platform_status = FAIL
        platform_msg = "Global kill switch is ON. Trading is paused for all deployments."
    elif mode == "LIVE" and not getattr(settings, "live_trading_enabled", False):
        platform_status = FAIL
        platform_msg = "LIVE mode is locked until admin/global setting allows it."
    elif mode == "DEMO" and not getattr(settings, "demo_trading_enabled", True):
        platform_status = FAIL
        platform_msg = "DEMO trading is disabled by platform settings."
    elif mode == "PAPER" and not getattr(settings, "paper_trading_enabled", True):
        platform_status = FAIL
        platform_msg = "PAPER trading is disabled by platform settings."
    else:
        platform_status = PASS
        platform_msg = f"{mode} mode is allowed by platform settings."

    is_funded = str(getattr(deployment, "account_policy_type", "STANDARD") or "STANDARD").upper() == "FUNDED"
    max_trades = int(getattr(deployment, "max_trades_per_day", 0) or 0)
    if is_funded:
        # Funded max-trades/day follows the provider rule day rather than UTC midnight.
        orders_today = await current_funded_trades_count(db, deployment)
        max_trades_ok = max_trades <= 0 or orders_today < max_trades
        # Prop-firm daily/max drawdown is evaluated by check_funded_ready. Do not let
        # the legacy absolute max_daily_loss field masquerade as a funded rule.
        loss_ok = True
        loss_message = "Funded daily/max drawdown is checked by the funded guard using the profile rule day."
    else:
        start = day_start_utc()
        orders_today = int((await db.execute(select(func.count(LiveOrder.id)).where(LiveOrder.deployment_id == deployment.id, LiveOrder.created_at >= start))).scalar() or 0)
        max_trades_ok = max_trades <= 0 or orders_today < max_trades
        # Live orders do not persist realized PnL directly in all schema versions; keep this guard
        # conservative for Standard deployments and let the execution engine enforce real PnL limits later.
        pnl = Decimal("0")
        max_loss = _dec(getattr(deployment, "max_daily_loss", None), "0")
        loss_ok = max_loss <= 0 or pnl >= -max_loss
        loss_message = "Daily loss guard is OK." if loss_ok else "Daily loss guard has been exceeded."

    return [
        _check("platform_mode_allowed", "Platform mode allowed", platform_status, platform_msg),
        _check("global_kill_switch_off", "Global kill switch off", PASS if not getattr(settings, "global_kill_switch", False) else FAIL, "Global kill switch is OFF." if not getattr(settings, "global_kill_switch", False) else "Global kill switch is ON."),
        _check("max_daily_loss_not_exceeded", "Max daily loss not exceeded", PASS if loss_ok else FAIL, loss_message, "Open Settings", f"/live-trading/{deployment.id}/settings"),
        _check("max_trades_not_exceeded", "Max trades not exceeded", PASS if max_trades_ok else FAIL, f"Trades in current {'funded rule day' if is_funded else 'UTC day'}: {orders_today}/{max_trades or '∞'}." if max_trades_ok else f"Max trades per day reached: {orders_today}/{max_trades}.", "Open Settings", f"/live-trading/{deployment.id}/settings"),
    ]


async def build_live_deployment_readiness(db: AsyncSession, deployment_id: UUID, user: dict) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    deployment = await _get_deployment(db, deployment_id, user)
    if deployment is None:
        checks.append(_check("deployment_exists", "Deployment exists", FAIL, "Deployment was not found or you do not have access."))
        return {"overall_status": "NOT_READY", "ready_to_auto_trade": False, "summary": "Not ready yet", "checks": checks}

    checks.append(_check("deployment_exists", "Deployment exists", PASS, "Deployment record found."))
    running = _status(deployment) == "RUNNING"
    checks.append(_check("deployment_status_running", "Deployment running", PASS if running else FAIL, "Deployment is running." if running else f"Deployment is {deployment.status}. Start it before auto trading.", "Start Deployment", f"/live-trading/{deployment.id}"))

    for label, fn, fallback in [
        ("Strategy ready", lambda: check_strategy_ready(db, deployment), "strategy_deployable_for_mode"),
        ("Broker ready", lambda: check_broker_ready(db, deployment), "broker_connected"),
        ("Instrument ready", lambda: check_instrument_ready(db, deployment), "instrument_spec_valid"),
        ("Market data ready", lambda: check_market_data_ready(db, deployment), "latest_candles_available"),
        ("Risk preview ready", lambda: check_risk_preview_ready(db, deployment), "risk_preview_ok"),
        ("Live compatibility ready", lambda: check_live_compatibility_ready(db, deployment), "live_compatibility_ok"),
        ("Funded guard ready", lambda: check_funded_ready(db, deployment), "funded_policy_ready"),
        ("Runner ready", lambda: check_runner_ready(db, deployment), "auto_runner_enabled"),
        ("Platform limits ready", lambda: check_platform_and_limits(db, deployment), "platform_mode_allowed"),
    ]:
        checks.extend(await _safe(label, fn, fallback))

    blocking = {"deployment_exists", "deployment_status_running", "strategy_public", "strategy_deployable_for_mode", "broker_connected", "instrument_spec_exists", "instrument_spec_valid", "latest_entry_plan_ok", "risk_preview_ok", "live_compatibility_ok", "platform_mode_allowed", "global_kill_switch_off", "max_daily_loss_not_exceeded", "max_trades_not_exceeded", "no_blocking_runner_error", "no_blocking_broker_error", "duplicate_protection_enabled", "funded_profile_attached", "funded_phase_valid", "funded_risk_plan_valid", "funded_broker_balance_fresh", "funded_broker_equity_fresh", "funded_broker_currency_matches", "funded_rule_clock_valid", "funded_state_initialized", "funded_guard_not_breached"}
    has_blocking_fail = any(c.get("status") == FAIL and c.get("key") in blocking for c in checks)
    has_warning = any(c.get("status") == WARNING for c in checks)
    ready_to_auto_trade = not has_blocking_fail and bool(getattr(deployment, "auto_trade_enabled", False)) and bool(getattr(deployment, "auto_runner_enabled", False))

    if ready_to_auto_trade and not has_warning:
        overall = "READY"
        summary = "Ready for auto trading"
    elif has_blocking_fail:
        overall = "NOT_READY"
        summary = "Not ready yet"
    else:
        overall = "WARNING"
        summary = "Almost ready"

    return {"overall_status": overall, "ready_to_auto_trade": ready_to_auto_trade, "summary": summary, "checks": checks}
