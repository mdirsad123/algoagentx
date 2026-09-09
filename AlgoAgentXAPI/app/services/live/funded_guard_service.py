from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import (
    BrokerAccount,
    FundedAccountPhase,
    FundedAccountProfile,
    FundedRiskTier,
    FundedLiveDailySnapshot,
    FundedLiveEvent,
    FundedLiveRiskDecision,
    FundedLiveState,
    LivePosition,
    LiveTradeLog,
    StrategyDeployment,
)
from ..funded_backtest.risk_policy import apply_effective_risk_guard, resolve_dynamic_risk
from ..funded_backtest.rule_engine import (
    calculate_daily_floor,
    calculate_max_loss_floor,
    evaluate_consistency,
    qualifies_trading_day,
    remaining_loss_capacity,
)

POLICY_FUNDED = "FUNDED"
RISK_DYNAMIC = "DYNAMIC"
RISK_FIXED = "FIXED"
ACTIVE_GUARD_STATES = {"READY", "RUNNING", "WARNING", "PAYOUT_ELIGIBLE", "PAYOUT_READY"}
BLOCKING_GUARD_STATES = {"BLOCKED", "FAILED", "PASS_READY", "AWAITING_PROVIDER_TRANSITION"}
DEFAULT_BROKER_STATE_MAX_AGE_SECONDS = 120
ZERO = Decimal("0")
ONE = Decimal("1")


def _d(value: Any, default: str = "0") -> Decimal:
    try:
        if value in (None, ""):
            return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(default)


def _json_number(value: Decimal | None):
    return None if value is None else str(value)


def _snapshot_profile(deployment: StrategyDeployment) -> dict[str, Any]:
    raw = deployment.funded_profile_snapshot or {}
    return dict(raw.get("profile") or {}) if isinstance(raw, dict) else {}


def _snapshot_phases(deployment: StrategyDeployment) -> list[dict[str, Any]]:
    raw = deployment.funded_profile_snapshot or {}
    phases = raw.get("phases") or [] if isinstance(raw, dict) else []
    return [dict(x) for x in phases if isinstance(x, dict)]


def _snapshot_tiers(deployment: StrategyDeployment) -> list[dict[str, Any]]:
    raw = deployment.funded_risk_plan_snapshot
    if isinstance(raw, dict):
        raw = raw.get("risk_tiers") or []
    if not isinstance(raw, list):
        raw = (deployment.funded_profile_snapshot or {}).get("risk_tiers") or []
    return [dict(x) for x in raw if isinstance(x, dict)]


def _phase_config(deployment: StrategyDeployment) -> dict[str, Any] | None:
    phases = sorted(_snapshot_phases(deployment), key=lambda x: int(x.get("sequence") or x.get("phase_number") or 0))
    if not phases:
        return None
    requested = int(deployment.funded_phase_number or phases[0].get("phase_number") or 1)
    return next((p for p in phases if int(p.get("phase_number") or 0) == requested), None)


def _rules_config(deployment: StrategyDeployment) -> dict[str, Any]:
    profile = _snapshot_profile(deployment)
    rules = profile.get("rules_json") or {}
    return dict(rules) if isinstance(rules, dict) else {}


def _payout_config(deployment: StrategyDeployment) -> dict[str, Any]:
    profile = _snapshot_profile(deployment)
    payout = profile.get("payout_config") or {}
    return dict(payout) if isinstance(payout, dict) else {}


def _funded_rule_config(deployment: StrategyDeployment) -> dict[str, Any]:
    phase = _phase_config(deployment)
    if phase:
        return phase
    # Instant profiles keep rule thresholds in payout_config/rules_json.
    payout = _payout_config(deployment)
    rules = _rules_config(deployment)
    return {**rules, **payout}


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _rule_clock(deployment: StrategyDeployment, now_utc: datetime | None = None) -> tuple[Any, str, str]:
    now_utc = now_utc or datetime.now(timezone.utc)
    rules = _rules_config(deployment)
    tz_name = str(rules.get("rule_timezone") or "UTC")
    reset_text = str(rules.get("daily_reset_time") or "00:00")[:5]
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Invalid funded rule timezone: {tz_name}") from exc
    try:
        hh, mm = [int(x) for x in reset_text.split(":", 1)]
        reset = time(hour=hh, minute=mm)
    except Exception as exc:
        raise ValueError(f"Invalid funded daily_reset_time: {reset_text}") from exc
    local_now = now_utc.astimezone(tz)
    local_date = local_now.date()
    if local_now.timetz().replace(tzinfo=None) < reset:
        local_date = local_date - timedelta(days=1)
    return local_date, tz_name, reset_text


def _broker_sources(broker: BrokerAccount) -> list[dict[str, Any]]:
    meta = broker.metadata_json or {}
    out: list[dict[str, Any]] = []
    if isinstance(meta, dict):
        for key in ("last_test", "account_info", "selected_account", "mt5_selected_account", "ctrader_selected_account", "upstox_account_info"):
            value = meta.get(key)
            if isinstance(value, dict):
                out.append(value)
        out.append(meta)
    return out


