"""Test script to verify the database initialization fix."""
import asyncio
import sys
import os

# Add the API path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'AlgoAgentXAPI'))

async def test_db_init():
    """Test database initialization to verify the Row await fix."""
    try:
        from AlgoAgentXAPI.app.db.init_db import check_db_connection, init_db
        
        print("Testing database connection check...")
        await check_db_connection()
        print("✅ Database connection check passed!")
        
        print("\nTesting full database initialization...")
        await init_db()
        print("✅ Database initialization completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_db_init())
    if success:
        print("\n🎉 All database initialization tests passed!")
    else:
        print("\n💥 Database initialization tests failed!")
        sys.exit(1)