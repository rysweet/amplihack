# JWT Authentication Security Requirements

## Executive Summary

This document outlines comprehensive security requirements for implementing JWT authentication in the Amplihack system, ensuring compliance with OWASP guidelines and industry best practices.

## 1. Key Generation and Storage (RSA-256)

### Requirements

#### 1.1 RSA Key Generation
- **Key Size**: Minimum 2048 bits, recommended 4096 bits for production
- **Algorithm**: RSA-256 (RS256) for asymmetric signing
- **Key Format**: PEM format with proper encoding
- **Generation Method**: Use cryptographically secure random number generator (CSRNG)

```python
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Generate private key
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=4096,  # 4096 bits for production
    backend=default_backend()
)

# Serialize private key with encryption
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.BestAvailableEncryption(b'strong_passphrase')
)

# Extract public key
public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
```

#### 1.2 Secure Key Storage
- **Private Keys**: NEVER store in code, configuration files, or version control
- **Storage Options**:
  1. **Environment Variables**: For development only
  2. **Hardware Security Module (HSM)**: Preferred for production
  3. **Key Management Service (KMS)**: Azure Key Vault, AWS KMS, HashiCorp Vault
  4. **File System**: Encrypted files with restrictive permissions (0400)

```python
# File system storage with proper permissions
import os
from pathlib import Path

key_path = Path("/secure/keys/jwt_private.pem")
key_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
key_path.write_bytes(private_pem)
os.chmod(key_path, 0o400)  # Read-only for owner
```

## 2. Key Rotation Strategy

### 2.1 Rotation Schedule
- **Primary Key Rotation**: Every 90 days minimum
- **Emergency Rotation**: Immediate upon compromise detection
- **Grace Period**: 24 hours overlap for old key acceptance

### 2.2 Implementation Strategy

```python
class KeyRotationManager:
    def __init__(self):
        self.rotation_period_days = 90
        self.grace_period_hours = 24
        self.key_versions = {}  # kid -> key mapping

    def rotate_keys(self):
        """Rotate keys with overlap period"""
        # Generate new key
        new_key = self.generate_new_key()
        new_kid = self.generate_key_id()

        # Mark current key as secondary
        if self.current_key:
            self.key_versions[self.current_kid]['status'] = 'secondary'
            self.key_versions[self.current_kid]['expires_at'] = (
                datetime.utcnow() + timedelta(hours=self.grace_period_hours)
            )

        # Add new key as primary
        self.key_versions[new_kid] = {
            'key': new_key,
            'status': 'primary',
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(days=self.rotation_period_days)
        }

        # Schedule cleanup of expired keys
        self.schedule_key_cleanup()
```

### 2.3 Key Distribution
- Use JWKS (JSON Web Key Set) endpoint for public key distribution
- Include key ID (kid) in JWT header
- Cache public keys with appropriate TTL

## 3. Token Security Best Practices

### 3.1 Token Structure
```python
# Secure JWT payload structure
jwt_payload = {
    # Standard claims
    "iss": "https://api.amplihack.com",  # Issuer
    "sub": user_id,                      # Subject (user ID)
    "aud": "amplihack-api",              # Audience
    "exp": timestamp + 900,              # Expiration (15 minutes)
    "nbf": timestamp,                     # Not before
    "iat": timestamp,                     # Issued at
    "jti": uuid.uuid4().hex,             # JWT ID (unique)

    # Custom claims
    "roles": ["user"],
    "permissions": ["read", "write"],
    "session_id": session_id,
    "ip_address": request_ip,  # For additional validation
}
```

### 3.2 Token Lifetime
- **Access Token**: 15 minutes maximum
- **Refresh Token**: 7 days with rotation on use
- **Session Binding**: Tie tokens to specific sessions

### 3.3 Token Storage (Client-side)
- **Browser**: httpOnly, secure, sameSite cookies
- **Mobile**: Secure keychain/keystore
- **NEVER**: localStorage or sessionStorage for sensitive tokens