def broker_funded_state(broker: BrokerAccount, *, max_age_seconds: int = DEFAULT_BROKER_STATE_MAX_AGE_SECONDS) -> dict[str, Any]:
    balance = equity = free_margin = None
    currency = None
    synced_at = None
    for src in _broker_sources(broker):
        if balance is None and src.get("balance") not in (None, ""):
            balance = _d(src.get("balance"))
        if equity is None and src.get("equity") not in (None, ""):
            equity = _d(src.get("equity"))
        if free_margin is None and (src.get("free_margin") or src.get("freeMargin")) not in (None, ""):
            free_margin = _d(src.get("free_margin") or src.get("freeMargin"))
        if not currency and (src.get("currency") or src.get("account_currency")):
            currency = str(src.get("currency") or src.get("account_currency")).upper()
        if synced_at is None:
            synced_at = _parse_datetime(src.get("synced_at") or src.get("timestamp") or src.get("updated_at"))
    # A generic DB row update is not proof that broker balance/equity was
    # refreshed. Funded trading only trusts an explicit broker metric timestamp
    # or the broker connection/sync timestamp.
    synced_at = synced_at or broker.last_connected_at
    if synced_at is not None and synced_at.tzinfo is None:
        synced_at = synced_at.replace(tzinfo=timezone.utc)
    age_seconds = None if synced_at is None else max(ZERO, _d((datetime.now(timezone.utc) - synced_at).total_seconds()))
    fresh = synced_at is not None and age_seconds <= Decimal(max_age_seconds)
    return {
        "balance": balance,
        "equity": equity,
        "free_margin": free_margin,
        "currency": currency,
        "synced_at": synced_at,
        "age_seconds": age_seconds,
        "fresh": fresh,
    }


async def add_funded_event(
    db: AsyncSession,
    deployment: StrategyDeployment,
    event_type: str,
    title: str,
    *,
    message: str | None = None,
    severity: str = "INFO",
    metadata: dict[str, Any] | None = None,
) -> FundedLiveEvent:
    row = FundedLiveEvent(
        deployment_id=deployment.id,
        event_type=event_type,
        severity=severity,
        title=title,
        message=message,
        metadata_json=metadata or {},
    )
    db.add(row)
    return row


def validate_risk_tiers(tiers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active = sorted([dict(t) for t in tiers if bool(t.get("is_active", True))], key=lambda t: int(t.get("sort_order") or 0))
    if not active:
        raise ValueError("At least one active funded risk tier is required")
    orders = [int(t.get("sort_order") or 0) for t in active]
    if len(orders) != len(set(orders)):
        raise ValueError("Funded risk tier sort_order values must be unique")
    for i, tier in enumerate(active):
        risk = _d(tier.get("risk_percent"))
        if risk <= 0 or risk > Decimal("0.10"):
            raise ValueError("Funded risk tier risk_percent must be > 0 and <= 10%")
        low = tier.get("min_account_return_pct")
        high = tier.get("max_account_return_pct")
        if low is not None and high is not None and _d(low) >= _d(high):
            raise ValueError(f"Invalid funded risk tier range: {tier.get('name')}")
        if i == 0 and low is not None:
            raise ValueError("First active funded risk tier must have an open lower bound")
        if i == len(active) - 1 and high is not None:
            raise ValueError("Last active funded risk tier must have an open upper bound")
        if i:
            prev_high = active[i - 1].get("max_account_return_pct")
            if prev_high is None or low is None or _d(prev_high) != _d(low):
                raise ValueError("Active funded risk tiers must have no gaps or overlaps")
    return active


async def validate_funded_profile_for_user(db: AsyncSession, profile_id: UUID, user_id: UUID):
    profile = (await db.execute(
        select(FundedAccountProfile).where(
            FundedAccountProfile.id == profile_id,
            FundedAccountProfile.is_active.is_(True),
            or_(FundedAccountProfile.user_id == user_id, FundedAccountProfile.is_template.is_(True)),
        )
    )).scalar_one_or_none()
    if profile is None:
        raise ValueError("Funded account profile not found, inactive, or not available to this user")
    phases = (await db.execute(select(FundedAccountPhase).where(FundedAccountPhase.profile_id == profile.id).order_by(FundedAccountPhase.sequence))).scalars().all()
    tiers = (await db.execute(select(FundedRiskTier).where(FundedRiskTier.profile_id == profile.id).order_by(FundedRiskTier.sort_order))).scalars().all()
    return profile, list(phases), list(tiers)


@dataclass
class FundedLiveGuardDecision:
    allowed_new_entry: bool
    reason: str | None
    guard_status: str
    balance: Decimal | None = None
    equity: Decimal | None = None
    free_margin: Decimal | None = None
    daily_floor: Decimal | None = None
    max_floor: Decimal | None = None
    remaining_daily_capacity: Decimal | None = None
    remaining_max_capacity: Decimal | None = None
    account_return_pct: Decimal = ZERO
    selected_risk_tier_name: str | None = None
    requested_risk_pct: Decimal = ZERO
    requested_risk_amount: Decimal = ZERO
    effective_risk_pct: Decimal = ZERO
    effective_risk_amount: Decimal = ZERO
    limiting_rule: str | None = None
    rule_date: Any = None
    rule_timezone: str | None = None
    phase_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, Decimal):
                data[key] = str(value)
            elif hasattr(value, "isoformat"):
                data[key] = value.isoformat()
        return data


