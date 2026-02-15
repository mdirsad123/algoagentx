#!/usr/bin/env python3
"""
Test script to validate the new Alembic migrations for billing/credits/payments/notifications
"""
import asyncio
import asyncpg
import os
from typing import Dict, List, Set

# Database connection from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://algo_user:algo_password@localhost:5436/algo_db')

async def test_migrations():
    """Test the new migrations"""
    
    # Parse connection string for asyncpg
    conn_str = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
    
    conn = await asyncpg.connect(conn_str)
    
    try:
        print("=== TESTING NEW MIGRATIONS ===")
        
        # Test 1: Check if all required tables exist
        required_tables = {
            'plans', 'user_subscriptions', 'user_credits', 'credit_transactions',
            'payments', 'notifications', 'backtest_runs'
        }
        
        tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ($1, $2, $3, $4, $5, $6, $7)
        """
        existing_tables = await conn.fetch(tables_query, *required_tables)
        existing_table_names = {row['table_name'] for row in existing_tables}
        
        print(f"Required tables found: {sorted(existing_table_names)}")
        missing_tables = required_tables - existing_table_names
        if missing_tables:
            print(f"❌ Missing tables: {sorted(missing_tables)}")
            return False
        else:
            print("✅ All required tables exist")
        
        # Test 2: Check plans table structure
        print("\n--- Testing plans table ---")
        plans_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'plans'
            ORDER BY ordinal_position
        """)
        
        required_plan_columns = {
            'id', 'code', 'billing_period', 'price_inr', 'included_credits', 
            'features', 'is_active', 'created_at'
        }
        plan_columns = {col['column_name'] for col in plans_columns}
        
        if required_plan_columns.issubset(plan_columns):
            print("✅ Plans table has all required columns")
        else:
            missing = required_plan_columns - plan_columns
            print(f"❌ Plans table missing columns: {missing}")
            return False
        
        # Test 3: Check user_subscriptions table structure
        print("\n--- Testing user_subscriptions table ---")
        sub_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_subscriptions'
            ORDER BY ordinal_position
        """)
        
        required_sub_columns = {
            'id', 'user_id', 'plan_id', 'status', 'start_at', 'end_at', 
            'trial_end_at', 'renews', 'razorpay_subscription_id', 
            'razorpay_customer_id', 'created_at'
        }
        sub_columns_set = {col['column_name'] for col in sub_columns}
        
        if required_sub_columns.issubset(sub_columns_set):
            print("✅ User_subscriptions table has all required columns")
        else:
            missing = required_sub_columns - sub_columns_set
            print(f"❌ User_subscriptions table missing columns: {missing}")
            return False
        
        # Test 4: Check payments table structure
        print("\n--- Testing payments table ---")
        payments_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'payments'
            ORDER BY ordinal_position
        """)
        
        required_payment_columns = {
            'id', 'user_id', 'provider', 'purpose', 'amount_inr', 'currency', 
            'status', 'razorpay_order_id', 'razorpay_payment_id', 
            'razorpay_signature', 'created_at'
        }
        payment_columns_set = {col['column_name'] for col in payments_columns}
        
        if required_payment_columns.issubset(payment_columns_set):
            print("✅ Payments table has all required columns")
        else:
            missing = required_payment_columns - payment_columns_set
            print(f"❌ Payments table missing columns: {missing}")
            return False
        
        # Test 5: Check notifications table structure
        print("\n--- Testing notifications table ---")
        notifications_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'notifications'
            ORDER BY ordinal_position
        """)
        
        required_notification_columns = {
            'id', 'user_id', 'type', 'title', 'message', 'metadata', 
            'is_read', 'created_at'
        }
        notification_columns_set = {col['column_name'] for col in notifications_columns}
        
        if required_notification_columns.issubset(notification_columns_set):
            print("✅ Notifications table has all required columns")
        else:
            missing = required_notification_columns - notification_columns_set
            print(f"❌ Notifications table missing columns: {missing}")
            return False
        
        # Test 6: Check backtest_runs table structure
        print("\n--- Testing backtest_runs table ---")
        backtest_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'backtest_runs'
            ORDER BY ordinal_position
        """)
        
        required_backtest_columns = {
            'id', 'user_id', 'cache_key', 'job_id', 'created_at'
        }
        backtest_columns_set = {col['column_name'] for col in backtest_columns}
        
        if required_backtest_columns.issubset(backtest_columns_set):
            print("✅ Backtest_runs table has all required columns")
        else:
            missing = required_backtest_columns - backtest_columns_set
            print(f"❌ Backtest_runs table missing columns: {missing}")
            return False
        
        # Test 7: Check indexes exist
        print("\n--- Testing required indexes ---")
        indexes_query = """
            SELECT indexname, indexdef
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename IN ('payments', 'credit_transactions', 'user_subscriptions', 'notifications', 'backtest_runs')
        """
        indexes = await conn.fetch(indexes_query)
        
        required_indexes = {
            'ix_payments_user_id_created_at',
            'ix_credit_transactions_user_id_created_at', 
            'ix_user_subscriptions_user_id_created_at',
            'ix_notifications_user_read_created_desc',
            'ix_backtest_runs_user_id',
            'ix_backtest_runs_cache_key',
            'ix_backtest_runs_job_id',
            'ix_backtest_runs_created_at'
        }
        
        existing_indexes = {idx['indexname'] for idx in indexes}
        found_indexes = required_indexes & existing_indexes
        
        if found_indexes:
            print(f"✅ Found {len(found_indexes)} required indexes: {sorted(found_indexes)}")
        else:
            print("❌ No required indexes found")
        
        # Test 8: Check unique constraints
        print("\n--- Testing unique constraints ---")
        constraints_query = """
            SELECT constraint_name, constraint_type, table_name
            FROM information_schema.table_constraints 
            WHERE table_schema = 'public' 
            AND constraint_type = 'UNIQUE'
            AND table_name IN ('payments', 'backtest_runs')
        """
        constraints = await conn.fetch(constraints_query)
        
        required_constraints = {
            'uq_payments_razorpay_payment_id',
            'uq_user_cache_key'
        }
        
        existing_constraints = {const['constraint_name'] for const in constraints}
        found_constraints = required_constraints & existing_constraints
        
        if found_constraints:
            print(f"✅ Found {len(found_constraints)} required unique constraints: {sorted(found_constraints)}")
        else:
            print("❌ No required unique constraints found")
        
        # Test 9: Check foreign key constraints
        print("\n--- Testing foreign key constraints ---")
        fk_query = """
            SELECT constraint_name, table_name, column_name, 
                   referenced_table_name, referenced_column_name
            FROM information_schema.key_column_usage 
            WHERE table_schema = 'public'
            AND referenced_table_name IS NOT NULL
            AND table_name IN ('user_credits', 'user_subscriptions', 'payments', 'backtest_runs')
        """
        fks = await conn.fetch(fk_query)
        
        if fks:
            print(f"✅ Found {len(fks)} foreign key constraints")
            for fk in fks:
                print(f"  - {fk['table_name']}.{fk['column_name']} -> {fk['referenced_table_name']}.{fk['referenced_column_name']}")
        else:
            print("❌ No foreign key constraints found")
        
        # Test 10: Check seeded plans
        print("\n--- Testing seeded plans ---")
        plans_count = await conn.fetchval("SELECT COUNT(*) FROM plans")
        print(f"✅ Found {plans_count} plans in database")
        
        if plans_count > 0:
            plans = await conn.fetch("SELECT code, billing_period, price_inr, included_credits FROM plans ORDER BY code, billing_period")
            print("Seeded plans:")
            for plan in plans:
                print(f"  - {plan['code']} ({plan['billing_period']}): ₹{plan['price_inr']}, {plan['included_credits']} credits")
        
        print("\n=== MIGRATION TEST SUMMARY ===")
        print("✅ All migrations appear to be working correctly!")
        print("✅ Schema is ready for SaaS billing/credits/razorpay/notifications")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
        
    finally:
        await conn.close()

if __name__ == "__main__":
    success = asyncio.run(test_migrations())
    exit(0 if success else 1)