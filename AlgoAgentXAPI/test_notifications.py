#!/usr/bin/env python3
"""
Test script for notification system implementation.
This script tests the notification functionality without running the full application.
"""

import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.models.notifications import Notification
from app.schemas.notifications import NotificationCreate, MarkReadRequest
from app.services.notifications import NotificationService
from app.services.notification_manager import NotificationManager, notify_credits_low_background, notify_payment_success_background, notify_backtest_done_background


async def test_notification_system():
    """Test the notification system implementation."""
    print("🧪 Testing Notification System Implementation...")
    
    # Create async engine and session
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        # Test 1: Check if notifications table exists
        print("\n1️⃣ Testing database connection and table existence...")
        async with async_session() as session:
            # Check if notifications table exists
            result = await session.execute(text("SELECT to_regclass('public.notifications')"))
            table_exists = result.scalar()
            if table_exists:
                print("✅ Notifications table exists in database")
            else:
                print("❌ Notifications table does not exist. Please run migrations first.")
                return False
        
        # Test 2: Test notification creation
        print("\n2️⃣ Testing notification creation...")
        async with async_session() as session:
            service = NotificationService(session)
            
            # Create a test notification
            notification_data = NotificationCreate(
                type="TEST_NOTIFICATION",
                title="Test Notification",
                message="This is a test notification for system verification.",
                metadata={"test": True, "timestamp": "2026-02-06T20:00:00Z"}
            )
            
            try:
                created_notification = await service.create_notification("test_user_123", notification_data)
                print(f"✅ Notification created successfully: {created_notification.id}")
                print(f"   Type: {created_notification.type}")
                print(f"   Title: {created_notification.title}")
                print(f"   Message: {created_notification.message}")
                print(f"   Created at: {created_notification.created_at}")
            except Exception as e:
                print(f"❌ Failed to create notification: {e}")
                return False
        
        # Test 3: Test getting notifications
        print("\n3️⃣ Testing notification retrieval...")
        async with async_session() as session:
            service = NotificationService(session)
            
            try:
                notifications = await service.get_notifications("test_user_123", skip=0, limit=10)
                print(f"✅ Retrieved {len(notifications)} notifications")
                for i, notification in enumerate(notifications):
                    print(f"   [{i+1}] {notification.type}: {notification.title}")
            except Exception as e:
                print(f"❌ Failed to retrieve notifications: {e}")
                return False
        
        # Test 4: Test marking notifications as read
        print("\n4️⃣ Testing mark as read functionality...")
        async with async_session() as session:
            service = NotificationService(session)
            
            # Get the test notification ID
            notifications = await service.get_notifications("test_user_123", skip=0, limit=1)
            if notifications:
                notification_id = notifications[0].id
                
                try:
                    mark_request = MarkReadRequest(notification_ids=[notification_id])
                    success = await service.mark_notifications_read(mark_request)
                    if success:
                        print(f"✅ Successfully marked notification {notification_id} as read")
                    else:
                        print("❌ Failed to mark notification as read")
                        return False
                except Exception as e:
                    print(f"❌ Failed to mark notification as read: {e}")
                    return False
            else:
                print("❌ No notifications found to test mark as read")
                return False
        
        # Test 5: Test unread count
        print("\n5️⃣ Testing unread count...")
        async with async_session() as session:
            service = NotificationService(session)
            
            try:
                unread_count = await service.get_unread_count("test_user_123")
                print(f"✅ Unread count: {unread_count}")
            except Exception as e:
                print(f"❌ Failed to get unread count: {e}")
                return False
        
        # Test 6: Test notification manager
        print("\n6️⃣ Testing notification manager...")
        async with async_session() as session:
            manager = NotificationManager(session)
            
            # Test creating a notification through manager
            try:
                await manager.create_notification_safe(
                    user_id="test_user_456",
                    notification_type="TEST_MANAGER",
                    title="Test from Manager",
                    message="This notification was created through the notification manager.",
                    metadata={"manager_test": True}
                )
                print("✅ Notification manager created notification successfully")
            except Exception as e:
                print(f"❌ Notification manager failed: {e}")
                return False
        
        print("\n🎉 All notification system tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False
    finally:
        await engine.dispose()


async def cleanup_test_data():
    """Clean up test data created during testing."""
    print("\n🧹 Cleaning up test data...")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        async with async_session() as session:
            # Delete test notifications
            await session.execute(text("DELETE FROM notifications WHERE user_id LIKE 'test_user_%'"))
            await session.commit()
            print("✅ Test data cleaned up successfully")
    except Exception as e:
        print(f"❌ Failed to clean up test data: {e}")
    finally:
        await engine.dispose()


async def main():
    """Main test function."""
    print("🚀 Starting Notification System Tests...")
    print("=" * 50)
    
    # Run tests
    success = await test_notification_system()
    
    if success:
        print("\n✅ All tests passed! Notification system is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
    
    # Clean up test data
    await cleanup_test_data()
    
    print("\n🏁 Test execution completed.")


if __name__ == "__main__":
    asyncio.run(main())