async def _state_for_update(db: AsyncSession, deployment_id) -> FundedLiveState | None:
    return (await db.execute(select(FundedLiveState).where(FundedLiveState.deployment_id == deployment_id))).scalar_one_or_none()


async def _open_positions_count(db: AsyncSession, deployment_id) -> int:
    return int((await db.execute(select(func.count(LivePosition.id)).where(LivePosition.deployment_id == deployment_id, LivePosition.status == "OPEN"))).scalar_one() or 0)


async def _get_daily_snapshot(db: AsyncSession, deployment_id, rule_date) -> FundedLiveDailySnapshot | None:
    return (await db.execute(select(FundedLiveDailySnapshot).where(
        FundedLiveDailySnapshot.deployment_id == deployment_id,
        FundedLiveDailySnapshot.rule_date == rule_date,
    ))).scalar_one_or_none()


async def _finalize_previous_day(db: AsyncSession, deployment: StrategyDeployment, state: FundedLiveState, now: datetime) -> None:
    if state.rule_date is None:
        return
    snap = await _get_daily_snapshot(db, deployment.id, state.rule_date)
    if snap is None:
        return
    snap.end_balance = state.last_balance
    snap.end_equity = state.last_equity
    snap.day_realized_pnl = _d(state.last_balance) - _d(snap.start_balance)
    snap.day_unrealized_pnl = _d(state.last_equity) - _d(state.last_balance)
    snap.day_total_pnl = _d(state.last_equity) - _d(snap.start_equity)
    cfg = _funded_rule_config(deployment)
    try:
        snap.qualifying_day = qualifies_trading_day(
            day_closed_profit=snap.day_realized_pnl,
            trades_count=snap.trades_count,
            account_size=state.initial_account_size,
            mode=cfg.get("qualifying_day_mode") or "ANY_TRADE_DAY",
            minimum_profit_pct=cfg.get("minimum_qualifying_day_profit_pct") or _payout_config(deployment).get("qualifying_day_minimum_profit_pct"),
        )
    except ValueError:
        snap.qualifying_day = False
    if snap.trades_count > 0:
        state.trading_days = int(state.trading_days or 0) + 1
    if snap.qualifying_day:
        state.qualifying_days = int(state.qualifying_days or 0) + 1
    snap.state = "FINAL"


async def _ensure_state(db: AsyncSession, deployment: StrategyDeployment, broker: dict[str, Any], now: datetime) -> FundedLiveState:
    state = await _state_for_update(db, deployment.id)
    rule_date, tz_name, reset_text = _rule_clock(deployment, now)
    profile = _snapshot_profile(deployment)
    initial = _d(profile.get("account_size"))
    if initial <= 0:
        raise ValueError("Funded profile account size must be greater than 0")
    balance = _d(broker.get("balance"))
    equity = _d(broker.get("equity"))
    init_cfg = dict(deployment.funded_initialization_json or {})
    attach_mode = str(deployment.funded_attach_mode or "NEW_OR_RESET_ACCOUNT").upper()

    if state is None:
        if attach_mode == "EXISTING_IN_PROGRESS":
            cfg = _funded_rule_config(deployment)
            max_mode = str(cfg.get("max_drawdown_mode") or "").upper()
            if max_mode in {"TRAILING_BALANCE", "HIGH_WATER_MARK"} and init_cfg.get("existing_high_water_balance") in (None, ""):
                raise ValueError("existing_high_water_balance is required for this in-progress trailing funded account")
            if max_mode in {"TRAILING_EQUITY", "HIGH_WATER_MARK"} and init_cfg.get("existing_high_water_equity") in (None, ""):
                raise ValueError("existing_high_water_equity is required for this in-progress trailing funded account")
            day_balance = _d(init_cfg.get("today_start_balance"), str(balance))
            day_equity = _d(init_cfg.get("today_start_equity"), str(equity))
            high_balance = _d(init_cfg.get("existing_high_water_balance"), str(max(initial, balance)))
            high_equity = _d(init_cfg.get("existing_high_water_equity"), str(max(initial, equity)))
            completed_trading_days = int(init_cfg.get("completed_trading_days") or 0)
            completed_qualifying_days = int(init_cfg.get("completed_qualifying_days") or 0)
        else:
            day_balance, day_equity = balance, equity
            high_balance, high_equity = max(initial, balance), max(initial, equity)
            completed_trading_days = completed_qualifying_days = 0

        state = FundedLiveState(
            deployment_id=deployment.id,
            guard_status="READY",
            rule_date=rule_date,
            rule_timezone=tz_name,
            daily_reset_time=reset_text,
            initial_account_size=initial,
            phase_number=deployment.funded_phase_number,
            # Challenge targets are measured from the provider phase baseline,
            # not from the balance at the moment an existing account is attached.
            # Without this, attaching a $5,000 account at $5,200 would incorrectly
            # move an 8% target from $5,400 to $5,616.
            phase_start_balance=initial,
            phase_start_equity=initial,
            day_start_balance=day_balance,
            day_start_equity=day_equity,
            high_water_balance=high_balance,
            high_water_equity=high_equity,
            trading_days=completed_trading_days,
            qualifying_days=completed_qualifying_days,
            warning_state_json={},
        )
        db.add(state)
        await db.flush()
        db.add(FundedLiveDailySnapshot(
            deployment_id=deployment.id,
            rule_date=rule_date,
            start_balance=day_balance,
            start_equity=day_equity,
            peak_balance=balance,
            peak_equity=equity,
            low_equity=equity,
        ))
        await add_funded_event(db, deployment, "FUNDED_GUARD_INITIALIZED", "Funded live guard initialized", metadata={"rule_date": rule_date.isoformat(), "rule_timezone": tz_name, "attach_mode": attach_mode})
    elif state.rule_date != rule_date:
        await _finalize_previous_day(db, deployment, state, now)
        state.rule_date = rule_date
        state.rule_timezone = tz_name
        state.daily_reset_time = reset_text
        state.day_start_balance = balance
        state.day_start_equity = equity
        # Daily-DD warnings reset with the provider rule day. Max-DD warnings are
        # phase/account-cycle warnings and should not spam again every calendar day.
        state.warning_state_json = {k: v for k, v in dict(state.warning_state_json or {}).items() if str(k).startswith("MAX_")}
        db.add(FundedLiveDailySnapshot(
            deployment_id=deployment.id,
            rule_date=rule_date,
            start_balance=balance,
            start_equity=equity,
            peak_balance=balance,
            peak_equity=equity,
            low_equity=equity,
        ))
        await add_funded_event(db, deployment, "FUNDED_RULE_DAY_STARTED", "New funded rule day started", metadata={"rule_date": rule_date.isoformat(), "rule_timezone": tz_name, "daily_reset_time": reset_text})
    return state


