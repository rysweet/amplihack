# JWT Authentication Implementation Guide for Amplihack

## Quick Start Implementation

This guide provides practical, production-ready implementation for JWT authentication in the Amplihack proxy system.

## Core JWT Module

### `/src/amplihack/security/jwt_manager.py`

```python
"""
JWT Manager for Amplihack Proxy
Implements secure JWT authentication with RSA-256
"""

import os
import time
import uuid
import json
import redis
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from amplihack.utils.logger import get_logger

logger = get_logger(__name__)


class JWTSecurityConfig:
    """Security configuration for JWT"""

    # Token configuration
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    # RSA key configuration
    RSA_KEY_SIZE = 4096  # Production: 4096, Development: 2048

    # Algorithm configuration
    ALLOWED_ALGORITHMS = ['RS256']

    # Security settings
    REQUIRE_JTI = True  # Require unique JWT ID
    REQUIRE_NBF = True  # Require "not before" claim
    MAX_TOKEN_LENGTH = 4096

    # Rate limiting
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_WINDOW_SECONDS = 300  # 5 minutes

    # Audit events
    AUDIT_EVENTS = {
        "LOGIN_SUCCESS": "info",
        "LOGIN_FAILED": "warning",
        "TOKEN_ISSUED": "info",
        "TOKEN_REFRESHED": "info",
        "TOKEN_REVOKED": "warning",
        "TOKEN_INVALID": "warning",
        "REPLAY_DETECTED": "critical",
        "ALGORITHM_CONFUSION": "critical",
    }


class JWTManager:
    """Secure JWT authentication manager"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize JWT manager with optional Redis for token blacklisting"""
        self.config = JWTSecurityConfig()
        self.redis_client = redis_client or self._init_redis()
        self.password_hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16
        )

        # Initialize keys
        self._init_keys()

        # Track used JTIs for replay prevention
        self.used_jtis = set()

    def _init_redis(self) -> Optional[redis.Redis]:
        """Initialize Redis connection for token management"""
        try:
            client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                decode_responses=True,
                socket_keepalive=True,
                socket_connect_timeout=5
            )
            client.ping()
            logger.info("Redis connection established for JWT management")
            return client
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory storage: {e}")
            return None

    def _init_keys(self):
        """Initialize RSA keys for JWT signing"""
        key_path = Path(os.getenv('JWT_KEY_PATH', '/secure/keys'))
        private_key_path = key_path / 'jwt_private.pem'
        public_key_path = key_path / 'jwt_public.pem'

        if not private_key_path.exists():
            self._generate_keys(private_key_path, public_key_path)

        # Load keys
        self.private_key = self._load_private_key(private_key_path)
        self.public_key = self._load_public_key(public_key_path)

        # Generate key ID for JWKS
        self.key_id = self._generate_key_id()

    def _generate_keys(self, private_path: Path, public_path: Path):
        """Generate new RSA key pair"""
        logger.info("Generating new RSA key pair")

        # Create secure directory
        private_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.config.RSA_KEY_SIZE,
            backend=default_backend()
        )

        # Serialize private key with encryption
        passphrase = os.getenv('JWT_KEY_PASSPHRASE', '').encode()
        if passphrase:
            encryption = serialization.BestAvailableEncryption(passphrase)
        else:
            encryption = serialization.NoEncryption()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption
        )

        # Extract and serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # Write keys with secure permissions
        private_path.write_bytes(private_pem)
        os.chmod(private_path, 0o400)  # Read-only for owner

        public_path.write_bytes(public_pem)
        os.chmod(public_path, 0o444)  # Read-only for all

        logger.info("RSA key pair generated successfully")

    def _load_private_key(self, path: Path):
        """Load private key from file"""
        passphrase = os.getenv('JWT_KEY_PASSPHRASE', '').encode() or None
        with open(path, 'rb') as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=passphrase,
                backend=default_backend()
            )

    def _load_public_key(self, path: Path):
        """Load public key from file"""
        with open(path, 'rb') as f:
            return serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )

    def _generate_key_id(self) -> str:
        """Generate unique key ID for JWKS"""
        return uuid.uuid4().hex[:8]

    def hash_password(self, password: str) -> str:
        """Hash password using Argon2id"""
        return self.password_hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> Tuple[bool, Optional[str]]:
        """
        Verify password and return new hash if rehashing needed
        Returns: (is_valid, new_hash_if_needed)
        """
        try:
            self.password_hasher.verify(password_hash, password)

            # Check if rehashing needed
            if self.password_hasher.check_needs_rehash(password_hash):
                new_hash = self.password_hasher.hash(password)
                return True, new_hash

            return True, None
        except VerifyMismatchError:
            return False, None

    def generate_jti(self) -> str:
        """Generate unique JWT ID"""
        return uuid.uuid4().hex

    def create_access_token(
        self,
        user_id: str,
        roles: list = None,
        permissions: list = None,
        session_id: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> str:
        """Create secure access token"""

        now = datetime.now(timezone.utc)
        jti = self.generate_jti()

        # Build payload with security claims
        payload = {
            # Standard claims
            "iss": os.getenv('JWT_ISSUER', 'https://api.amplihack.com'),
            "sub": user_id,
            "aud": os.getenv('JWT_AUDIENCE', 'amplihack-api'),
            "exp": now + timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES),
            "nbf": now,
            "iat": now,
            "jti": jti,

            # Custom claims
            "type": "access",
            "roles": roles or ["user"],
            "permissions": permissions or [],
        }

        # Add session binding for additional security
        if session_id:
            payload["sid"] = session_id
        if ip_address:
            payload["ip"] = ip_address
        if user_agent:
            payload["ua_hash"] = hash(user_agent)

        # Sign token with private key
        token = jwt.encode(
            payload,
            self.private_key,
            algorithm='RS256',
            headers={"kid": self.key_id}
        )

        # Store JTI for replay prevention
        self._store_jti(jti, payload["exp"])

        # Audit log
        self._audit_log("TOKEN_ISSUED", user_id, {"jti": jti, "type": "access"})

        return token

    def create_refresh_token(
        self,
        user_id: str,
        session_id: str = None
    ) -> str:
        """Create refresh token with rotation"""

        now = datetime.now(timezone.utc)
        jti = self.generate_jti()

        payload = {
            "iss": os.getenv('JWT_ISSUER', 'https://api.amplihack.com'),
            "sub": user_id,
            "aud": os.getenv('JWT_AUDIENCE', 'amplihack-api'),
            "exp": now + timedelta(days=self.config.REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": now,
            "jti": jti,
            "type": "refresh"
        }

        if session_id:
            payload["sid"] = session_id

        token = jwt.encode(
            payload,
            self.private_key,
            algorithm='RS256',
            headers={"kid": self.key_id}
        )

        # Store refresh token metadata
        self._store_refresh_token(user_id, jti, payload["exp"])

        return token

    def validate_token(
        self,
        token: str,
        token_type: str = "access",
        verify_session: bool = True,
        request_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Validate JWT token with comprehensive security checks

        Args:
            token: JWT token to validate
            token_type: Expected token type (access/refresh)
            verify_session: Whether to verify session binding
            request_context: Request context for additional validation

        Returns:
            Decoded token payload

        Raises:
            SecurityError: If token validation fails
        """

        # Format validation
        if not self._validate_format(token):
            self._audit_log("TOKEN_INVALID", None, {"reason": "invalid_format"})
            raise SecurityError("Invalid token format")

        try:
            # Decode with strict validation
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=self.config.ALLOWED_ALGORITHMS,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "require": ["exp", "iat", "nbf", "aud", "iss", "sub", "jti", "type"]
                },
                audience=os.getenv('JWT_AUDIENCE', 'amplihack-api'),
                issuer=os.getenv('JWT_ISSUER', 'https://api.amplihack.com')
            )

            # Verify token type
            if payload.get("type") != token_type:
                raise SecurityError(f"Invalid token type: expected {token_type}")

            # Check replay attack
            if self._is_jti_used(payload["jti"]):
                self._audit_log("REPLAY_DETECTED", payload.get("sub"), {"jti": payload["jti"]})
                raise SecurityError("Token replay detected")

            # Check if token is blacklisted
            if self._is_token_blacklisted(payload["jti"]):
                raise SecurityError("Token has been revoked")

            # Verify session binding if enabled
            if verify_session and request_context:
                self._verify_session_binding(payload, request_context)

            # Mark JTI as used for access tokens
            if token_type == "access":
                self._store_jti(payload["jti"], payload["exp"])

            return payload

        except jwt.InvalidAlgorithmError:
            self._audit_log("ALGORITHM_CONFUSION", None, {"token": token[:20]})
            raise SecurityError("Invalid algorithm")
        except jwt.ExpiredSignatureError:
            raise SecurityError("Token has expired")
        except jwt.InvalidTokenError as e:
            self._audit_log("TOKEN_INVALID", None, {"error": str(e)})
            raise SecurityError(f"Invalid token: {e}")

    def _validate_format(self, token: str) -> bool:
        """Validate JWT format"""
        if not token or not isinstance(token, str):
            return False

        if len(token) > self.config.MAX_TOKEN_LENGTH:
            return False

        parts = token.split('.')
        if len(parts) != 3:
            return False

        # Ensure signature exists
        if not parts[2]:
            return False

        return True

    def _verify_session_binding(self, payload: Dict[str, Any], context: Dict[str, Any]):
        """Verify token is bound to the correct session"""

        # Verify IP address if present
        if "ip" in payload and context.get("ip_address"):
            if payload["ip"] != context["ip_address"]:
                raise SecurityError("IP address mismatch")

        # Verify user agent hash if present
        if "ua_hash" in payload and context.get("user_agent"):
            if payload["ua_hash"] != hash(context["user_agent"]):
                raise SecurityError("User agent mismatch")

        # Verify session ID if present
        if "sid" in payload and context.get("session_id"):
            if payload["sid"] != context["session_id"]:
                raise SecurityError("Session ID mismatch")

    def refresh_access_token(self, refresh_token: str, request_context: Dict[str, Any] = None) -> Tuple[str, str]:
        """
        Refresh access token using refresh token with rotation
        Returns: (new_access_token, new_refresh_token)
        """

        # Validate refresh token
        payload = self.validate_token(
            refresh_token,
            token_type="refresh",
            request_context=request_context
        )

        # Revoke old refresh token
        self.revoke_token(refresh_token)

        # Generate new tokens
        new_access_token = self.create_access_token(
            user_id=payload["sub"],
            session_id=payload.get("sid"),
            ip_address=request_context.get("ip_address") if request_context else None,
            user_agent=request_context.get("user_agent") if request_context else None
        )

        new_refresh_token = self.create_refresh_token(
            user_id=payload["sub"],
            session_id=payload.get("sid")
        )

        self._audit_log("TOKEN_REFRESHED", payload["sub"], {
            "old_jti": payload["jti"],
            "new_jti": jwt.decode(new_access_token, options={"verify_signature": False})["jti"]
        })

        return new_access_token, new_refresh_token

    def revoke_token(self, token: str):
        """Revoke a token by blacklisting its JTI"""
        try:
            # Decode without verification to get JTI
            payload = jwt.decode(token, options={"verify_signature": False})
            jti = payload.get("jti")
            exp = payload.get("exp")

            if jti and exp:
                self._blacklist_token(jti, exp)
                self._audit_log("TOKEN_REVOKED", payload.get("sub"), {"jti": jti})
        except:
            pass  # Silent fail for invalid tokens

    def _store_jti(self, jti: str, exp: datetime):
        """Store JTI for replay prevention"""
        if self.redis_client:
            ttl = int(exp.timestamp() - time.time())
            if ttl > 0:
                self.redis_client.setex(f"jti:{jti}", ttl, "1")
        else:
            self.used_jtis.add(jti)

    def _is_jti_used(self, jti: str) -> bool:
        """Check if JTI has been used"""
        if self.redis_client:
            return bool(self.redis_client.get(f"jti:{jti}"))
        return jti in self.used_jtis

    def _blacklist_token(self, jti: str, exp: datetime):
        """Blacklist a token"""
        if self.redis_client:
            ttl = int(exp.timestamp() - time.time())
            if ttl > 0:
                self.redis_client.setex(f"blacklist:{jti}", ttl, "1")

    def _is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted"""
        if self.redis_client:
            return bool(self.redis_client.get(f"blacklist:{jti}"))
        return False

    def _store_refresh_token(self, user_id: str, jti: str, exp: datetime):
        """Store refresh token metadata"""
        if self.redis_client:
            ttl = int(exp.timestamp() - time.time())
            if ttl > 0:
                self.redis_client.setex(
                    f"refresh:{user_id}:{jti}",
                    ttl,
                    json.dumps({"created": time.time()})
                )

    def _audit_log(self, event: str, user_id: Optional[str], details: Dict[str, Any]):
        """Log security audit event"""
        severity = self.config.AUDIT_EVENTS.get(event, "info")
        log_entry = {
            "timestamp": time.time(),
            "event": event,
            "severity": severity,
            "user_id": user_id,
            "details": details
        }

        logger.log(
            getattr(logger, severity.upper(), logger.INFO),
            f"SECURITY_AUDIT: {json.dumps(log_entry)}"
        )

    def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set for public key distribution"""
        from cryptography.hazmat.primitives import hashes
        from base64 import urlsafe_b64encode

        # Get public key components
        public_numbers = self.public_key.public_numbers()

        # Convert to base64url without padding
        def to_base64url(num: int) -> str:
            byte_length = (num.bit_length() + 7) // 8
            return urlsafe_b64encode(
                num.to_bytes(byte_length, 'big')
            ).decode('ascii').rstrip('=')

        return {
            "keys": [{
                "kty": "RSA",
                "kid": self.key_id,
                "use": "sig",
                "alg": "RS256",
                "n": to_base64url(public_numbers.n),
                "e": to_base64url(public_numbers.e)
            }]
        }


class RateLimiter:
    """Rate limiter for authentication endpoints"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.memory_store = {}  # Fallback for when Redis is unavailable

    def check_rate_limit(
        self,
        key: str,
        max_requests: int = 10,
        window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """
        Check if rate limit exceeded
        Returns: (is_allowed, remaining_requests)
        """

        if self.redis_client:
            return self._check_redis(key, max_requests, window_seconds)
        else:
            return self._check_memory(key, max_requests, window_seconds)

    def _check_redis(self, key: str, max_requests: int, window: int) -> Tuple[bool, int]:
        """Check rate limit using Redis"""
        now = time.time()
        window_start = now - window
        redis_key = f"rate:{key}"

        # Remove old entries
        self.redis_client.zremrangebyscore(redis_key, 0, window_start)

        # Count requests in window
        request_count = self.redis_client.zcard(redis_key)

        if request_count >= max_requests:
            return False, 0

        # Add current request
        self.redis_client.zadd(redis_key, {str(now): now})
        self.redis_client.expire(redis_key, window + 1)

        return True, max_requests - request_count - 1

    def _check_memory(self, key: str, max_requests: int, window: int) -> Tuple[bool, int]:
        """Check rate limit using in-memory storage"""
        now = time.time()
        window_start = now - window

        if key not in self.memory_store:
            self.memory_store[key] = []

        # Remove old entries
        self.memory_store[key] = [
            t for t in self.memory_store[key] if t > window_start
        ]

        # Count requests
        request_count = len(self.memory_store[key])

        if request_count >= max_requests:
            return False, 0

        # Add current request
        self.memory_store[key].append(now)

        return True, max_requests - request_count - 1


def jwt_required(token_type: str = "access"):
    """Decorator to require valid JWT token"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request, g

            # Extract token from header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return {"error": "Missing or invalid authorization header"}, 401

            token = auth_header.split(' ', 1)[1]

            # Get JWT manager instance
            jwt_manager = getattr(g, 'jwt_manager', JWTManager())

            try:
                # Validate token with request context
                payload = jwt_manager.validate_token(
                    token,
                    token_type=token_type,
                    request_context={
                        "ip_address": request.remote_addr,
                        "user_agent": request.user_agent.string,
                        "session_id": request.cookies.get('session_id')
                    }
                )

                # Store user info in context
                g.current_user = {
                    "user_id": payload["sub"],
                    "roles": payload.get("roles", []),
                    "permissions": payload.get("permissions", [])
                }

                return func(*args, **kwargs)

            except SecurityError as e:
                return {"error": str(e)}, 401

        return wrapper
    return decorator


def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        @wraps(func)
        @jwt_required()
        def wrapper(*args, **kwargs):
            from flask import g

            user = g.get('current_user')
            if not user or permission not in user.get('permissions', []):
                return {"error": "Insufficient permissions"}, 403

            return func(*args, **kwargs)

        return wrapper
    return decorator


class SecurityError(Exception):
    """Security-related exception"""
    pass
```

