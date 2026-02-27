#!/usr/bin/env python3
"""
Test admin login with the provided credentials.
If login fails, remove the existing user and recreate with the new password.
"""

import os
import sys
import asyncio
import bcrypt
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from AlgoAgentXAPI.app.db.models.users import User
from AlgoAgentXAPI.app.core.config import settings

# Create database engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
)

# Create session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def test_admin_login():
    """Test admin login with the provided credentials."""
    admin_email = "algoagentx@gmail.com"
    admin_password = "admin@123"
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if admin user exists
            result = await session.execute(
                select(User).where(User.email == admin_email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"ERROR: User with email {admin_email} does not exist")
                return False
            
            print(f"Found user: {user.email}")
            print(f"User ID: {user.id}")
            print(f"Role: {user.role}")
            
            # Test password
            password_bytes = admin_password.encode('utf-8')
            stored_hash = user.password_hash.strip()
            
            if bcrypt.checkpw(password_bytes, stored_hash.encode('utf-8')):
                print("✅ Login successful! Password is correct.")
                return True
            else:
                print("❌ Password is incorrect.")
                print("Removing existing user and recreating with new password...")
                return await recreate_admin_user(session, user)
                
        except Exception as e:
            print(f"ERROR: Failed to test login: {e}")
            return False

async def recreate_admin_user(session, existing_user):
    """Remove existing user and create new admin user with correct password."""
    try:
        # Delete existing user
        await session.delete(existing_user)
        await session.commit()
        print("✅ Existing user removed successfully.")
        
        # Create new admin user with correct password
        admin_email = "algoagentx@gmail.com"
        admin_password = "admin@123"
        
        # Hash the password
        hashed_password = bcrypt.hashpw(
            admin_password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Create admin user
        admin_user = User(
            id=str(uuid.uuid4()),
            email=admin_email,
            password_hash=hashed_password,
            role="admin",
            fullname="Admin User",
            mobile=None
        )
        
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)
        
        print("✅ New admin user created successfully!")
        print(f"   Email: {admin_user.email}")
        print(f"   User ID: {admin_user.id}")
        print(f"   Role: {admin_user.role}")
        print(f"   Password: {admin_password} (set as requested)")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to recreate admin user: {e}")
        await session.rollback()
        return False

if __name__ == "__main__":
    print("AlgoAgentX Admin Login Test")
    print("=" * 40)
    
    success = asyncio.run(test_admin_login())
    
    if success:
        print("\n✅ Admin login test completed successfully!")
        print("You can now login with:")
        print("   Email: algoagentx@gmail.com")
        print("   Password: admin@123")
    else:
        print("\n❌ Admin login test failed!")
    
    sys.exit(0 if success else 1)