async def _update_daily_snapshot(db: AsyncSession, deployment: StrategyDeployment, state: FundedLiveState, balance: Decimal, equity: Decimal) -> None:
    snap = await _get_daily_snapshot(db, deployment.id, state.rule_date)
    if snap is None:
        snap = FundedLiveDailySnapshot(
            deployment_id=deployment.id,
            rule_date=state.rule_date,
            start_balance=state.day_start_balance or balance,
            start_equity=state.day_start_equity or equity,
        )
        db.add(snap)
    snap.end_balance = balance
    snap.end_equity = equity
    snap.peak_balance = max(_d(snap.peak_balance, str(balance)), balance)
    snap.peak_equity = max(_d(snap.peak_equity, str(equity)), equity)
    if snap.low_equity is None:
        snap.low_equity = equity
    else:
        snap.low_equity = min(_d(snap.low_equity), equity)
    snap.day_realized_pnl = balance - _d(snap.start_balance)
    snap.day_unrealized_pnl = equity - balance
    snap.day_total_pnl = equity - _d(snap.start_equity)
    dd = max(ZERO, _d(snap.peak_equity, str(equity)) - equity)
    snap.daily_drawdown_amount = dd
    snap.daily_drawdown_pct = ZERO if _d(snap.peak_equity) <= 0 else dd / _d(snap.peak_equity)


