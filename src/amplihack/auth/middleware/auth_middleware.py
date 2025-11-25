"""
Authentication Middleware for FastAPI.
Protects endpoints by validating JWT tokens.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List, Optional, Callable
import re

from ..services import TokenService
from ..exceptions import TokenError


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to authenticate requests using JWT tokens."""

    def __init__(
        self,
        app,
        token_service: TokenService,
        excluded_paths: Optional[List[str]] = None,
        excluded_patterns: Optional[List[str]] = None
    ):
        """
        Initialize authentication middleware.

        Args:
            app: FastAPI application
            token_service: Token service for validation
            excluded_paths: List of paths to exclude from authentication
            excluded_patterns: List of regex patterns to exclude from authentication
        """
        super().__init__(app)
        self.token_service = token_service

        # Default excluded paths (public endpoints)
        self.excluded_paths = excluded_paths or [
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/",
        ]

        # Compile excluded patterns
        self.excluded_patterns = []
        if excluded_patterns:
            self.excluded_patterns = [re.compile(pattern) for pattern in excluded_patterns]

    def _is_excluded(self, path: str) -> bool:
        """
        Check if path is excluded from authentication.

        Args:
            path: Request path

        Returns:
            True if path is excluded, False otherwise
        """
        # Check exact matches
        if path in self.excluded_paths:
            return True

        # Check pattern matches
        for pattern in self.excluded_patterns:
            if pattern.match(path):
                return True

        return False

    def _extract_token(self, authorization: Optional[str]) -> Optional[str]:
        """
        Extract JWT token from Authorization header.

        Args:
            authorization: Authorization header value

        Returns:
            Token string or None
        """
        if not authorization:
            return None

        # Check for Bearer scheme
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request through authentication middleware.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Check if path is excluded
        if self._is_excluded(request.url.path):
            return await call_next(request)

        # Extract token from header
        authorization = request.headers.get("Authorization")
        token = self._extract_token(authorization)

        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "missing_token",
                        "message": "Authorization token required"
                    }
                },
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Validate token
        try:
            payload = self.token_service.validate_token(
                token=token,
                token_type="access",
                check_blacklist=True
            )

            # Add user info to request state for downstream use
            request.state.user_id = payload.user_id
            request.state.user_email = payload.email
            request.state.user_roles = payload.roles
            request.state.user_permissions = payload.permissions
            request.state.token_payload = payload

        except TokenError as e:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "invalid_token",
                        "message": str(e)
                    }
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "authentication_error",
                        "message": f"Authentication failed: {str(e)}"
                    }
                }
            )

        # Continue to next handler
        return await call_next(request)


def require_auth(request: Request) -> dict:
    """
    Dependency function to require authentication.

    Args:
        request: FastAPI request

    Returns:
        User info dict

    Raises:
        HTTPException: If not authenticated
    """
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return {
        "user_id": request.state.user_id,
        "email": request.state.user_email,
        "roles": request.state.user_roles,
        "permissions": request.state.user_permissions,
    }


def require_role(*required_roles: str):
    """
    Dependency factory to require specific roles.

    Args:
        required_roles: Required role names

    Returns:
        Dependency function

    Example:
        @app.get("/admin", dependencies=[Depends(require_role("admin"))])
    """
    def role_checker(request: Request) -> dict:
        user_info = require_auth(request)
        user_roles = user_info.get("roles", [])

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(required_roles)}"
            )

        return user_info

    return role_checker


def require_permission(*required_permissions: str):
    """
    Dependency factory to require specific permissions.

    Args:
        required_permissions: Required permission names

    Returns:
        Dependency function

    Example:
        @app.get("/data", dependencies=[Depends(require_permission("read:data"))])
    """
    def permission_checker(request: Request) -> dict:
        user_info = require_auth(request)
        user_permissions = user_info.get("permissions", [])

        if not all(perm in user_permissions for perm in required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required permissions: {', '.join(required_permissions)}"
            )

        return user_info

    return permission_checker
