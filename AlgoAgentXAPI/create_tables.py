#!/usr/bin/env python3
"""
Script to create database tables using SQLAlchemy's create_all()
This ensures all tables are created before the application starts.
"""

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.base import Base
from app.db.models import *  # Import all models to ensure they're registered with Base


async def create_database_tables():
    """Create all database tables"""
    print("Creating database tables...")
    print(f"Database URL: {settings.database_url}")
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=True,  # Enable SQL logging to see what's happening
    )
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            print("Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("✓ All tables created successfully!")
            
            # Verify tables were created
            await verify_tables_created(conn)
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    finally:
        await engine.dispose()
    
    return True


async def verify_tables_created(conn):
    """Verify that tables were actually created"""
    print("\nVerifying table creation...")
    
    # Get list of tables
    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
    tables = [row[0] for row in result.fetchall()]
    
    expected_tables = [
        'users',
        'instruments', 
        'strategies',
        'market_data',
        'performance_metrics',
        'trades',
        'equity_curve',
        'pnl_calendar',
        'job_status',
        'credit_transactions',
        'plans',
        'user_subscriptions',
        'user_credits',
        'payments',
        'notifications',
        'strategy_requests',
        'screener_news',
        'screener_announcements',
        'screener_runs',
        'support_tickets',
        'support_ticket_replies'
    ]
    
    created_tables = []
    missing_tables = []
    
    for table in expected_tables:
        if table in tables:
            created_tables.append(table)
            print(f"  ✓ {table}")
        else:
            missing_tables.append(table)
            print(f"  ❌ {table}")
    
    print(f"\nSummary: {len(created_tables)}/{len(expected_tables)} tables created")
    
    if missing_tables:
        print(f"Missing tables: {missing_tables}")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(create_database_tables())
    if success:
        print("\n🎉 Database setup completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Database setup failed!")
        sys.exit(1)