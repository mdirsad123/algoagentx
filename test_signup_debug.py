import requests
import json

# Test data from the frontend form
test_user = {
    "email": "test@example.com",
    "password": "password123",
    "fullname": "Md Irsad",
    "mobile": "+918409718735"
}

try:
    # Test signup
    print("Testing signup...")
    response = requests.post(
        "http://localhost:8000/api/v1/auth/signup",
        json=test_user,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code != 200:
        print("❌ Signup failed!")
        try:
            error_data = response.json()
            print(f"Error details: {json.dumps(error_data, indent=2)}")
        except:
            print("Could not parse error response as JSON")
    else:
        print("✅ Signup successful!")
        result = response.json()
        print(f"Result: {json.dumps(result, indent=2)}")

except Exception as e:
    print(f"Error making request: {e}")