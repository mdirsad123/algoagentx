#!/usr/bin/env python3
"""
Test script to verify notification API endpoints are working correctly.
This script tests the notification system without requiring a full frontend build.
"""

import requests
import json
import uuid
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer test_token"  # This would need to be a real token in production
}

def test_notification_endpoints():
    """Test all notification API endpoints"""
    
    print("🧪 Testing Notification API Endpoints")
    print("=" * 50)
    
    # Test 1: Get unread count
    print("\n1. Testing GET /notifications/unread-count")
    try:
        response = requests.get(f"{BASE_URL}/notifications/unread-count", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Get notifications
    print("\n2. Testing GET /notifications")
    try:
        response = requests.get(f"{BASE_URL}/notifications?limit=10", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Found {len(data)} notifications")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Create a test notification (if endpoint exists)
    print("\n3. Testing POST /notifications (create)")
    test_notification = {
        "type": "TEST",
        "title": "Test Notification",
        "message": "This is a test notification created by the test script",
        "metadata": {"test": True, "timestamp": datetime.now().isoformat()}
    }
    
    try:
        response = requests.post(f"{BASE_URL}/notifications", 
                               json=test_notification, 
                               headers=HEADERS)
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ Success: Created notification {data.get('id')}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Mark all as read
    print("\n4. Testing POST /notifications/mark-all-read")
    try:
        response = requests.post(f"{BASE_URL}/notifications/mark-all-read", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Notification API Test Complete")
    print("\nNote: Some tests may fail if:")
    print("- Backend server is not running")
    print("- Authentication is required")
    print("- Database is not properly configured")

if __name__ == "__main__":
    test_notification_endpoints()