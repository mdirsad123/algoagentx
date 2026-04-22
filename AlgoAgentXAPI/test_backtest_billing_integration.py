import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Plan, User, UserCredit, UserSubscription
from app.services.credits.management import CreditManagementService


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session

    await engine.dispose()


async def _seed_user_with_plan(
    db: AsyncSession,
    *,
    wallet_balance: int,
    included_remaining: int,
) -> str:
    user_uuid = uuid.uuid4()
    user_id = str(user_uuid)
    plan_id = uuid.uuid4()
    subscription_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    db.add(
        User(
            id=user_uuid,
            email=f"tester-{user_id[:8]}@example.com",
            password_hash="hashed",
            role="user",
            fullname="Test User",
        )
    )
    db.add(
        Plan(
            id=plan_id,
            code="PRO",
            billing_period="MONTHLY",
            price_inr=999,
            included_credits=200,
            features={"backtests_per_day": 100},
            is_active=True,
        )
    )
    db.add(
        UserCredit(
            user_id=user_id,
            balance=wallet_balance,
        )
    )
    db.add(
        UserSubscription(
            id=subscription_id,
            user_id=user_id,
            plan_id=plan_id,
            status="ACTIVE",
            start_at=now,
            end_at=now.replace(year=now.year + 1),
            renews=True,
            plan_code_snapshot="PRO",
            billing_period_snapshot="MONTHLY",
            plan_price_inr=999,
            included_credits_total=200,
            included_credits_remaining=included_remaining,
            last_credit_refill_at=now,
            next_credit_refill_at=now + timedelta(days=30),
        )
    )
    await db.commit()
    return user_id


@pytest.mark.asyncio
async def test_subscription_then_wallet_deduction_and_refund_idempotent(db_session: AsyncSession):
    user_id = await _seed_user_with_plan(db_session, wallet_balance=40, included_remaining=30)
    job_id = str(uuid.uuid4())

    consume = await CreditManagementService.consume_credits_for_backtest(
        db=db_session,
        user_id=user_id,
        total_cost=Decimal("55"),
        description="Backtest run",
        job_id=job_id,
        auto_commit=True,
    )

    assert int(consume["included_debited"]) == 30
    assert int(consume["wallet_debited"]) == 25
    assert int(consume["effective_included_debited"]) == 30
    assert int(consume["effective_wallet_debited"]) == 25

    capacity_after = await CreditManagementService.get_credit_capacity(db_session, user_id, for_update=False)
    assert int(capacity_after["included_balance"]) == 0
    assert int(capacity_after["wallet_balance"]) == 15

    second_consume = await CreditManagementService.consume_credits_for_backtest(
        db=db_session,
        user_id=user_id,
        total_cost=Decimal("55"),
        description="Backtest run retry",
        job_id=job_id,
        auto_commit=True,
    )
    assert bool(second_consume["idempotent"]) is True
    assert int(second_consume["effective_included_debited"]) == 30
    assert int(second_consume["effective_wallet_debited"]) == 25

    refund = await CreditManagementService.restore_consumed_credits(
        db=db_session,
        user_id=user_id,
        job_id=job_id,
        description="Refund failed backtest",
        auto_commit=True,
    )
    assert int(refund["included_refunded"]) == 30
    assert int(refund["wallet_refunded"]) == 25

    capacity_restored = await CreditManagementService.get_credit_capacity(db_session, user_id, for_update=False)
    assert int(capacity_restored["included_balance"]) == 30
    assert int(capacity_restored["wallet_balance"]) == 40

    second_refund = await CreditManagementService.restore_consumed_credits(
        db=db_session,
        user_id=user_id,
        job_id=job_id,
        description="Refund retry",
        auto_commit=True,
    )
    assert bool(second_refund["idempotent"]) is True
    assert int(second_refund["included_refunded"]) == 0
    assert int(second_refund["wallet_refunded"]) == 0


@pytest.mark.asyncio
async def test_insufficient_total_capacity_raises_value_error(db_session: AsyncSession):
    user_id = await _seed_user_with_plan(db_session, wallet_balance=10, included_remaining=5)

    with pytest.raises(ValueError):
        await CreditManagementService.consume_credits_for_backtest(
            db=db_session,
            user_id=user_id,
            total_cost=Decimal("20"),
            description="Should fail",
            job_id=str(uuid.uuid4()),
            auto_commit=True,
        )
