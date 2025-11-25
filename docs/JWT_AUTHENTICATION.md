# JWT Authentication System Documentation

## Overview

This JWT (JSON Web Token) authentication system provides secure user authentication and authorization for FastAPI applications. It includes user registration, login, token refresh, and protected route middleware.

## Features

- ✅ User registration with email validation
- ✅ Secure password hashing (bcrypt)
- ✅ JWT access and refresh tokens
- ✅ Protected route middleware
- ✅ Role-based access control (Admin support)
- ✅ Token refresh mechanism
- ✅ Optional authentication for public routes
- ✅ User profile management
- ✅ Comprehensive test suite

## Installation

The authentication system is part of the amplihack package. To use it:

```python
from amplihack.auth import (
    auth_router,
    get_current_user,
    get_current_admin_user,
    User,
    jwt_handler,
)
```

## Required Dependencies

Make sure you have the following dependencies installed:

```bash
pip install fastapi uvicorn[standard] pyjwt[crypto] bcrypt python-dotenv email-validator
```

## Quick Start

### 1. Basic Setup

```python
from fastapi import FastAPI, Depends
from amplihack.auth import auth_router, get_current_user, User

# Create FastAPI app
app = FastAPI()

# Include authentication routes
app.include_router(auth_router)

# Protected route example
@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}!"}
```

### 2. Environment Configuration

Create a `.env` file with the following variables:

```env
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here  # IMPORTANT: Use a strong secret in production  # pragma: allowlist secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

**⚠️ Security Warning:** Never commit your JWT_SECRET_KEY to version control!

### 3. Run the Example Application

```bash
# Run the example API
python examples/jwt_api_example.py

# The API will be available at:
# http://127.0.0.1:8000
# API Documentation: http://127.0.0.1:8000/docs
```

## API Endpoints

### Authentication Endpoints

#### Register a New User

```http
POST /auth/register
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePass123!",  // pragma: allowlist secret
  "full_name": "John Doe"  // Optional
}
```

**Response:**

```json
{
  "id": "uuid-here",
  "username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "created_at": "2024-11-25T10:00:00Z",
  "is_active": true,
  "is_admin": false
}
```

#### Login

```http
POST /auth/login
Content-Type: application/json

{
  "username": "johndoe",  // Or email
  "password": "SecurePass123!"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

#### Refresh Token

```http
POST /auth/refresh?refresh_token=your-refresh-token
```

**Response:**

```json
{
  "access_token": "new-access-token",
  "refresh_token": "new-refresh-token",
  "token_type": "bearer"
}
```

#### Get Current User

```http
GET /auth/me
Authorization: Bearer your-access-token
```

**Response:**

```json
{
  "id": "uuid-here",
  "username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "created_at": "2024-11-25T10:00:00Z",
  "is_active": true,
  "is_admin": false
}
```

## Using Protected Routes

### Basic Authentication

```python
from fastapi import Depends
from amplihack.auth import get_current_user, User

@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    """This route requires authentication."""
    return {"user": current_user.username}
```

### Admin-Only Routes

```python
from amplihack.auth import get_current_admin_user

@app.get("/admin/dashboard")
async def admin_dashboard(admin_user: User = Depends(get_current_admin_user)):
    """This route requires admin privileges."""
    return {"message": f"Welcome admin {admin_user.username}"}
```

### Optional Authentication

```python
from amplihack.auth import get_optional_current_user

@app.get("/public")
async def public_route(user: User = Depends(get_optional_current_user)):
    """Public route with optional authentication."""
    if user:
        return {"message": f"Hello {user.username}"}
    else:
        return {"message": "Hello anonymous"}
```

## Password Requirements

Passwords must meet the following criteria:

- Minimum 8 characters long
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

## Token Structure

### Access Token Payload

```json
{
  "user_id": "uuid-here",
  "username": "johndoe",
  "is_admin": false,
  "type": "access",
  "exp": 1234567890 // Expiration timestamp
}
```

### Refresh Token Payload

```json
{
  "user_id": "uuid-here",
  "username": "johndoe",
  "is_admin": false,
  "type": "refresh",
  "exp": 1234567890 // Expiration timestamp
}
```

## User Storage

By default, users are stored in a JSON file at `~/.amplihack/users.json`. You can customize the storage location:

```python
from amplihack.auth.user_store import UserStore

# Custom storage location
user_store = UserStore(storage_path="/path/to/users.json")
```

## Testing the Authentication System

### Run Tests

```bash
# Run authentication tests
pytest tests/test_auth.py -v

# Run with coverage
pytest tests/test_auth.py --cov=amplihack.auth
```

### Test Examples

```python
# Test user registration
def test_register():
    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!",
    })
    assert response.status_code == 201

# Test login
def test_login():
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "TestPass123!",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

# Test protected route
def test_protected():
    token = login_and_get_token()
    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
```

## Security Best Practices

### 1. JWT Secret Key

- Use a strong, random secret key (at least 32 characters)
- Never hardcode the secret in your code
- Use environment variables or secure key management
- Rotate secrets regularly in production

### 2. Token Expiration

- Keep access tokens short-lived (15-30 minutes recommended)
- Use refresh tokens for longer sessions (7-30 days)
- Implement token blacklisting for logout in production

### 3. HTTPS Only

- Always use HTTPS in production
- Never send tokens over unencrypted connections

### 4. CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization"],
)
```

### 5. Rate Limiting

Consider implementing rate limiting for authentication endpoints to prevent brute force attacks.

## Advanced Usage

### Custom Token Claims

```python
# Add custom claims to tokens
token_data = {
    "user_id": user.id,
    "username": user.username,
    "is_admin": user.is_admin,
    "department": "engineering",  # Custom claim
    "permissions": ["read", "write"],  # Custom claim
}
access_token = jwt_handler.create_access_token(token_data)
```

### Token Blacklisting (Production)

For production use, implement token blacklisting:

```python
# Store revoked tokens in Redis or database
revoked_tokens = set()

