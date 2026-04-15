"""
python debug_admin_metrics.py
"""

import asyncio
import json
from dotenv import load_dotenv
import os

# Load environment variables first
load_dotenv()

from app.core.dependencies import get_db, get_admin_user
from app.api.v1.admin import get_admin_metrics
from sqlalchemy.ext.asyncio import AsyncSession


async def debug_admin_metrics():
    print("=" * 80)
    print("DEBUGGING ADMIN METRICS ENDPOINT /api/v1/admin/metrics")
    print("=" * 80)
    
    try:
        # Get database session
        db: AsyncSession = await anext(get_db())
        print("✅ Database connection established")
        
        # Mock admin user (bypassing auth for debug)
        mock_admin_user = {
            "user_id": "debug-test-admin",
            "email": "debug@algoagentx.com",
            "role": "admin"
        }
        
        print("\n🔍 Calling actual endpoint function get_admin_metrics()...")
        print("-" * 60)
        
        # Call the actual endpoint function directly
        result = await get_admin_metrics(db=db, current_user=mock_admin_user)
        
        print("\n✅ ENDPOINT RETURNED DATA SUCCESSFULLY!")
        print("=" * 80)
        
        # Pretty print the response
        print(json.dumps(result, indent=2, default=str))
        
        print("\n" + "=" * 80)
        print("✅ DEBUG COMPLETE - DATA IS COMING FINE!")
        print("=" * 80)
        
        # Also print summary
        if 'data' in result:
            data = result['data']
            print("\n📊 QUICK SUMMARY:")
            print(f"   Total Users: {data.get('users', {}).get('total', 0)}")
            print(f"   Active Users: {data.get('users', {}).get('active', 0)}")
            print(f"   Total Revenue: ₹ {data.get('payments', {}).get('revenue', 0):.2f}")
            print(f"   Total Credits Issued: {data.get('credits', {}).get('total', 0)}")
            print(f"   Total Subscriptions: {data.get('credits', {}).get('active_subscriptions', 0)}")
            print(f"   Pending Strategy Requests: {data.get('strategies', {}).get('pending', 0)}")
            print(f"   Total Backtests: {data.get('backtests', {}).get('total', 0)}")
            print(f"   Total Orders: {data.get('orders', {}).get('total', 0)}")
        
        await db.close()
        
    except Exception as e:
        print("\n❌ ERROR OCCURRED:")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Message: {str(e)}")
        import traceback
        print("\nFull Traceback:")
        print(traceback.format_exc())
        return False
    
    return True


if __name__ == "__main__":
    asyncio.run(debug_admin_metrics())