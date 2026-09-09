from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable


@dataclass(frozen=True)
class RiskDecision:
    account_return_percentage: Decimal
    selected_tier_id: str | None
    selected_tier_name: str | None
    requested_risk_percentage: Decimal
    reason: str


@dataclass(frozen=True)
class EffectiveRiskDecision:
    requested_risk_percentage: Decimal
    effective_risk_percentage: Decimal
    requested_risk_amount: Decimal
    effective_risk_amount: Decimal
    remaining_daily_capacity: Decimal | None
    remaining_max_capacity: Decimal | None
    limiting_rule: str | None


def _d(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    return Decimal(str(value))


def _get(tier: Any, name: str, default=None):
    return tier.get(name, default) if isinstance(tier, dict) else getattr(tier, name, default)


def resolve_dynamic_risk(initial_balance, current_balance, risk_tiers: Iterable[Any]) -> RiskDecision:
    initial = _d(initial_balance)
    current = _d(current_balance)
    if initial <= 0:
        raise ValueError("initial_balance must be greater than 0")
    account_return = (current - initial) / initial
    active = [tier for tier in risk_tiers if bool(_get(tier, "is_active", True))]
    active.sort(key=lambda x: int(_get(x, "sort_order", 0)))
    for tier in active:
        low = _get(tier, "min_account_return_pct")
        high = _get(tier, "max_account_return_pct")
        low_ok = low is None or account_return >= _d(low)
        high_ok = high is None or account_return < _d(high)
        if low_ok and high_ok:
            risk = _d(_get(tier, "risk_percent"))
            return RiskDecision(
                account_return_percentage=account_return,
                selected_tier_id=str(_get(tier, "id")) if _get(tier, "id") is not None else None,
                selected_tier_name=_get(tier, "name"),
                requested_risk_percentage=risk,
                reason=f"Account return {account_return:.6f} matched configured tier {_get(tier, 'name', '')}".strip(),
            )

    # Backward compatibility for profiles created before full-coverage validation.
    # Only outer-edge gaps are repaired deterministically: below the first configured
    # lower bound uses the first tier, above the last configured upper bound uses the
    # last tier. Internal gaps remain configuration errors and are never guessed.
    if active:
        first = active[0]
        first_low = _get(first, "min_account_return_pct")
        if first_low is not None and account_return < _d(first_low):
            risk = _d(_get(first, "risk_percent"))
            return RiskDecision(
                account_return_percentage=account_return,
                selected_tier_id=str(_get(first, "id")) if _get(first, "id") is not None else None,
                selected_tier_name=_get(first, "name"),
                requested_risk_percentage=risk,
                reason=(f"Account return {account_return:.6f} fell below legacy first-tier bound "
                        f"{_d(first_low):.6f}; using first tier {_get(first, 'name', '')} as open-ended fallback"),
            )
        last = active[-1]
        last_high = _get(last, "max_account_return_pct")
        if last_high is not None and account_return >= _d(last_high):
            risk = _d(_get(last, "risk_percent"))
            return RiskDecision(
                account_return_percentage=account_return,
                selected_tier_id=str(_get(last, "id")) if _get(last, "id") is not None else None,
                selected_tier_name=_get(last, "name"),
                requested_risk_percentage=risk,
                reason=(f"Account return {account_return:.6f} exceeded legacy last-tier bound "
                        f"{_d(last_high):.6f}; using last tier {_get(last, 'name', '')} as open-ended fallback"),
            )
    raise ValueError(f"No active funded risk tier covers account return {account_return}")


def apply_effective_risk_guard(
    *,
    current_balance,
    requested_risk_percentage,
    remaining_daily_capacity=None,
    remaining_max_capacity=None,
    configured_max_risk=None,
    safety_buffer_percentage=Decimal("0"),
) -> EffectiveRiskDecision:
    balance = _d(current_balance)
    requested_pct = _d(requested_risk_percentage)
    if balance <= 0:
        raise ValueError("current_balance must be greater than 0")
    if requested_pct <= 0:
        raise ValueError("requested_risk_percentage must be greater than 0")
    max_pct = _d(configured_max_risk, str(requested_pct))
    pct = min(requested_pct, max_pct)
    requested_amount = balance * requested_pct
    allowed_amount = balance * pct
    limiting_rule = "CONFIGURED_MAX_RISK" if pct < requested_pct else None
    buffer = _d(safety_buffer_percentage)
    if buffer < 0 or buffer >= 1:
        raise ValueError("safety_buffer_percentage must be >= 0 and < 1")
    for label, raw_capacity in (("DAILY_DD", remaining_daily_capacity), ("MAX_DD", remaining_max_capacity)):
        if raw_capacity is None:
            continue
        capacity = max(Decimal("0"), _d(raw_capacity)) * (Decimal("1") - buffer)
        if capacity < allowed_amount:
            allowed_amount = capacity
            limiting_rule = label
    effective_pct = max(Decimal("0"), allowed_amount / balance)
    return EffectiveRiskDecision(
        requested_risk_percentage=requested_pct,
        effective_risk_percentage=effective_pct,
        requested_risk_amount=requested_amount,
        effective_risk_amount=allowed_amount,
        remaining_daily_capacity=None if remaining_daily_capacity is None else _d(remaining_daily_capacity),
        remaining_max_capacity=None if remaining_max_capacity is None else _d(remaining_max_capacity),
        limiting_rule=limiting_rule,
    )
