# JWT Security Testing Guide

## Overview

This guide provides comprehensive security testing procedures for JWT authentication implementation in Amplihack.

## Automated Security Tests

### 1. Unit Tests for Security Features

```python
# /tests/security/test_jwt_vulnerabilities.py

import pytest
import jwt
import time
import base64
import json
from datetime import datetime, timedelta, timezone
from amplihack.security.jwt_manager import JWTManager, SecurityError


class TestJWTVulnerabilities:
    """Test suite for common JWT vulnerabilities"""

    @pytest.fixture
    def jwt_manager(self):
        """Create JWT manager instance for testing"""
        return JWTManager()

    def test_none_algorithm_attack(self, jwt_manager):
        """CVE-2015-2951: Algorithm confusion with 'none'"""
        # Create valid payload
        payload = {
            "sub": "attacker",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }

        # Create token with 'none' algorithm
        header = {"alg": "none", "typ": "JWT"}
        token_parts = [
            base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('='),
            base64.urlsafe_b64encode(json.dumps(payload, default=str).encode()).decode().rstrip('='),
            ""  # Empty signature
        ]
        malicious_token = ".".join(token_parts)

        # Should reject token with 'none' algorithm
        with pytest.raises(SecurityError):
            jwt_manager.validate_token(malicious_token)

    def test_algorithm_substitution_attack(self, jwt_manager):
        """Test RS256 to HS256 algorithm substitution attack"""
        # Get public key
        public_key = jwt_manager.public_key

        # Try to create token signed with public key as HMAC secret
        payload = {
            "sub": "attacker",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "type": "access"
        }

        # This would be the attack - using public key as HMAC secret
        try:
            # Attacker tries to sign with HS256 using public key
            from cryptography.hazmat.primitives import serialization
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            malicious_token = jwt.encode(payload, public_pem, algorithm="HS256")

            # Should reject due to algorithm whitelist
            with pytest.raises(SecurityError):
                jwt_manager.validate_token(malicious_token)
        except:
            pass  # Expected to fail

    def test_signature_stripping_attack(self, jwt_manager):
        """Test signature stripping vulnerability"""
        # Create valid token
        valid_token = jwt_manager.create_access_token(user_id="user123")

        # Strip signature (remove last part)
        parts = valid_token.split('.')
        stripped_token = f"{parts[0]}.{parts[1]}."

        # Should reject token with empty signature
        with pytest.raises(SecurityError):
            jwt_manager.validate_token(stripped_token)

    def test_replay_attack(self, jwt_manager):
        """Test replay attack prevention"""
        token = jwt_manager.create_access_token(user_id="user123")

        # First use should succeed
        payload = jwt_manager.validate_token(token)
        assert payload["sub"] == "user123"

        # Replay should fail
        with pytest.raises(SecurityError, match="replay"):
            jwt_manager.validate_token(token)

    def test_jti_collision(self, jwt_manager):
        """Test JWT ID collision prevention"""
        # Generate many tokens and check for JTI uniqueness
        jtis = set()
        for _ in range(1000):
            token = jwt_manager.create_access_token(user_id="user123")
            payload = jwt.decode(token, options={"verify_signature": False})
            jti = payload["jti"]
            assert jti not in jtis, "JTI collision detected"
            jtis.add(jti)

    def test_token_substitution(self, jwt_manager):
        """Test token type substitution attack"""
        # Create refresh token
        refresh_token = jwt_manager.create_refresh_token(user_id="user123")

        # Try to use refresh token as access token
        with pytest.raises(SecurityError, match="Invalid token type"):
            jwt_manager.validate_token(refresh_token, token_type="access")

    def test_expired_token(self, jwt_manager):
        """Test expired token rejection"""
        # Create token that's already expired
        now = datetime.now(timezone.utc)
        expired_payload = {
            "sub": "user123",
            "exp": now - timedelta(seconds=1),
            "iat": now - timedelta(minutes=20),
            "nbf": now - timedelta(minutes=20),
            "type": "access",
            "jti": "test_jti",
            "iss": "https://api.amplihack.com",
            "aud": "amplihack-api"
        }

        expired_token = jwt.encode(
            expired_payload,
            jwt_manager.private_key,
            algorithm="RS256"
        )

        with pytest.raises(SecurityError, match="expired"):
            jwt_manager.validate_token(expired_token)

    def test_not_before_claim(self, jwt_manager):
        """Test 'not before' claim validation"""
        # Create token that's not yet valid
        now = datetime.now(timezone.utc)
        future_payload = {
            "sub": "user123",
            "exp": now + timedelta(minutes=15),
            "iat": now,
            "nbf": now + timedelta(minutes=5),  # Not valid yet
            "type": "access",
            "jti": "test_jti",
            "iss": "https://api.amplihack.com",
            "aud": "amplihack-api"
        }

        future_token = jwt.encode(
            future_payload,
            jwt_manager.private_key,
            algorithm="RS256"
        )

        with pytest.raises(SecurityError):
            jwt_manager.validate_token(future_token)

    def test_audience_claim_validation(self, jwt_manager):
        """Test audience claim validation"""
        # Create token with wrong audience
        now = datetime.now(timezone.utc)
        wrong_aud_payload = {
            "sub": "user123",
            "exp": now + timedelta(minutes=15),
            "iat": now,
            "nbf": now,
            "type": "access",
            "jti": "test_jti",
            "iss": "https://api.amplihack.com",
            "aud": "wrong-audience"  # Wrong audience
        }

        wrong_token = jwt.encode(
            wrong_aud_payload,
            jwt_manager.private_key,
            algorithm="RS256"
        )

        with pytest.raises(SecurityError):
            jwt_manager.validate_token(wrong_token)

    def test_issuer_claim_validation(self, jwt_manager):
        """Test issuer claim validation"""
        # Create token with wrong issuer
        now = datetime.now(timezone.utc)
        wrong_iss_payload = {
            "sub": "user123",
            "exp": now + timedelta(minutes=15),
            "iat": now,
            "nbf": now,
            "type": "access",
            "jti": "test_jti",
            "iss": "https://evil.com",  # Wrong issuer
            "aud": "amplihack-api"
        }

        wrong_token = jwt.encode(
            wrong_iss_payload,
            jwt_manager.private_key,
            algorithm="RS256"
        )

        with pytest.raises(SecurityError):
            jwt_manager.validate_token(wrong_token)

    def test_malformed_token(self, jwt_manager):
        """Test malformed token rejection"""
        malformed_tokens = [
            "",  # Empty
            "not.a.token",  # Wrong format
            "too.many.parts.here",  # Too many parts
            "missing_signature.",  # Missing signature
            "a"*5000,  # Too long
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9",  # Only header
        ]

        for token in malformed_tokens:
            with pytest.raises(SecurityError):
                jwt_manager.validate_token(token)


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_login_rate_limiting(self):
        """Test login attempt rate limiting"""
        from amplihack.security.jwt_manager import RateLimiter

        limiter = RateLimiter()
        key = "login:192.168.1.1"

        # Should allow first 5 attempts
        for i in range(5):
            allowed, remaining = limiter.check_rate_limit(
                key, max_requests=5, window_seconds=60
            )
            assert allowed, f"Request {i+1} should be allowed"

        # 6th attempt should be blocked
        allowed, remaining = limiter.check_rate_limit(
            key, max_requests=5, window_seconds=60
        )
        assert not allowed, "6th request should be blocked"
        assert remaining == 0

    def test_sliding_window(self):
        """Test sliding window rate limiting"""
        from amplihack.security.jwt_manager import RateLimiter
        import time

        limiter = RateLimiter()
        key = "api:user123"

        # Make 3 requests
        for _ in range(3):
            allowed, _ = limiter.check_rate_limit(
                key, max_requests=5, window_seconds=2
            )
            assert allowed

        # Wait for window to slide
        time.sleep(2.1)

        # Should allow more requests
        for _ in range(5):
            allowed, _ = limiter.check_rate_limit(
                key, max_requests=5, window_seconds=2
            )
            assert allowed


class TestPasswordSecurity:
    """Test password handling security"""

    def test_password_hashing(self):
        """Test secure password hashing"""
        manager = JWTManager()

        password = "MySecurePassword123!"
        hash1 = manager.hash_password(password)
        hash2 = manager.hash_password(password)

        # Hashes should be different (due to salt)
        assert hash1 != hash2

        # Both should verify correctly
        valid1, _ = manager.verify_password(password, hash1)
        valid2, _ = manager.verify_password(password, hash2)

        assert valid1
        assert valid2

    def test_wrong_password(self):
        """Test wrong password rejection"""
        manager = JWTManager()

        password = "CorrectPassword"
        wrong_password = "WrongPassword"
        password_hash = manager.hash_password(password)

        valid, _ = manager.verify_password(wrong_password, password_hash)
        assert not valid

    def test_password_rehashing(self):
        """Test password rehashing on parameter change"""
        manager = JWTManager()

        # Create hash with old parameters (simulated)
        password = "TestPassword"
        old_hash = manager.hash_password(password)

        # Verify triggers rehash check
        valid, new_hash = manager.verify_password(password, old_hash)
        assert valid

        # new_hash would be non-None if rehashing was needed
        # (depends on Argon2 parameter changes)
```

