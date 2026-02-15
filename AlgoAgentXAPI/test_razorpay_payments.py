#!/usr/bin/env python3
"""
Test script for Razorpay payments implementation.
This script tests the payment endpoints and verifies the integration works correctly.
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


class RazorpayTestClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.test_user_id = "test_user_123"
        self.test_credits = 10
        
    async def test_razorpay_config(self):
        """Test if Razorpay is configured."""
        print("Testing Razorpay configuration...")
        
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/payments/razorpay/config")
            if response.status_code == 200:
                config = response.json()
                print(f"✓ Razorpay configured: {config}")
                return config
            else:
                print(f"✗ Failed to get config: {response.status_code}")
                return None
        except Exception as e:
            print(f"✗ Error testing config: {e}")
            return None
    
    async def test_create_order(self):
        """Test creating a Razorpay order."""
        print(f"Testing order creation for {self.test_credits} credits...")
        
        try:
            # Mock JWT token for testing (in real scenario, this would be a valid JWT)
            headers = {
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json"
            }
            
            payload = {
                "credits_to_buy": self.test_credits
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/payments/razorpay/create-order",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                order_data = response.json()
                print(f"✓ Order created: {order_data}")
                return order_data
            else:
                print(f"✗ Failed to create order: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ Error creating order: {e}")
            return None
    
    async def test_verify_payment(self, order_id: str, payment_id: str, signature: str):
        """Test payment verification."""
        print(f"Testing payment verification for order {order_id}...")
        
        try:
            headers = {
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json"
            }
            
            payload = {
                "order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/payments/razorpay/verify",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Payment verified: {result}")
                return result
            else:
                print(f"✗ Failed to verify payment: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ Error verifying payment: {e}")
            return None
    
    async def test_webhook(self, payload: Dict[str, Any], signature: str):
        """Test webhook handling."""
        print("Testing webhook handling...")
        
        try:
            headers = {
                "X-Razorpay-Signature": signature,
                "Content-Type": "application/json"
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/payments/razorpay/webhook",
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
        print("=== Razorpay Payments Test Suite ===")
        print(f"Base URL: {self.base_url}")
        print(f"Test User ID: {self.test_user_id}")
        print(f"Test Credits: {self.test_credits}")
        print()
        
        # Test 1: Check configuration
        config = await self.test_razorpay_config()
        if not config:
            print("Cannot proceed without Razorpay configuration")
            return False
        
        # Test 2: Create order (this would normally require a valid JWT)
        order_data = await self.test_create_order()
        if not order_data:
            print("Cannot proceed without order creation")
            return False
        
        # Test 3: Test webhook (simulate payment captured event)
        webhook_payload = {
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_123",
                        "order_id": order_data["order_id"],
                        "status": "captured"
                    }
                }
            }
        }
        
        # Generate a fake signature for testing (in real scenario, this would be from Razorpay)
        fake_signature = "test_signature_123"
        
        webhook_result = await self.test_webhook(webhook_payload, fake_signature)
        
        print("\n=== Test Summary ===")
        print(f"✓ Configuration test: {'PASSED' if config else 'FAILED'}")
        print(f"✓ Order creation test: {'PASSED' if order_data else 'FAILED'}")
        print(f"✓ Webhook test: {'PASSED' if webhook_result else 'FAILED'}")
        
        return config and order_data and webhook_result
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Main test function."""
    print("Starting Razorpay payments tests...")
    
    # Check if environment variables are set
    if not settings.razorpay_key_id:
        print("⚠️  Warning: RAZORPAY_KEY_ID not set in environment")
    if not settings.razorpay_key_secret:
        print("⚠️  Warning: RAZORPAY_KEY_SECRET not set in environment")
    if not settings.razorpay_webhook_secret:
        print("⚠️  Warning: RAZORPAY_WEBHOOK_SECRET not set in environment")
    
    print()
    
    # Run tests
    test_client = RazorpayTestClient()
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