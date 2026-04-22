from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import String, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...billing.cost_rules import CostRules
from ...db.compat import as_uuid_or_str, table_has_column
from ...db.models import (
    CreditTransaction,
    CreditTransactionType,
    User,
    UserCredit,
    UserSubscription,
)
from ..pricing.backtest_pricing_service import BacktestPricingService
from ..subscriptions.lifecycle import SubscriptionLifecycleService, SubscriptionLifecycleState


class CreditManagementService:
    """Centralized credit ledger + wallet/subscription deduction helpers."""

    SOURCE_BACKTEST_WALLET_DEBIT = "backtest_wallet_debit"
    SOURCE_BACKTEST_INCLUDED_DEBIT = "backtest_included_debit"
    SOURCE_BACKTEST_WALLET_REFUND = "backtest_wallet_refund"
    SOURCE_BACKTEST_INCLUDED_REFUND = "backtest_included_refund"

    _supports_credit_tx_source: bool | None = None
    _supports_credit_tx_actor: bool | None = None

    @staticmethod
    def _to_decimal(value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value or 0))

    @staticmethod
    def _to_int(value: Decimal | int | float | str) -> int:
        return int(CreditManagementService._to_decimal(value))

    @staticmethod
    async def _ensure_credit_transaction_audit_columns(db: AsyncSession) -> None:
        if CreditManagementService._supports_credit_tx_source is None:
            CreditManagementService._supports_credit_tx_source = await table_has_column(
                db,
                "credit_transactions",
                "source",
            )
        if CreditManagementService._supports_credit_tx_actor is None:
            CreditManagementService._supports_credit_tx_actor = await table_has_column(
                db,
                "credit_transactions",
                "actor_user_id",
            )

    @staticmethod
    async def _get_backtest_job_transaction_summary(
        db: AsyncSession,
        user_id: str,
        job_id: str | None,
    ) -> dict[str, Any]:
        if not job_id:
            return {
                "debit_total": 0,
                "refund_total": 0,
                "included_debited": 0,
                "wallet_debited": 0,
                "included_refunded": 0,
                "wallet_refunded": 0,
                "wallet_debit_txn": None,
                "included_debit_txn": None,
                "wallet_refund_txn": None,
                "included_refund_txn": None,
                "debit_transaction_ids": [],
                "refund_transaction_ids": [],
            }

        await CreditManagementService._ensure_credit_transaction_audit_columns(db)
        has_source = bool(CreditManagementService._supports_credit_tx_source)

        stmt = (
            select(CreditTransaction)
            .where(
                cast(CreditTransaction.user_id, String) == str(user_id),
                CreditTransaction.job_id == str(job_id),
            )
            .order_by(CreditTransaction.created_at.asc())
        )
        rows = (await db.execute(stmt)).scalars().all()

        summary: dict[str, Any] = {
            "debit_total": 0,
            "refund_total": 0,
            "included_debited": 0,
            "wallet_debited": 0,
            "included_refunded": 0,
            "wallet_refunded": 0,
            "wallet_debit_txn": None,
            "included_debit_txn": None,
            "wallet_refund_txn": None,
            "included_refund_txn": None,
            "debit_transaction_ids": [],
            "refund_transaction_ids": [],
        }

        for txn in rows:
            tx_type = str(getattr(txn, "transaction_type", "")).upper()
            source = str(getattr(txn, "source", "") or "") if has_source else ""
            amount = int(CreditManagementService._to_decimal(getattr(txn, "amount", 0)))

            if tx_type == CreditTransactionType.DEBIT.name:
                summary["debit_total"] += amount
                summary["debit_transaction_ids"].append(str(txn.id))
                if source == CreditManagementService.SOURCE_BACKTEST_INCLUDED_DEBIT:
                    summary["included_debited"] += amount
                    summary["included_debit_txn"] = txn
                else:
                    summary["wallet_debited"] += amount
                    summary["wallet_debit_txn"] = txn
                continue

            if tx_type == CreditTransactionType.REFUND.name:
                summary["refund_total"] += amount
                summary["refund_transaction_ids"].append(str(txn.id))
                if source == CreditManagementService.SOURCE_BACKTEST_INCLUDED_REFUND:
                    summary["included_refunded"] += amount
                    summary["included_refund_txn"] = txn
                else:
                    summary["wallet_refunded"] += amount
                    summary["wallet_refund_txn"] = txn

        return summary

    @staticmethod
    async def _ensure_credit_row(db: AsyncSession, user_id: str, *, for_update: bool = False) -> UserCredit:
        stmt = select(UserCredit).where(cast(UserCredit.user_id, String) == str(user_id)).limit(1)
        if for_update:
            stmt = stmt.with_for_update()

        row = (await db.execute(stmt)).scalar_one_or_none()
        if row:
            return row

        row = UserCredit(user_id=str(user_id), balance=0)
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def _lock_user(db: AsyncSession, user_id: str) -> None:
        try:
            stmt = select(User.id).where(cast(User.id, String) == str(user_id)).limit(1)
            bind = db.get_bind()
            if bind is not None and bind.dialect.name != "sqlite":
                stmt = stmt.with_for_update()
            await db.execute(stmt)
        except Exception:
            # Best effort only.
            return

    @staticmethod
    async def get_user_balance(db: AsyncSession, user_id: str) -> Decimal:
        row = (
            await db.execute(
                select(UserCredit.balance).where(cast(UserCredit.user_id, String) == str(user_id)).limit(1)
            )
        ).scalar_one_or_none()
        if row is not None:
            return CreditManagementService._to_decimal(row)

        latest = (
            await db.execute(
                select(CreditTransaction.balance_after)
                .where(cast(CreditTransaction.user_id, String) == str(user_id))
                .order_by(CreditTransaction.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if latest is not None:
            return CreditManagementService._to_decimal(latest)
        return Decimal("0")

    @staticmethod
    async def create_transaction(
        db: AsyncSession,
        user_id: str,
        transaction_type: CreditTransactionType,
        amount: Decimal | int | float | str,
        description: str,
        backtest_id: Optional[str] = None,
        job_id: Optional[str] = None,
        source: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        auto_commit: bool = True,
    ) -> CreditTransaction:
        del metadata  # schema-safe: metadata json column may not exist

        await CreditManagementService._ensure_credit_transaction_audit_columns(db)

        await CreditManagementService._lock_user(db, user_id)
        row = await CreditManagementService._ensure_credit_row(db, user_id, for_update=True)

        amount_dec = CreditManagementService._to_decimal(amount)
        current = CreditManagementService._to_decimal(row.balance)

        if transaction_type == CreditTransactionType.DEBIT:
            new_balance = current - amount_dec
            if new_balance < 0:
                raise ValueError(f"Insufficient credits. Current balance: {current}, Required: {amount_dec}")
        else:
            new_balance = current + amount_dec

        txn = CreditTransaction(
            id=str(uuid4()),
            user_id=as_uuid_or_str(user_id),
            transaction_type=transaction_type,
            amount=amount_dec,
            balance_after=new_balance,
            description=description,
            backtest_id=backtest_id,
            job_id=job_id,
            source=source if CreditManagementService._supports_credit_tx_source else None,
            actor_user_id=actor_user_id if CreditManagementService._supports_credit_tx_actor else None,
        )
        db.add(txn)

        # Keep legacy wallet row in sync.
        row.balance = CreditManagementService._to_int(new_balance)

        await db.flush()
        if auto_commit:
            await db.commit()
            await db.refresh(txn)
        return txn

    @staticmethod
    async def debit_credits(
        db: AsyncSession,
        user_id: str,
        amount: Decimal | int | float | str,
        description: str,
        backtest_id: Optional[str] = None,
        job_id: Optional[str] = None,
        source: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        auto_commit: bool = True,
    ) -> CreditTransaction:
        return await CreditManagementService.create_transaction(
            db=db,
            user_id=user_id,
            transaction_type=CreditTransactionType.DEBIT,
            amount=amount,
            description=description,
            backtest_id=backtest_id,
            job_id=job_id,
            source=source,
            actor_user_id=actor_user_id,
            metadata=metadata,
            auto_commit=auto_commit,
        )

    @staticmethod
    async def refund_credits(
        db: AsyncSession,
        user_id: str,
        amount: Decimal | int | float | str,
        description: str,
        backtest_id: Optional[str] = None,
        job_id: Optional[str] = None,
        source: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        auto_commit: bool = True,
    ) -> CreditTransaction:
        return await CreditManagementService.create_transaction(
            db=db,
            user_id=user_id,
            transaction_type=CreditTransactionType.REFUND,
            amount=amount,
            description=description,
            backtest_id=backtest_id,
            job_id=job_id,
            source=source,
            actor_user_id=actor_user_id,
            metadata=metadata,
            auto_commit=auto_commit,
        )

    @staticmethod
    async def credit_credits(
        db: AsyncSession,
        user_id: str,
        amount: Decimal | int | float | str,
        description: str,
        source: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        auto_commit: bool = True,
    ) -> CreditTransaction:
        return await CreditManagementService.create_transaction(
            db=db,
            user_id=user_id,
            transaction_type=CreditTransactionType.CREDIT,
            amount=amount,
            description=description,
            source=source,
            actor_user_id=actor_user_id,
            metadata=metadata,
            auto_commit=auto_commit,
        )

    @staticmethod
    async def refund_transaction(db: AsyncSession, transaction_id: str) -> CreditTransaction:
        txn = (
            await db.execute(select(CreditTransaction).where(CreditTransaction.id == str(transaction_id)).limit(1))
        ).scalar_one_or_none()
        if not txn:
            raise ValueError(f"Transaction {transaction_id} not found")
        if txn.transaction_type == CreditTransactionType.REFUND:
            raise ValueError("Cannot refund a REFUND transaction")

        return await CreditManagementService.refund_credits(
            db=db,
            user_id=str(txn.user_id),
            amount=txn.amount,
            description=f"Refund for transaction {txn.id}: {txn.description or ''}".strip(),
            backtest_id=getattr(txn, "backtest_id", None),
            job_id=getattr(txn, "job_id", None),
            auto_commit=True,
        )

    @staticmethod
    async def _create_non_wallet_ledger_entry(
        db: AsyncSession,
        *,
        user_id: str,
        transaction_type: CreditTransactionType,
        amount: Decimal | int | float | str,
        description: str,
        backtest_id: Optional[str] = None,
        job_id: Optional[str] = None,
        source: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        auto_commit: bool = False,
    ) -> CreditTransaction | None:
        amount_dec = CreditManagementService._to_decimal(amount)
        if amount_dec <= 0:
            return None

        await CreditManagementService._ensure_credit_transaction_audit_columns(db)
        await CreditManagementService._lock_user(db, user_id)
        row = await CreditManagementService._ensure_credit_row(db, user_id, for_update=True)
        wallet_balance = CreditManagementService._to_decimal(row.balance)

        txn = CreditTransaction(
            id=str(uuid4()),
            user_id=as_uuid_or_str(user_id),
            transaction_type=transaction_type,
            amount=amount_dec,
            balance_after=wallet_balance,
            description=description,
            backtest_id=backtest_id,
            job_id=job_id,
            source=source if CreditManagementService._supports_credit_tx_source else None,
            actor_user_id=actor_user_id if CreditManagementService._supports_credit_tx_actor else None,
        )
        db.add(txn)
        await db.flush()

        if auto_commit:
            await db.commit()
            await db.refresh(txn)
        return txn

    @staticmethod
    async def get_transaction_history(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CreditTransaction]:
        rows = (
            await db.execute(
                select(CreditTransaction)
                .where(cast(CreditTransaction.user_id, String) == str(user_id))
                .order_by(CreditTransaction.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        return list(rows)

    @staticmethod
    async def get_user_credit_summary(db: AsyncSession, user_id: str) -> dict[str, Any]:
        current_balance = await CreditManagementService.get_user_balance(db, user_id)

        counts = (
            await db.execute(
                select(CreditTransaction.transaction_type, func.count(CreditTransaction.id))
                .where(cast(CreditTransaction.user_id, String) == str(user_id))
                .group_by(CreditTransaction.transaction_type)
            )
        ).all()

        tx_counts: dict[str, int] = {}
        total = 0
        for tx_type, count in counts:
            key = tx_type.value if hasattr(tx_type, "value") else str(tx_type)
            tx_counts[key] = int(count or 0)
            total += int(count or 0)

        lifecycle = await SubscriptionLifecycleService.ensure_user_subscription_cycle(
            db,
            str(user_id),
            for_update=False,
            auto_commit=False,
        )

        return {
            "user_id": str(user_id),
            "current_balance": float(current_balance),
            "included_remaining": int(lifecycle.get("included_remaining") or 0),
            "subscription_state": lifecycle.get("lifecycle_state") or SubscriptionLifecycleState.NONE.value,
            "total_transactions": int(total),
            "transaction_counts": tx_counts,
            "last_updated": datetime.utcnow().isoformat(),
        }

    @staticmethod
    async def get_trial_backtest_count(db: AsyncSession, user_id: str) -> int:
        result = await db.execute(
            select(func.count(CreditTransaction.id)).where(
                cast(CreditTransaction.user_id, String) == str(user_id),
                cast(CreditTransaction.transaction_type, String) == CreditTransactionType.DEBIT.name,
                CreditTransaction.description.ilike("%backtest%"),
                CreditTransaction.created_at >= text("NOW() - INTERVAL '7 days'"),
            )
        )
        return int(result.scalar() or 0)

    @staticmethod
    async def get_trial_ai_screener_count(db: AsyncSession, user_id: str) -> int:
        result = await db.execute(
            select(func.count(CreditTransaction.id)).where(
                cast(CreditTransaction.user_id, String) == str(user_id),
                cast(CreditTransaction.transaction_type, String) == CreditTransactionType.DEBIT.name,
                CreditTransaction.description.ilike("%ai screener%"),
                CreditTransaction.created_at >= text("NOW() - INTERVAL '7 days'"),
            )
        )
        return int(result.scalar() or 0)

    @staticmethod
    async def update_included_credits(
        db: AsyncSession,
        user_id: str,
        amount_change: Decimal | int | float | str,
        *,
        auto_commit: bool = True,
    ) -> None:
        cycle = await SubscriptionLifecycleService.ensure_user_subscription_cycle(
            db,
            str(user_id),
            for_update=True,
            auto_commit=False,
        )
        sub: UserSubscription | None = cycle.get("subscription")
        if not sub:
            raise ValueError("No subscription found for user")

        delta = CreditManagementService._to_int(amount_change)
        current = int(getattr(sub, "included_credits_remaining", 0) or 0)
        new_value = current + delta
        if new_value < 0:
            raise ValueError("Insufficient subscription included credits")
        sub.included_credits_remaining = new_value

        if auto_commit:
            await db.commit()

    @staticmethod
    async def get_credit_capacity(
        db: AsyncSession,
        user_id: str,
        *,
        for_update: bool = False,
    ) -> dict[str, Any]:
        lifecycle = await SubscriptionLifecycleService.ensure_user_subscription_cycle(
            db,
            str(user_id),
            for_update=for_update,
            auto_commit=False,
        )

        state = str(lifecycle.get("lifecycle_state") or SubscriptionLifecycleState.NONE.value)
        included = int(lifecycle.get("included_remaining") or 0)
        if state not in {SubscriptionLifecycleState.ACTIVE.value, SubscriptionLifecycleState.TRIAL.value}:
            included = 0

        wallet = CreditManagementService._to_int(await CreditManagementService.get_user_balance(db, str(user_id)))
        return {
            "wallet_balance": wallet,
            "included_balance": included,
            "total_available": wallet + included,
            "subscription_state": state,
            "subscription_id": str(lifecycle["subscription"].id) if lifecycle.get("subscription") else None,
            "refill_applied": bool(lifecycle.get("refill_applied")),
            "next_refill_at": lifecycle.get("next_refill_at"),
        }

    @staticmethod
    async def consume_credits_for_backtest(
        db: AsyncSession,
        user_id: str,
        total_cost: Decimal | int | float | str,
        *,
        description: str,
        job_id: Optional[str] = None,
        auto_commit: bool = False,
    ) -> dict[str, Any]:
        needed = CreditManagementService._to_int(total_cost)
        if needed <= 0:
            return {
                "total_cost": 0,
                "included_debited": 0,
                "wallet_debited": 0,
                "effective_included_debited": 0,
                "effective_wallet_debited": 0,
                "idempotent": True,
                "included_transaction": None,
                "wallet_transaction": None,
                "wallet_balance_after": CreditManagementService._to_int(await CreditManagementService.get_user_balance(db, user_id)),
                "included_balance_after": 0,
                "subscription_state": SubscriptionLifecycleState.NONE.value,
            }

        existing_summary = await CreditManagementService._get_backtest_job_transaction_summary(
            db,
            user_id,
            job_id,
        )
        net_effective_debit = max(
            int(existing_summary["debit_total"]) - int(existing_summary["refund_total"]),
            0,
        )
        remaining_to_consume = max(needed - net_effective_debit, 0)

        if remaining_to_consume <= 0:
            remaining = await CreditManagementService.get_credit_capacity(db, user_id, for_update=False)
            effective_included = max(
                int(existing_summary["included_debited"]) - int(existing_summary["included_refunded"]),
                0,
            )
            effective_wallet = max(
                int(existing_summary["wallet_debited"]) - int(existing_summary["wallet_refunded"]),
                0,
            )
            return {
                "total_cost": needed,
                "included_debited": 0,
                "wallet_debited": 0,
                "effective_included_debited": effective_included,
                "effective_wallet_debited": effective_wallet,
                "idempotent": True,
                "included_transaction": existing_summary.get("included_debit_txn"),
                "wallet_transaction": existing_summary.get("wallet_debit_txn"),
                "wallet_balance_after": int(remaining["wallet_balance"]),
                "included_balance_after": int(remaining["included_balance"]),
                "subscription_state": remaining["subscription_state"],
                "subscription_id": remaining["subscription_id"],
            }

        capacity = await CreditManagementService.get_credit_capacity(db, user_id, for_update=True)
        if int(capacity["total_available"]) < remaining_to_consume:
            raise ValueError(
                f"Insufficient credits. Available: {capacity['total_available']}, Required: {remaining_to_consume}"
            )

        included_available = int(capacity["included_balance"])
        use_included = min(remaining_to_consume, included_available)
        use_wallet = remaining_to_consume - use_included

        included_txn: CreditTransaction | None = None

        if use_included > 0:
            await CreditManagementService.update_included_credits(
                db,
                user_id,
                -use_included,
                auto_commit=False,
            )
            included_txn = await CreditManagementService._create_non_wallet_ledger_entry(
                db,
                user_id=user_id,
                transaction_type=CreditTransactionType.DEBIT,
                amount=Decimal(use_included),
                description=description,
                job_id=job_id,
                source=CreditManagementService.SOURCE_BACKTEST_INCLUDED_DEBIT,
                auto_commit=False,
            )

        wallet_txn: CreditTransaction | None = None
        if use_wallet > 0:
            wallet_txn = await CreditManagementService.debit_credits(
                db=db,
                user_id=user_id,
                amount=Decimal(use_wallet),
                description=description,
                job_id=job_id,
                source=CreditManagementService.SOURCE_BACKTEST_WALLET_DEBIT,
                auto_commit=False,
            )

        if auto_commit:
            await db.commit()
            if included_txn is not None:
                await db.refresh(included_txn)
            if wallet_txn is not None:
                await db.refresh(wallet_txn)

        updated_summary = await CreditManagementService._get_backtest_job_transaction_summary(
            db,
            user_id,
            job_id,
        )
        effective_included = max(
            int(updated_summary["included_debited"]) - int(updated_summary["included_refunded"]),
            0,
        )
        effective_wallet = max(
            int(updated_summary["wallet_debited"]) - int(updated_summary["wallet_refunded"]),
            0,
        )

        remaining = await CreditManagementService.get_credit_capacity(db, user_id, for_update=False)
        return {
            "total_cost": needed,
            "included_debited": use_included,
            "wallet_debited": use_wallet,
            "effective_included_debited": effective_included,
            "effective_wallet_debited": effective_wallet,
            "idempotent": False,
            "included_transaction": included_txn,
            "wallet_transaction": wallet_txn,
            "wallet_balance_after": int(remaining["wallet_balance"]),
            "included_balance_after": int(remaining["included_balance"]),
            "subscription_state": remaining["subscription_state"],
            "subscription_id": remaining["subscription_id"],
        }

    @staticmethod
    async def restore_consumed_credits(
        db: AsyncSession,
        user_id: str,
        *,
        included_amount: int = 0,
        wallet_amount: int = 0,
        job_id: Optional[str] = None,
        description: str = "Refund for failed execution",
        auto_commit: bool = False,
    ) -> dict[str, Any]:
        summary = await CreditManagementService._get_backtest_job_transaction_summary(
            db,
            user_id,
            job_id,
        )

        pending_included = max(
            int(summary["included_debited"]) - int(summary["included_refunded"]),
            0,
        )
        pending_wallet = max(
            int(summary["wallet_debited"]) - int(summary["wallet_refunded"]),
            0,
        )

        target_included = int(included_amount or 0)
        target_wallet = int(wallet_amount or 0)
        if job_id:
            if target_included <= 0:
                target_included = pending_included
            if target_wallet <= 0:
                target_wallet = pending_wallet

            target_included = min(target_included, pending_included)
            target_wallet = min(target_wallet, pending_wallet)

        if target_included <= 0 and target_wallet <= 0:
            return {
                "included_refunded": 0,
                "wallet_refunded": 0,
                "idempotent": True,
                "included_transaction": summary.get("included_refund_txn"),
                "wallet_transaction": summary.get("wallet_refund_txn"),
            }

        included_txn: CreditTransaction | None = None
        wallet_txn: CreditTransaction | None = None

        backtest_id = None
        if summary.get("included_debit_txn") is not None:
            backtest_id = getattr(summary["included_debit_txn"], "backtest_id", None)
        if backtest_id is None and summary.get("wallet_debit_txn") is not None:
            backtest_id = getattr(summary["wallet_debit_txn"], "backtest_id", None)

        if target_included > 0:
            await CreditManagementService.update_included_credits(
                db,
                user_id,
                target_included,
                auto_commit=False,
            )
            included_txn = await CreditManagementService._create_non_wallet_ledger_entry(
                db,
                user_id=user_id,
                transaction_type=CreditTransactionType.REFUND,
                amount=Decimal(target_included),
                description=description,
                backtest_id=backtest_id,
                job_id=job_id,
                source=CreditManagementService.SOURCE_BACKTEST_INCLUDED_REFUND,
                auto_commit=False,
            )

        if target_wallet > 0:
            wallet_txn = await CreditManagementService.refund_credits(
                db=db,
                user_id=user_id,
                amount=Decimal(target_wallet),
                description=description,
                backtest_id=backtest_id,
                job_id=job_id,
                source=CreditManagementService.SOURCE_BACKTEST_WALLET_REFUND,
                auto_commit=False,
            )

        if auto_commit:
            await db.commit()
            if included_txn is not None:
                await db.refresh(included_txn)
            if wallet_txn is not None:
                await db.refresh(wallet_txn)

        return {
            "included_refunded": int(target_included),
            "wallet_refunded": int(target_wallet),
            "idempotent": False,
            "included_transaction": included_txn,
            "wallet_transaction": wallet_txn,
        }

    @staticmethod
    async def compute_backtest_cost(
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime,
        timeframe: str,
        *,
        instrument_id: int | None = None,
        strategy_parameters: dict[str, Any] | None = None,
        plan_code: str | None = None,
        use_actual_candle_count: bool = False,
    ) -> Decimal:
        quote = await BacktestPricingService.quote_backtest_cost(
            db,
            timeframe=timeframe,
            start_date=start_date.date(),
            end_date=end_date.date(),
            instrument_id=instrument_id,
            strategy_parameters=strategy_parameters,
            use_actual_candle_count=use_actual_candle_count,
            plan_code=plan_code,
        )
        return Decimal(str(quote.get("total_cost") or 0))

    @staticmethod
    async def compute_ai_screener_cost(mode: str, depth: str) -> Decimal:
        return Decimal(CostRules.calculate_ai_screener_cost(mode, depth))

    @staticmethod
    async def check_and_debit_backtest_credits(
        db: AsyncSession,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str,
        job_id: Optional[str] = None,
        instrument_id: int | None = None,
        strategy_parameters: dict[str, Any] | None = None,
        plan_code: str | None = None,
        use_actual_candle_count: bool = False,
    ) -> CreditTransaction:
        cost = await CreditManagementService.compute_backtest_cost(
            db,
            start_date,
            end_date,
            timeframe,
            instrument_id=instrument_id,
            strategy_parameters=strategy_parameters,
            plan_code=plan_code,
            use_actual_candle_count=use_actual_candle_count,
        )
        consumption = await CreditManagementService.consume_credits_for_backtest(
            db=db,
            user_id=user_id,
            total_cost=cost,
            description=f"Backtest run: {start_date.date()} to {end_date.date()} ({timeframe})",
            job_id=job_id,
            auto_commit=False,
        )
        included_txn = consumption.get("included_transaction")
        if included_txn is not None:
            return included_txn
        wallet_txn = consumption.get("wallet_transaction")
        if wallet_txn is not None:
            return wallet_txn

        # Subscription-only consumption: create no-op credit transaction object contract fallback.
        return CreditTransaction(
            id=str(uuid4()),
            user_id=as_uuid_or_str(user_id),
            transaction_type=CreditTransactionType.DEBIT,
            amount=Decimal("0"),
            balance_after=await CreditManagementService.get_user_balance(db, user_id),
            description="Backtest consumed subscription included credits",
            job_id=job_id,
        )

    @staticmethod
    async def check_and_debit_ai_screener_credits(
        db: AsyncSession,
        user_id: str,
        mode: str,
        depth: str,
        job_id: Optional[str] = None,
    ) -> CreditTransaction:
        cost = await CreditManagementService.compute_ai_screener_cost(mode, depth)
        return await CreditManagementService.debit_credits(
            db=db,
            user_id=user_id,
            amount=cost,
            description=f"AI screener run: {mode} mode, {depth} depth",
            job_id=job_id,
            auto_commit=False,
        )