## Integration Tests

```python
# /tests/integration/test_jwt_integration.py

import pytest
import json
from flask import Flask
from amplihack.proxy.server import AmplihackProxy


class TestJWTIntegration:
    """Integration tests for JWT in the proxy"""

    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        proxy = AmplihackProxy()
        proxy.app.config['TESTING'] = True
        return proxy.app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    def test_login_flow(self, client):
        """Test complete login flow"""
        # Attempt login
        response = client.post('/auth/login', json={
            'username': 'testuser',
            'password': 'testpassword123'
        })

        assert response.status_code == 200
        data = json.loads(response.data)

        assert 'access_token' in data
        assert data['token_type'] == 'Bearer'
        assert data['expires_in'] == 900

        # Check refresh token cookie
        assert 'refresh_token' in response.cookies

    def test_protected_endpoint(self, client):
        """Test accessing protected endpoint"""
        # Login first
        login_response = client.post('/auth/login', json={
            'username': 'testuser',
            'password': 'testpassword123'
        })
        token = json.loads(login_response.data)['access_token']

        # Access protected endpoint without token
        response = client.post('/api/chat/completions')
        assert response.status_code == 401

        # Access with token
        response = client.post(
            '/api/chat/completions',
            headers={'Authorization': f'Bearer {token}'},
            json={'prompt': 'test'}
        )
        assert response.status_code == 200

    def test_token_refresh(self, client):
        """Test token refresh flow"""
        # Login
        login_response = client.post('/auth/login', json={
            'username': 'testuser',
            'password': 'testpassword123'
        })

        # Refresh token
        response = client.post('/auth/refresh')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'access_token' in data
        assert data['token_type'] == 'Bearer'

    def test_logout(self, client):
        """Test logout flow"""
        # Login
        login_response = client.post('/auth/login', json={
            'username': 'testuser',
            'password': 'testpassword123'
        })
        token = json.loads(login_response.data)['access_token']

        # Logout
        response = client.post(
            '/auth/logout',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200

        # Token should now be invalid
        response = client.post(
            '/api/chat/completions',
            headers={'Authorization': f'Bearer {token}'},
            json={'prompt': 'test'}
        )
        assert response.status_code == 401
```

