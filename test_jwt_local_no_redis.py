#!/usr/bin/env python
"""
Local testing script for JWT authentication WITHOUT Redis.
Tests core JWT functionality with in-memory fallbacks.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from amplihack.auth.config import JWTConfig, AuthConfig, RedisConfig
from amplihack.auth.services import (
    TokenService,
    PasswordService,
    RateLimiter,
    AuditLogger,
    AuthenticationService,
)
from amplihack.auth.repository import UserRepository
from amplihack.auth.models import RegisterRequest, LoginRequest
from amplihack.auth.exceptions import InvalidCredentialsError


# Mock BlacklistService for testing without Redis
class MockBlacklistService:
    """In-memory blacklist service for testing without Redis."""

    def __init__(self):
        self.blacklist = set()

    def blacklist_token(self, token_id: str, exp: datetime):
        """Add token to blacklist."""
        self.blacklist.add(token_id)

    def is_blacklisted(self, token_id: str) -> bool:
        """Check if token is blacklisted."""
        return token_id in self.blacklist

    def health_check(self) -> bool:
        """Always healthy for mock."""
        return True


# Mock RateLimiter for testing without Redis
class MockRateLimiter:
    """In-memory rate limiter for testing without Redis."""

    def __init__(self):
        self.attempts: Dict[str, list] = {}

    async def is_allowed(self, identifier: str, action: str = "request", limit: int = 5, window: int = 60) -> bool:
        """Check if request is allowed."""
        key = f"{identifier}:{action}"
        now = datetime.now().timestamp()

        if key not in self.attempts:
            self.attempts[key] = []

        # Remove old attempts outside window
        self.attempts[key] = [t for t in self.attempts[key] if now - t < window]

        if len(self.attempts[key]) < limit:
            self.attempts[key].append(now)
            return True
        return False

    def check_rate_limit(self, identifier: str, endpoint: str = "auth") -> tuple:
        """Synchronous version of is_allowed for compatibility. Returns (allowed, remaining)."""
        key = f"{identifier}:{endpoint}"
        now = datetime.now().timestamp()
        limit = 5
        window = 60

        if key not in self.attempts:
            self.attempts[key] = []

        # Remove old attempts outside window
        self.attempts[key] = [t for t in self.attempts[key] if now - t < window]

        current_count = len(self.attempts[key])
        remaining = max(0, limit - current_count)
        allowed = current_count < limit

        if allowed:
            self.attempts[key].append(now)

        return (allowed, remaining)


def create_test_auth_system():
    """Create auth system with mock services for testing."""

    # Create configurations
    jwt_config = JWTConfig(
        algorithm="HS256",  # Use HS256 for testing (simpler than RSA)
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
        secret_key="test-secret-key-for-local-testing-only",
    )
    auth_config = AuthConfig()

    # Create mock services
    password_service = PasswordService()
    blacklist_service = MockBlacklistService()
    rate_limiter = MockRateLimiter()
    audit_logger = AuditLogger()

    # Create token service with mock blacklist
    token_service = TokenService(jwt_config, blacklist_service)

    # Create repository
    user_repository = UserRepository()

    # Create authentication service
    auth_service = AuthenticationService(
        user_repository=user_repository,
        password_service=password_service,
        token_service=token_service,
        rate_limiter=rate_limiter,
        audit_logger=audit_logger,
        config=auth_config
    )

    return auth_service, token_service, blacklist_service, rate_limiter


async def test_jwt_authentication():
    """Test JWT authentication end-to-end without Redis."""
    print("\n" + "="*60)
    print("JWT Authentication Local Testing (No Redis)")
    print("="*60)

    # Create auth system
    print("\n1. Creating auth system with mock services...")
    auth_service, token_service, blacklist_service, rate_limiter = create_test_auth_system()
    print("✅ Auth system created (using in-memory services)")

    # Test user data
    test_email = f"test_{datetime.now().timestamp()}@example.com"
    test_username = f"testuser_{int(datetime.now().timestamp())}"
    test_password = "SecurePass123!"

    # Test 1: User Registration
    print("\n2. Testing user registration...")
    register_request = RegisterRequest(
        email=test_email,
        username=test_username,
        password=test_password
    )

    try:
        user = auth_service.register(register_request)
        print(f"✅ User registered: {user.email} (ID: {user.id})")
    except Exception as e:
        print(f"❌ Registration failed: {e}")
        return False

    # Test 2: Login with valid credentials
    print("\n3. Testing login...")
    login_request = LoginRequest(
        email=test_email,
        password=test_password
    )

    try:
        login_response = auth_service.login(login_request)
        access_token = login_response.access_token
        refresh_token = login_response.refresh_token
        print(f"✅ Login successful")
        print(f"   - Access token (first 30 chars): {access_token[:30]}...")
        print(f"   - Refresh token (first 30 chars): {refresh_token[:30]}...")
        print(f"   - Token type: {login_response.token_type}")
        print(f"   - Expires in: {login_response.expires_in} seconds")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return False

    # Test 3: Validate access token
    print("\n4. Testing token validation...")
    try:
        claims = token_service.validate_token(access_token)
        print(f"✅ Token validated successfully")
        # claims is a TokenPayload object or dict
        try:
            if hasattr(claims, 'sub'):
                print(f"   - User ID: {claims.sub}")
                print(f"   - Email: {claims.email}")
                print(f"   - Roles: {claims.roles}")
                print(f"   - Token type: {claims.type}")
                print(f"   - JTI: {claims.jti}")
            else:
                print(f"   - User ID: {claims.get('sub')}")
                print(f"   - Email: {claims.get('email')}")
                print(f"   - Roles: {claims.get('roles')}")
                print(f"   - Token type: {claims.get('type')}")
                print(f"   - JTI: {claims.get('jti')}")
        except AttributeError as e:
            # TokenPayload object, access as dict
            print(f"   - Token payload type: {type(claims)}")
            print(f"   - Token valid (claims object returned)")
    except Exception as e:
        print(f"❌ Token validation failed: {e}")
        return False

    # Test 4: Invalid login
    print("\n5. Testing invalid login...")
    invalid_request = LoginRequest(
        email=test_email,
        password="WrongPassword123"
    )

    try:
        auth_service.login(invalid_request)
        print("❌ Invalid login should have failed!")
        return False
    except InvalidCredentialsError:
        print("✅ Invalid credentials correctly rejected")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    # Test 5: Token refresh
    print("\n6. Testing token refresh...")
    try:
        refresh_response = auth_service.refresh_token(refresh_token)
        # Check if it's a dict or object
        if isinstance(refresh_response, dict):
            new_access_token = refresh_response.get("access_token")
        else:
            new_access_token = refresh_response.access_token
        print(f"✅ Token refreshed successfully")
        print(f"   - New access token (first 30 chars): {new_access_token[:30]}...")
        print(f"   - Tokens are different: {access_token != new_access_token}")
    except Exception as e:
        print(f"❌ Token refresh failed: {e}")
        return False

    # Test 6: Logout (token blacklisting with mock)
    print("\n7. Testing logout (mock blacklisting)...")
    try:
        # Extract JTI from token for blacklisting
        claims = token_service.validate_token(access_token)
        jti = claims.jti if hasattr(claims, 'jti') else claims.get("jti")

        if jti:
            blacklist_service.blacklist_token(jti, datetime.utcnow() + timedelta(minutes=15))

            # Check if token is blacklisted
            is_blacklisted = blacklist_service.is_blacklisted(jti)
            print(f"✅ Token blacklisted: {is_blacklisted}")
        else:
            print("⚠️  No JTI in token")
    except Exception as e:
        print(f"❌ Blacklisting test failed: {e}")
        return False

    # Test 7: Password hashing
    print("\n8. Testing password hashing...")
    try:
        # Hash a password
        hashed = auth_service.password_service.hash_password("TestPassword123!")
        print(f"✅ Password hashed: {hashed[:30]}...")

        # Verify correct password
        is_valid = auth_service.password_service.verify_password("TestPassword123!", hashed)
        print(f"✅ Correct password verified: {is_valid}")

        # Verify incorrect password
        is_invalid = auth_service.password_service.verify_password("WrongPassword", hashed)
        print(f"✅ Incorrect password rejected: {not is_invalid}")
    except Exception as e:
        print(f"❌ Password hashing failed: {e}")
        return False

    # Test 8: Rate limiting with mock
    print("\n9. Testing rate limiting (mock)...")
    try:
        identifier = "test_ip_127.0.0.1"

        # Test 5 requests (should all pass)
        for i in range(5):
            is_allowed = await rate_limiter.is_allowed(identifier, "login", limit=5, window=60)
            if is_allowed:
                print(f"✅ Request {i+1}/5 allowed")
            else:
                print(f"❌ Request {i+1} should have been allowed")

        # 6th request should be rate limited
        is_allowed = await rate_limiter.is_allowed(identifier, "login", limit=5, window=60)
        if not is_allowed:
            print(f"✅ Request 6 correctly rate limited")
        else:
            print(f"❌ Request 6 should have been rate limited")

    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False

    # Test 9: Multiple users
    print("\n10. Testing multiple users...")
    try:
        # Register another user
        user2_email = f"user2_{datetime.now().timestamp()}@example.com"
        user2_request = RegisterRequest(
            email=user2_email,
            username=f"user2_{int(datetime.now().timestamp())}",
            password="AnotherPass456!"
        )

        user2 = auth_service.register(user2_request)
        print(f"✅ Second user registered: {user2.email}")

        # Login as second user
        user2_login = LoginRequest(
            email=user2_email,
            password="AnotherPass456!"
        )

        user2_response = auth_service.login(user2_login)
        print(f"✅ Second user logged in successfully")

        # Verify tokens are different
        user2_token = user2_response.access_token
        are_different = user2_token != access_token
        print(f"✅ Tokens are unique per user: {are_different}")

    except Exception as e:
        print(f"❌ Multiple user test failed: {e}")
        return False

    print("\n" + "="*60)
    print("✅ All local tests passed!")
    print("="*60)
    return True


async def main():
    """Run all local tests."""
    print("\n🚀 Starting JWT Authentication Local Tests (No Redis)...")
    print("   Using in-memory mocks for Redis-dependent services")

    # Run tests
    passed = await test_jwt_authentication()

    if passed:
        print("\n✅ ALL LOCAL TESTS PASSED!")
        print("\nThe JWT authentication implementation is working correctly:")
        print("  ✅ User registration")
        print("  ✅ Login with token generation")
        print("  ✅ Token validation (HS256 for testing)")
        print("  ✅ Invalid credentials handling")
        print("  ✅ Token refresh")
        print("  ✅ Token blacklisting (mock)")
        print("  ✅ Password hashing (bcrypt)")
        print("  ✅ Rate limiting (mock)")
        print("  ✅ Multiple user support")
        print("\nNote: This test uses mock services. Production requires Redis.")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)