## Integration with Amplihack Proxy

### Update `/src/amplihack/proxy/server.py`

```python
# Add JWT authentication to the proxy server

from amplihack.security.jwt_manager import JWTManager, RateLimiter, jwt_required

class AmplihackProxy:
    def __init__(self):
        # ... existing initialization ...
        self.jwt_manager = JWTManager()
        self.rate_limiter = RateLimiter()

    def setup_routes(self):
        """Setup proxy routes with authentication"""

        @self.app.route('/auth/login', methods=['POST'])
        def login():
            """Authenticate user and issue tokens"""
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')

            # Check rate limit
            ip_key = f"login:{request.remote_addr}"
            allowed, remaining = self.rate_limiter.check_rate_limit(
                ip_key, max_requests=5, window_seconds=300
            )

            if not allowed:
                return {"error": "Too many login attempts"}, 429

            # Authenticate user (implement your user verification)
            user = authenticate_user(username, password)
            if not user:
                return {"error": "Invalid credentials"}, 401

            # Generate tokens
            access_token = self.jwt_manager.create_access_token(
                user_id=user.id,
                roles=user.roles,
                permissions=user.permissions,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )

            refresh_token = self.jwt_manager.create_refresh_token(
                user_id=user.id
            )

            response = jsonify({
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 900  # 15 minutes
            })

            # Set refresh token as httpOnly cookie
            response.set_cookie(
                'refresh_token',
                value=refresh_token,
                max_age=7*24*60*60,  # 7 days
                secure=True,
                httponly=True,
                samesite='Strict'
            )

            return response

        @self.app.route('/auth/refresh', methods=['POST'])
        def refresh():
            """Refresh access token"""
            refresh_token = request.cookies.get('refresh_token')
            if not refresh_token:
                return {"error": "Refresh token required"}, 401

            try:
                access_token, new_refresh_token = self.jwt_manager.refresh_access_token(
                    refresh_token,
                    request_context={
                        "ip_address": request.remote_addr,
                        "user_agent": request.user_agent.string
                    }
                )

                response = jsonify({
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": 900
                })

                # Update refresh token cookie
                response.set_cookie(
                    'refresh_token',
                    value=new_refresh_token,
                    max_age=7*24*60*60,
                    secure=True,
                    httponly=True,
                    samesite='Strict'
                )

                return response

            except SecurityError as e:
                return {"error": str(e)}, 401

        @self.app.route('/auth/logout', methods=['POST'])
        @jwt_required()
        def logout():
            """Logout and revoke tokens"""
            # Get current token
            auth_header = request.headers.get('Authorization')
            if auth_header:
                token = auth_header.split(' ', 1)[1]
                self.jwt_manager.revoke_token(token)

            # Revoke refresh token
            refresh_token = request.cookies.get('refresh_token')
            if refresh_token:
                self.jwt_manager.revoke_token(refresh_token)

            response = jsonify({"message": "Logged out successfully"})
            response.set_cookie('refresh_token', '', expires=0)

            return response

        @self.app.route('/auth/jwks', methods=['GET'])
        def jwks():
            """Public key endpoint for token verification"""
            return jsonify(self.jwt_manager.get_jwks())

        # Protect API routes
        @self.app.route('/api/chat/completions', methods=['POST'])
        @jwt_required()
        def chat_completions():
            """Protected chat completions endpoint"""
            # ... existing chat completion logic ...
```