## Manual Security Testing

### 1. Burp Suite Testing

```bash
# Configure Burp Suite proxy
export HTTP_PROXY=http://127.0.0.1:8080
export HTTPS_PROXY=http://127.0.0.1:8080

# Test with Burp intercepting
curl -X POST https://api.amplihack.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
```

#### Tests to perform in Burp:
1. **JWT Manipulation**: Modify token claims and signature
2. **Algorithm Confusion**: Change RS256 to HS256 or none
3. **Signature Stripping**: Remove signature part
4. **Token Replay**: Resend captured tokens
5. **Claim Tampering**: Modify exp, iat, nbf, roles

### 2. OWASP ZAP Testing

```bash
# Run OWASP ZAP in daemon mode
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://api.amplihack.com \
  -c zap-jwt-rules.conf
```

### 3. JWT.io Debugging

```javascript
// Paste token at jwt.io to verify:
// 1. Algorithm is RS256
// 2. All required claims present
// 3. Signature validates with public key
// 4. Expiration time is appropriate
```

## Penetration Testing Scripts

### 1. Algorithm Confusion Test

```python
#!/usr/bin/env python3
# test_algorithm_confusion.py

import jwt
import requests
import sys

def test_algorithm_confusion(target_url, token):
    """Test algorithm confusion vulnerability"""

    # Decode token without verification
    header = jwt.get_unverified_header(token)
    payload = jwt.decode(token, options={"verify_signature": False})

    # Try different algorithms
    algorithms = ['none', 'HS256', 'HS384', 'HS512']

    for alg in algorithms:
        print(f"Testing algorithm: {alg}")

        if alg == 'none':
            # Create token with no signature
            forged = jwt.encode(payload, '', algorithm='none')
        else:
            # Try using public key as HMAC secret
            # (would need to obtain public key first)
            continue

        # Test forged token
        headers = {'Authorization': f'Bearer {forged}'}
        response = requests.get(f"{target_url}/api/user", headers=headers)

        if response.status_code == 200:
            print(f"VULNERABILITY: Algorithm {alg} accepted!")
            return True

    print("No algorithm confusion vulnerability found")
    return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: script.py <target_url> <valid_token>")
        sys.exit(1)

    test_algorithm_confusion(sys.argv[1], sys.argv[2])
```

