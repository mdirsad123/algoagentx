#!/usr/bin/env python3
"""
Test script to check the signup endpoint
"""
import requests
import json

def test_signup():
    url = "http://localhost:8000/api/v1/auth/signup"
    
    # Test data
    test_data = {
        "email": "test@example.com",
        "password": "test123",
        "fullname": "Test User",
        "mobile": "1234567890"
    }
    
    try:
        print("Testing signup endpoint...")
        print(f"URL: {url}")
        print(f"Data: {json.dumps(test_data, indent=2)}")
        
        response = requests.post(url, json=test_data, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Signup endpoint is working!")
        else:
            print("❌ Signup endpoint returned error")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure FastAPI is running on localhost:8000")
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_signup()