import requests
import json

# Test with the exact email from the frontend screenshot
test_user = {
    "email": "algoagentx@gmail.com",
    "password": "password123",
    "fullname": "Md Irsad",
    "mobile": "+918409718735"
}

def test_signup():
    print("=" * 60)
    print("TESTING SIGNUP WITH FRONTEND EMAIL")
    print("=" * 60)
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/auth/signup",
            json=test_user,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response: {response.text}")
        
        if response.status_code == 400:
            print("✅ Duplicate user check working!")
        elif response.status_code == 200:
            print("✅ New user created successfully!")
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_login():
    print("\n" + "=" * 60)
    print("TESTING LOGIN WITH FRONTEND EMAIL")
    print("=" * 60)
    
    login_data = {
        "email": "algoagentx@gmail.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Login successful!")
            result = response.json()
            if "access_token" in result:
                print("✅ JWT token received!")
                return result["access_token"]
        else:
            print(f"❌ Login failed with status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Login error: {e}")
    
    return None

def check_api_health():
    print("\n" + "=" * 60)
    print("CHECKING API HEALTH")
    print("=" * 60)
    
    try:
        # Test basic connectivity
        response = requests.get("http://localhost:8000/docs", timeout=5)
        print(f"API Docs Status: {response.status_code}")
        
        # Test CORS headers
        response = requests.options(
            "http://localhost:8000/api/v1/auth/signup",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            },
            timeout=5
        )
        print(f"CORS Preflight Status: {response.status_code}")
        print(f"CORS Headers: {dict(response.headers)}")
        
    except Exception as e:
        print(f"❌ API Health check error: {e}")

if __name__ == "__main__":
    check_api_health()
    test_signup()
    test_login()