## 4. Prevention of Common Attacks

### 4.1 Token Replay Attacks

**Prevention Mechanisms:**
```python
class ReplayPrevention:
    def __init__(self):
        self.used_tokens = {}  # jti -> expiration

    def validate_token(self, token):
        claims = decode_token(token)
        jti = claims.get('jti')

        # Check if token was already used
        if jti in self.used_tokens:
            raise SecurityError("Token replay detected")

        # Mark token as used
        self.used_tokens[jti] = claims['exp']

        # Cleanup expired entries periodically
        self.cleanup_expired_tokens()

    def cleanup_expired_tokens(self):
        current_time = time.time()
        self.used_tokens = {
            jti: exp for jti, exp in self.used_tokens.items()
            if exp > current_time
        }
```

### 4.2 JWT Algorithm Confusion

**Prevention:**
```python
import jwt

ALLOWED_ALGORITHMS = ['RS256']  # Only allow RSA-256

def decode_token(token, public_key):
    try:
        # Explicitly specify allowed algorithms
        payload = jwt.decode(
            token,
            public_key,
            algorithms=ALLOWED_ALGORITHMS,  # Critical: prevent algorithm confusion
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": True,
                "require": ["exp", "iat", "nbf", "aud", "iss", "sub", "jti"]
            }
        )
        return payload
    except jwt.InvalidAlgorithmError:
        raise SecurityError("Invalid algorithm")
```

### 4.3 Signature Stripping

**Prevention:**
```python
def validate_token_format(token):
    """Ensure token has all three parts"""
    parts = token.split('.')
    if len(parts) != 3:
        raise SecurityError("Invalid token format")

    # Ensure signature exists and is not empty
    if not parts[2]:
        raise SecurityError("Missing signature")

    return True
```

### 4.4 Token Sidejacking

**Prevention:**
```python
class SessionValidator:
    def validate_token_binding(self, token, request):
        claims = decode_token(token)

        # Validate IP address binding
        if claims.get('ip_address') != request.remote_addr:
            raise SecurityError("IP address mismatch")

        # Validate user agent
        if claims.get('user_agent_hash') != hash(request.user_agent):
            raise SecurityError("User agent mismatch")

        # Validate TLS session
        if hasattr(request, 'ssl_session_id'):
            if claims.get('tls_session') != request.ssl_session_id:
                raise SecurityError("TLS session mismatch")
```

## 5. Secure Password Handling

### 5.1 Password Hashing
```python
import bcrypt
from argon2 import PasswordHasher
import secrets

class PasswordManager:
    def __init__(self):
        # Use Argon2id (recommended by OWASP)
        self.ph = PasswordHasher(
            time_cost=3,       # iterations
            memory_cost=65536, # 64MB
            parallelism=4,     # threads
            hash_len=32,       # output length
            salt_len=16        # salt length
        )

    def hash_password(self, password: str) -> str:
        """Hash password with Argon2id"""
        return self.ph.hash(password)

    def verify_password(self, password: str, hash: str) -> bool:
        """Verify password with automatic rehashing if needed"""
        try:
            self.ph.verify(hash, password)

            # Check if rehashing is needed (parameters changed)
            if self.ph.check_needs_rehash(hash):
                return True, self.ph.hash(password)  # Return new hash
            return True, None
        except:
            return False, None
```

### 5.2 Password Requirements
- **Minimum Length**: 12 characters
- **Complexity**: Not required if length >= 16 (per NIST)
- **Password History**: Prevent reuse of last 12 passwords
- **Password Age**: Maximum 365 days, minimum 1 day

### 5.3 Password Reset Security
```python
def generate_reset_token(user_id):
    """Generate secure password reset token"""
    token = secrets.token_urlsafe(32)

    # Store with expiration
    redis_client.setex(
        f"reset:{token}",
        300,  # 5 minutes expiration
        json.dumps({
            "user_id": user_id,
            "attempts": 0,
            "created_at": time.time()
        })
    )

    return token
```

