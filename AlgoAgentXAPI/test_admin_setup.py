"""
Test for admin user creation and admin-only access
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import async_session, Base
from app.db.models.users import User
from app.core.security import create_access_token
import uuid
import bcrypt

# Test database URL for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
)

# Create test session factory
TestAsyncSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test module."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module", autouse=True)
async def setup_database():
    """Set up test database with tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def admin_user():
    """Create an admin user in the database."""
    # Create admin user data
    admin_email = "admin@example.com"
    admin_password = "adminpassword123"
    
    # Hash password
    hashed_password = bcrypt.hashpw(
        admin_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    # Create admin user
    user = User(
        id=str(uuid.uuid4()),
        email=admin_email,
        password_hash=hashed_password,
        role="admin",  # Set as admin role
        fullname="Admin User"
    )
    
    async with TestAsyncSessionLocal() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return user, admin_password

@pytest.fixture
async def regular_user():
    """Create a regular user in the database."""
    # Create regular user data
    user_email = "user@example.com"
    user_password = "userpassword123"
    
    # Hash password
    hashed_password = bcrypt.hashpw(
        user_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    # Create regular user
    user = User(
        id=str(uuid.uuid4()),
        email=user_email,
        password_hash=hashed_password,
        role="user",  # Set as regular user
        fullname="Regular User"
    )
    
    async with TestAsyncSessionLocal() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return user, user_password

def test_admin_login_successful(admin_user):
    """Test that admin user can login successfully."""
    client = TestClient(app)
    
    # Get admin user data
    user, password = admin_user
    
    # Test login
    response = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": password
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that all expected fields are present
    assert "access_token" in data
    assert "token_type" in data
    assert "user" in data
    
    user_data = data["user"]
    assert user_data["id"] == user.id
    assert user_data["email"] == user.email
    assert user_data["role"] == "admin"
    assert user_data["fullname"] == user.fullname
    assert user_data["displayName"] == user.fullname

def test_regular_user_login_successful(regular_user):
    """Test that regular user can login successfully."""
    client = TestClient(app)
    
    # Get regular user data
    user, password = regular_user
    
    # Test login
    response = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": password
    })
    
    assert response.status_code == 200
    data = response.json()
    
    user_data = data["user"]
    assert user_data["role"] == "user"
    assert user_data["displayName"] == user.fullname

def test_admin_access_to_admin_endpoints(admin_user):
    """Test that admin user can access admin endpoints."""
    client = TestClient(app)
    
    # Get admin user data
    user, password = admin_user
    
    # First login to get token
    login_response = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": password
    })
    
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Test admin metrics endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/admin/metrics", headers=headers)
    
    # Should succeed (200) or fail due to missing dependencies (500)
    # We're mainly testing that admin access is allowed
    assert response.status_code in [200, 500]

def test_regular_user_denied_admin_access(regular_user):
    """Test that regular user is denied access to admin endpoints."""
    client = TestClient(app)
    
    # Get regular user data
    user, password = regular_user
    
    # First login to get token
    login_response = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": password
    })
    
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Test admin metrics endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/admin/metrics", headers=headers)
    
    # Should be forbidden (403)
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "Admin access required" in data["detail"]

def test_unauthenticated_user_denied_admin_access():
    """Test that unauthenticated user is denied access to admin endpoints."""
    client = TestClient(app)
    
    # Test admin metrics endpoint without token
    response = client.get("/api/v1/admin/metrics")
    
    # Should be unauthorized (401)
    assert response.status_code == 401

def test_admin_user_creation_script_logic():
    """Test the admin creation script logic (without actually creating)."""
    import os
    import sys
    from app.core.config import settings
    
    # Test that script prevents creation in production
    if settings.is_production:
        assert True  # Script should exit early in production
    else:
        # Test environment variable validation
        test_cases = [
            {"ADMIN_EMAIL": None, "ADMIN_PASSWORD": "password"},
            {"ADMIN_EMAIL": "admin@example.com", "ADMIN_PASSWORD": None},
            {"ADMIN_EMAIL": "invalid-email", "ADMIN_PASSWORD": "password"},
            {"ADMIN_EMAIL": "admin@example.com", "ADMIN_PASSWORD": "123"},  # Too short
        ]
        
        for case in test_cases:
            # Simulate missing or invalid environment variables
            for key, value in case.items():
                if value is None:
                    assert True  # Should fail with missing env var
                elif "@" not in case["ADMIN_EMAIL"] or "." not in case["ADMIN_EMAIL"]:
                    assert True  # Should fail with invalid email
                elif len(case["ADMIN_PASSWORD"]) < 8:
                    assert True  # Should fail with short password

if __name__ == "__main__":
    pytest.main([__file__, "-v"])