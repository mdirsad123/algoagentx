#!/usr/bin/env python3
"""
Test database connection using the actual application configuration
"""

import os
import sys
import asyncio
sys.path.append('AlgoAgentXAPI')

from app.core.config import settings
from app.db.session import engine, get_db_session
from sqlalchemy import text

async def test_app_db_connection():
    """Test database connection using app configuration"""
    print("Testing database connection using app configuration...")
    print(f"Database URL: {settings.masked_database_url}")
    print(f"Database Name: {settings.database_name}")
    print(f"Database Host: {settings.database_host}:{settings.database_port}")
    print(f"Environment: {settings.env}")
    print(f"Is Development: {settings.is_development}")
    print(f"Is Production: {settings.is_production}")
    
    try:
        # Test connection using the app's engine
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            print(f"✅ Database connection successful! Test query returned: {test_value}")
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def test_session_factory():
    """Test the session factory"""
    print("\nTesting session factory...")
    try:
        async with get_db_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            print(f"✅ Session factory test successful! Test query returned: {test_value}")
            return True
    except Exception as e:
        print(f"❌ Session factory test failed: {e}")
        return False

def main():
    """Main function to run the async tests"""
    try:
        # Run the async tests
        result1 = asyncio.run(test_app_db_connection())
        result2 = asyncio.run(test_session_factory())
        
        if result1 and result2:
            print("\n🎉 All database connection tests passed!")
            return 0
        else:
            print("\n💥 Some database connection tests failed!")
            return 1
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)