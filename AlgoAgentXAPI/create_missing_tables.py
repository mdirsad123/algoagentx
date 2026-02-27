#!/usr/bin/env python3
"""
Create missing tables directly using SQL
"""

import sys
import os
sys.path.append('.')

from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql

# Use sync URL for creating tables
sync_url = 'postgresql://algo_user:algo_password@localhost:5432/algo_db'
engine = create_engine(sync_url)

def create_missing_tables():
    """Create all missing tables"""
    
    # SQL statements to create missing tables
    create_tables_sql = [
        # Create plans table
        """
        CREATE TABLE IF NOT EXISTS plans (
            id UUID PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            billing_period VARCHAR(20) NOT NULL,
            price_inr INTEGER NOT NULL,
            included_credits INTEGER NOT NULL,
            features JSON NOT NULL,
            is_active BOOLEAN NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
        """,
        
        # Create user_subscriptions table
        """
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL,
            plan_id UUID NOT NULL,
            status VARCHAR(20) NOT NULL,
            start_at TIMESTAMP WITH TIME ZONE NOT NULL,
            end_at TIMESTAMP WITH TIME ZONE NOT NULL,
            trial_end_at TIMESTAMP WITH TIME ZONE,
            renews BOOLEAN NOT NULL,
            razorpay_subscription_id VARCHAR(100),
            razorpay_customer_id VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        )
        """,
        
        # Create user_credits table
        """
        CREATE TABLE IF NOT EXISTS user_credits (
            user_id UUID PRIMARY KEY,
            balance INTEGER NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """,
        
        # Create payments table
        """
        CREATE TABLE IF NOT EXISTS payments (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL,
            provider VARCHAR(50) NOT NULL,
            purpose VARCHAR(50) NOT NULL,
            amount_inr INTEGER NOT NULL,
            currency VARCHAR(3) NOT NULL,
            status VARCHAR(20) NOT NULL,
            razorpay_order_id VARCHAR(100),
            razorpay_payment_id VARCHAR(100),
            razorpay_signature VARCHAR(200),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """,
        
        # Create credit_transactions table
        """
        CREATE TABLE IF NOT EXISTS credit_transactions (
            id VARCHAR PRIMARY KEY,
            user_id UUID NOT NULL,
            transaction_type VARCHAR(20) NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            balance_after DECIMAL(10,2) NOT NULL,
            description TEXT,
            backtest_id TEXT,
            job_id VARCHAR,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            FOREIGN KEY (backtest_id) REFERENCES performance_metrics(id),
            FOREIGN KEY (job_id) REFERENCES job_status(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """,
        
        # Create notifications table
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL,
            type VARCHAR(50) NOT NULL,
            title VARCHAR(200) NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            read_at TIMESTAMP WITH TIME ZONE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """,
        
        # Create strategy_requests table
        """
        CREATE TABLE IF NOT EXISTS strategy_requests (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL,
            strategy_name VARCHAR(100) NOT NULL,
            description TEXT,
            status VARCHAR(20) DEFAULT 'PENDING',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """,
        
        # Create screener_news table
        """
        CREATE TABLE IF NOT EXISTS screener_news (
            id UUID PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            news_date DATE NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            source VARCHAR(100),
            url TEXT,
            sentiment VARCHAR(20),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            UNIQUE (symbol, news_date, title)
        )
        """,
        
        # Create screener_announcements table
        """
        CREATE TABLE IF NOT EXISTS screener_announcements (
            id UUID PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            announce_date DATE NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            exchange VARCHAR(50) NOT NULL,
            category VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            UNIQUE (symbol, announce_date, title, exchange)
        )
        """,
        
        # Create screener_runs table
        """
        CREATE TABLE IF NOT EXISTS screener_runs (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL,
            run_type VARCHAR(50) NOT NULL,
            parameters JSON,
            results JSON,
            status VARCHAR(20) DEFAULT 'PENDING',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            completed_at TIMESTAMP WITH TIME ZONE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    ]
    
    # Create indexes
    create_indexes_sql = [
        "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_user_id ON user_subscriptions(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_plan_id ON user_subscriptions(plan_id)",
        "CREATE INDEX IF NOT EXISTS ix_user_subscriptions_status ON user_subscriptions(status)",
        "CREATE INDEX IF NOT EXISTS ix_payments_user_id ON payments(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_payments_status ON payments(status)",
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications(is_read)",
        "CREATE INDEX IF NOT EXISTS ix_strategy_requests_user_id ON strategy_requests(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_strategy_requests_status ON strategy_requests(status)",
        "CREATE INDEX IF NOT EXISTS ix_screener_news_symbol ON screener_news(symbol)",
        "CREATE INDEX IF NOT EXISTS ix_screener_news_date ON screener_news(news_date)",
        "CREATE INDEX IF NOT EXISTS ix_screener_announcements_symbol ON screener_announcements(symbol)",
        "CREATE INDEX IF NOT EXISTS ix_screener_announcements_date ON screener_announcements(announce_date)",
        "CREATE INDEX IF NOT EXISTS ix_screener_runs_user_id ON screener_runs(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_screener_runs_status ON screener_runs(status)"
    ]
    
    try:
        with engine.connect() as conn:
            # Create tables
            print("Creating missing tables...")
            for sql in create_tables_sql:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"✓ Table created successfully")
                except Exception as e:
                    print(f"✗ Error creating table: {e}")
                    conn.rollback()
            
            # Create indexes
            print("\nCreating indexes...")
            for sql in create_indexes_sql:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"✓ Index created successfully")
                except Exception as e:
                    print(f"✗ Error creating index: {e}")
                    conn.rollback()
            
            print("\n✅ All missing tables and indexes created successfully!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def verify_tables():
    """Verify that all tables were created"""
    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        '''))
        tables = [row[0] for row in result]
        
        print("\nCurrent tables in database:")
        for table in tables:
            print(f"  - {table}")
        
        # Check for all expected tables
        all_expected_tables = [
            'users', 'user_role', 'user_m', 'otp', 'strategies', 'instruments', 
            'market_data', 'signals', 'trades', 'performance_metrics', 
            'equity_curve', 'pnl_calendar', 'job_status',
            'user_credits', 'credit_transactions', 'user_subscriptions', 
            'plans', 'payments', 'notifications', 'strategy_requests',
            'screener_news', 'screener_announcements', 'screener_runs'
        ]
        
        missing = [t for t in all_expected_tables if t not in tables]
        if missing:
            print(f"\n❌ Still missing tables: {missing}")
            return False
        else:
            print("\n✅ All expected tables are now present!")
            return True

if __name__ == "__main__":
    print("Creating missing tables...")
    success = create_missing_tables()
    
    if success:
        print("\nVerifying tables...")
        verify_tables()