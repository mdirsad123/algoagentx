#!/usr/bin/env python3
"""
Direct API test for login functionality
"""

import asyncio
import httpx
import json

async def test_login():
    """Test login with the credentials"""
    print("🔧 Testing AlgoAgentX Login API")
    print("=" * 50)
    
    # Test data
    login_data = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Try to connect to the API
            base_url = "http://localhost:8000"
            
            print(f"📡 Attempting to connect to {base_url}/api/v1/auth/login")
            print(f"📝 Login data: {json.dumps(login_data, indent=2)}")
            
            try:
                response = await client.post(
                    f"{base_url}/api/v1/auth/login", 
                    json=login_data, 
                    timeout=10.0
                )
                
                print(f"\n📊 Response Status: {response.status_code}")
                print(f"📋 Response Headers: {dict(response.headers)}")
                print(f"📄 Response Body: {response.text}")
                
                if response.status_code == 200:
                    print("\n✅ LOGIN SUCCESSFUL!")
                    data = response.json()
                    print(f"🔑 Access Token: {data.get('access_token', 'N/A')[:50]}...")
                    print(f"👤 User Info: {data.get('user', {})}")
                    return True
                else:
                    print(f"\n❌ LOGIN FAILED with status {response.status_code}")
                    return False
                    
            except httpx.ConnectError as e:
                print(f"\n❌ Cannot connect to API: {e}")
                print("💡 The API server might not be running.")
                print("💡 Try starting it with: uvicorn app.main:app --host 0.0.0.0 --port 4000")
                return False
                
            except httpx.TimeoutException as e:
                print(f"\n⏰ Request timed out: {e}")
                return False
                
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                return False
                
    except ImportError:
        print("❌ httpx not available")
        return False

async def test_debug_endpoints():
    """Test the debug endpoints"""
    print("\n🔍 Testing Debug Endpoints")
    print("-" * 30)
    
    try:
        async with httpx.AsyncClient() as client:
            base_url = "http://localhost:8000"
            
            # Test debug database endpoint
            try:
                response = await client.get(f"{base_url}/api/v1/auth/debug/db", timeout=5.0)
                print(f"📊 Debug DB endpoint: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Environment: {data.get('environment', 'N/A')}")
                    print(f"   Database: {data.get('database', {}).get('name', 'N/A')}")
                    print(f"   Users count: {data.get('users_table', {}).get('total_count', 'N/A')}")
                else:
                    print(f"   Error: {response.text}")
            except Exception as e:
                print(f"   Debug DB endpoint not accessible: {e}")
            
            # Test debug reset password endpoint
            try:
                reset_data = {
                    "email": "test@example.com",
                    "new_password": "password123"
                }
                response = await client.post(
                    f"{base_url}/api/v1/auth/debug/reset-password",
                    json=reset_data,
                    timeout=5.0
                )
                print(f"🔑 Debug reset password: {response.status_code}")
                if response.status_code == 200:
                    print("   Password reset successful")
                else:
                    print(f"   Error: {response.text}")
            except Exception as e:
                print(f"   Debug reset password endpoint not accessible: {e}")
                
    except ImportError:
        print("❌ httpx not available for debug testing")

async def main():
    """Main test function"""
    success = await test_login()
    await test_debug_endpoints()
    
    print("\n" + "=" * 50)
    print("📊 FINAL RESULT:")
    if success:
        print("✅ Login test PASSED - API is working correctly!")
    else:
        print("❌ Login test FAILED - Check API server status")
    
    print("\n💡 If the API server is not running:")
    print("   1. cd AlgoAgentXAPI")
    print("   2. uvicorn app.main:app --host 0.0.0.0 --port 4000")
    print("   3. Run this test again")

if __name__ == "__main__":
    asyncio.run(main())