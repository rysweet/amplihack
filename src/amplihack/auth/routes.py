"""Authentication routes for the API."""
# ruff: noqa: B008  # Depends() in argument defaults is the FastAPI pattern

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from .jwt_handler import jwt_handler
from .middleware import get_current_user, jwt_bearer
from .models import TokenResponse, User, UserCreate, UserLogin, UserResponse
from .user_store import user_store

# Create router for authentication endpoints
auth_router = APIRouter(prefix="/auth", tags=["authentication"])


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user.

    Args:
        user_data: User registration data

    Returns:
        The created user (without sensitive data)

    Raises:
        HTTPException: If username or email already exists
    """
    try:
        user = user_store.create_user(user_data)
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@auth_router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """
    Login a user and get access/refresh tokens.

    Args:
        login_data: User login credentials

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If credentials are invalid
    """
    # Authenticate user
    user = user_store.authenticate_user(login_data.username, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password"
        )

    # Create tokens
    token_data = {"user_id": user.id, "username": user.username, "is_admin": user.is_admin}

    access_token = jwt_handler.create_access_token(token_data)
    refresh_token = jwt_handler.create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """
    Refresh access token using a refresh token.

    Args:
        refresh_token: The refresh token

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
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
    Logout a user.

    Note: In a real application, you might want to blacklist the token
    or implement a token revocation mechanism.

    Args:
        token: The current access token

    Returns:
        Logout confirmation message
    """
    # In a production app, you would add the token to a blacklist
    # For now, we just return a success message
    return {"message": "Successfully logged out"}


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
