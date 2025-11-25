"""Authentication middleware and dependencies."""
# ruff: noqa: B008  # Depends() in argument defaults is the FastAPI pattern

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .jwt_handler import jwt_handler
from .models import User
from .user_store import user_store


class JWTBearer(HTTPBearer):
    """JWT Bearer token authentication."""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authentication scheme."
                )

            # Verify the token
            try:
                jwt_handler.verify_access_token(credentials.credentials)
                return credentials.credentials
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid or expired token: {e!s}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authorization code."
            )


# Create reusable JWT bearer instance
jwt_bearer = JWTBearer()


async def get_current_user(token: str = Depends(jwt_bearer)) -> User:
    """
    Get the current authenticated user.

    Args:
        token: JWT token from the request

    Returns:
        The authenticated user

    Raises:
        HTTPException: If the token is invalid or user not found
    """
    try:
        payload = jwt_handler.verify_access_token(token)
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        user = user_store.get_user(user_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

        return user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {e!s}",
        )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current active user.

    Args:
        current_user: The current authenticated user

    Returns:
        The active user

    Raises:
        HTTPException: If the user is not active
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current admin user.

    Args:
        current_user: The current authenticated user

    Returns:
        The admin user

    Raises:
        HTTPException: If the user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user


class OptionalJWTBearer(HTTPBearer):
    """Optional JWT Bearer token authentication."""

    def __init__(self):
        super(OptionalJWTBearer, self).__init__(auto_error=False)

    async def __call__(self, request: Request) -> Optional[str]:
        credentials: Optional[HTTPAuthorizationCredentials] = await super().__call__(request)

        if credentials:
            if credentials.scheme != "Bearer":
                return None

            # Try to verify the token
            try:
                payload = jwt_handler.verify_access_token(credentials.credentials)
                return credentials.credentials
            except Exception:
                return None

        return None


# Create reusable optional JWT bearer instance
optional_jwt_bearer = OptionalJWTBearer()


async def get_optional_current_user(
    token: Optional[str] = Depends(optional_jwt_bearer),
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.

    Args:
        token: Optional JWT token from the request

    Returns:
        The authenticated user or None
    """
    if not token:
        return None

    try:
        payload = jwt_handler.verify_access_token(token)
        user_id = payload.get("user_id")

        if user_id:
            user = user_store.get_user(user_id)
            if user and user.is_active:
                return user
    except Exception:
        pass

    return None
