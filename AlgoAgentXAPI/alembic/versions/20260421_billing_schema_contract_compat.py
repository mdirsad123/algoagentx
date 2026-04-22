"""Billing schema contract compatibility stabilization.

Revision ID: 20260421_billing_schema_contract_compat
Revises: 20260408_merge_all_heads
Create Date: 2026-04-21
"""

from __future__ import annotations

import json
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260421_billing_schema_contract_compat"
down_revision = "20260408_merge_all_heads"
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    insp = sa.inspect(bind)
    return table_name in insp.get_table_names()


def _has_column(bind, table_name: str, column_name: str) -> bool:
    insp = sa.inspect(bind)
    try:
        return any(col.get("name") == column_name for col in insp.get_columns(table_name))
    except Exception:
        return False


def _has_index(bind, table_name: str, index_name: str) -> bool:
    insp = sa.inspect(bind)
    try:
        return any(idx.get("name") == index_name for idx in insp.get_indexes(table_name))
    except Exception:
        return False


def _has_unique_on_columns(bind, table_name: str, columns: list[str]) -> bool:
    insp = sa.inspect(bind)
    wanted = tuple(columns)
    for uc in insp.get_unique_constraints(table_name):
        cols = tuple(uc.get("column_names") or [])
        if cols == wanted:
            return True
    return False


def _drop_uniques_on_columns(bind, table_name: str, columns: list[str]) -> None:
    insp = sa.inspect(bind)
    wanted = tuple(columns)
    for uc in insp.get_unique_constraints(table_name):
        cols = tuple(uc.get("column_names") or [])
        name = uc.get("name")
        if cols == wanted and name:
            op.drop_constraint(name, table_name, type_="unique")


def _ensure_column(bind, table_name: str, column: sa.Column) -> None:
    if not _has_column(bind, table_name, str(column.name)):
        op.add_column(table_name, column)