## 6. Rate Limiting Implementation

### 6.1 Rate Limiting Strategy
```python
from functools import wraps
import redis
import time

class RateLimiter:
    def __init__(self):
        self.redis = redis.Redis()

    def limit(self, key_prefix, max_requests=10, window=60):
        """Sliding window rate limiter"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate rate limit key
                key = f"{key_prefix}:{request.remote_addr}"

                # Current timestamp
                now = time.time()
                window_start = now - window

                # Remove old entries
                self.redis.zremrangebyscore(key, 0, window_start)

                # Count requests in window
                request_count = self.redis.zcard(key)

                if request_count >= max_requests:
                    raise RateLimitExceeded(
                        f"Rate limit exceeded: {max_requests} requests per {window} seconds"
                    )

                # Add current request
                self.redis.zadd(key, {str(now): now})
                self.redis.expire(key, window + 1)

                return func(*args, **kwargs)
            return wrapper
        return decorator
```

### 6.2 Rate Limit Configuration
```python
RATE_LIMITS = {
    "login": {"requests": 5, "window": 300},      # 5 attempts per 5 minutes
    "register": {"requests": 3, "window": 3600},  # 3 per hour
    "api_default": {"requests": 100, "window": 60}, # 100 per minute
    "password_reset": {"requests": 3, "window": 3600}, # 3 per hour
}
```

## 7. Audit Logging Requirements

### 7.1 Events to Log
```python
AUDIT_EVENTS = {
    # Authentication events
    "AUTH_LOGIN_SUCCESS": "info",
    "AUTH_LOGIN_FAILURE": "warning",
    "AUTH_LOGOUT": "info",
    "AUTH_TOKEN_ISSUED": "info",
    "AUTH_TOKEN_REFRESHED": "info",
    "AUTH_TOKEN_REVOKED": "warning",

    # Security events
    "SEC_INVALID_TOKEN": "warning",
    "SEC_TOKEN_EXPIRED": "info",
    "SEC_RATE_LIMIT_EXCEEDED": "warning",
    "SEC_REPLAY_ATTACK": "critical",
    "SEC_ALGORITHM_CONFUSION": "critical",

    # Password events
    "PWD_RESET_REQUESTED": "info",
    "PWD_RESET_COMPLETED": "info",
    "PWD_CHANGE": "info",

    # Key management
    "KEY_ROTATION": "info",
    "KEY_COMPROMISE": "critical",
}
```

### 7.2 Log Format
```python
import json
import time

class AuditLogger:
    def log_event(self, event_type, user_id=None, details=None):
        log_entry = {
            "timestamp": time.time(),
            "event_type": event_type,
            "severity": AUDIT_EVENTS.get(event_type, "info"),
            "user_id": user_id,
            "ip_address": request.remote_addr,
            "user_agent": request.user_agent.string,
            "session_id": session.get('id'),
            "details": details,
            "correlation_id": request.headers.get('X-Correlation-Id')
        }

        # Write to secure audit log
        audit_logger.log(json.dumps(log_entry))

        # Send to SIEM if configured
        if self.siem_enabled:
            self.send_to_siem(log_entry)
```

### 7.3 Log Retention
- **Retention Period**: Minimum 90 days, recommended 1 year
- **Storage**: Encrypted, write-only append log
- **Access Control**: Restricted to security team
- **Integrity**: Use hash chaining or digital signatures

## 8. CORS Configuration for Tokens

