# JWT Authentication Module

A minimal, secure JWT authentication module using RSA-256 signing.

## Module Structure

```
auth_module/
├── openapi.yaml      # Complete API contract
├── routes/          # Endpoint implementations
│   ├── register.py
│   ├── login.py
│   ├── refresh.py
│   ├── logout.py
│   ├── verify.py
│   └── revoke.py
├── models/          # Request/response models
│   ├── requests.py
│   └── responses.py
├── validators/      # Input validation
│   ├── email.py
│   ├── password.py
│   └── token.py
├── services/        # Business logic
│   ├── jwt_service.py
│   ├── blacklist_service.py
│   └── user_service.py
├── middleware/      # Request processing
│   ├── rate_limiter.py
│   └── auth_middleware.py
└── tests/          # Contract tests
    ├── test_endpoints.py
    └── test_validators.py
```

## API Endpoints

All endpoints follow the OpenAPI specification in `openapi.yaml`.

### Public Endpoints (No Auth Required)
- `POST /auth/register` - Create new user account
- `POST /auth/login` - Authenticate and receive tokens
- `POST /auth/refresh` - Exchange refresh token for new access token

### Protected Endpoints (Bearer Token Required)
- `POST /auth/logout` - Blacklist current tokens
- `GET /auth/verify` - Verify token validity
- `POST /auth/revoke` - Admin-only token revocation

## Security Features

### Token Management
- **RSA-256** algorithm for JWT signing
- **15-minute** access token expiry
- **7-day** refresh token expiry
- Token blacklisting for logout/revocation
- Unique token IDs for tracking

### Token Storage
- Access tokens: `Authorization: Bearer <token>` header
- Refresh tokens: httpOnly, Secure, SameSite=Strict cookies

### Rate Limiting
- 5 requests per minute per IP/user
- Custom headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- 429 status with `Retry-After` header when exceeded

## Error Handling

Consistent error format across all endpoints:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {},
    "request_id": "uuid"
  }
}
```

### Standard Error Codes
- `VALIDATION_ERROR` - Request validation failed
- `MISSING_FIELD` - Required field missing
- `INVALID_CREDENTIALS` - Authentication failed
- `TOKEN_EXPIRED` - Access token expired
- `TOKEN_INVALID` - Malformed or invalid token
- `TOKEN_BLACKLISTED` - Token has been revoked
- `USER_EXISTS` - Email already registered
- `INSUFFICIENT_PERMISSIONS` - Admin access required
- `TOKEN_NOT_FOUND` - Token doesn't exist
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INTERNAL_ERROR` - Server error

## Implementation Notes

### Password Requirements
- Minimum 8 characters
- Must contain: uppercase, lowercase, number, special character
- Maximum 128 characters
- Bcrypt hashing with salt rounds

### Username Constraints
- 3-30 characters
- Alphanumeric, underscore, hyphen only
- Case-insensitive uniqueness

### Email Validation
- RFC 5322 compliant
- Case-insensitive uniqueness
- Maximum 255 characters

## Testing

Run contract tests to verify implementation matches OpenAPI spec:

```bash
pytest tests/test_endpoints.py
pytest tests/test_validators.py
```

## Dependencies

Required packages:
- `pyjwt[crypto]` - JWT handling with RSA support
- `cryptography` - RSA key management
- `bcrypt` - Password hashing
- `email-validator` - Email validation
- `redis` - Token blacklist storage
- `fastapi` or `flask` - Web framework
- `pydantic` - Request/response validation