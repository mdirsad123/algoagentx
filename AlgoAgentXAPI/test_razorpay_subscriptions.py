#!/usr/bin/env python3
"""
Test script for Razorpay subscriptions implementation.
This script tests the subscription endpoints and verifies the integration works correctly.
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any
import httpx
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings


class RazorpaySubscriptionTestClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.test_user_id = "test_user_123"
        self.test_plan_code = "PRO"
        self.test_billing_period = "MONTHLY"
        
    async def test_razorpay_config(self):
        """Test if Razorpay is configured for subscriptions."""
        print("Testing Razorpay subscription configuration...")
        
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/subscriptions/razorpay/config")
            if response.status_code == 200:
                config = response.json()
                print(f"✓ Razorpay subscription configured: {config}")
                return config
            else:
                print(f"✗ Failed to get config: {response.status_code}")
                return None
        except Exception as e:
            print(f"✗ Error testing config: {e}")
            return None
    
    async def test_get_plans(self):
        """Test getting available plans."""
        print("Testing get available plans...")
        
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/subscriptions/plans")
            if response.status_code == 200:
                plans = response.json()
                print(f"✓ Available plans: {len(plans.get('plans', {}))} plans")
                return plans
            else:
                print(f"✗ Failed to get plans: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ Error getting plans: {e}")
            return None
    
    async def test_create_subscription(self):
        """Test creating a Razorpay subscription."""
        print(f"Testing subscription creation for {self.test_plan_code} {self.test_billing_period}...")
        
        try:
            # Mock JWT token for testing (in real scenario, this would be a valid JWT)
            headers = {
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json"
            }
            
            payload = {
                "plan_code": self.test_plan_code,
                "billing_period": self.test_billing_period
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/subscriptions/razorpay/create",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                subscription_data = response.json()
                print(f"✓ Subscription created: {subscription_data}")
                return subscription_data
            else:
                print(f"✗ Failed to create subscription: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ Error creating subscription: {e}")
            return None
    
    async def test_get_subscription_status(self):
        """Test getting subscription status."""
        print("Testing subscription status retrieval...")
        
        try:
            headers = {
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json"
            }
            
            response = await self.client.get(
                f"{self.base_url}/api/v1/subscriptions/me",
                headers=headers
            )
            
            if response.status_code == 200:
                status_data = response.json()
                print(f"✓ Subscription status: {status_data}")
                return status_data
            else:
                print(f"✗ Failed to get subscription status: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ Error getting subscription status: {e}")
            return None
    
    async def test_subscription_webhook(self, payload: Dict[str, Any], signature: str):
        """Test subscription webhook handling."""
        print("Testing subscription webhook handling...")
        
        try:
            headers = {
                "X-Razorpay-Signature": signature,
                "Content-Type": "application/json"
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/subscriptions/razorpay/webhook",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Webhook processed: {result}")
                return result
            else:
                print(f"✗ Failed to process webhook: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ Error processing webhook: {e}")
            return None
    
    async def run_all_tests(self):
        """Run all tests."""
        print("=== Razorpay Subscriptions Test Suite ===")
        print(f"Base URL: {self.base_url}")
        print(f"Test User ID: {self.test_user_id}")
        print(f"Test Plan: {self.test_plan_code} {self.test_billing_period}")
        print()
        
        # Test 1: Check configuration
        config = await self.test_razorpay_config()
        if not config:
            print("Cannot proceed without Razorpay configuration")
            return False
        
        # Test 2: Get available plans
        plans = await self.test_get_plans()
        if not plans:
            print("Cannot proceed without plans")
            return False
        
        # Test 3: Create subscription (this would normally require a valid JWT)
        subscription_data = await self.test_create_subscription()
        if not subscription_data:
            print("Cannot proceed without subscription creation")
            return False
        
        # Test 4: Get subscription status
        status_data = await self.test_get_subscription_status()
        
        # Test 5: Test webhook (simulate subscription activated event)
        webhook_payload = {
            "event": "subscription.activated",
            "payload": {
                "subscription": {
                    "entity": {
                        "id": subscription_data.get("razorpay_subscription_id", "test_sub_123")
                    }
                }
            }
        }
        
        # Generate a fake signature for testing (in real scenario, this would be from Razorpay)
        fake_signature = "test_signature_123"
        
        webhook_result = await self.test_subscription_webhook(webhook_payload, fake_signature)
        
        print("\n=== Test Summary ===")
        print(f"✓ Configuration test: {'PASSED' if config else 'FAILED'}")
        print(f"✓ Plans test: {'PASSED' if plans else 'FAILED'}")
        print(f"✓ Subscription creation test: {'PASSED' if subscription_data else 'FAILED'}")
        print(f"✓ Subscription status test: {'PASSED' if status_data else 'FAILED'}")
        print(f"✓ Webhook test: {'PASSED' if webhook_result else 'FAILED'}")
        
        return config and plans and subscription_data and status_data and webhook_result
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main test function."""
    print("Starting Razorpay subscriptions tests...")
    
    # Check if environment variables are set
    if not settings.razorpay_key_id:
        print("⚠️  Warning: RAZORPAY_KEY_ID not set in environment")
    if not settings.razorpay_key_secret:
        print("⚠️  Warning: RAZORPAY_KEY_SECRET not set in environment")
    if not settings.razorpay_webhook_secret:
        print("⚠️  Warning: RAZORPAY_WEBHOOK_SECRET not set in environment")
    
    print()
    
    # Run tests
    test_client = RazorpaySubscriptionTestClient()
    try:
        success = await test_client.run_all_tests()
        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed!")
    finally:
        await test_client.close()


if __name__ == "__main__":
    asyncio.run(main())