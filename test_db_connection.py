#!/usr/bin/env python3
"""
python -m test_db_connection
Simple database connection test
"""

import os
import sys
import asyncio
sys.path.append('AlgoAgentXAPI')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

async def test_db_connection():
    """Test database connection"""
    print("Testing database connection...")
    
    # Get database URL from environment or use default
    database_url = os.getenv('DATABASE_URL', 'postgresql+asyncpg://algo_user:algo_password@localhost:5432/algo_db')
    print(f"Database URL: {database_url}")
    
    try:
        # Create async engine
        engine = create_async_engine(database_url, echo=False)
        
        # Test connection
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            print(f"✅ Database connection successful! Test query returned: {test_value}")
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    finally:
        # Clean up engine
        await engine.dispose()

def main():
    """Main function to run the async test"""
    try:
        # Run the async test
        result = asyncio.run(test_db_connection())
        if result:
            print("\n🎉 Database connection test passed!")
            return 0
        else:
            print("\n💥 Database connection test failed!")
            return 1
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
