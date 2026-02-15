#!/usr/bin/env python3
import requests
import sys
import time

def test_endpoints():
    base_url = "http://localhost:8000"
    
    print("Testing FastAPI endpoints...")
    print("=" * 50)
    
    # Test root endpoint
    print("1. Testing root endpoint...")
    try:
        r = requests.get(f"{base_url}/")
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test timeframes endpoint
    print("\n2. Testing timeframes endpoint...")
    try:
        r = requests.get(f"{base_url}/api/v1/market-data/timeframes")
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            print(f"   Response: {r.json()}")
        else:
            print(f"   Response: {r.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test range endpoint
    print("\n3. Testing range endpoint...")
    try:
        r = requests.get(f"{base_url}/api/v1/market-data/range?instrument_id=1&timeframe=5m")
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            print(f"   Response: {r.json()}")
        else:
            print(f"   Response: {r.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test docs endpoint
    print("\n4. Testing docs endpoint...")
    try:
        r = requests.get(f"{base_url}/docs")
        print(f"   Status: {r.status_code}")
        print(f"   Response length: {len(r.text)}")
        if "market-data" in r.text:
            print("   ✓ market-data endpoints found in docs")
        else:
            print("   ✗ market-data endpoints NOT found in docs")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test openapi.json endpoint
    print("\n5. Testing openapi.json endpoint...")
    try:
        r = requests.get(f"{base_url}/openapi.json")
        print(f"   Status: {r.status_code}")
        print(f"   Response length: {len(r.text)}")
        if "market-data" in r.text:
            print("   ✓ market-data endpoints found in openapi.json")
        else:
            print("   ✗ market-data endpoints NOT found in openapi.json")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 50)
    print("Testing complete!")

if __name__ == "__main__":
    test_endpoints()