async def _phase_and_payout_status(db: AsyncSession, deployment: StrategyDeployment, state: FundedLiveState, now: datetime) -> None:
    profile = _snapshot_profile(deployment)
    challenge = str(profile.get("challenge_type") or "CUSTOM").upper()
    balance = _d(state.last_balance)
    initial = _d(state.initial_account_size)
    phase = _phase_config(deployment)
    if phase:
        target_pct = phase.get("profit_target_pct")
        target_required = bool(phase.get("profit_target_required", True))
        if target_required and target_pct is not None:
            base = _d(state.phase_start_balance, str(initial))
            state.target_balance = base * (ONE + _d(target_pct))
            denom = max(Decimal("0.00000001"), state.target_balance - base)
            state.target_progress_pct = max(ZERO, min(ONE, (balance - base) / denom))
            if balance >= state.target_balance and state.target_reached_at is None:
                state.target_reached_at = now
                await add_funded_event(db, deployment, "FUNDED_TARGET_REACHED", "Funded phase target reached", metadata={"balance": str(balance), "target_balance": str(state.target_balance), "phase": state.phase_number})
        else:
            state.target_progress_pct = ONE
        required_days = int(phase.get("minimum_trading_days") or 0)
        mode = str(phase.get("qualifying_day_mode") or "ANY_TRADE_DAY").upper()
        completed = int(state.qualifying_days if mode == "MIN_PROFIT_DAY" else state.trading_days)
        target_ok = (not target_required) or (state.target_balance is not None and balance >= state.target_balance)
        if target_ok and completed >= required_days and state.guard_status not in {"FAILED", "BLOCKED", "PASS_READY", "AWAITING_PROVIDER_TRANSITION"}:
            state.guard_status = "PASS_READY"
            state.guard_reason = "Phase pass conditions satisfied; waiting for explicit provider phase transition"
            deployment.auto_trade_enabled = False
            if deployment.status == "RUNNING":
                deployment.status = "PAUSED"
            await add_funded_event(db, deployment, "FUNDED_PHASE_PASS_READY", "Funded phase is ready to pass", message=state.guard_reason, metadata={"phase": state.phase_number, "trading_days": state.trading_days, "qualifying_days": state.qualifying_days})
        return

    if challenge != "INSTANT":
        return
    payout = _payout_config(deployment)
    if not payout:
        return
    profit = max(ZERO, balance - initial)
    target = _d(payout.get("profit_target_amount")) if payout.get("profit_target_amount") is not None else initial * _d(payout.get("profit_target_pct"))
    minimum_payout = _d(payout.get("minimum_payout_amount"))
    req_trading = int(payout.get("minimum_trading_days") or 0)
    req_qualifying = int(payout.get("minimum_qualifying_profitable_days") or 0)
    snaps = (await db.execute(select(FundedLiveDailySnapshot).where(FundedLiveDailySnapshot.deployment_id == deployment.id))).scalars().all()
    positive = [_d(s.day_realized_pnl) for s in snaps if _d(s.day_realized_pnl) > 0]
    best = max(positive, default=ZERO)
    consistency_ok = True
    consistency_pct = ZERO
    if payout.get("consistency_rule_enabled"):
        maximum = payout.get("consistency_maximum_pct")
        if maximum is None:
            consistency_ok = False
        else:
            c = evaluate_consistency(best, positive, maximum)
            consistency_ok = bool(c["satisfied"])
            consistency_pct = _d(c["consistency_pct"])
    eligible = (
        state.guard_status not in {"FAILED", "BLOCKED"}
        and (target <= 0 or profit >= target)
        and (minimum_payout <= 0 or profit >= minimum_payout)
        and int(state.trading_days or 0) >= req_trading
        and int(state.qualifying_days or 0) >= req_qualifying
        and consistency_ok
    )
    if eligible and state.payout_eligible_at is None:
        state.payout_eligible_at = now
        state.guard_status = "PAYOUT_ELIGIBLE"
        await add_funded_event(db, deployment, "FUNDED_PAYOUT_ELIGIBLE", "Funded account is payout eligible", metadata={"profit": str(profit), "consistency_pct": str(consistency_pct)})
    if state.payout_eligible_at is not None:
        wait_days = int(payout.get("payout_waiting_calendar_days") or 0)
        ready_at = state.payout_eligible_at + timedelta(days=wait_days)
        if now >= ready_at and state.payout_ready_at is None and state.guard_status not in {"FAILED", "BLOCKED"}:
            state.payout_ready_at = ready_at
            state.guard_status = "PAYOUT_READY"
            await add_funded_event(db, deployment, "FUNDED_PAYOUT_READY", "Funded account payout is ready", metadata={"ready_at": ready_at.isoformat()})


async def _warning_events(db: AsyncSession, deployment: StrategyDeployment, state: FundedLiveState) -> None:
    warnings = dict(state.warning_state_json or {})
    cfg = _funded_rule_config(deployment)
    pairs = [
        ("DAILY", _d(cfg.get("daily_drawdown_pct")), state.remaining_daily_capacity, state.daily_floor, state.day_start_equity),
        ("MAX", _d(cfg.get("max_drawdown_pct")), state.remaining_max_capacity, state.max_loss_floor, state.initial_account_size),
    ]
    for label, pct, remaining, floor, reference in pairs:
        if pct <= 0 or remaining is None or floor is None or reference is None:
            continue
        allowance = max(ZERO, _d(reference) - _d(floor))
        if allowance <= 0:
            continue
        used_pct = ONE - max(ZERO, min(ONE, _d(remaining) / allowance))
        for threshold in (Decimal("0.50"), Decimal("0.75"), Decimal("0.90")):
            key = f"{label}_{int(threshold * 100)}"
            if used_pct >= threshold and not warnings.get(key):
                warnings[key] = True
                await add_funded_event(db, deployment, f"FUNDED_{label}_DD_WARNING", f"Funded {label.lower()} drawdown warning", severity="WARNING", metadata={"used_pct": str(used_pct), "threshold": str(threshold), "remaining_capacity": _json_number(remaining)})
    state.warning_state_json = warnings