def revoke_token(token: str):
    revoked_tokens.add(token)

def is_token_revoked(token: str) -> bool:
    return token in revoked_tokens
```

### Database Integration

For production, replace the file-based user store with a database:

```python
# Example with SQLAlchemy
from sqlalchemy.orm import Session

class UserDB:
    def create_user(self, db: Session, user_data: UserCreate):
        db_user = UserModel(**user_data.dict())
        db.add(db_user)
        db.commit()
        return db_user

    def get_user(self, db: Session, user_id: str):
        return db.query(UserModel).filter(
            UserModel.id == user_id
        ).first()
```

## Troubleshooting

### Common Issues

1. **"Invalid or expired token"**
   - Check if the token has expired
   - Verify JWT_SECRET_KEY is set correctly
   - Ensure you're using the correct token type

2. **"Signature verification failed"**
   - JWT_SECRET_KEY mismatch between encoding and decoding
   - Token has been tampered with

3. **"Token has expired"**
   - Request a new token using the refresh token
   - Adjust ACCESS_TOKEN_EXPIRE_MINUTES if needed

4. **CORS errors in browser**
   - Configure CORS middleware properly
   - Ensure your frontend origin is allowed

## Example Client Code

### Python Client

```python
import requests

# Register
response = requests.post("http://localhost:8000/auth/register", json={
    "username": "user1",
    "email": "user1@example.com",
    "password": "SecurePass123!"
})

# Login
response = requests.post("http://localhost:8000/auth/login", json={
    "username": "user1",
    "password": "SecurePass123!"
})
tokens = response.json()

# Use protected endpoint
headers = {"Authorization": f"Bearer {tokens['access_token']}"}
response = requests.get("http://localhost:8000/protected", headers=headers)
print(response.json())
```

### JavaScript/TypeScript Client

```javascript
// Login
const response = await fetch("http://localhost:8000/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    username: "user1",
    password: "SecurePass123!",
  }),
});

const { access_token, refresh_token } = await response.json();

// Store tokens securely (e.g., httpOnly cookies in production)
localStorage.setItem("access_token", access_token);

// Use protected endpoint
const protectedResponse = await fetch("http://localhost:8000/protected", {
  headers: {
    Authorization: `Bearer ${access_token}`,
  },
});

const data = await protectedResponse.json();
```

## Migration from Existing Systems

If migrating from another authentication system:

1. Export existing user data
2. Hash passwords with bcrypt if not already
3. Import users into the new system
4. Update API endpoints to use new authentication

## Support and Contributing

For issues, questions, or contributions, please refer to the main project documentation.

## License

This authentication system is part of the amplihack project and follows the same license terms.
