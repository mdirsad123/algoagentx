#!/usr/bin/env python3
"""
CLI script to create an admin user for AlgoAgentX.
Usage: python scripts/create_admin.py
Environment variables required:
- ADMIN_EMAIL: Email address for the admin user
- ADMIN_PASSWORD: Password for the admin user
"""

import os
import sys
import asyncio
import bcrypt
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.models.users import User
from app.core.config import settings

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

async def create_admin_user():
    """Create an admin user from environment variables."""
    
    # Check if we're in production
    if settings.is_production:
        print("❌ ERROR: Admin creation script cannot be run in production environment")
        print("Use a secure method to create admin users in production.")
        return False
    
    # Get admin credentials from environment
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    
    if not admin_email or not admin_password:
        print("❌ ERROR: Missing required environment variables")
        print("Please set ADMIN_EMAIL and ADMIN_PASSWORD")
        print("Example: ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=securepassword123 python scripts/create_admin.py")
        return False
    
    # Validate email format (basic check)
    if "@" not in admin_email or "." not in admin_email:
        print(f"❌ ERROR: Invalid email format: {admin_email}")
        return False
    
    # Validate password strength
    if len(admin_password) < 8:
        print("❌ ERROR: Password must be at least 8 characters long")
        return False
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if admin already exists
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.email == admin_email)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"⚠️  WARNING: User with email {admin_email} already exists")
                print(f"   User ID: {existing_user.id}")
                print(f"   Role: {existing_user.role}")
                return False
            
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
                role="admin",  # Set as admin role
                fullname="Admin User",
                mobile=None
            )
            
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            
            print("✅ Admin user created successfully!")
            print(f"   Email: {admin_user.email}")
            print(f"   User ID: {admin_user.id}")
            print(f"   Role: {admin_user.role}")
            print(f"   Created at: {admin_user.created_at}")
            print("")
            print("⚠️  SECURITY REMINDER:")
            print("   - Store the admin credentials securely")
            print("   - Consider changing the default fullname")
            print("   - This script should only be used in development/testing")
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR: Failed to create admin user: {e}")
            await session.rollback()
            return False

if __name__ == "__main__":
    print("🚀 AlgoAgentX Admin User Creation Script")
    print("=" * 50)
    
    # Check if running in production
    if settings.is_production:
        print("❌ ERROR: This script cannot be run in production")
        sys.exit(1)
    
    success = asyncio.run(create_admin_user())
    
    if success:
        print("\n✅ Admin user creation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Admin user creation failed!")
        sys.exit(1)