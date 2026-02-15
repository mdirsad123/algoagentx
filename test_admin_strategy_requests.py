#!/usr/bin/env python3
"""
Test script for admin strategy request management APIs
"""

import asyncio
import httpx
import json
from uuid import uuid4

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = "your_admin_jwt_token_here"  # Replace with actual admin token
USER_TOKEN = "your_user_jwt_token_here"    # Replace with actual user token

async def test_admin_endpoints():
    """Test all admin strategy request endpoints"""
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        user_headers = {"Authorization": f"Bearer {USER_TOKEN}"}
        
        print("=== Testing Admin Strategy Request Management APIs ===\n")
        
        # Test 1: List strategy requests (should fail without admin role)
        print("1. Testing list strategy requests without admin role...")
        try:
            response = await client.get(f"{BASE_URL}/api/v1/admin/strategy-requests", headers=user_headers)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 2: List strategy requests (with admin role)
        print("\n2. Testing list strategy requests with admin role...")
        try:
            response = await client.get(f"{BASE_URL}/api/v1/admin/strategy-requests", headers=headers)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                requests = response.json()
                print(f"   Found {len(requests)} strategy requests")
                if requests:
                    print(f"   First request: {requests[0]}")
            else:
                print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 3: List strategy requests with status filter
        print("\n3. Testing list strategy requests with status filter...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/admin/strategy-requests?status=UNDER_DEVELOPMENT", 
                headers=headers
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                requests = response.json()
                print(f"   Found {len(requests)} requests with status UNDER_DEVELOPMENT")
            else:
                print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test 4: Get specific strategy request detail
        print("\n4. Testing get strategy request detail...")
        # Use a known request ID or the first one from the list
        test_request_id = "your_test_request_id_here"  # Replace with actual UUID
        if test_request_id != "your_test_request_id_here":
            try:
                response = await client.get(
                    f"{BASE_URL}/api/v1/admin/strategy-requests/{test_request_id}", 
                    headers=headers
                )
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    request_detail = response.json()
                    print(f"   Request detail: {json.dumps(request_detail, indent=2)}")
                else:
                    print(f"   Response: {response.json()}")
            except Exception as e:
                print(f"   Error: {e}")
        else:
            print("   Skipping - no test request ID provided")
        
        # Test 5: Update strategy request status to DEPLOYED
        print("\n5. Testing update strategy request status to DEPLOYED...")
        if test_request_id != "your_test_request_id_here":
            try:
                update_data = {
                    "status": "DEPLOYED",
                    "admin_notes": "Strategy has been reviewed and deployed",
                    "assigned_to": "admin_user"
                }
                
                response = await client.patch(
                    f"{BASE_URL}/api/v1/admin/strategy-requests/{test_request_id}",
                    json=update_data,
                    headers=headers
                )
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    print(f"   Response: {response.json()}")
                    print("   Strategy request successfully deployed!")
                else:
                    print(f"   Response: {response.json()}")
            except Exception as e:
                print(f"   Error: {e}")
        else:
            print("   Skipping - no test request ID provided")
        
        # Test 6: Update strategy request with existing strategy ID
        print("\n6. Testing update strategy request with existing strategy ID...")
        if test_request_id != "your_test_request_id_here":
            try:
                update_data = {
                    "status": "DEPLOYED",
                    "admin_notes": "Using existing strategy",
                    "deployed_strategy_id": "your_existing_strategy_id_here"  # Replace with actual UUID
                }
                
                response = await client.patch(
                    f"{BASE_URL}/api/v1/admin/strategy-requests/{test_request_id}",
                    json=update_data,
                    headers=headers
                )
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    print(f"   Response: {response.json()}")
                else:
                    print(f"   Response: {response.json()}")
            except Exception as e:
                print(f"   Error: {e}")
        else:
            print("   Skipping - no test request ID provided")
        
        print("\n=== Test completed ===")

if __name__ == "__main__":
    asyncio.run(test_admin_endpoints())