### 8.1 CORS Headers
```python
from flask_cors import CORS

CORS_CONFIG = {
    "origins": ["https://app.amplihack.com"],  # Explicit whitelist
    "methods": ["GET", "POST"],
    "allow_headers": ["Content-Type", "Authorization"],
    "expose_headers": ["X-Total-Count", "X-Page"],
    "supports_credentials": True,  # Required for cookies
    "max_age": 3600
}

@app.after_request
def apply_cors(response):
    origin = request.headers.get('Origin')

    # Validate origin against whitelist
    if origin in CORS_CONFIG["origins"]:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'

        if request.method == 'OPTIONS':
            response.headers['Access-Control-Allow-Methods'] = ','.join(CORS_CONFIG["methods"])
            response.headers['Access-Control-Allow-Headers'] = ','.join(CORS_CONFIG["allow_headers"])
            response.headers['Access-Control-Max-Age'] = str(CORS_CONFIG["max_age"])

    return response
```

### 8.2 Preflight Handling
```python
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", request.headers.get("Origin"))
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "GET,POST,PUT,DELETE,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', "true")
        return response
```

## 9. Security Headers

### 9.1 Required Headers
```python
class SecurityHeaders:
    @staticmethod
    def apply(response):
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://api.amplihack.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        # Strict Transport Security
        response.headers['Strict-Transport-Security'] = (
            'max-age=31536000; includeSubDomains; preload'
        )

        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions Policy (formerly Feature Policy)
        response.headers['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=()'
        )

        return response
```

### 9.2 Cookie Security
```python
def set_auth_cookie(response, token):
    response.set_cookie(
        'auth_token',
        value=token,
        max_age=900,  # 15 minutes
        secure=True,  # HTTPS only
        httponly=True,  # No JavaScript access
        samesite='Strict',  # CSRF protection
        path='/',
        domain='.amplihack.com'
    )
```

## 10. Input Validation and Sanitization

### 10.1 JWT Input Validation
```python
import re
from typing import Optional

class JWTValidator:
    # JWT regex pattern
    JWT_PATTERN = re.compile(
        r'^[A-Za-z0-9_-]{2,}(?:\.[A-Za-z0-9_-]{2,}){2}$'
    )

    @classmethod
    def validate_token_format(cls, token: str) -> bool:
        """Validate JWT format before processing"""
        if not token or not isinstance(token, str):
            return False

        # Check length limits
        if len(token) > 4096:  # Reasonable max length
            return False

        # Check format
        if not cls.JWT_PATTERN.match(token):
            return False

        # Check parts
        parts = token.split('.')
        if len(parts) != 3:
            return False

        # Validate each part is valid base64url
        for part in parts:
            try:
                # Add padding if needed
                padding = 4 - len(part) % 4
                if padding != 4:
                    part += '=' * padding
                base64.urlsafe_b64decode(part)
            except:
                return False

        return True
```

### 10.2 Request Validation
```python
from marshmallow import Schema, fields, validate, ValidationError

class LoginSchema(Schema):
    username = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$')
        ]
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=12, max=128)
    )
    remember_me = fields.Bool(missing=False)

class TokenRefreshSchema(Schema):
    refresh_token = fields.Str(
        required=True,
        validate=validate.Length(min=32, max=512)
    )

def validate_request(schema_class):
    """Decorator for request validation"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            schema = schema_class()
            try:
                data = schema.load(request.get_json())
                request.validated_data = data
            except ValidationError as e:
                return jsonify({"errors": e.messages}), 400
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

### 10.3 SQL Injection Prevention
```python
# Use parameterized queries
def get_user_by_id(user_id: str):
    # SAFE: Parameterized query
    query = "SELECT * FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))

    # UNSAFE: String concatenation
    # query = f"SELECT * FROM users WHERE id = '{user_id}'"
    # cursor.execute(query)
```

### 10.4 XSS Prevention
```python
from markupsafe import Markup, escape

def sanitize_output(data: str) -> str:
    """Sanitize data for HTML output"""
    return escape(data)

def render_user_content(content: str) -> str:
    """Render user content safely"""
    # Sanitize HTML
    safe_content = bleach.clean(
        content,
        tags=['p', 'br', 'strong', 'em', 'u'],
        attributes={},
        strip=True
    )
    return Markup(safe_content)
