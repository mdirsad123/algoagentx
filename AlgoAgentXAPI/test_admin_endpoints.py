#!/usr/bin/env python3
"""
Comprehensive test script to verify all admin endpoints work correctly.
This tests the fixes for user not found and user creation issues.
"""
import asyncio
from sqlalchemy import cast, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session
from app.db.models import User, CreditTransaction, Payment, UserSubscription, Plan
from app.db.compat import as_uuid_or_str, column_text, table_has_column
import bcrypt


async def test_user_creation():
    """Test creating a new user."""
    try:
        async with async_session() as db:
            print("Testing user creation...")
            
            # Test creating a user
            password_hash = bcrypt.hashpw("testpassword123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            user = User(
                email="test@example.com",
                password_hash=password_hash,
                role="user",
                fullname="Test User",
                mobile="1234567890",
            )
            db.add(user)
            await db.flush()
            
            # Ensure user credit row is created
            from app.api.v1.admin import _ensure_user_credit_row
            await _ensure_user_credit_row(db, str(user.id))
            
            await db.commit()
            await db.refresh(user)
            
            print(f"✅ User created successfully: {user.email}")
            return user
    except Exception as e:
        print(f"❌ User creation failed: {e}")
        return None


async def test_user_retrieval(user_id):
    """Test retrieving a user by ID."""
    try:
        async with async_session() as db:
            print(f"Testing user retrieval for ID: {user_id}")
            
            user = (await db.execute(select(User).where(column_text(User.id) == str(user_id)))).scalar_one_or_none()
            if not user:
                print("❌ User not found")
                return False
            
            print(f"✅ User found: {user.email}")
            
            # Test the _user_is_active_value function
            from app.api.v1.admin import _user_is_active_value
            is_active = await _user_is_active_value(db, user)
            print(f"✅ User is_active value: {is_active}")
            
            return True
    except Exception as e:
        print(f"❌ User retrieval failed: {e}")
        return False


async def test_admin_users_endpoint():
    """Test the admin users endpoint logic."""
    try:
        async with async_session() as db:
            print("Testing admin users endpoint...")
            
            # Test the main query
            query = select(User)
            count_query = select(func.count()).select_from(User)
            
            rows = (await db.execute(query.order_by(User.created_at.desc()).limit(20))).scalars().all()
            total = (await db.execute(count_query)).scalar() or 0
            
            print(f"Found {len(rows)} users out of {total} total")
            
            if not rows:
                print("No users found, but that's okay")
                return True
            
            # Test the problematic functions
            from app.api.v1.admin import _user_is_active_value, _get_credit_balance_map, _get_subscription_map
            
            user_ids = [str(row.id) for row in rows]
            balances = await _get_credit_balance_map(db, user_ids)
            subs = await _get_subscription_map(db, user_ids)
            
            print("✅ Successfully processed user data")
            
            # Build the items list
            items = []
            for user in rows:
                uid = str(user.id)
                items.append(
                    {
                        "id": uid,
                        "email": user.email,
                        "role": user.role,
                        "is_active": await _user_is_active_value(db, user),
                        "fullname": user.fullname,
                        "mobile": user.mobile,
                        "plan": subs.get(uid, {}).get("plan", "free"),
                        "subscription_status": subs.get(uid, {}).get("status"),
                        "credits": balances.get(uid, 0),
                    }
                )
            
            print(f"✅ Successfully built {len(items)} user items")
            return True
    except Exception as e:
        print(f"❌ Admin users endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_admin_metrics():
    """Test the admin metrics endpoint logic."""
    try:
        async with async_session() as db:
            print("Testing admin metrics endpoint...")
            
            # Test user count
            total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
            print(f"Total users: {total_users}")
            
            # Test the table_has_column check
            has_is_active = await table_has_column(db, "users", "is_active")
            print(f"Has is_active column: {has_is_active}")
            
            if has_is_active:
                active_users = (await db.execute(text("SELECT COUNT(*) FROM users WHERE is_active = true"))).scalar() or 0
                print(f"Active users: {active_users}")
            else:
                print("Using fallback active users count")
            
            print("✅ Admin metrics endpoint test passed")
            return True
    except Exception as e:
        print(f"❌ Admin metrics endpoint test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("Starting comprehensive admin endpoints test...")
    print("=" * 50)
    
    all_passed = True
    
    # Test user creation
    user = await test_user_creation()
    if user:
        # Test user retrieval
        retrieval_passed = await test_user_retrieval(user.id)
        all_passed = all_passed and retrieval_passed
    else:
        all_passed = False
    
    print("-" * 30)
    
    # Test admin users endpoint
    users_passed = await test_admin_users_endpoint()
    all_passed = all_passed and users_passed
    
    print("-" * 30)
    
    # Test admin metrics endpoint
    metrics_passed = await test_admin_metrics()
    all_passed = all_passed and metrics_passed
    
    print("=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Admin endpoints should work correctly.")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())