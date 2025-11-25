# JWT Authentication API Design Decisions

## Overview

This document explains the design decisions for the JWT authentication API, following principles of ruthless simplicity and clear contracts.

## Key Design Decisions

### 1. Single-Purpose Endpoints

Each endpoint has ONE clear responsibility:
- `/auth/register` - Create user account
- `/auth/login` - Authenticate and get tokens
- `/auth/refresh` - Exchange refresh token
- `/auth/logout` - Blacklist tokens
- `/auth/verify` - Check token validity
- `/auth/revoke` - Admin token revocation

No combined operations, no ambiguous endpoints.

### 2. Token Storage Strategy

**Access Token**: Authorization header
- Standard Bearer token format
- 15-minute expiry for security
- Stateless validation via RSA public key

**Refresh Token**: httpOnly cookie
- Prevents XSS attacks
- 7-day expiry for convenience
- Secure, SameSite=Strict flags

This split provides security (httpOnly refresh) with convenience (header access).

### 3. RSA-256 Over HMAC

Chose RSA-256 for JWT signing because:
- Public key can verify without exposing signing capability
- Microservices can validate tokens independently
- Key rotation is simpler
- Industry standard for distributed systems

### 4. Structured Error Responses

Single error format across all endpoints:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human message",
    "details": {},
    "request_id": "uuid"
  }
}
```

Benefits:
- Consistent client error handling
- Machine-readable codes
- Human-friendly messages
- Debugging via request_id

### 5. Rate Limiting Design

Sliding window algorithm with Redis:
- 5 requests per minute default
- Per-IP for unauthenticated endpoints
- Standard headers (X-RateLimit-*)
- Retry-After for 429 responses

Simple, effective, standard.

### 6. Validation Rules

**Email**:
- RFC 5322 compliant
- Case-insensitive storage
- 255 character limit

**Password**:
- 8-128 characters
- Requires: uppercase, lowercase, digit, special
- Bcrypt with 12 rounds

**Username**:
- 3-30 characters
- Alphanumeric + underscore/hyphen
- Display only, not for login

### 7. Token Blacklisting

Necessary for logout and revocation:
- Redis SET with token ID
- TTL matches token expiry
- Check on every request
- Minimal performance impact

### 8. No Unnecessary Complexity

What we DON'T include:
- OAuth2/OpenID Connect (overkill for simple JWT)
- Multiple auth methods (just email/password)
- Password reset in core API (separate concern)
- User profiles (separate service)
- Permission system (separate service)
- Email verification (separate workflow)

## API Versioning Strategy

Started with v1, will stay there until:
- Breaking changes are unavoidable
- Major architectural shift
- Deprecation of core features

Adding optional fields doesn't require new version.

## Security Considerations

1. **Timing Attacks**: Same error for invalid email vs password
2. **Token Storage**: Never log or return full tokens
3. **HTTPS Only**: Enforce TLS in production
4. **Cookie Security**: httpOnly, Secure, SameSite
5. **Rate Limiting**: Prevent brute force
6. **Input Validation**: Strict regex patterns
7. **Token Rotation**: New refresh token on use

## Testing Strategy

Contract-first testing:
1. OpenAPI spec is source of truth
2. Models validated against spec
3. Endpoints tested against spec
4. Integration tests verify flow

## Module Structure

```
auth_module/
├── openapi.yaml       # THE contract
├── routes/           # Endpoint handlers
├── models/           # Request/response
├── validators/       # Input validation
├── services/         # Business logic
├── middleware/       # Cross-cutting
├── constants/        # Error codes
└── tests/           # Contract tests
```

Each directory has single responsibility.

## Why This Design Works

1. **Clear Contract**: OpenAPI spec defines everything
2. **Simple Implementation**: Each file does one thing
3. **Testable**: Contract tests ensure compliance
4. **Maintainable**: Clear boundaries, no surprises
5. **Secure**: Industry standard practices
6. **Scalable**: Stateless, distributable

## What Could Be Added Later

If needed (but not in core):
- Two-factor authentication
- Social login providers
- Password reset flow
- Email verification
- Session management
- API key authentication
- Webhook events

These are separate modules, not core JWT auth.

## Summary

This API design prioritizes:
- Clarity over flexibility
- Security over convenience
- Simplicity over features
- Standards over innovation

The result: A JWT authentication API that just works, every time, without surprises.