```

## Implementation Checklist

### Phase 1: Foundation
- [ ] Implement RSA-256 key generation
- [ ] Set up secure key storage (KMS/Vault)
- [ ] Create key rotation mechanism
- [ ] Implement JWKS endpoint

### Phase 2: Token Management
- [ ] Implement token generation with all required claims
- [ ] Add token validation with all security checks
- [ ] Implement refresh token rotation
- [ ] Add token revocation mechanism

### Phase 3: Security Hardening
- [ ] Implement replay attack prevention
- [ ] Add algorithm confusion protection
- [ ] Implement signature validation
- [ ] Add token binding validation

### Phase 4: Password Security
- [ ] Implement Argon2id password hashing
- [ ] Add password complexity requirements
- [ ] Implement secure password reset
- [ ] Add password history tracking

### Phase 5: Rate Limiting & Monitoring
- [ ] Implement sliding window rate limiting
- [ ] Add endpoint-specific limits
- [ ] Set up comprehensive audit logging
- [ ] Configure SIEM integration

### Phase 6: Headers & CORS
- [ ] Configure all security headers
- [ ] Implement CORS with whitelist
- [ ] Set up cookie security flags
- [ ] Add CSP policy

### Phase 7: Input Validation
- [ ] Implement JWT format validation
- [ ] Add request schema validation
- [ ] Implement output sanitization
- [ ] Add SQL injection prevention

### Phase 8: Testing & Validation
- [ ] Security testing (penetration testing)
- [ ] Load testing for rate limiters
- [ ] Token expiration testing
- [ ] Key rotation testing

## Compliance Requirements

### OWASP Compliance
- **OWASP Top 10**: Address all relevant vulnerabilities
- **OWASP ASVS**: Level 2 minimum, Level 3 for sensitive data
- **OWASP JWT Cheat Sheet**: Follow all recommendations

### Regulatory Compliance
- **GDPR**: Token data minimization, right to erasure
- **PCI DSS**: If handling payment data
- **HIPAA**: If handling health data
- **SOC 2**: Audit logging and access controls

## Security Testing Requirements

### 1. Static Analysis
- Run security linters (bandit, safety)
- Dependency vulnerability scanning
- Secret scanning

### 2. Dynamic Testing
```python
# Example security test
def test_algorithm_confusion():
    """Test that 'none' algorithm is rejected"""
    token = create_token_with_algorithm('none')
    with pytest.raises(SecurityError):
        validate_token(token)

def test_replay_attack():
    """Test that replayed tokens are rejected"""
    token = create_valid_token()
    validate_token(token)  # First use
    with pytest.raises(SecurityError):
        validate_token(token)  # Replay attempt
```

### 3. Penetration Testing
- JWT manipulation attacks
- Rate limit bypass attempts
- Session fixation attacks
- CORS bypass attempts

## Monitoring and Alerting

### Key Metrics
- Failed authentication attempts
- Token validation failures
- Rate limit violations
- Key rotation events
- Unusual token patterns

### Alert Thresholds
```python
ALERT_THRESHOLDS = {
    "failed_logins": {"count": 10, "window": 300},
    "invalid_tokens": {"count": 20, "window": 60},
    "rate_limit_violations": {"count": 50, "window": 300},
    "algorithm_confusion_attempts": {"count": 1, "window": 3600},
}
```

## Incident Response

### Security Incident Playbook
1. **Detection**: Automated alerting on security events
2. **Containment**: Automatic token revocation, account lockout
3. **Investigation**: Audit log analysis, correlation
4. **Recovery**: Key rotation, forced re-authentication
5. **Post-Mortem**: Root cause analysis, prevention improvements

## References

- [OWASP JWT Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [RFC 7519 - JSON Web Token](https://tools.ietf.org/html/rfc7519)
- [RFC 8725 - JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [NIST SP 800-63B - Digital Identity Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)