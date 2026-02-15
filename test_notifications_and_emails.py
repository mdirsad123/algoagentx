#!/usr/bin/env python3
"""
Test script for notifications and email functionality for Strategy Requests
"""

import asyncio
import httpx
import json
from uuid import uuid4

# Configuration
BASE_URL = "http://localhost:8000"
USER_TOKEN = "your_user_jwt_token_here"    # Replace with actual user token
ADMIN_TOKEN = "your_admin_jwt_token_here"  # Replace with actual admin token

async def test_notifications_and_emails():
    """Test notifications and email functionality"""
    
    async with httpx.AsyncClient() as client:
        user_headers = {"Authorization": f"Bearer {USER_TOKEN}"}
        admin_headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        
        print("=== Testing Notifications and Email Functionality ===\n")
        
        # Test 1: Create strategy request (should trigger admin notifications)
        print("1. Testing strategy request creation with notifications...")
        try:
            request_data = {
                "title": "Test Strategy Request",
                "strategy_type": "trend",
                "market": "equity",
                "timeframe": "1d",
                "indicators": {"sma": {"period": 20}},
                "entry_rules": "Price crosses above SMA",
                "exit_rules": "Price crosses below SMA",
                "risk_rules": "Stop loss 2%",
                "notes": "Test request for notifications"
            }
            
            response = await client.post(
                f"{BASE_URL}/api/v1/strategy-requests",
                json=request_data,
                headers=user_headers
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                request_result = response.json()
                request_id = request_result["id"]
                print(f"   Request created: {request_id}")
                
                # Check if admin notifications were created
                print("   Checking for admin notifications...")
                admin_notifications_response = await client.get(
                    f"{BASE_URL}/api/v1/notifications?unread_only=true",
                    headers=admin_headers
                )
                
                if admin_notifications_response.status_code == 200:
                    notifications = admin_notifications_response.json()
                    strategy_request_notifications = [
                        n for n in notifications 
                        if n.get("type") == "STRATEGY_REQUEST"
                    ]
                    print(f"   Found {len(strategy_request_notifications)} STRATEGY_REQUEST notifications")
                    if strategy_request_notifications:
                        print(f"   Notification: {strategy_request_notifications[0]['message']}")
                
            else:
                print(f"   Response: {response.json()}")
                
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 2: Get user notifications (should be empty initially)
        print("\n2. Testing user notifications...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/notifications?unread_only=true",
                headers=user_headers
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                notifications = response.json()
                print(f"   User has {len(notifications)} unread notifications")
            else:
                print(f"   Response: {response.json()}")
                
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 3: Deploy strategy request (should trigger user notification)
        print("\n3. Testing strategy deployment with notifications...")
        if 'request_id' in locals():
            try:
                update_data = {
                    "status": "DEPLOYED",
                    "admin_notes": "Strategy reviewed and deployed",
                    "assigned_to": "admin_user"
                }
                
                response = await client.patch(
                    f"{BASE_URL}/api/v1/admin/strategy-requests/{request_id}",
                    json=update_data,
                    headers=admin_headers
                )
                
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    print("   Strategy deployed successfully!")
                    
                    # Check if user notification was created
                    print("   Checking for user deployment notification...")
                    user_notifications_response = await client.get(
                        f"{BASE_URL}/api/v1/notifications?unread_only=true",
                        headers=user_headers
                    )
                    
                    if user_notifications_response.status_code == 200:
                        notifications = user_notifications_response.json()
                        deployment_notifications = [
                            n for n in notifications 
                            if n.get("type") == "STRATEGY_DEPLOYED"
                        ]
                        print(f"   Found {len(deployment_notifications)} STRATEGY_DEPLOYED notifications")
                        if deployment_notifications:
                            print(f"   Notification: {deployment_notifications[0]['message']}")
                    
                else:
                    print(f"   Response: {response.json()}")
                    
            except Exception as e:
                print(f"   Error: {e}")
        else:
            print("   Skipping - no request ID available")
        
        # Test 4: Check all notifications for user
        print("\n4. Testing all user notifications...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/notifications",
                headers=user_headers
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                notifications = response.json()
                print(f"   User has {len(notifications)} total notifications")
                for notification in notifications:
                    print(f"   - {notification['type']}: {notification['message']}")
            else:
                print(f"   Response: {response.json()}")
                
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 5: Check all notifications for admin
        print("\n5. Testing all admin notifications...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/notifications",
                headers=admin_headers
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                notifications = response.json()
                print(f"   Admin has {len(notifications)} total notifications")
                for notification in notifications:
                    print(f"   - {notification['type']}: {notification['message']}")
            else:
                print(f"   Response: {response.json()}")
                
        except Exception as e:
            print(f"   Error: {e}")
        
        print("\n=== Test completed ===")
        print("\nNote: Email functionality requires:")
        print("- SMTP environment variables configured")
        print("- ADMIN_NOTIFY_EMAILS environment variable with comma-separated admin emails")
        print("- Valid SMTP credentials for sending emails")

if __name__ == "__main__":
    asyncio.run(test_notifications_and_emails())