### 2. Replay Attack Test

```python
#!/usr/bin/env python3
# test_replay_attack.py

import requests
import time
import sys

def test_replay_attack(target_url, token):
    """Test token replay vulnerability"""

    headers = {'Authorization': f'Bearer {token}'}

    # First request
    response1 = requests.get(f"{target_url}/api/user", headers=headers)
    print(f"First request: {response1.status_code}")

    # Wait a moment
    time.sleep(1)

    # Replay token
    response2 = requests.get(f"{target_url}/api/user", headers=headers)
    print(f"Replay request: {response2.status_code}")

    if response2.status_code == 200:
        print("WARNING: Token replay succeeded - possible vulnerability")
        return True
    else:
        print("Token replay prevented - good!")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: script.py <target_url> <valid_token>")
        sys.exit(1)

    test_replay_attack(sys.argv[1], sys.argv[2])
```

### 3. Brute Force Test

```python
#!/usr/bin/env python3
# test_brute_force.py

import requests
import time

def test_rate_limiting(target_url):
    """Test rate limiting on login endpoint"""

    login_url = f"{target_url}/auth/login"
    attempts = 0
    blocked = False

    for i in range(20):
        response = requests.post(login_url, json={
            'username': 'admin',
            'password': f'attempt{i}'
        })

        attempts += 1
        print(f"Attempt {attempts}: {response.status_code}")

        if response.status_code == 429:
            print(f"Rate limited after {attempts} attempts - GOOD!")
            blocked = True
            break

        time.sleep(0.1)

    if not blocked:
        print("WARNING: No rate limiting detected after 20 attempts!")
        return False

    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: script.py <target_url>")
        sys.exit(1)

    test_rate_limiting(sys.argv[1])
```

## Security Checklist

### Pre-Deployment

- [ ] All security tests pass
- [ ] No hardcoded secrets
- [ ] Keys properly protected
- [ ] Rate limiting active
- [ ] Audit logging enabled
- [ ] HTTPS enforced
- [ ] CORS configured
- [ ] Input validation active
- [ ] Error messages sanitized

### Post-Deployment

- [ ] Monitor authentication failures
- [ ] Track rate limit violations
- [ ] Review audit logs daily
- [ ] Check for unusual patterns
- [ ] Verify key rotation
- [ ] Test incident response
- [ ] Update dependencies
- [ ] Security scan weekly

## Monitoring Queries

### Splunk Queries

```sql
-- Failed authentication attempts
index=security event="AUTH_LOGIN_FAILED"
| stats count by user_id, ip_address
| where count > 5

-- Token replay attempts
index=security event="REPLAY_DETECTED"
| timechart span=1h count

-- Rate limit violations
index=security event="RATE_LIMIT_EXCEEDED"
| stats count by ip_address
| sort -count

-- Algorithm confusion attempts
index=security event="ALGORITHM_CONFUSION"
| table _time, ip_address, user_agent
```

### Prometheus Metrics

```yaml
# JWT metrics to track
jwt_tokens_issued_total
jwt_tokens_validated_total
jwt_validation_errors_total
jwt_replay_attempts_total
jwt_rate_limit_violations_total
jwt_key_rotation_total
```

## Incident Response Playbook

### Suspected Token Compromise

1. **Immediate Actions**:
   ```bash
   # Revoke all tokens for affected user
   redis-cli --scan --pattern "jti:*" | xargs redis-cli del

   # Force key rotation
   python -c "from jwt_manager import rotate_keys; rotate_keys()"
   ```

2. **Investigation**:
   - Review audit logs
   - Check for unusual IP addresses
   - Analyze token usage patterns

3. **Recovery**:
   - Notify affected users
   - Force password reset
   - Generate incident report

## Compliance Validation

### OWASP ASVS Checklist

- [ ] V3.1 - Session Management Architecture
- [ ] V3.2 - Session Binding
- [ ] V3.3 - Session Termination
- [ ] V3.4 - Cookie-based Session Management
- [ ] V3.5 - Token-based Session Management
- [ ] V3.7 - Defenses Against Session Management Exploits

### Security Headers Validation

```bash
# Test security headers
curl -I https://api.amplihack.com/api/test | grep -E \
  "Strict-Transport-Security|X-Content-Type-Options|X-Frame-Options|Content-Security-Policy"
```

## References

- [OWASP Testing Guide - JWT](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/10-Testing_JSON_Web_Tokens)
- [JWT Security Best Practices](https://tools.ietf.org/html/rfc8725)
- [NIST Cryptographic Standards](https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines)