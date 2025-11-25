#!/usr/bin/env python
"""Test JWT authentication endpoints locally."""

import json
import sys

import requests

BASE_URL = "http://127.0.0.1:8000"


def test_jwt_authentication():
    """Test the JWT authentication flow."""
    print("🏴‍☠️ Testing JWT Authentication System")
    print("=" * 50)

    # Test 1: Public endpoint
    print("\n1. Testing public endpoint (no auth required)...")
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200, "Public endpoint failed"
    print("✅ Public endpoint accessible")

    # Test 2: Protected endpoint without token
    print("\n2. Testing protected endpoint without token...")
    response = requests.get(f"{BASE_URL}/protected")
    assert response.status_code == 403, "Should require authentication"
    print("✅ Protected endpoint blocked without token")

    # Test 3: Register new user
    print("\n3. Registering new test user...")
    user_data = {
        "username": "livetest",
        "email": "livetest@example.com",
        "password": "LiveTest123!",
        "full_name": "Live Test User"
    }
    response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
    if response.status_code == 400:
        print("   User already exists, continuing...")
    else:
        assert response.status_code == 201, f"Registration failed: {response.text}"
        print("✅ User registered successfully")

    # Test 4: Login
    print("\n4. Testing login...")
    login_data = {
        "username": "livetest",
        "password": "LiveTest123!"
    }
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    assert response.status_code == 200, f"Login failed: {response.text}"
    tokens = response.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    print("✅ Login successful, tokens received")
    print(f"   Access token: {access_token[:50]}...")

    # Test 5: Access protected route with token
    print("\n5. Testing protected route with valid token...")
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{BASE_URL}/protected", headers=headers)
    assert response.status_code == 200, f"Protected route failed: {response.text}"
    data = response.json()
    assert data["user_data"]["username"] == "livetest"
    print("✅ Protected route accessible with valid token")
    print(f"   Response: {data['message']}")

    # Test 6: Get current user info
    print("\n6. Testing /auth/me endpoint...")
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    assert response.status_code == 200, f"Get user info failed: {response.text}"
    user_info = response.json()
    assert user_info["username"] == "livetest"
    print("✅ Current user info retrieved successfully")
    print(f"   User: {user_info['username']} ({user_info['email']})")

    # Test 7: Admin endpoint (should fail for regular user)
    print("\n7. Testing admin endpoint (should fail)...")
    response = requests.get(f"{BASE_URL}/admin", headers=headers)
    assert response.status_code == 403, "Regular user shouldn't access admin"
    print("✅ Admin endpoint properly blocked for regular user")

    # Test 8: Token refresh
    print("\n8. Testing token refresh...")
    response = requests.post(f"{BASE_URL}/auth/refresh", params={"refresh_token": refresh_token})
    assert response.status_code == 200, f"Token refresh failed: {response.text}"
    new_tokens = response.json()
    assert "access_token" in new_tokens
    print("✅ Token refresh successful")
    print(f"   New access token: {new_tokens['access_token'][:50]}...")

    # Test 9: Logout
    print("\n9. Testing logout...")
    response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
    assert response.status_code == 200, f"Logout failed: {response.text}"
    print("✅ Logout successful")

    # Test 10: Test password validation
    print("\n10. Testing password validation...")
    invalid_users = [
        {"username": "weak1", "email": "weak1@test.com", "password": "weak"},  # Too short
        {"username": "weak2", "email": "weak2@test.com", "password": "NoDigits!"},  # No digits
        {"username": "weak3", "email": "weak3@test.com", "password": "nouppercase123!"},  # No uppercase
    ]

    for invalid_user in invalid_users:
        response = requests.post(f"{BASE_URL}/auth/register", json=invalid_user)
        assert response.status_code == 422, f"Weak password should be rejected: {invalid_user['password']}"
    print("✅ Password validation working correctly")

    print("\n" + "=" * 50)
    print("🎉 All JWT authentication tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    try:
        test_jwt_authentication()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to server. Is it running on http://127.0.0.1:8000?")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)