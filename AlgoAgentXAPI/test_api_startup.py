"""Test script to verify API startup and database initialization."""
import asyncio
import sys
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_api_startup():
    """Test the complete API startup process including database initialization."""
    print("🚀 Testing AlgoAgentX API Startup Process...")
    print("=" * 60)
    
    try:
        # Test database initialization
        print("📊 Testing database initialization...")
        from app.db.init_db import init_db
        await init_db()
        print("✅ Database initialization completed successfully!")
        
        # Test Redis manager
        print("\n🔴 Testing Redis connection...")
        from app.core.redis_manager import redis_manager
        redis_available = await redis_manager.initialize()
        if redis_available:
            print("✅ Redis connection established successfully!")
        else:
            print("⚠️ Redis unavailable - using fallback (this is OK for development)")
        
        # Test basic app creation (without actually starting the server)
        print("\n🌐 Testing FastAPI app creation...")
        from app.main import app
        print(f"✅ FastAPI app created: {app.title}")
        
        # Test health endpoints would be available
        print("\n🏥 Testing health check functions...")
        from app.db.init_db import check_db_connection
        await check_db_connection()
        print("✅ Database health check passed!")
        
        redis_health = await redis_manager.health_check()
        print(f"✅ Redis health check completed: {redis_health.get('redis_available', False)}")
        
        print("\n" + "=" * 60)
        print("🎉 API startup simulation completed successfully!")
        print("✅ The 'object Row can't be used in await expression' error is FIXED!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ API startup test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up Redis connection
        try:
            await redis_manager.close()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(test_api_startup())
    if success:
        print("\n✅ All API startup tests passed! The database error is resolved.")
    else:
        print("\n❌ API startup tests failed!")
        sys.exit(1)