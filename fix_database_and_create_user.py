#!/usr/bin/env python3
"""
Fix database tables and create test user
"""

import asyncio
import sys
import os
import bcrypt

# Add the API directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "AlgoAgentXAPI"))

from sqlalchemy import text
from AlgoAgentXAPI.app.db.session import async_session
from AlgoAgentXAPI.app.db.base import Base
from AlgoAgentXAPI.app.db.session import engine
from AlgoAgentXAPI.app.db.models import User

async def recreate_tables():
    """Drop and recreate all tables to fix foreign key issues"""
    print("🔄 Recreating database tables...")
    
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)
        print("✅ Dropped all tables")
        
        # Create all tables (with fixed foreign keys)
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Created all tables with fixed foreign keys")

async def create_test_user():
    """Create a test user for login testing"""
    print("👤 Creating test user...")
    
    # Test user credentials
    email = "test@example.com"
    password = "password123"
    fullname = "Test User"
    
    async with async_session() as db:
        # Check if user already exists
        from sqlalchemy import select
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"✅ Test user {email} already exists")
            return
        
        # Hash password
        hashed_password = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Create user
        new_user = User(
            email=email,
            password_hash=hashed_password,
            role="user",
            fullname=fullname
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        print(f"✅ Created test user: {email} / {password}")
        print(f"   User ID: {new_user.id}")
        print(f"   Role: {new_user.role}")

async def verify_setup():
    """Verify database setup and user creation"""
    print("🔍 Verifying setup...")
    
    async with async_session() as db:
        try:
            # Check tables exist
            result = await db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"✅ Tables created: {', '.join(tables)}")
            
            # Check user count
            result = await db.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar_one()
            print(f"✅ Users in database: {user_count}")
            
            # Test login with created user
            from sqlalchemy import select
            stmt = select(User).where(User.email == "test@example.com")
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                # Test password verification
                test_password = "password123"
                password_valid = bcrypt.checkpw(
                    test_password.encode('utf-8'),
                    user.password_hash.encode('utf-8')
                )
                print(f"✅ Password verification test: {'PASSED' if password_valid else 'FAILED'}")
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            raise

async def main():
    """Main function"""
    print("🚀 Starting database fix and user creation...")
    
    try:
        await recreate_tables()
        await create_test_user()
        await verify_setup()
        
        print("\n🎉 Database setup completed successfully!")
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