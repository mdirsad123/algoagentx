import requests
import json

# Test login with the user we just created
login_data = {
    "email": "test@example.com",
    "password": "password123"
}

try:
    # Test login
    print("Testing login...")
    response = requests.post(
        "http://localhost:8000/api/v1/auth/login",
        json=login_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code != 200:
        print("❌ Login failed!")
        try:
            error_data = response.json()
            print(f"Error details: {json.dumps(error_data, indent=2)}")
        except:
            print("Could not parse error response as JSON")
    else:
        print("✅ Login successful!")
        result = response.json()
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Test token verification
        if "access_token" in result:
            print("\nTesting token verification...")
            verify_response = requests.get(
                "http://localhost:8000/api/v1/auth/verify",
                headers={"Authorization": f"Bearer {result['access_token']}"}
            )
            print(f"Verify Status: {verify_response.status_code}")
            if verify_response.status_code == 200:
                print("✅ Token verification successful!")
                print(f"Verify Result: {json.dumps(verify_response.json(), indent=2)}")
            else:
                print("❌ Token verification failed!")

except Exception as e:
    print(f"Error making request: {e}")