def _create_plans_table(bind) -> None:
    if _has_table(bind, "plans"):
        return

    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("billing_period", sa.String(length=20), nullable=False),
        sa.Column("price_inr", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("included_credits", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("features", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("code", "billing_period", name="uq_plans_code_billing_period"),
    )


def _sync_plans_schema(bind) -> None:
    _create_plans_table(bind)

    _ensure_column(bind, "plans", sa.Column("billing_period", sa.String(length=20), nullable=True))
    _ensure_column(bind, "plans", sa.Column("price_inr", sa.Integer(), nullable=True))
    _ensure_column(bind, "plans", sa.Column("included_credits", sa.Integer(), nullable=True))
    _ensure_column(bind, "plans", sa.Column("features", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    _ensure_column(bind, "plans", sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")))
    _ensure_column(bind, "plans", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")))

    op.execute(
        sa.text(
            """
            UPDATE plans
            SET billing_period = CASE
                WHEN UPPER(COALESCE(code, '')) = 'FREE' THEN 'NONE'
                ELSE 'MONTHLY'
            END
            WHERE billing_period IS NULL OR TRIM(billing_period) = ''
            """
        )
    )

    _drop_uniques_on_columns(bind, "plans", ["code"])
    if not _has_unique_on_columns(bind, "plans", ["code", "billing_period"]):
        op.create_unique_constraint(
            "uq_plans_code_billing_period",
            "plans",
            ["code", "billing_period"],
        )


def _seed_plans(bind) -> None:
    plans = [
        {
            "code": "FREE",
            "billing_period": "NONE",
            "price_inr": 0,
            "included_credits": 50,
            "features": {
                "backtests_per_day": 5,
                "ai_runs_per_day": 3,
                "max_parallel_jobs": 1,
                "max_date_range_days": 30,
                "export_enabled": False,
                "support_priority": "LOW",
            },
        },
        {
            "code": "PRO",
            "billing_period": "MONTHLY",
            "price_inr": 999,
            "included_credits": 500,
            "features": {
                "backtests_per_day": 50,
                "ai_runs_per_day": 20,
                "max_parallel_jobs": 3,
                "max_date_range_days": 180,
                "export_enabled": True,
                "support_priority": "MEDIUM",
            },
        },
        {
            "code": "PRO",
            "billing_period": "YEARLY",
            "price_inr": 9999,
            "included_credits": 6000,
            "features": {
                "backtests_per_day": 50,
                "ai_runs_per_day": 20,
                "max_parallel_jobs": 3,
                "max_date_range_days": 180,
                "export_enabled": True,
                "support_priority": "MEDIUM",
            },
        },
        {
            "code": "PREMIUM",
            "billing_period": "MONTHLY",
            "price_inr": 1999,
            "included_credits": 1500,
            "features": {
                "backtests_per_day": 200,
                "ai_runs_per_day": 100,
                "max_parallel_jobs": 5,
                "max_date_range_days": 365,
                "export_enabled": True,
                "support_priority": "HIGH",
            },
        },
        {
            "code": "PREMIUM",
            "billing_period": "YEARLY",
            "price_inr": 19999,
            "included_credits": 18000,
            "features": {
                "backtests_per_day": 200,
                "ai_runs_per_day": 100,
                "max_parallel_jobs": 5,
                "max_date_range_days": 365,
                "export_enabled": True,
                "support_priority": "HIGH",
            },
        },
        {
            "code": "ULTIMATE",
            "billing_period": "MONTHLY",
            "price_inr": 3999,
            "included_credits": 5000,
            "features": {
                "backtests_per_day": 500,
                "ai_runs_per_day": 300,
                "max_parallel_jobs": 10,
                "max_date_range_days": 730,
                "export_enabled": True,
                "support_priority": "PRIORITY",
            },
        },
        {
            "code": "ULTIMATE",
            "billing_period": "YEARLY",
            "price_inr": 39999,
            "included_credits": 60000,
            "features": {
                "backtests_per_day": 500,
                "ai_runs_per_day": 300,
                "max_parallel_jobs": 10,
                "max_date_range_days": 730,
                "export_enabled": True,
                "support_priority": "PRIORITY",
            },
        },
    ]

    for row in plans:
        op.execute(
            sa.text(
                """
                INSERT INTO plans (id, code, billing_period, price_inr, included_credits, features, is_active, created_at)
                VALUES (
                    :id,
                    :code,
                    :billing_period,
                    :price_inr,
                    :included_credits,
                    CAST(:features AS JSON),
                    true,
                    now()
                )
                ON CONFLICT (code, billing_period)
                DO UPDATE SET
                    price_inr = EXCLUDED.price_inr,
                    included_credits = EXCLUDED.included_credits,
                    features = EXCLUDED.features,
                    is_active = EXCLUDED.is_active
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "code": row["code"],
                "billing_period": row["billing_period"],
                "price_inr": row["price_inr"],
                "included_credits": row["included_credits"],
                "features": json.dumps(row["features"]),
            },
        )


def _sync_user_subscriptions_schema(bind) -> None:
    if not _has_table(bind, "user_subscriptions"):
        op.create_table(
            "user_subscriptions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("trial_end_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("renews", sa.Boolean(), nullable=True, server_default=sa.text("true")),
            sa.Column("razorpay_subscription_id", sa.String(length=100), nullable=True),
            sa.Column("razorpay_customer_id", sa.String(length=100), nullable=True),
            sa.Column("plan_code_snapshot", sa.String(length=50), nullable=True),
            sa.Column("billing_period_snapshot", sa.String(length=20), nullable=True),
            sa.Column("plan_price_inr", sa.Integer(), nullable=True),
            sa.Column("included_credits_total", sa.Integer(), nullable=True),
            sa.Column("included_credits_remaining", sa.Integer(), nullable=True),
            sa.Column("last_credit_refill_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("next_credit_refill_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_refill_cycle_key", sa.String(length=80), nullable=True),
            sa.Column("source_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    _ensure_column(bind, "user_subscriptions", sa.Column("plan_code_snapshot", sa.String(length=50), nullable=True))
    _ensure_column(bind, "user_subscriptions", sa.Column("billing_period_snapshot", sa.String(length=20), nullable=True))
    _ensure_column(bind, "user_subscriptions", sa.Column("plan_price_inr", sa.Integer(), nullable=True))
    _ensure_column(bind, "user_subscriptions", sa.Column("included_credits_total", sa.Integer(), nullable=True))
    _ensure_column(bind, "user_subscriptions", sa.Column("included_credits_remaining", sa.Integer(), nullable=True))
    _ensure_column(bind, "user_subscriptions", sa.Column("last_credit_refill_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(bind, "user_subscriptions", sa.Column("next_credit_refill_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(bind, "user_subscriptions", sa.Column("last_refill_cycle_key", sa.String(length=80), nullable=True))
    _ensure_column(bind, "user_subscriptions", sa.Column("source_payment_id", postgresql.UUID(as_uuid=True), nullable=True))
    _ensure_column(bind, "user_subscriptions", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    if not _has_index(bind, "user_subscriptions", "idx_user_subscriptions_user_created"):
        op.create_index(
            "idx_user_subscriptions_user_created",
            "user_subscriptions",
            ["user_id", "created_at"],
            unique=False,
        )


def _sync_user_credits_schema(bind) -> None:
    if not _has_table(bind, "user_credits"):
        op.create_table(
            "user_credits",
            sa.Column("user_id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("balance", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        )
    _ensure_column(bind, "user_credits", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")))


def _sync_credit_transactions_schema(bind) -> None:
    credit_enum = postgresql.ENUM("DEBIT", "CREDIT", "REFUND", name="credittransactiontype")
    credit_enum.create(bind, checkfirst=True)

    if not _has_table(bind, "credit_transactions"):
        op.create_table(
            "credit_transactions",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("transaction_type", credit_enum, nullable=False),
            sa.Column("amount", sa.DECIMAL(precision=10, scale=2), nullable=False),
            sa.Column("balance_after", sa.DECIMAL(precision=10, scale=2), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("backtest_id", sa.String(), nullable=True),
            sa.Column("job_id", sa.String(), nullable=True),
            sa.Column("actor_user_id", sa.String(length=36), nullable=True),
            sa.Column("source", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        )

    _ensure_column(bind, "credit_transactions", sa.Column("actor_user_id", sa.String(length=36), nullable=True))
    _ensure_column(bind, "credit_transactions", sa.Column("source", sa.String(length=64), nullable=True))
    _ensure_column(bind, "credit_transactions", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")))

    if _has_column(bind, "credit_transactions", "user_id"):
        op.execute(
            sa.text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'credit_transactions'
                          AND column_name = 'user_id'
                          AND data_type IN ('character varying', 'text')
                    ) THEN
                        BEGIN
                            ALTER TABLE credit_transactions
                            ALTER COLUMN user_id TYPE UUID
                            USING NULLIF(user_id::text, '')::uuid;
                        EXCEPTION WHEN others THEN
                            -- keep legacy type if conversion fails for non-uuid values
                            NULL;
                        END;
                    END IF;
                END $$;
                """
            )
        )

    if not _has_index(bind, "credit_transactions", "idx_credit_transactions_user_created"):
        op.create_index(
            "idx_credit_transactions_user_created",
            "credit_transactions",
            ["user_id", "created_at"],
            unique=False,
        )


def _sync_payments_schema(bind) -> None:
    if not _has_table(bind, "payments"):
        op.create_table(
            "payments",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("purpose", sa.String(length=50), nullable=False),
            sa.Column("amount_inr", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("billing_order_id", sa.String(length=64), nullable=True),
            sa.Column("razorpay_order_id", sa.String(length=100), nullable=True),
            sa.Column("razorpay_payment_id", sa.String(length=100), nullable=True),
            sa.Column("razorpay_signature", sa.String(length=200), nullable=True),
            sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("plan_code", sa.String(length=50), nullable=True),
            sa.Column("billing_period", sa.String(length=20), nullable=True),
            sa.Column("subscription_id", sa.String(length=64), nullable=True),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    _ensure_column(bind, "payments", sa.Column("billing_order_id", sa.String(length=64), nullable=True))
    _ensure_column(bind, "payments", sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=True))
    _ensure_column(bind, "payments", sa.Column("plan_code", sa.String(length=50), nullable=True))
    _ensure_column(bind, "payments", sa.Column("billing_period", sa.String(length=20), nullable=True))
    _ensure_column(bind, "payments", sa.Column("subscription_id", sa.String(length=64), nullable=True))
    _ensure_column(bind, "payments", sa.Column("failure_reason", sa.Text(), nullable=True))
    _ensure_column(bind, "payments", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(bind, "payments", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    if not _has_index(bind, "payments", "idx_payments_user_created"):
        op.create_index("idx_payments_user_created", "payments", ["user_id", "created_at"], unique=False)
    if not _has_index(bind, "payments", "idx_payments_billing_order_id"):
        op.create_index("idx_payments_billing_order_id", "payments", ["billing_order_id"], unique=False)
    if not _has_index(bind, "payments", "idx_payments_plan_code"):
        op.create_index("idx_payments_plan_code", "payments", ["plan_code"], unique=False)
    if not _has_index(bind, "payments", "idx_payments_subscription_id"):
        op.create_index("idx_payments_subscription_id", "payments", ["subscription_id"], unique=False)


def _sync_billing_orders_schema(bind) -> None:
    if not _has_table(bind, "billing_orders"):
        op.create_table(
            "billing_orders",
            sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("payment_id", sa.String(length=64), nullable=True),
            sa.Column("subscription_id", sa.String(length=64), nullable=True),
            sa.Column("billing_order_id", sa.String(length=64), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("purpose", sa.String(length=50), nullable=False),
            sa.Column("amount_inr", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(length=3), nullable=True, server_default="INR"),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("plan_id", sa.String(length=64), nullable=True),
            sa.Column("plan_code", sa.String(length=50), nullable=True),
            sa.Column("billing_period", sa.String(length=20), nullable=True),
            sa.Column("razorpay_order_id", sa.String(length=100), nullable=True),
            sa.Column("razorpay_payment_id", sa.String(length=100), nullable=True),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    _ensure_column(bind, "billing_orders", sa.Column("payment_id", sa.String(length=64), nullable=True))
    _ensure_column(bind, "billing_orders", sa.Column("subscription_id", sa.String(length=64), nullable=True))
    _ensure_column(bind, "billing_orders", sa.Column("plan_id", sa.String(length=64), nullable=True))
    _ensure_column(bind, "billing_orders", sa.Column("plan_code", sa.String(length=50), nullable=True))
    _ensure_column(bind, "billing_orders", sa.Column("billing_period", sa.String(length=20), nullable=True))
    _ensure_column(bind, "billing_orders", sa.Column("failure_reason", sa.Text(), nullable=True))
    _ensure_column(bind, "billing_orders", sa.Column("metadata_json", sa.Text(), nullable=True))
    _ensure_column(bind, "billing_orders", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(bind, "billing_orders", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    if not _has_index(bind, "billing_orders", "idx_billing_orders_user_created"):
        op.create_index("idx_billing_orders_user_created", "billing_orders", ["user_id", "created_at"], unique=False)
    if not _has_index(bind, "billing_orders", "idx_billing_orders_billing_order_id"):
        op.create_index("idx_billing_orders_billing_order_id", "billing_orders", ["billing_order_id"], unique=False)
    if not _has_index(bind, "billing_orders", "idx_billing_orders_payment_id"):
        op.create_index("idx_billing_orders_payment_id", "billing_orders", ["payment_id"], unique=False)
    if not _has_index(bind, "billing_orders", "idx_billing_orders_purpose"):
        op.create_index("idx_billing_orders_purpose", "billing_orders", ["purpose"], unique=False)


def upgrade() -> None:
    bind = op.get_bind()

    _sync_plans_schema(bind)
    _seed_plans(bind)
    _sync_user_subscriptions_schema(bind)
    _sync_user_credits_schema(bind)
    _sync_credit_transactions_schema(bind)
    _sync_payments_schema(bind)
    _sync_billing_orders_schema(bind)


def downgrade() -> None:
    # Compatibility migration is intentionally non-destructive.
    pass
