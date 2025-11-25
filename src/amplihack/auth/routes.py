"""Authentication routes for the API."""
# ruff: noqa: B008  # Depends() in argument defaults is the FastAPI pattern

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .jwt_handler import jwt_handler
from .middleware import get_current_user, jwt_bearer
from .models import TokenResponse, User, UserCreate, UserLogin, UserResponse
from .rate_limiter import general_rate_limiter, login_rate_limiter, register_rate_limiter
from .user_store import user_store

# Create router for authentication endpoints
auth_router = APIRouter(prefix="/auth", tags=["authentication"])

# Configure logger
logger = logging.getLogger(__name__)


async def check_rate_limit(request: Request, rate_limiter):
    """Check rate limit for the given request."""
    client_ip = request.client.host if request.client else "unknown"
    allowed, remaining = rate_limiter.is_allowed(client_ip)

    if not allowed:
        reset_time = rate_limiter.get_reset_time(client_ip)
        logger.warning(f"Rate limit exceeded for IP {client_ip} on {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={
                "X-RateLimit-Limit": str(rate_limiter.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": reset_time.isoformat(),
            }
        )

    return remaining


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, request: Request):
    """
    Register a new user.

    Args:
        user_data: User registration data
        request: The request object (for rate limiting)

    Returns:
        The created user (without sensitive data)

    Raises:
        HTTPException: If username or email already exists or rate limit exceeded
    """
    # Check rate limit
    await check_rate_limit(request, register_rate_limiter)

    try:
        user = user_store.create_user(user_data)
        logger.info(f"User registered successfully: {user.username} (ID: {user.id})")
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at,
            is_active=user.is_active,
            is_admin=user.is_admin,
        )
    except ValueError as e:
        logger.warning(f"Registration failed for username '{user_data.username}': {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, request: Request):
    """
    Login a user and get access/refresh tokens.

    Args:
        login_data: User login credentials
        request: The request object (for rate limiting)

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid or rate limit exceeded
    """
    # Check rate limit
    await check_rate_limit(request, login_rate_limiter)

    # Authenticate user
    user = user_store.authenticate_user(login_data.username, login_data.password)

    if not user:
        logger.warning(f"Failed login attempt for username: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password"
        )

    # Create tokens
    token_data = {"user_id": user.id, "username": user.username, "is_admin": user.is_admin}

    access_token = jwt_handler.create_access_token(token_data)
    refresh_token = jwt_handler.create_refresh_token(token_data)

    logger.info(f"User logged in successfully: {user.username} (ID: {user.id})")

    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, request: Request):
    """
    Refresh access token using a refresh token.

    Args:
        refresh_token: The refresh token
        request: The request object (for rate limiting)

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid or rate limit exceeded
    """
    # Check rate limit (use general limiter for refresh)
    await check_rate_limit(request, general_rate_limiter)

    try:
        # Verify refresh token
        payload = jwt_handler.verify_refresh_token(refresh_token)
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        # Get user
        user = user_store.get_user(user_id)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
            )

        # Create new tokens
        token_data = {"user_id": user.id, "username": user.username, "is_admin": user.is_admin}

        new_access_token = jwt_handler.create_access_token(token_data)
        new_refresh_token = jwt_handler.create_refresh_token(token_data)

        return TokenResponse(
            access_token=new_access_token, refresh_token=new_refresh_token, token_type="bearer"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid refresh token: {e!s}"
        )


@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.

    Args:
        current_user: The authenticated user

    Returns:
        User information (without sensitive data)
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        created_at=current_user.created_at,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )


@auth_router.post("/logout")
async def logout(token: str = Depends(jwt_bearer)):
    """
    Logout a user by blacklisting their token.

    The token will be added to the blacklist and will no longer be valid
    for authentication, even if it hasn't expired yet.

    Args:
        token: The current access token

    Returns:
        Logout confirmation message
    """
    # Add the token to the blacklist
    jwt_handler.blacklist_token(token)

    # Log the logout event (don't log the full token for security)
    token_preview = f"{token[:10]}..." if len(token) > 10 else token
    logger.info(f"User logged out, token blacklisted: {token_preview}")

    return {"message": "Successfully logged out", "detail": "Token has been invalidated"}


@auth_router.put("/me", response_model=UserResponse)
async def update_current_user(
    full_name: Optional[str] = None, current_user: User = Depends(get_current_user)
):
    """
    Update current user information.

    Args:
        full_name: New full name (optional)
        current_user: The authenticated user

    Returns:
        Updated user information
    """
    update_data = {}

    if full_name is not None:
        update_data["full_name"] = full_name

    if update_data:
        updated_user = user_store.update_user(current_user.id, update_data)

        if updated_user:
            return UserResponse(
                id=updated_user.id,
                username=updated_user.username,
                email=updated_user.email,
                full_name=updated_user.full_name,
                created_at=updated_user.created_at,
                is_active=updated_user.is_active,
                is_admin=updated_user.is_admin,
            )

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        created_at=current_user.created_at,
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
    )