async def evaluate_funded_guard(
    db: AsyncSession,
    deployment: StrategyDeployment,
    *,
    signal_id: UUID | None = None,
    purpose: str = "ENTRY",
    max_age_seconds: int = DEFAULT_BROKER_STATE_MAX_AGE_SECONDS,
    persist_decision: bool = True,
    auto_pause_on_breach: bool = True,
) -> FundedLiveGuardDecision:
    if str(getattr(deployment, "account_policy_type", "STANDARD") or "STANDARD").upper() != POLICY_FUNDED:
        return FundedLiveGuardDecision(True, None, "STANDARD")
    if not deployment.broker_account_id:
        return FundedLiveGuardDecision(False, "Funded deployment has no broker account", "BLOCKED")
    broker_row = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
    if broker_row is None:
        return FundedLiveGuardDecision(False, "Funded broker account not found", "BLOCKED")
    broker = broker_funded_state(broker_row, max_age_seconds=max_age_seconds)
    profile = _snapshot_profile(deployment)
    profile_currency = str(profile.get("account_currency") or "USD").upper()

    fail_reason = None
    fail_status = "BLOCKED"
    if broker_row.status != "CONNECTED":
        fail_reason = "Funded broker is not CONNECTED"
    elif not broker.get("fresh"):
        fail_reason = "Funded broker balance/equity is stale; fresh broker sync is required"
    elif broker.get("balance") is None or _d(broker.get("balance")) <= 0:
        fail_reason = "Valid positive broker balance is required for funded trading"
    elif broker.get("equity") is None or _d(broker.get("equity")) <= 0:
        fail_reason = "Valid positive broker equity is required for funded trading"
    elif not broker.get("currency"):
        fail_reason = "Broker account currency is unavailable for funded compatibility validation"
    elif str(broker.get("currency")).upper() != profile_currency:
        fail_reason = f"Broker currency {broker.get('currency')} does not match funded profile currency {profile_currency}"
    if fail_reason:
        decision = FundedLiveGuardDecision(False, fail_reason, fail_status, balance=broker.get("balance"), equity=broker.get("equity"), free_margin=broker.get("free_margin"))
        existing_state = await _state_for_update(db, deployment.id)
        if existing_state is not None:
            existing_state.guard_status = "BLOCKED"
            existing_state.guard_reason = fail_reason
            existing_state.last_evaluated_at = datetime.now(timezone.utc)
        if auto_pause_on_breach and purpose.upper() in {"SYNC", "ENTRY", "START"}:
            deployment.auto_trade_enabled = False
            if deployment.status == "RUNNING":
                deployment.status = "PAUSED"
        if persist_decision:
            db.add(FundedLiveRiskDecision(deployment_id=deployment.id, signal_id=signal_id, balance=broker.get("balance"), equity=broker.get("equity"), allowed=False, reason=fail_reason, metadata_json={"purpose": purpose, "broker_state_age_seconds": _json_number(broker.get("age_seconds"))}))
            await add_funded_event(db, deployment, "FUNDED_BROKER_STATE_STALE", "Funded broker state is not safe for entry", message=fail_reason, severity="WARNING")
        return decision

    now = datetime.now(timezone.utc)
    balance = _d(broker["balance"])
    equity = _d(broker["equity"])
    state = await _ensure_state(db, deployment, broker, now)
    cfg = _funded_rule_config(deployment)
    if cfg.get("daily_drawdown_pct") is None or cfg.get("daily_drawdown_mode") is None:
        reason = "Funded profile does not define a daily drawdown rule for the active stage"
        return FundedLiveGuardDecision(False, reason, "BLOCKED", balance=balance, equity=equity)
    if cfg.get("max_drawdown_pct") is None or cfg.get("max_drawdown_mode") is None:
        reason = "Funded profile does not define a maximum drawdown rule for the active stage"
        return FundedLiveGuardDecision(False, reason, "BLOCKED", balance=balance, equity=equity)

    state.last_balance = balance
    state.last_equity = equity
    state.last_free_margin = broker.get("free_margin")
    state.high_water_balance = max(_d(state.high_water_balance, str(balance)), balance)
    state.high_water_equity = max(_d(state.high_water_equity, str(equity)), equity)
    state.last_evaluated_at = now
    state.daily_floor = calculate_daily_floor(
        cfg.get("daily_drawdown_mode"), initial_balance=state.initial_account_size,
        start_balance=state.day_start_balance, start_equity=state.day_start_equity,
        drawdown_pct=cfg.get("daily_drawdown_pct"),
    )
    state.max_loss_floor = calculate_max_loss_floor(
        cfg.get("max_drawdown_mode"), initial_balance=state.initial_account_size,
        high_water_balance=state.high_water_balance, high_water_equity=state.high_water_equity,
        drawdown_pct=cfg.get("max_drawdown_pct"),
    )
    state.remaining_daily_capacity = remaining_loss_capacity(equity, state.daily_floor)
    state.remaining_max_capacity = remaining_loss_capacity(equity, state.max_loss_floor)
    await _update_daily_snapshot(db, deployment, state, balance, equity)

    breach = None
    if equity <= _d(state.daily_floor):
        breach = "DAILY_DD"
    elif equity <= _d(state.max_loss_floor):
        breach = "MAX_DD"
    if breach:
        first_breach = state.failed_at is None or str(state.guard_status or "").upper() != "FAILED"
        state.guard_status = "FAILED"
        state.guard_reason = f"Funded {breach} floor breached by broker equity"
        state.failed_at = state.failed_at or now
        if auto_pause_on_breach:
            deployment.auto_trade_enabled = False
            if deployment.status == "RUNNING":
                deployment.status = "PAUSED"
        if first_breach:
            await add_funded_event(db, deployment, f"FUNDED_{breach}_BREACHED", "Funded account drawdown rule breached", message=state.guard_reason, severity="ERROR", metadata={"equity": str(equity), "daily_floor": _json_number(state.daily_floor), "max_floor": _json_number(state.max_loss_floor)})
        decision = FundedLiveGuardDecision(False, state.guard_reason, "FAILED", balance, equity, broker.get("free_margin"), state.daily_floor, state.max_loss_floor, state.remaining_daily_capacity, state.remaining_max_capacity, rule_date=state.rule_date, rule_timezone=state.rule_timezone, phase_number=state.phase_number)
    else:
        risk_mode = str(deployment.funded_risk_mode or "DYNAMIC").upper()
        tier_name = None
        tier_order = None
        account_return = ZERO if _d(state.initial_account_size) <= 0 else (balance - _d(state.initial_account_size)) / _d(state.initial_account_size)
        if risk_mode == RISK_FIXED:
            requested_pct = _d(deployment.funded_fixed_risk_pct)
            if requested_pct <= 0:
                raise ValueError("Funded FIXED risk requires funded_fixed_risk_pct > 0")
        else:
            tiers = validate_risk_tiers(_snapshot_tiers(deployment))
            rd = resolve_dynamic_risk(state.initial_account_size, balance, tiers)
            requested_pct = rd.requested_risk_percentage
            account_return = rd.account_return_percentage
            tier_name = rd.selected_tier_name
            match = next((t for t in tiers if str(t.get("name")) == str(tier_name)), None)
            tier_order = int((match or {}).get("sort_order") or 0) or None
        er = apply_effective_risk_guard(
            current_balance=balance,
            requested_risk_percentage=requested_pct,
            remaining_daily_capacity=state.remaining_daily_capacity,
            remaining_max_capacity=state.remaining_max_capacity,
            configured_max_risk=deployment.funded_configured_max_risk_pct,
            safety_buffer_percentage=_d(deployment.funded_safety_buffer_pct),
        )
        state.account_return_pct = account_return
        state.selected_risk_tier_name = tier_name
        state.selected_risk_tier_sort_order = tier_order
        state.requested_risk_pct = er.requested_risk_percentage
        state.requested_risk_amount = er.requested_risk_amount
        state.effective_risk_pct = er.effective_risk_percentage
        state.effective_risk_amount = er.effective_risk_amount
        state.limiting_rule = er.limiting_rule
        # BLOCKED can be transient (for example stale broker state). Once a fresh
        # authoritative broker state is valid again, allow the guard to recover.
        # FAILED/PASS_READY/provider-transition states are intentionally terminal
        # until explicit lifecycle action.
        if str(state.guard_status or "").upper() not in {"FAILED", "PASS_READY", "AWAITING_PROVIDER_TRANSITION"}:
            state.guard_status = "RUNNING" if deployment.status == "RUNNING" else "READY"
            state.guard_reason = None
        if er.effective_risk_amount <= 0:
            state.guard_status = "BLOCKED"
            state.guard_reason = "No funded loss capacity remains for a new entry"
        elif er.limiting_rule and purpose.upper() in {"ENTRY", "START"}:
            await add_funded_event(db, deployment, "FUNDED_RISK_REDUCED", "Funded guard reduced requested trade risk", severity="WARNING", metadata={"requested_risk_amount": str(er.requested_risk_amount), "effective_risk_amount": str(er.effective_risk_amount), "limiting_rule": er.limiting_rule})
        await _warning_events(db, deployment, state)
        await _phase_and_payout_status(db, deployment, state, now)
        allowed = state.guard_status not in BLOCKING_GUARD_STATES and er.effective_risk_amount > 0
        decision = FundedLiveGuardDecision(
            allowed, state.guard_reason if not allowed else None, state.guard_status,
            balance, equity, broker.get("free_margin"), state.daily_floor, state.max_loss_floor,
            state.remaining_daily_capacity, state.remaining_max_capacity, account_return, tier_name,
            er.requested_risk_percentage, er.requested_risk_amount, er.effective_risk_percentage,
            er.effective_risk_amount, er.limiting_rule, state.rule_date, state.rule_timezone, state.phase_number,
        )

    if persist_decision:
        db.add(FundedLiveRiskDecision(
            deployment_id=deployment.id,
            signal_id=signal_id,
            balance=decision.balance,
            equity=decision.equity,
            daily_floor=decision.daily_floor,
            max_floor=decision.max_floor,
            remaining_daily_capacity=decision.remaining_daily_capacity,
            remaining_max_capacity=decision.remaining_max_capacity,
            risk_mode=deployment.funded_risk_mode,
            risk_tier=decision.selected_risk_tier_name,
            requested_risk_pct=decision.requested_risk_pct,
            requested_risk_amount=decision.requested_risk_amount,
            effective_risk_pct=decision.effective_risk_pct,
            effective_risk_amount=decision.effective_risk_amount,
            limiting_rule=decision.limiting_rule,
            allowed=decision.allowed_new_entry,
            reason=decision.reason,
            metadata_json={"purpose": purpose, "rule_date": str(decision.rule_date), "rule_timezone": decision.rule_timezone},
        ))
        if not decision.allowed_new_entry and decision.guard_status not in {"FAILED", "PASS_READY"}:
            await add_funded_event(db, deployment, "FUNDED_ENTRY_BLOCKED", "Funded guard blocked a new entry", message=decision.reason, severity="WARNING", metadata={"purpose": purpose})
    return decision


