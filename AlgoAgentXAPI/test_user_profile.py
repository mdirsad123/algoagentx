"""
Test for GET /api/v1/users/me endpoint and enhanced login response
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
async def test_user():
    """Create a test user in the database."""
    # Create test user data
    test_email = "test@example.com"
    test_password = "testpassword123"
    test_fullname = "Test User"
    
    # Hash password
    hashed_password = bcrypt.hashpw(
        test_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    # Create user
    user = User(
        id=str(uuid.uuid4()),
        email=test_email,
        password_hash=hashed_password,
        role="user",
        fullname=test_fullname
    )
    
    async with TestAsyncSessionLocal() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return user, test_password

def test_login_returns_display_name(test_user):
    """Test that login endpoint returns displayName field."""
    client = TestClient(app)
    
    # Get test user data
    user, password = test_user
    
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
    assert user_data["role"] == user.role
    assert user_data["fullname"] == user.fullname
    assert user_data["displayName"] == user.fullname  # Should be fullname when available

def test_login_returns_email_as_display_name_when_no_fullname():
    """Test that login returns email as displayName when fullname is None."""
    client = TestClient(app)
    
    # Create user without fullname
    test_email = "no_name@example.com"
    test_password = "testpassword123"
    
    hashed_password = bcrypt.hashpw(
        test_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    user = User(
        id=str(uuid.uuid4()),
        email=test_email,
        password_hash=hashed_password,
        role="user",
        fullname=None  # No fullname
    )
    
    async def create_user():
        async with TestAsyncSessionLocal() as session:
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user
    
    user = asyncio.run(create_user())
    
    # Test login
    response = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": test_password
    })
    
    assert response.status_code == 200
    data = response.json()
    
    user_data = data["user"]
    assert user_data["displayName"] == user.email  # Should be email when fullname is None

def test_get_current_user_profile(test_user):
    """Test GET /api/v1/users/me endpoint."""
    client = TestClient(app)
    
    # Get test user data
    user, password = test_user
    
    # First login to get token
    login_response = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": password
    })
    
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Test GET /users/me with token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/users/me", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that all expected fields are present
    assert data["id"] == user.id
    assert data["email"] == user.email
    assert data["role"] == user.role
    assert data["full_name"] == user.fullname
    assert "created_at" in data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])