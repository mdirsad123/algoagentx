"""Add subscription system tables

Revision ID: 0002_add_subscription_system
Revises: 0001_add_credit_system
Create Date: 2026-02-06 18:09:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002_add_subscription_system'
down_revision = '0001_add_credit_system'
branch_labels = None
depends_on = None


def upgrade():
    # Create plans table
    op.create_table('plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('billing_period', sa.String(length=20), nullable=False),
        sa.Column('price_inr', sa.Integer(), nullable=False),
        sa.Column('included_credits', sa.Integer(), nullable=False),
        sa.Column('features', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # Create user_subscriptions table
    op.create_table('user_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('trial_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('renews', sa.Boolean(), nullable=False),
        sa.Column('razorpay_subscription_id', sa.String(length=100), nullable=True),
        sa.Column('razorpay_customer_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_credits table
    op.create_table('user_credits',
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('balance', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('user_id')
    )

    # Create payments table
    op.create_table('payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('purpose', sa.String(length=50), nullable=False),
        sa.Column('amount_inr', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('razorpay_order_id', sa.String(length=100), nullable=True),
        sa.Column('razorpay_payment_id', sa.String(length=100), nullable=True),
        sa.Column('razorpay_signature', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_user_subscriptions_user_id', 'user_subscriptions', ['user_id'])
    op.create_index('ix_user_subscriptions_plan_id', 'user_subscriptions', ['plan_id'])
    op.create_index('ix_user_subscriptions_status', 'user_subscriptions', ['status'])
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_payments_status')
    op.drop_index('ix_payments_user_id')
    op.drop_index('ix_user_subscriptions_status')
    op.drop_index('ix_user_subscriptions_plan_id')
    op.drop_index('ix_user_subscriptions_user_id')

    # Drop tables
    op.drop_table('payments')
    op.drop_table('user_credits')
    op.drop_table('user_subscriptions')
    op.drop_table('plans')