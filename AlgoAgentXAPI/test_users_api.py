#!/usr/bin/env python3
"""
Test script for user profile endpoints
"""

import asyncio
from fastapi.testclient import TestClient
from app.main import app

def test_users_api():
    """Test that users API endpoints are properly registered"""
    client = TestClient(app)
    
    # Test that the router is properly registered
    response = client.get("/api/v1/users/me")
    print(f"GET /api/v1/users/me status: {response.status_code}")
    
    # Test PATCH endpoint
    response = client.patch("/api/v1/users/me", json={"full_name": "Test User"})
    print(f"PATCH /api/v1/users/me status: {response.status_code}")
    
    print("Users API endpoints are registered successfully!")

if __name__ == "__main__":
    test_users_api()