"""Add credit transactions and debit_txn_id to job_status

Revision ID: add_credit_system
Revises: update_backtest_schema
Create Date: 2026-02-06 17:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_credit_system'
down_revision = 'update_backtest_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Create credit_transactions table
    op.create_table('credit_transactions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('transaction_type', postgresql.ENUM('DEBIT', 'CREDIT', 'REFUND', name='credittransactiontype', create_type=False), nullable=False),
        sa.Column('amount', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('balance_after', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('backtest_id', sa.String(), nullable=True),
        sa.Column('job_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['backtest_id'], ['performance_metrics.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['job_status.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add debit_txn_id column to job_status table
    op.add_column('job_status', sa.Column('debit_txn_id', sa.String(), nullable=True))
    op.create_foreign_key('job_status_debit_txn_id_fkey', 'job_status', 'credit_transactions', ['debit_txn_id'], ['id'])


def downgrade():
    # Drop foreign key constraint
    op.drop_constraint('job_status_debit_txn_id_fkey', 'job_status', type_='foreignkey')
    
    # Drop debit_txn_id column
    op.drop_column('job_status', 'debit_txn_id')
    
    # Drop credit_transactions table
    op.drop_table('credit_transactions')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS credittransactiontype')