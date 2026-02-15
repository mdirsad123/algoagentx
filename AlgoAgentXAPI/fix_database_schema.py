#!/usr/bin/env python3
"""
Script to fix database schema by adding missing columns
"""
import os
import sys
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def fix_database_schema():
    """Add missing columns to the users table"""
    try:
        # Import database configuration
        from app.core.config import settings
        
        # Create async engine
        engine = create_async_engine(settings.DATABASE_URL)
        
        # SQL to add missing columns
        sql_statements = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS fullname VARCHAR;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS mobile VARCHAR;"
        ]
        
        async with engine.begin() as conn:
            for sql in sql_statements:
                print(f"Executing: {sql}")
                await conn.execute(text(sql))
            
            print("✅ Database schema updated successfully!")
            print("✅ Added 'fullname' and 'mobile' columns to users table")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the AlgoAgentXAPI directory")
        return False
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Run the async function
    success = asyncio.run(fix_database_schema())
    if not success:
        sys.exit(1)