async def funded_status_payload(db: AsyncSession, deployment: StrategyDeployment) -> dict[str, Any] | None:
    if str(getattr(deployment, "account_policy_type", "STANDARD") or "STANDARD").upper() != POLICY_FUNDED:
        return None
    state = await _state_for_update(db, deployment.id)
    profile = _snapshot_profile(deployment)
    phase = _phase_config(deployment)
    broker = None
    if deployment.broker_account_id:
        broker_row = (await db.execute(select(BrokerAccount).where(BrokerAccount.id == deployment.broker_account_id))).scalar_one_or_none()
        if broker_row:
            broker = broker_funded_state(broker_row)
    return {
        "account_policy_type": "FUNDED",
        "profile": {
            "id": str(deployment.funded_profile_id) if deployment.funded_profile_id else None,
            "name": profile.get("name"),
            "provider_name": profile.get("provider_name"),
            "challenge_type": profile.get("challenge_type"),
            "account_size": profile.get("account_size"),
            "account_currency": profile.get("account_currency"),
        },
        "phase": phase,
        "phase_number": deployment.funded_phase_number,
        "risk_mode": deployment.funded_risk_mode,
        "risk_plan": deployment.funded_risk_plan_snapshot,
        "fixed_risk_pct": _json_number(deployment.funded_fixed_risk_pct),
        "safety_buffer_pct": _json_number(deployment.funded_safety_buffer_pct),
        "configured_max_risk_pct": _json_number(deployment.funded_configured_max_risk_pct),
        "attach_mode": deployment.funded_attach_mode,
        "broker": None if broker is None else {
            "balance": _json_number(broker.get("balance")), "equity": _json_number(broker.get("equity")), "free_margin": _json_number(broker.get("free_margin")),
            "currency": broker.get("currency"), "fresh": broker.get("fresh"), "age_seconds": _json_number(broker.get("age_seconds")),
            "synced_at": broker.get("synced_at").isoformat() if broker.get("synced_at") else None,
        },
        "guard": None if state is None else {
            "status": state.guard_status, "reason": state.guard_reason,
            "rule_date": state.rule_date.isoformat() if state.rule_date else None,
            "rule_timezone": state.rule_timezone, "daily_reset_time": state.daily_reset_time,
            "balance": _json_number(state.last_balance), "equity": _json_number(state.last_equity),
            "daily_floor": _json_number(state.daily_floor), "max_floor": _json_number(state.max_loss_floor),
            "remaining_daily_capacity": _json_number(state.remaining_daily_capacity), "remaining_max_capacity": _json_number(state.remaining_max_capacity),
            "account_return_pct": _json_number(state.account_return_pct), "risk_tier": state.selected_risk_tier_name,
            "requested_risk_pct": _json_number(state.requested_risk_pct), "requested_risk_amount": _json_number(state.requested_risk_amount),
            "effective_risk_pct": _json_number(state.effective_risk_pct), "effective_risk_amount": _json_number(state.effective_risk_amount), "limiting_rule": state.limiting_rule,
            "trading_days": state.trading_days, "qualifying_days": state.qualifying_days,
            "target_balance": _json_number(state.target_balance), "target_progress_pct": _json_number(state.target_progress_pct), "target_reached_at": state.target_reached_at.isoformat() if state.target_reached_at else None,
            "payout_eligible_at": state.payout_eligible_at.isoformat() if state.payout_eligible_at else None, "payout_ready_at": state.payout_ready_at.isoformat() if state.payout_ready_at else None,
            "failed_at": state.failed_at.isoformat() if state.failed_at else None, "last_evaluated_at": state.last_evaluated_at.isoformat() if state.last_evaluated_at else None,
        },
    }


