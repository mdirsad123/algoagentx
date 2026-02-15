#!/usr/bin/env python3
"""
Debug script to test login issue with test@example.com and password123
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the AlgoAgentXAPI directory to Python path
api_path = Path(__file__).parent / "AlgoAgentXAPI"
sys.path.insert(0, str(api_path))

async def test_database_connection():
    """Test database connection and check for test user"""
    try:
        from app.db.session import async_session
        from app.db.models.users import User
        from sqlalchemy import select
        
        print("🔍 Testing database connection...")
        
        async with async_session() as db:
            # Check if database is accessible
            result = await db.execute(select(User).limit(1))
            users = result.scalars().all()
            print(f"✅ Database connection successful. Found {len(users)} users.")
            
            # Look for test user
            result = await db.execute(select(User).where(User.email == "test@example.com"))
            test_user = result.scalar_one_or_none()
            
            if test_user:
                print(f"✅ Found test user: {test_user.email}")
                print(f"   User ID: {test_user.id}")
                print(f"   Role: {test_user.role}")
                print(f"   Password hash length: {len(test_user.password_hash) if test_user.password_hash else 0}")
                if test_user.password_hash:
                    print(f"   Password hash preview: {test_user.password_hash[:30]}...")
                return test_user
            else:
                print("❌ Test user not found in database")
                return None
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

async def test_password_verification():
    """Test password verification with bcrypt"""
    try:
        import bcrypt
        
        print("\n🔍 Testing password verification...")
        
        # Test password
        test_password = "password123"
        password_bytes = test_password.encode('utf-8')
        
        # Try to find the user and verify password
        user = await test_database_connection()
        if not user or not user.password_hash:
            print("❌ Cannot test password - no user found")
            return False
            
        stored_hash = user.password_hash.strip()
        
        # Handle both bytes and string stored hashes
        if isinstance(stored_hash, str):
            stored_hash_bytes = stored_hash.encode('utf-8')
        else:
            stored_hash_bytes = stored_hash
            
        print(f"Testing password: '{test_password}'")
        print(f"Stored hash type: {type(stored_hash)}")
        print(f"Stored hash length: {len(stored_hash)}")
        
        try:
            password_valid = bcrypt.checkpw(password_bytes, stored_hash_bytes)
            print(f"✅ bcrypt.checkpw result: {password_valid}")
            return password_valid
        except Exception as e:
            print(f"❌ bcrypt error: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Password verification test failed: {e}")
        return False

async def test_auth_endpoint():
    """Test the actual auth endpoint"""
    try:
        import httpx
        from app.core.config import settings
        
        print("\n🔍 Testing auth endpoint...")
        
        # Test login
        login_data = {
            "email": "test@example.com",
            "password": "password123"
        }
        
        async with httpx.AsyncClient() as client:
            # Try to connect to the API
            base_url = "http://localhost:4000"
            try:
                response = await client.post(f"{base_url}/api/v1/auth/login", json=login_data, timeout=10.0)
                print(f"API Response Status: {response.status_code}")
                print(f"API Response: {response.text}")
                
                if response.status_code == 200:
                    print("✅ Login successful!")
                    return True
                else:
                    print("❌ Login failed")
                    return False
                    
            except httpx.ConnectError:
                print("❌ Cannot connect to API - is it running?")
                print("   Try: cd AlgoAgentXAPI && uvicorn app.main:app --host 0.0.0.0 --port 4000")
                return False
            except Exception as e:
                print(f"❌ API test failed: {e}")
                return False
                
    except ImportError:
        print("❌ httpx not available for API testing")
        return False

async def main():
    """Main debug function"""
    print("🔧 AlgoAgentX Login Debug Tool")
    print("=" * 50)
    
    # Test database
    user = await test_database_connection()
    
    # Test password verification
    if user:
        password_ok = await test_password_verification()
    else:
        password_ok = False
    
    # Test API endpoint
    api_ok = await test_auth_endpoint()
    
    print("\n" + "=" * 50)
    print("📊 DEBUG SUMMARY:")
    print(f"   Database connection: {'✅' if user else '❌'}")
    print(f"   User found: {'✅' if user else '❌'}")
    print(f"   Password verification: {'✅' if password_ok else '❌'}")
    print(f"   API endpoint: {'✅' if api_ok else '❌'}")
    
    if not user:
        print("\n💡 SUGGESTION: Create test user with:")
        print("   python -c \"from AlgoAgentXAPI.app.db.session import async_session; from AlgoAgentXAPI.app.db.models.users import User; import bcrypt; import asyncio; async def create(): async with async_session() as db: user = User(email='test@example.com', password_hash=bcrypt.hashpw('password123'.encode(), bcrypt.gensalt()).decode()); db.add(user); await db.commit(); print('User created'); asyncio.run(create())\"")
    
    if user and not password_ok:
        print("\n💡 SUGGESTION: Reset password for test user:")
        print("   Use the debug endpoint: POST /api/v1/auth/debug/reset-password")
        print("   Body: {\"email\": \"test@example.com\", \"new_password\": \"password123\"}")

if __name__ == "__main__":
    asyncio.run(main())