## Environment Configuration

### Update `.env` file

```bash
# JWT Configuration
JWT_KEY_PATH=/secure/keys
JWT_KEY_PASSPHRASE=your-strong-passphrase-here
JWT_ISSUER=https://api.amplihack.com
JWT_AUDIENCE=amplihack-api

# Redis Configuration (for token management)
REDIS_HOST=localhost
REDIS_PORT=6379

# Security Settings
ENABLE_JWT_AUTH=true
JWT_ACCESS_TOKEN_MINUTES=15
JWT_REFRESH_TOKEN_DAYS=7
```

## Testing Implementation

### `/tests/test_jwt_security.py`

```python
import pytest
import time
from amplihack.security.jwt_manager import JWTManager, RateLimiter, SecurityError

class TestJWTSecurity:

    def test_token_generation_and_validation(self):
        """Test basic token generation and validation"""
        manager = JWTManager()

        # Generate token
        token = manager.create_access_token(
            user_id="test_user",
            roles=["user"],
            permissions=["read"]
        )

        # Validate token
        payload = manager.validate_token(token)
        assert payload["sub"] == "test_user"
        assert payload["type"] == "access"

    def test_replay_attack_prevention(self):
        """Test that replayed tokens are rejected"""
        manager = JWTManager()

        token = manager.create_access_token(user_id="test_user")

        # First validation should succeed
        manager.validate_token(token)

        # Replay should fail
        with pytest.raises(SecurityError, match="replay"):
            manager.validate_token(token)

    def test_algorithm_confusion_prevention(self):
        """Test that 'none' algorithm is rejected"""
        manager = JWTManager()

        # Create token with 'none' algorithm (manually)
        import jwt
        payload = {"sub": "test_user", "exp": time.time() + 900}
        bad_token = jwt.encode(payload, "", algorithm="none")

        with pytest.raises(SecurityError):
            manager.validate_token(bad_token)

    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        limiter = RateLimiter()

        key = "test_key"

        # First 5 requests should succeed
        for i in range(5):
            allowed, remaining = limiter.check_rate_limit(key, max_requests=5, window_seconds=60)
            assert allowed

        # 6th request should be blocked
        allowed, remaining = limiter.check_rate_limit(key, max_requests=5, window_seconds=60)
        assert not allowed
        assert remaining == 0

    def test_token_expiration(self):
        """Test that expired tokens are rejected"""
        manager = JWTManager()

        # Create token with very short expiration
        import jwt
        from datetime import datetime, timedelta, timezone

        payload = {
            "sub": "test_user",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }

        expired_token = jwt.encode(payload, manager.private_key, algorithm="RS256")

        with pytest.raises(SecurityError, match="expired"):
            manager.validate_token(expired_token)
```

