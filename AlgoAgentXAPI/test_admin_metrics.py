"""
Test for the enhanced /api/v1/admin/metrics endpoint
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import async_session, Base
from app.db.models.users import User
from app.db.models.payments import Payment
from app.db.models.user_subscriptions import UserSubscription
from app.db.models.credit_transactions import CreditTransaction
from app.db.models.job_status import JobStatus
from app.db.models.notifications import Notification
from app.db.models.strategies import Strategy
from app.db.models.performance_metrics import PerformanceMetric
from app.core.security import create_access_token
import uuid
import bcrypt
from datetime import datetime, timedelta

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
    admin_email = "admin@example.com"
    admin_password = "adminpassword123"
    
    hashed_password = bcrypt.hashpw(
        admin_password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')
    
    user = User(
        id=str(uuid.uuid4()),
        email=admin_email,
        password_hash=hashed_password,
        role="admin",
        fullname="Admin User"
    )
    
    async with TestAsyncSessionLocal() as session:
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return user, admin_password

@pytest.fixture
async def test_data():
    """Create test data for metrics calculation."""
    async with TestAsyncSessionLocal() as session:
        # Create users
        users = []
        for i in range(10):
            user = User(
                id=str(uuid.uuid4()),
                email=f"user{i}@example.com",
                password_hash="hashed_password",
                role="user",
                fullname=f"User {i}",
                is_active=(i % 2 == 0)  # Half active, half inactive
            )
            users.append(user)
            session.add(user)
        
        # Create payments
        payments = []
        for i in range(15):
            payment = Payment(
                id=uuid.uuid4(),
                user_id=users[i % 10].id,
                provider="RAZORPAY",
                purpose="SUBSCRIPTION",
                amount_inr=1000 + i * 100,
                status="PAID" if i < 10 else "FAILED",
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            payments.append(payment)
            session.add(payment)
        
        # Create subscriptions
        subscriptions = []
        for i in range(8):
            subscription = UserSubscription(
                id=uuid.uuid4(),
                user_id=users[i].id,
                plan_id=uuid.uuid4(),
                status="ACTIVE" if i < 5 else "EXPIRED",
                start_at=datetime.utcnow() - timedelta(days=30),
                end_at=datetime.utcnow() + timedelta(days=30 if i < 5 else -1)
            )
            subscriptions.append(subscription)
            session.add(subscription)
        
        # Create credit transactions
        credit_txns = []
        for i in range(20):
            txn = CreditTransaction(
                id=str(uuid.uuid4()),
                user_id=users[i % 10].id,
                credits=100 + i * 10,
                type="CREDIT" if i < 10 else "DEBIT",
                reason="Test credits" if i < 10 else "AI screener usage",
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            credit_txns.append(txn)
            session.add(txn)
        
        # Create job statuses (AI screener jobs)
        jobs = []
        for i in range(12):
            job = JobStatus(
                id=str(uuid.uuid4()),
                user_id=users[i % 10].id,
                job_type="ai_screener",
                status="completed" if i < 8 else "failed",
                progress=100 if i < 8 else 0,
                message="Test job",
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            jobs.append(job)
            session.add(job)
        
        # Create notifications (support tickets)
        notifications = []
        for i in range(5):
            notification = Notification(
                id=str(uuid.uuid4()),
                user_id=users[i].id,
                title=f"Test notification {i}",
                message="Test message",
                status="unread" if i < 3 else "read",
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            notifications.append(notification)
            session.add(notification)
        
        # Create strategies
        strategies = []
        for i in range(3):
            strategy = Strategy(
                id=str(uuid.uuid4()),
                user_id=users[i].id,
                name=f"Test Strategy {i}",
                description="Test strategy",
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            strategies.append(strategy)
            session.add(strategy)
        
        # Create performance metrics (backtests)
        backtests = []
        for i in range(8):
            backtest = PerformanceMetric(
                id=str(uuid.uuid4()),
                strategy_id=strategies[i % 3].id,
                user_id=users[i].id,
                total_return=10.5 + i,
                sharpe_ratio=1.2 + i * 0.1,
                max_drawdown=5.0 + i,
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            backtests.append(backtest)
            session.add(backtest)
        
        await session.commit()
        
        return {
            "users": users,
            "payments": payments,
            "subscriptions": subscriptions,
            "credit_txns": credit_txns,
            "jobs": jobs,
            "notifications": notifications,
            "strategies": strategies,
            "backtests": backtests
        }

def test_admin_metrics_endpoint(admin_user, test_data):
    """Test the comprehensive admin metrics endpoint."""
    client = TestClient(app)
    
    # Get admin user data
    user, password = admin_user
    
    # Login to get token
    login_response = client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": password
    })
    
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Test admin metrics endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/admin/metrics", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify structure and required fields
    assert "users" in data
    assert "payments" in data
    assert "subscriptions" in data
    assert "credits" in data
    assert "strategies" in data
    assert "backtests" in data
    assert "ai_screener_jobs" in data
    assert "support_tickets" in data
    assert "recent_activity" in data
    assert "generated_at" in data
    
    # Verify user metrics
    assert data["users"]["total"] == 10
    assert data["users"]["active"] == 5  # Half of users are active
    assert "recent" in data["users"]
    
    # Verify payment metrics
    assert data["payments"]["total"] == 15
    assert data["payments"]["paid"] == 10
    assert data["payments"]["failed"] == 5
    assert data["payments"]["revenue_total"] > 0
    
    # Verify subscription metrics
    assert data["subscriptions"]["total"] == 8
    assert data["subscriptions"]["active"] == 5
    
    # Verify credit metrics
    assert data["credits"]["total_issued"] > 0
    assert data["credits"]["used"] > 0
    assert data["credits"]["available"] >= 0
    
    # Verify strategy metrics
    assert data["strategies"]["total"] == 3
    
    # Verify backtest metrics
    assert data["backtests"]["total"] == 8
    
    # Verify AI screener job metrics
    assert data["ai_screener_jobs"]["total"] == 12
    assert data["ai_screener_jobs"]["completed"] == 8
    assert data["ai_screener_jobs"]["failed"] == 4
    assert "recent" in data["ai_screener_jobs"]
    
    # Verify support ticket metrics
    assert data["support_tickets"]["total"] == 5
    assert data["support_tickets"]["unread"] == 3
    
    # Verify recent activity
    assert "recent_users" in data["recent_activity"]
    assert "recent_payments" in data["recent_activity"]
    assert "recent_jobs" in data["recent_activity"]

def test_admin_metrics_unauthorized():
    """Test that unauthorized users cannot access admin metrics."""
    client = TestClient(app)
    
    # Test without token
    response = client.get("/api/v1/admin/metrics")
    assert response.status_code == 401
    
    # Test with invalid token
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/v1/admin/metrics", headers=headers)
    assert response.status_code == 401

def test_admin_metrics_non_admin_user(admin_user, test_data):
    """Test that regular users cannot access admin metrics."""
    client = TestClient(app)
    
    # Create a regular user
    regular_user = User(
        id=str(uuid.uuid4()),
        email="regular@example.com",
        password_hash=bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        role="user",
        fullname="Regular User"
    )
    
    async def create_regular_user():
        async with TestAsyncSessionLocal() as session:
            session.add(regular_user)
            await session.commit()
            await session.refresh(regular_user)
        return regular_user
    
    regular_user = asyncio.run(create_regular_user())
    
    # Login as regular user
    login_response = client.post("/api/v1/auth/login", json={
        "email": regular_user.email,
        "password": "password123"
    })
    
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Test admin metrics endpoint with regular user token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/admin/metrics", headers=headers)
    
    # Should be forbidden
    assert response.status_code == 403
    data = response.json()
    assert "Admin access required" in data["detail"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])