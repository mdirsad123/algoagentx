#!/usr/bin/env python3
"""
Simple fix for login issues - create minimal tables and test user
"""

import asyncio
import sys
import os
import bcrypt

# Add the API directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "AlgoAgentXAPI"))

from sqlalchemy import text
from AlgoAgentXAPI.app.db.session import async_session
from AlgoAgentXAPI.app.db.session import engine

async def create_minimal_tables():
    """Create just the essential tables for login"""
    print("🔄 Creating minimal tables for login...")
    
    async with engine.begin() as conn:
        # Drop and create just the users table
        await conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        
        await conn.execute(text("""
            CREATE TABLE users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR UNIQUE NOT NULL,
                password_hash VARCHAR NOT NULL,
                role VARCHAR DEFAULT 'user',
                fullname VARCHAR,
                mobile VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """))
        
        print("✅ Created users table")

async def create_test_user():
    """Create a test user for login testing"""
    print("👤 Creating test user...")
    
    # Test user credentials
    email = "test@example.com"
    password = "password123"
    fullname = "Test User"
    
    # Hash password
    hashed_password = bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    async with async_session() as db:
        # Check if user already exists
        result = await db.execute(text(
            "SELECT email FROM users WHERE email = :email"
        ), {"email": email})
        
        existing_user = result.fetchone()
        
        if existing_user:
            print(f"✅ Test user {email} already exists")
            return
        
        # Create user
        await db.execute(text("""
            INSERT INTO users (email, password_hash, role, fullname)
            VALUES (:email, :password_hash, :role, :fullname)
        """), {
            "email": email,
            "password_hash": hashed_password,
            "role": "user",
            "fullname": fullname
        })
        
        await db.commit()
        
        print(f"✅ Created test user: {email} / {password}")

async def verify_setup():
    """Verify database setup and user creation"""
    print("🔍 Verifying setup...")
    
    async with async_session() as db:
        try:
            # Check user count
            result = await db.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            print(f"✅ Users in database: {user_count}")
            
            # Test login with created user
            result = await db.execute(text(
                "SELECT email, password_hash FROM users WHERE email = :email"
            ), {"email": "test@example.com"})
            
            user = result.fetchone()
            
            if user:
                # Test password verification
                test_password = "password123"
                password_valid = bcrypt.checkpw(
                    test_password.encode('utf-8'),
                    user[1].encode('utf-8')  # password_hash
                )
                print(f"✅ Password verification test: {'PASSED' if password_valid else 'FAILED'}")
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            raise

async def main():
    """Main function"""
    print("🚀 Starting simple login fix...")
    
    try:
        await create_minimal_tables()
        await create_test_user()
        await verify_setup()
        
        print("\n🎉 Simple login setup completed successfully!")
        print("\n📋 Test credentials:")
        print("   Email: test@example.com")
        print("   Password: password123")
        print("\nYou can now test the login functionality.")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())