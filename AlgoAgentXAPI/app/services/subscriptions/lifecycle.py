from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import Plan, UserSubscription


class SubscriptionLifecycleState(str, Enum):
    ACTIVE = "active"
    TRIAL = "trial"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"
    FAILED = "failed"
    NONE = "none"


@dataclass
class SubscriptionCycleInfo:
    subscription: UserSubscription | None
    plan: Plan | None
    lifecycle_state: SubscriptionLifecycleState
    refill_applied: bool
    included_credits_total: int
    included_credits_remaining: int
    next_credit_refill_at: datetime | None
    last_credit_refill_at: datetime | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "subscription": self.subscription,
            "plan": self.plan,
            "lifecycle_state": self.lifecycle_state.value,
            "refill_applied": self.refill_applied,
            "included_total": self.included_credits_total,
            "included_remaining": self.included_credits_remaining,
            "next_refill_at": self.next_credit_refill_at,
            "last_refill_at": self.last_credit_refill_at,
        }


class SubscriptionLifecycleService:
    """Lifecycle + refill orchestration for subscriptions (schema-compatible, additive)."""

    _ACTIVE_RAW = {"ACTIVE"}
    _TRIAL_RAW = {"TRIAL", "TRIALING"}
    _CANCELLED_RAW = {"CANCELLED", "CANCELED"}
    _EXPIRED_RAW = {"EXPIRED"}
    _PENDING_RAW = {"PENDING"}
    _FAILED_RAW = {"FAILED"}

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def _canonical_status(cls, state: SubscriptionLifecycleState) -> str:
        mapping = {
            SubscriptionLifecycleState.ACTIVE: "ACTIVE",
            SubscriptionLifecycleState.TRIAL: "TRIAL",
            SubscriptionLifecycleState.CANCELLED: "CANCELLED",
            SubscriptionLifecycleState.EXPIRED: "EXPIRED",
            SubscriptionLifecycleState.PENDING: "PENDING",
            SubscriptionLifecycleState.FAILED: "FAILED",
            SubscriptionLifecycleState.NONE: "NONE",
        }
        return mapping[state]

    @classmethod
    def _cycle_days(cls, billing_period: str | None) -> int:
        period = str(billing_period or "MONTHLY").upper()
        if period in {"YEARLY", "ANNUAL"}:
            return 365
        return 30

    @classmethod
    def _cycle_key(cls, subscription: UserSubscription, cycle_start: datetime, cycle_days: int) -> str:
        return f"{subscription.id}:{cycle_start.strftime('%Y%m%d')}:{cycle_days}"

    @classmethod
    async def get_latest_subscription(
        cls,
        db: AsyncSession,
        user_id: str,
        *,
        for_update: bool = False,
    ) -> UserSubscription | None:
        now = cls._now()

        # Prefer currently active/trial subscriptions so latest canceled rows
        # do not hide an older still-active entitlement.
        active_stmt = (
            select(UserSubscription)
            .where(
                cast(UserSubscription.user_id, String) == str(user_id),
                UserSubscription.status.in_(["ACTIVE", "TRIAL", "TRIALING"]),
                UserSubscription.end_at > now,
            )
            .order_by(UserSubscription.end_at.desc(), UserSubscription.created_at.desc())
            .limit(1)
        )
        if for_update:
            active_stmt = active_stmt.with_for_update()

        active = (await db.execute(active_stmt)).scalar_one_or_none()
        if active:
            return active

        fallback_stmt = (
            select(UserSubscription)
            .where(cast(UserSubscription.user_id, String) == str(user_id))
            .order_by(UserSubscription.created_at.desc())
            .limit(1)
        )
        if for_update:
            fallback_stmt = fallback_stmt.with_for_update()
        return (await db.execute(fallback_stmt)).scalar_one_or_none()

    @classmethod
    async def _load_plan(cls, db: AsyncSession, plan_id) -> Plan | None:
        if not plan_id:
            return None
        return await db.get(Plan, plan_id)

    @classmethod
    def derive_lifecycle_state(
        cls,
        subscription: UserSubscription | None,
        now: datetime | None = None,
    ) -> SubscriptionLifecycleState:
        if not subscription:
            return SubscriptionLifecycleState.NONE

        current = now or cls._now()
        raw = str(subscription.status or "").upper().strip()

        if raw in cls._FAILED_RAW:
            return SubscriptionLifecycleState.FAILED
        if raw in cls._PENDING_RAW:
            return SubscriptionLifecycleState.PENDING
        if raw in cls._CANCELLED_RAW:
            return SubscriptionLifecycleState.CANCELLED
        if raw in cls._TRIAL_RAW:
            trial_end = getattr(subscription, "trial_end_at", None)
            if trial_end and trial_end < current:
                # Trial ended; if still valid by end_at then treat as active, else expired.
                end_at = getattr(subscription, "end_at", None)
                if end_at and end_at > current:
                    return SubscriptionLifecycleState.ACTIVE
                return SubscriptionLifecycleState.EXPIRED
            return SubscriptionLifecycleState.TRIAL

        end_at = getattr(subscription, "end_at", None)
        if end_at and end_at < current:
            return SubscriptionLifecycleState.EXPIRED

        if raw in cls._ACTIVE_RAW:
            return SubscriptionLifecycleState.ACTIVE
        if raw in cls._EXPIRED_RAW:
            return SubscriptionLifecycleState.EXPIRED

        return SubscriptionLifecycleState.PENDING

    @classmethod
    async def ensure_user_subscription_cycle(
        cls,
        db: AsyncSession,
        user_id: str,
        *,
        for_update: bool = True,
        auto_commit: bool = False,
    ) -> dict[str, Any]:
        """
        Normalize lifecycle state and apply single refill for due cycle.
        Uses row lock to avoid duplicate cycle refill under concurrent requests.
        """
        now = cls._now()
        changed = False
        refill_applied = False

        subscription = await cls.get_latest_subscription(db, user_id, for_update=for_update)
        if not subscription:
            info = SubscriptionCycleInfo(
                subscription=None,
                plan=None,
                lifecycle_state=SubscriptionLifecycleState.NONE,
                refill_applied=False,
                included_credits_total=0,
                included_credits_remaining=0,
                next_credit_refill_at=None,
                last_credit_refill_at=None,
            )
            return info.as_dict()

        plan = await cls._load_plan(db, subscription.plan_id)
        lifecycle_state = cls.derive_lifecycle_state(subscription, now=now)

        canonical = cls._canonical_status(lifecycle_state)
        if str(subscription.status or "").upper() != canonical:
            subscription.status = canonical
            changed = True

        if getattr(subscription, "plan_code_snapshot", None) is None and plan is not None:
            subscription.plan_code_snapshot = str(plan.code)
            changed = True
        if getattr(subscription, "billing_period_snapshot", None) is None and plan is not None:
            subscription.billing_period_snapshot = str(plan.billing_period)
            changed = True
        if getattr(subscription, "plan_price_inr", None) is None and plan is not None:
            subscription.plan_price_inr = int(plan.price_inr or 0)
            changed = True

        included_total = int(
            getattr(subscription, "included_credits_total", None)
            if getattr(subscription, "included_credits_total", None) is not None
            else int(getattr(plan, "included_credits", 0) or 0)
        )
        if getattr(subscription, "included_credits_total", None) is None:
            subscription.included_credits_total = included_total
            changed = True

        included_remaining_raw = getattr(subscription, "included_credits_remaining", None)
        if included_remaining_raw is None:
            # For legacy rows initialize once; do not re-grant if already set.
            subscription.included_credits_remaining = included_total
            changed = True
        included_remaining = int(getattr(subscription, "included_credits_remaining", 0) or 0)

        period = str(getattr(subscription, "billing_period_snapshot", None) or getattr(plan, "billing_period", None) or "MONTHLY")
        cycle_days = cls._cycle_days(period)
        cycle_delta = timedelta(days=cycle_days)

        if lifecycle_state in {SubscriptionLifecycleState.ACTIVE, SubscriptionLifecycleState.TRIAL} and included_total > 0:
            anchor = getattr(subscription, "start_at", None) or now
            last_refill_at = getattr(subscription, "last_credit_refill_at", None)
            next_refill_at = getattr(subscription, "next_credit_refill_at", None)

            if last_refill_at is None:
                subscription.last_credit_refill_at = anchor
                last_refill_at = subscription.last_credit_refill_at
                changed = True

            if next_refill_at is None:
                subscription.next_credit_refill_at = (last_refill_at or now) + cycle_delta
                next_refill_at = subscription.next_credit_refill_at
                changed = True

            if next_refill_at and now >= next_refill_at:
                elapsed = max((now - anchor).total_seconds(), 0.0)
                cycle_seconds = max(cycle_delta.total_seconds(), 1.0)
                cycle_index = int(elapsed // cycle_seconds)
                cycle_start = anchor + (cycle_delta * cycle_index)
                cycle_key = cls._cycle_key(subscription, cycle_start, cycle_days)

                if getattr(subscription, "last_refill_cycle_key", None) != cycle_key:
                    subscription.included_credits_remaining = included_total
                    subscription.last_credit_refill_at = now
                    subscription.next_credit_refill_at = now + cycle_delta
                    if hasattr(subscription, "last_refill_cycle_key"):
                        subscription.last_refill_cycle_key = cycle_key
                    refill_applied = True
                    changed = True

        if changed and auto_commit:
            await db.commit()

        info = SubscriptionCycleInfo(
            subscription=subscription,
            plan=plan,
            lifecycle_state=lifecycle_state,
            refill_applied=refill_applied,
            included_credits_total=int(getattr(subscription, "included_credits_total", 0) or 0),
            included_credits_remaining=int(getattr(subscription, "included_credits_remaining", 0) or 0),
            next_credit_refill_at=getattr(subscription, "next_credit_refill_at", None),
            last_credit_refill_at=getattr(subscription, "last_credit_refill_at", None),
        )
        return info.as_dict()
