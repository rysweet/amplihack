# JWT Authentication Module

A complete JWT authentication system for FastAPI applications with user management, role-based access control, and token refresh capabilities.

## Quick Start

```python
from fastapi import FastAPI, Depends
from amplihack.auth import auth_router, get_current_user, User

app = FastAPI()
app.include_router(auth_router)

@app.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    return {"message": f"Hello {user.username}!"}
```

## Features

- 🔐 JWT-based authentication
- 👤 User registration and login
- 🔄 Token refresh mechanism
- 🛡️ Protected route middleware
- 👮 Role-based access control (Admin support)
- 🔒 Secure password hashing with bcrypt
- ✅ Comprehensive test suite

## Installation

```bash
pip install -r requirements-auth.txt
```

## Configuration

Set these environment variables in your `.env` file:

```env
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

## Running the Example

```bash
python examples/jwt_api_example.py
```

Visit http://127.0.0.1:8000/docs for the interactive API documentation.

## API Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/auth/register` | POST | Register new user | No |
| `/auth/login` | POST | Login user | No |
| `/auth/refresh` | POST | Refresh tokens | No |
| `/auth/me` | GET | Get current user | Yes |
| `/auth/logout` | POST | Logout user | Yes |

## Testing

```bash
pytest tests/test_auth.py -v
```

## Documentation

See [JWT_AUTHENTICATION.md](/docs/JWT_AUTHENTICATION.md) for complete documentation.

## License

Part of the amplihack project.