async def funded_compatibility_preview(db: AsyncSession, deployment: StrategyDeployment) -> dict[str, Any]:
    payload = await funded_status_payload(db, deployment)
    if payload is None:
        return {"ready": True, "reason": None}
    try:
        decision = await evaluate_funded_guard(db, deployment, purpose="READINESS", persist_decision=False, auto_pause_on_breach=False)
        return {"ready": bool(decision.allowed_new_entry), "reason": decision.reason, "decision": decision.to_dict(), **payload}
    except Exception as exc:
        return {"ready": False, "reason": str(exc), **payload}


async def current_funded_trades_count(db: AsyncSession, deployment: StrategyDeployment) -> int:
    """Return the deployment trade count for the current funded rule day.

    The funded rule day may differ from UTC midnight, so max-trades/day for a
    FUNDED deployment must use its funded daily snapshot rather than a UTC query.
    """
    if str(getattr(deployment, "account_policy_type", "STANDARD") or "STANDARD").upper() != POLICY_FUNDED:
        return 0
    state = await _state_for_update(db, deployment.id)
    if state is None or state.rule_date is None:
        return 0
    snap = await _get_daily_snapshot(db, deployment.id, state.rule_date)
    return int(getattr(snap, "trades_count", 0) or 0) if snap is not None else 0


async def record_funded_trade_count(db: AsyncSession, deployment: StrategyDeployment, *, pnl: Decimal | None = None) -> None:
    """Update the current funded daily audit row after a broker-confirmed trade/position close.

    This is intentionally conservative: account balance/equity remains authoritative;
    the count/PnL fields exist for qualifying-day and audit reporting only.
    """
    if str(getattr(deployment, "account_policy_type", "STANDARD") or "STANDARD").upper() != POLICY_FUNDED:
        return
    state = await _state_for_update(db, deployment.id)
    if state is None or state.rule_date is None:
        return
    snap = await _get_daily_snapshot(db, deployment.id, state.rule_date)
    if snap is None:
        return
    snap.trades_count = int(snap.trades_count or 0) + 1
    if pnl is not None:
        if _d(pnl) > 0:
            snap.winning_trades = int(snap.winning_trades or 0) + 1
        elif _d(pnl) < 0:
            snap.losing_trades = int(snap.losing_trades or 0) + 1