## Deployment Checklist

### Security Hardening

- [ ] Generate production RSA keys (4096 bits)
- [ ] Store keys in secure location (KMS/Vault)
- [ ] Configure Redis for token management
- [ ] Set up key rotation schedule
- [ ] Enable audit logging
- [ ] Configure rate limiting
- [ ] Set up monitoring and alerting
- [ ] Implement HTTPS/TLS
- [ ] Configure security headers
- [ ] Set up CORS properly
- [ ] Enable CSRF protection
- [ ] Implement input validation
- [ ] Set up log aggregation
- [ ] Configure backup authentication methods
- [ ] Document incident response procedures

### Performance Optimization

- [ ] Configure Redis connection pooling
- [ ] Implement token caching
- [ ] Optimize key loading
- [ ] Set up horizontal scaling
- [ ] Configure load balancing
- [ ] Implement circuit breakers
- [ ] Set up health checks

### Monitoring

- [ ] Track authentication metrics
- [ ] Monitor token validation performance
- [ ] Alert on suspicious patterns
- [ ] Track rate limit violations
- [ ] Monitor key rotation events
- [ ] Set up dashboard for security events

## Additional Security Recommendations

1. **Use a Web Application Firewall (WAF)** to filter malicious requests
2. **Implement IP allowlisting** for admin endpoints
3. **Use mutual TLS (mTLS)** for service-to-service communication
4. **Regular security audits** and penetration testing
5. **Implement account lockout** after repeated failed attempts
6. **Use secure session management** alongside JWT
7. **Implement device fingerprinting** for additional validation
8. **Regular dependency updates** and vulnerability scanning
9. **Implement API versioning** for backward compatibility
10. **Use centralized logging** with tamper protection