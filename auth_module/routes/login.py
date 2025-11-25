"""
User login endpoint implementation.
POST /auth/login
"""

from fastapi import APIRouter, HTTPException, Response, Request, Header
from typing import Optional

from ..models.requests import LoginRequest
from ..models.responses import LoginResponse, UserResponse, ErrorResponse
from ..validators.email import EmailValidator
from ..validators.password import PasswordValidator
from ..services.jwt_service import JWTService
from ..middleware.rate_limiter import RateLimiter


router = APIRouter()


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    },
    summary="User login",
    description="Authenticate user and receive JWT tokens"
)
async def login_user(
    request: LoginRequest,
    response: Response,
    req: Request,
    jwt_service: JWTService,
    rate_limiter: RateLimiter,
    user_service,  # Injected service
    x_request_id: Optional[str] = Header(None)
):
    """
    Authenticate user and issue JWT tokens.

    Returns access token in response body and
    sets refresh token as httpOnly cookie.
    """
    # Rate limiting check
    client_ip = req.client.host
    rate_result = rate_limiter.check_rate_limit(f"login:{client_ip}")

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

    # Get user by email
    normalized_email = EmailValidator.normalize(request.email)
    user = await user_service.get_user_by_email(normalized_email)

    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                    "request_id": x_request_id
                }
            }
        )

    # Verify password
    if not PasswordValidator.verify(request.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                    "request_id": x_request_id
                }
            }
        )

    # Generate tokens
    access_token, access_expires, access_token_id = jwt_service.create_access_token(
        user_id=str(user.id)
    )

    refresh_token, refresh_expires, refresh_token_id = jwt_service.create_refresh_token(
        user_id=str(user.id)
    )

    # Store token metadata for tracking
    await user_service.store_token_metadata(
        user_id=user.id,
        access_token_id=access_token_id,
        refresh_token_id=refresh_token_id
    )

    # Set refresh token as httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # HTTPS only
        samesite="strict",
        path="/",
        max_age=7 * 24 * 60 * 60  # 7 days in seconds
    )

    # Set rate limit headers
    for header, value in rate_limiter.get_headers(rate_result).items():
        response.headers[header] = value

    return LoginResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=jwt_service.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            created_at=user.created_at
        )
    )