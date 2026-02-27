#!/usr/bin/env python3
"""
Complete Authentication System Test
Tests all authentication features including signup, login, duplicate validation, and forgot password
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_auth_flow():
    print("=" * 80)
    print("🔐 COMPLETE AUTHENTICATION SYSTEM TEST")
    print("=" * 80)
    
    # Test user data
    test_users = [
        {
            "email": "testuser1@example.com",
            "password": "password123",
            "fullname": "Test User One",
            "mobile": "+919876543210"
        },
        {
            "email": "testuser2@example.com", 
            "password": "password456",
            "fullname": "Test User Two",
            "mobile": "+919876543211"
        }
    ]

    # 1. Test New User Signup
    print("\n1️⃣ Testing New User Signup...")
    for i, user in enumerate(test_users):
        response = requests.post(f"{BASE_URL}/api/v1/auth/signup", json=user)
        if response.status_code == 200:
            print(f"   ✅ User {i+1} signup successful")
            result = response.json()
            print(f"   📧 Email: {result['user']['email']}")
            print(f"   🆔 ID: {result['user']['id']}")
        elif response.status_code == 400 and "already exists" in response.text:
            print(f"   ⚠️  User {i+1} already exists (expected if running multiple times)")
        else:
            print(f"   ❌ User {i+1} signup failed: {response.status_code} - {response.text}")

    # 2. Test Duplicate Email Validation
    print("\n2️⃣ Testing Duplicate Email Validation...")
    response = requests.post(f"{BASE_URL}/api/v1/auth/signup", json=test_users[0])
    if response.status_code == 400:
        error_msg = response.json().get('detail', '')
        if "email already exists" in error_msg:
            print("   ✅ Duplicate email validation working")
        else:
            print(f"   ⚠️  Unexpected error message: {error_msg}")
    else:
        print(f"   ❌ Should have returned 400 for duplicate email: {response.status_code}")

    # 3. Test Duplicate Mobile Validation  
    print("\n3️⃣ Testing Duplicate Mobile Number Validation...")
    duplicate_mobile_user = {
        "email": "different@example.com",
        "password": "password789",
        "fullname": "Different User",
        "mobile": test_users[0]["mobile"]  # Same mobile as first user
    }
    response = requests.post(f"{BASE_URL}/api/v1/auth/signup", json=duplicate_mobile_user)
    if response.status_code == 400:
        error_msg = response.json().get('detail', '')
        if "mobile number already exists" in error_msg:
            print("   ✅ Duplicate mobile validation working")
        else:
            print(f"   ⚠️  Unexpected error message: {error_msg}")
    else:
        print(f"   ❌ Should have returned 400 for duplicate mobile: {response.status_code}")

    # 4. Test Login
    print("\n4️⃣ Testing Login Functionality...")
    for i, user in enumerate(test_users):
        login_data = {"email": user["email"], "password": user["password"]}
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ User {i+1} login successful")
            print(f"   🔑 Token received: {result['access_token'][:20]}...")
            
            # Test token verification
            headers = {"Authorization": f"Bearer {result['access_token']}"}
            verify_response = requests.get(f"{BASE_URL}/api/v1/auth/verify", headers=headers)
            if verify_response.status_code == 200:
                print(f"   ✅ Token verification successful")
            else:
                print(f"   ❌ Token verification failed")
        else:
            print(f"   ❌ User {i+1} login failed: {response.status_code}")

    # 5. Test Invalid Login
    print("\n5️⃣ Testing Invalid Login...")
    invalid_login = {"email": test_users[0]["email"], "password": "wrongpassword"}
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=invalid_login)
    if response.status_code == 401:
        print("   ✅ Invalid login properly rejected")
    else:
        print(f"   ❌ Should have returned 401: {response.status_code}")

    # 6. Test Forgot Password
    print("\n6️⃣ Testing Forgot Password...")
    forgot_data = {"email": test_users[0]["email"]}
    response = requests.post(f"{BASE_URL}/api/v1/auth/forgot-password", json=forgot_data)
    if response.status_code == 200:
        print("   ✅ Forgot password request successful")
        result = response.json()
        print(f"   💌 Message: {result['message']}")
    else:
        print(f"   ❌ Forgot password failed: {response.status_code}")

    # 7. Test Reset Password
    print("\n7️⃣ Testing Password Reset...")
    reset_data = {
        "email": test_users[0]["email"], 
        "new_password": "newpassword123",
        "reset_token": "dev-token"
    }
    response = requests.post(f"{BASE_URL}/api/v1/auth/reset-password", json=reset_data)
    if response.status_code == 200:
        print("   ✅ Password reset successful")
        
        # Test login with new password
        print("   🔄 Testing login with new password...")
        new_login = {"email": test_users[0]["email"], "password": "newpassword123"}
        login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=new_login)
        if login_response.status_code == 200:
            print("   ✅ Login with new password successful")
        else:
            print("   ❌ Login with new password failed")
            
        # Test login with old password should fail
        old_login = {"email": test_users[0]["email"], "password": test_users[0]["password"]}
        old_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=old_login)
        if old_response.status_code == 401:
            print("   ✅ Old password properly rejected")
        else:
            print("   ❌ Old password should be rejected")
    else:
        print(f"   ❌ Password reset failed: {response.status_code}")

    # 8. Test API Health
    print("\n8️⃣ Testing API Health & CORS...")
    try:
        # Test CORS headers for frontend
        response = requests.options(
            f"{BASE_URL}/api/v1/auth/signup",
            headers={
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        if response.status_code == 200:
            cors_origin = response.headers.get('Access-Control-Allow-Origin', '')
            if 'localhost:3001' in cors_origin:
                print("   ✅ CORS configured for frontend (port 3001)")
            else:
                print(f"   ⚠️  CORS may not include port 3001: {cors_origin}")
        
        # Test API documentation 
        docs_response = requests.get(f"{BASE_URL}/docs")
        if docs_response.status_code == 200:
            print("   ✅ API documentation accessible")
        
    except Exception as e:
        print(f"   ❌ API health check error: {e}")

    print("\n" + "=" * 80)
    print("🎉 AUTHENTICATION SYSTEM TEST COMPLETE!")
    print("=" * 80)
    print("✅ Summary:")
    print("   - User signup with validation")
    print("   - Duplicate email/mobile detection")  
    print("   - Login with JWT tokens")
    print("   - Token verification")
    print("   - Forgot/reset password")
    print("   - CORS configuration")
    print("   - API documentation")
    print("\n🌐 Frontend should now work at: http://localhost:3001")
    print("📚 Backend API docs available at: http://localhost:8000/docs")

if __name__ == "__main__":
    test_auth_flow()