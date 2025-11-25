"""
Security tests for JWT token vulnerabilities.
These tests follow TDD approach and should fail initially.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
import jwt
import base64
import json
import hashlib
import hmac
from typing import Dict, Any

# Import the modules to be tested (these don't exist yet - TDD approach)
from src.amplihack.auth.services import TokenService, SecurityValidator
from src.amplihack.auth.exceptions import (
    InvalidTokenError,
    SecurityViolationError,
    AlgorithmNotAllowedError,
    TokenTamperingDetectedError,
)
from src.amplihack.auth.config import JWTConfig


class TestTokenSecurityVulnerabilities:
    """Test for common JWT security vulnerabilities."""

    @pytest.fixture
    def jwt_config(self):
        """Create secure JWT configuration."""
        return JWTConfig(
            secret_key="test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
            allowed_algorithms=["HS256"],  # Strict algorithm allowlist
            access_token_expire_minutes=60,
            refresh_token_expire_days=30,
            issuer="amplihack-auth",
            audience="amplihack-api",
            require_expiration=True,
            require_not_before=True,
        )

    @pytest.fixture
    def token_service(self, jwt_config):
        """Create a TokenService instance."""
        return TokenService(config=jwt_config)

    @pytest.fixture
    def security_validator(self, jwt_config):
        """Create a SecurityValidator instance."""
        return SecurityValidator(config=jwt_config)

    def test_none_algorithm_attack(self, token_service):
        """Test protection against 'none' algorithm attack."""
        # Create a token with 'none' algorithm (no signature)
        payload = {
            "sub": "user_123",
            "email": "attacker@example.com",
            "roles": ["admin"],  # Elevated privileges
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }

        # Create token with 'none' algorithm
        header = {"alg": "none", "typ": "JWT"}
        token_parts = [
            base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("="),
            base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("="),
            "",  # No signature with 'none' algorithm
        ]
        malicious_token = ".".join(token_parts)

        # Should reject token with 'none' algorithm
        with pytest.raises(AlgorithmNotAllowedError) as exc_info:
            token_service.validate_token(malicious_token)

        assert "algorithm not allowed" in str(exc_info.value).lower()

    def test_algorithm_confusion_attack(self, token_service):
        """Test protection against algorithm confusion attack (RS256 to HS256)."""
        # Attacker tries to change RS256 to HS256 to use public key as secret
        public_key = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0B..."

        payload = {
            "sub": "user_123",
            "roles": ["admin"],
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }

        # Create token signed with public key using HS256 (attack attempt)
        malicious_token = jwt.encode(payload, public_key, algorithm="HS256")

        # Should reject token with unexpected algorithm
        with pytest.raises(AlgorithmNotAllowedError):
            token_service.validate_token(malicious_token)

    def test_weak_secret_key_detection(self, security_validator):
        """Test detection of weak secret keys."""
        weak_keys = [
            "secret",
            "password",
            "12345678",
            "admin123",
            "jwt_secret",
            "a" * 10,  # Too short
        ]

        for weak_key in weak_keys:
            with pytest.raises(SecurityViolationError) as exc_info:
                security_validator.validate_secret_key(weak_key)

            assert "weak secret key" in str(exc_info.value).lower()

    def test_token_tampering_detection(self, token_service):
        """Test detection of tampered tokens."""
        # Create a valid token
        valid_token = jwt.encode(
            {
                "sub": "user_123",
                "roles": ["user"],
                "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            },
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
        )

        # Tamper with the payload
        parts = valid_token.split(".")
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        payload["roles"] = ["admin"]  # Privilege escalation attempt

        # Re-encode tampered payload
        tampered_payload = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")

        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

        # Should detect tampering
        with pytest.raises(InvalidTokenError):
            token_service.validate_token(tampered_token)

    def test_sql_injection_in_token_claims(self, security_validator):
        """Test protection against SQL injection in token claims."""
        malicious_claims = {
            "user_id": "1' OR '1'='1",
            "email": "admin@example.com'; DROP TABLE users; --",
            "roles": ["user', 'admin'); --"],
        }

        for key, value in malicious_claims.items():
            with pytest.raises(SecurityViolationError) as exc_info:
                security_validator.validate_token_claims({key: value})

            assert "suspicious content" in str(exc_info.value).lower()

    def test_xss_in_token_claims(self, security_validator):
        """Test protection against XSS in token claims."""
        xss_payloads = {
            "name": "<script>alert('XSS')</script>",
            "bio": "Normal text <img src=x onerror=alert(1)>",
            "website": "javascript:alert(document.cookie)",
        }

        for key, value in xss_payloads.items():
            with pytest.raises(SecurityViolationError) as exc_info:
                security_validator.validate_token_claims({key: value})

            assert "suspicious content" in str(exc_info.value).lower()

    def test_token_replay_attack_protection(self, token_service):
        """Test protection against token replay attacks."""
        # Create a token
        token = jwt.encode(
            {
                "sub": "user_123",
                "jti": "unique_token_id_123",
                "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            },
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
        )

        # First use should succeed
        payload1 = token_service.validate_token(token)
        assert payload1 is not None

        # Mark token as used (simulate one-time token)
        token_service.mark_token_used(payload1.jti)

        # Replay attempt should fail
        with pytest.raises(SecurityViolationError) as exc_info:
            token_service.validate_token(token)

        assert "token already used" in str(exc_info.value).lower()

    def test_token_without_expiration(self, token_service):
        """Test rejection of tokens without expiration."""
        # Create token without expiration
        token = jwt.encode(
            {
                "sub": "user_123",
                # No 'exp' claim
            },
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
        )

        with pytest.raises(SecurityViolationError) as exc_info:
            token_service.validate_token(token)

        assert "expiration required" in str(exc_info.value).lower()

    def test_token_with_future_iat(self, token_service):
        """Test rejection of tokens with future issued-at time."""
        # Create token issued in the future
        future_iat = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()

        token = jwt.encode(
            {
                "sub": "user_123",
                "iat": future_iat,
                "exp": future_iat + 3600,
            },
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
        )

        with pytest.raises(SecurityViolationError) as exc_info:
            token_service.validate_token(token)

        assert "token issued in future" in str(exc_info.value).lower()

    def test_token_nbf_validation(self, token_service):
        """Test 'not before' (nbf) claim validation."""
        # Create token not valid yet
        future_nbf = (datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()

        token = jwt.encode(
            {
                "sub": "user_123",
                "nbf": future_nbf,
                "exp": future_nbf + 3600,
            },
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
        )

        with pytest.raises(SecurityViolationError) as exc_info:
            token_service.validate_token(token)

        assert "token not yet valid" in str(exc_info.value).lower()

    def test_kid_injection_attack(self, token_service):
        """Test protection against Key ID (kid) injection attack."""
        # Attacker tries to inject file path in kid header
        malicious_header = {
            "alg": "HS256",
            "typ": "JWT",
            "kid": "../../../../../../etc/passwd",  # Path traversal attempt
        }

        payload = {
            "sub": "user_123",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }

        # Create token with malicious kid
        token_parts = [
            base64.urlsafe_b64encode(json.dumps(malicious_header).encode()).decode().rstrip("="),
            base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("="),
        ]

        # Add fake signature
        fake_signature = base64.urlsafe_b64encode(b"fake_signature").decode().rstrip("=")
        malicious_token = ".".join(token_parts + [fake_signature])

        with pytest.raises(SecurityViolationError) as exc_info:
            token_service.validate_token(malicious_token)

        assert "invalid kid" in str(exc_info.value).lower()

    def test_jku_injection_attack(self, token_service):
        """Test protection against JKU (JWK Set URL) injection attack."""
        # Attacker tries to inject malicious JWK URL
        malicious_header = {
            "alg": "RS256",
            "typ": "JWT",
            "jku": "http://evil.com/jwks.json",  # Malicious JWKS URL
        }

        payload = {
            "sub": "user_123",
            "roles": ["admin"],
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }

        # Create token with malicious jku
        token_parts = [
            base64.urlsafe_b64encode(json.dumps(malicious_header).encode()).decode().rstrip("="),
            base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("="),
        ]

        fake_signature = base64.urlsafe_b64encode(b"fake_signature").decode().rstrip("=")
        malicious_token = ".".join(token_parts + [fake_signature])

        with pytest.raises(SecurityViolationError) as exc_info:
            token_service.validate_token(malicious_token)

        assert "jku not allowed" in str(exc_info.value).lower()

    def test_token_size_limit(self, security_validator):
        """Test protection against oversized tokens (DoS prevention)."""
        # Create oversized payload
        large_payload = {
            "sub": "user_123",
            "data": "x" * 100000,  # 100KB of data
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }

        oversized_token = jwt.encode(
            large_payload,
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
        )

        with pytest.raises(SecurityViolationError) as exc_info:
            security_validator.validate_token_size(oversized_token)

        assert "token too large" in str(exc_info.value).lower()

    def test_timing_attack_resistance(self, token_service):
        """Test resistance to timing attacks on signature verification."""
        valid_token = jwt.encode(
            {
                "sub": "user_123",
                "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            },
            "test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
        )

        # Create tokens with incrementally different signatures
        parts = valid_token.split(".")
        base_signature = parts[2]

        timing_results = []

        for i in range(10):
            # Modify signature slightly
            modified_signature = base_signature[:-i] + "x" * i if i > 0 else base_signature
            test_token = f"{parts[0]}.{parts[1]}.{modified_signature}"

            import time
            start = time.perf_counter()

            try:
                token_service.validate_token(test_token)
            except:
                pass

            end = time.perf_counter()
            timing_results.append(end - start)

        # Check that timing differences are minimal (constant time comparison)
        import statistics
        std_dev = statistics.stdev(timing_results)
        assert std_dev < 0.001  # Less than 1ms standard deviation

    def test_csrf_token_binding(self, token_service):
        """Test CSRF protection with token binding."""
        csrf_token = "csrf_token_123"

        # Create token bound to CSRF token
        token = token_service.generate_bound_token(
            user_id="user_123",
            csrf_token=csrf_token,
        )

        # Validation should succeed with correct CSRF token
        payload = token_service.validate_bound_token(token, csrf_token)
        assert payload.user_id == "user_123"

        # Validation should fail with incorrect CSRF token
        with pytest.raises(SecurityViolationError) as exc_info:
            token_service.validate_bound_token(token, "wrong_csrf_token")

        assert "csrf token mismatch" in str(exc_info.value).lower()

    def test_token_fingerprinting(self, token_service):
        """Test token fingerprinting for additional security."""
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        ip_address = "192.168.1.1"

        # Create fingerprinted token
        token = token_service.generate_fingerprinted_token(
            user_id="user_123",
            user_agent=user_agent,
            ip_address=ip_address,
        )

        # Validation should succeed with correct fingerprint
        payload = token_service.validate_fingerprinted_token(
            token,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        assert payload.user_id == "user_123"

        # Validation should fail with different fingerprint
        with pytest.raises(SecurityViolationError) as exc_info:
            token_service.validate_fingerprinted_token(
                token,
                user_agent="Different Browser",
                ip_address=ip_address,
            )

        assert "fingerprint mismatch" in str(exc_info.value).lower()