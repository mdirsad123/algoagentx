"""Seed default plans for the subscription system

Revision ID: 002_seed_default_plans
Revises: 001_add_backtest_cache_table
Create Date: 2026-02-06 20:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '002_seed_default_plans'
down_revision = '001_add_backtest_cache_table'
branch_labels = None
depends_on = None


def upgrade():
    # Insert default plans using upsert logic
    plans_data = [
        {
            'id': str(uuid.uuid4()),
            'code': 'FREE',
            'billing_period': 'NONE',
            'price_inr': 0,
            'included_credits': 1000,
            'features': {
                'max_backtests_per_month': 5,
                'max_concurrent_backtests': 1,
                'max_backtest_duration_days': 30,
                'max_backtest_candles': 10000,
                'ai_screener_access': False,
                'priority_support': False,
                'api_access': True
            },
            'is_active': True,
            'created_at': datetime.utcnow()
        },
        {
            'id': str(uuid.uuid4()),
            'code': 'PRO',
            'billing_period': 'MONTHLY',
            'price_inr': 999,
            'included_credits': 10000,
            'features': {
                'max_backtests_per_month': 50,
                'max_concurrent_backtests': 3,
                'max_backtest_duration_days': 90,
                'max_backtest_candles': 50000,
                'ai_screener_access': True,
                'priority_support': False,
                'api_access': True
            },
            'is_active': True,
            'created_at': datetime.utcnow()
        },
        {
            'id': str(uuid.uuid4()),
            'code': 'PRO',
            'billing_period': 'YEARLY',
            'price_inr': 9999,
            'included_credits': 120000,
            'features': {
                'max_backtests_per_month': 50,
                'max_concurrent_backtests': 3,
                'max_backtest_duration_days': 90,
                'max_backtest_candles': 50000,
                'ai_screener_access': True,
                'priority_support': False,
                'api_access': True
            },
            'is_active': True,
            'created_at': datetime.utcnow()
        },
        {
            'id': str(uuid.uuid4()),
            'code': 'PREMIUM',
            'billing_period': 'MONTHLY',
            'price_inr': 1999,
            'included_credits': 25000,
            'features': {
                'max_backtests_per_month': 200,
                'max_concurrent_backtests': 5,
                'max_backtest_duration_days': 180,
                'max_backtest_candles': 100000,
                'ai_screener_access': True,
                'priority_support': True,
                'api_access': True
            },
            'is_active': True,
            'created_at': datetime.utcnow()
        },
        {
            'id': str(uuid.uuid4()),
            'code': 'PREMIUM',
            'billing_period': 'YEARLY',
            'price_inr': 19999,
            'included_credits': 300000,
            'features': {
                'max_backtests_per_month': 200,
                'max_concurrent_backtests': 5,
                'max_backtest_duration_days': 180,
                'max_backtest_candles': 100000,
                'ai_screener_access': True,
                'priority_support': True,
                'api_access': True
            },
            'is_active': True,
            'created_at': datetime.utcnow()
        },
        {
            'id': str(uuid.uuid4()),
            'code': 'ULTIMATE',
            'billing_period': 'MONTHLY',
            'price_inr': 3999,
            'included_credits': 50000,
            'features': {
                'max_backtests_per_month': 500,
                'max_concurrent_backtests': 10,
                'max_backtest_duration_days': 365,
                'max_backtest_candles': 200000,
                'ai_screener_access': True,
                'priority_support': True,
                'api_access': True,
                'custom_strategies': True,
                'dedicated_account_manager': True
            },
            'is_active': True,
            'created_at': datetime.utcnow()
        },
        {
            'id': str(uuid.uuid4()),
            'code': 'ULTIMATE',
            'billing_period': 'YEARLY',
            'price_inr': 39999,
            'included_credits': 600000,
            'features': {
                'max_backtests_per_month': 500,
                'max_concurrent_backtests': 10,
                'max_backtest_duration_days': 365,
                'max_backtest_candles': 200000,
                'ai_screener_access': True,
                'priority_support': True,
                'api_access': True,
                'custom_strategies': True,
                'dedicated_account_manager': True
            },
            'is_active': True,
            'created_at': datetime.utcnow()
        }
    ]

    # Use raw SQL for upsert to ensure idempotency
    connection = op.get_bind()
    
    for plan in plans_data:
        # Use ON CONFLICT DO UPDATE to handle duplicates
        connection.execute(
            sa.text("""
                INSERT INTO plans (id, code, billing_period, price_inr, included_credits, features, is_active, created_at)
                VALUES (:id, :code, :billing_period, :price_inr, :included_credits, :features, :is_active, :created_at)
                ON CONFLICT (code, billing_period) 
                DO UPDATE SET
                    price_inr = EXCLUDED.price_inr,
                    included_credits = EXCLUDED.included_credits,
                    features = EXCLUDED.features,
                    is_active = EXCLUDED.is_active
            """),
            {
                'id': plan['id'],
                'code': plan['code'],
                'billing_period': plan['billing_period'],
                'price_inr': plan['price_inr'],
                'included_credits': plan['included_credits'],
                'features': plan['features'],
                'is_active': plan['is_active'],
                'created_at': plan['created_at']
            }
        )


def downgrade():
    # Remove all seeded plans
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            DELETE FROM plans 
            WHERE code IN ('FREE', 'PRO', 'PREMIUM', 'ULTIMATE')
        """)
    )