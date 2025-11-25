"""
User registration endpoint implementation.
POST /auth/register
"""

from fastapi import APIRouter, HTTPException, Header, Request
from typing import Optional
import uuid
from datetime import datetime

from ..models.requests import RegisterRequest
from ..models.responses import UserResponse, ErrorResponse, ErrorDetail
from ..validators.email import EmailValidator
from ..validators.password import PasswordValidator
from ..middleware.rate_limiter import RateLimiter


router = APIRouter()


@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        409: {"model": ErrorResponse, "description": "User already exists"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    },
    summary="Register new user",
    description="Create a new user account"
)
async def register_user(
    request: RegisterRequest,
    req: Request,
    rate_limiter: RateLimiter,
    user_service,  # Injected service
    x_request_id: Optional[str] = Header(None)
):
    """
    Register a new user account.

    Validates email and password requirements,
    ensures email uniqueness, and creates user record.
    """
    # Rate limiting check
    client_ip = req.client.host
    rate_result = rate_limiter.check_rate_limit(f"register:{client_ip}")

    if not rate_result.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests, please try again later",
                    "details": {"retry_after": rate_result.retry_after},
                    "request_id": x_request_id
                }
            },
            headers=rate_limiter.get_headers(rate_result)
        )

    # Validate email format
    valid, error = EmailValidator.validate(request.email)
    if not valid:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters",
                    "details": {"field": "email", "reason": error},
                    "request_id": x_request_id
                }
            }
        )

    # Validate password strength
    valid, error = PasswordValidator.validate(request.password)
    if not valid:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters",
                    "details": {"field": "password", "reason": error},
                    "request_id": x_request_id
                }
            }
        )

    # Check if user already exists
    normalized_email = EmailValidator.normalize(request.email)
    if await user_service.user_exists(normalized_email):
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "USER_EXISTS",
                    "message": "User with this email already exists",
                    "request_id": x_request_id
                }
            }
        )

    # Hash password
    hashed_password = PasswordValidator.hash(request.password)

    # Create user
    user = await user_service.create_user(
        email=normalized_email,
        username=request.username,
        password_hash=hashed_password
    )

    # Return user response with rate limit headers
    response_headers = rate_limiter.get_headers(rate_result)

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        created_at=user.created_at
    )