"""Add missing indexes and constraints for production requirements

Revision ID: 003_add_missing_indexes_constraints
Revises: 002_seed_default_plans
Create Date: 2026-02-06 20:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_missing_indexes_constraints'
down_revision = '002_seed_default_plans'
branch_labels = None
depends_on = None


def upgrade():
    # Add unique constraint for razorpay_payment_id in payments table
    op.create_unique_constraint(
        'uq_payments_razorpay_payment_id', 
        'payments', 
        ['razorpay_payment_id']
    )
    
    # Add index on payments.user_id and payments.created_at for better query performance
    op.create_index(
        'ix_payments_user_id_created_at', 
        'payments', 
        ['user_id', 'created_at']
    )
    
    # Add index on credit_transactions.user_id and credit_transactions.created_at
    op.create_index(
        'ix_credit_transactions_user_id_created_at', 
        'credit_transactions', 
        ['user_id', 'created_at']
    )
    
    # Add index on user_subscriptions.user_id and user_subscriptions.created_at
    op.create_index(
        'ix_user_subscriptions_user_id_created_at', 
        'user_subscriptions', 
        ['user_id', 'created_at']
    )
    
    # Add index on notifications.user_id, notifications.is_read, notifications.created_at desc
    op.create_index(
        'ix_notifications_user_read_created_desc', 
        'notifications', 
        ['user_id', 'is_read', sa.text('created_at DESC')]
    )
    
    # Add foreign key constraints for user_credits.user_id -> users.id
    op.create_foreign_key(
        'fk_user_credits_user_id', 
        'user_credits', 
        'users', 
        ['user_id'], 
        ['id']
    )
    
    # Add foreign key constraints for user_subscriptions.user_id -> users.id
    op.create_foreign_key(
        'fk_user_subscriptions_user_id', 
        'user_subscriptions', 
        'users', 
        ['user_id'], 
        ['id']
    )
    
    # Add foreign key constraints for user_subscriptions.plan_id -> plans.id
    op.create_foreign_key(
        'fk_user_subscriptions_plan_id', 
        'user_subscriptions', 
        'plans', 
        ['plan_id'], 
        ['id']
    )
    
    # Add foreign key constraints for payments.user_id -> users.id
    op.create_foreign_key(
        'fk_payments_user_id', 
        'payments', 
        'users', 
        ['user_id'], 
        ['id']
    )
    
    # Add foreign key constraints for backtest_runs.user_id -> users.id
    op.create_foreign_key(
        'fk_backtest_runs_user_id', 
        'backtest_runs', 
        'users', 
        ['user_id'], 
        ['id']
    )
    
    # Add foreign key constraints for backtest_runs.job_id -> job_status.id
    op.create_foreign_key(
        'fk_backtest_runs_job_id', 
        'backtest_runs', 
        'job_status', 
        ['job_id'], 
        ['id']
    )


def downgrade():
    # Drop foreign key constraints
    op.drop_constraint('fk_backtest_runs_job_id', 'backtest_runs', type_='foreignkey')
    op.drop_constraint('fk_backtest_runs_user_id', 'backtest_runs', type_='foreignkey')
    op.drop_constraint('fk_payments_user_id', 'payments', type_='foreignkey')
    op.drop_constraint('fk_user_subscriptions_plan_id', 'user_subscriptions', type_='foreignkey')
    op.drop_constraint('fk_user_subscriptions_user_id', 'user_subscriptions', type_='foreignkey')
    op.drop_constraint('fk_user_credits_user_id', 'user_credits', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_notifications_user_read_created_desc', table_name='notifications')
    op.drop_index('ix_user_subscriptions_user_id_created_at', table_name='user_subscriptions')
    op.drop_index('ix_credit_transactions_user_id_created_at', table_name='credit_transactions')
    op.drop_index('ix_payments_user_id_created_at', table_name='payments')
    
    # Drop unique constraint
    op.drop_constraint('uq_payments_razorpay_payment_id', 'payments', type_='unique')