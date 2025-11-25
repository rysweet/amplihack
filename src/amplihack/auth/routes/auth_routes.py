"""
Authentication routes for FastAPI.
Implements register, login, refresh, logout, verify, and revoke endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from ..models import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshResponse,
    RevokeTokenRequest,
    VerifyResponse,
    MessageResponse,
    UserResponse,
    ErrorResponse,
    ErrorDetail,
)
from ..services import AuthenticationService
from ..exceptions import (
    AuthenticationError,
    TokenError,
    UserError,
    RateLimitExceededError,
    InsufficientPermissionsError,
)

# HTTP Bearer security scheme
security = HTTPBearer()

# Router
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Extract client IP and user agent from request."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


def create_error_response(code: str, message: str, details: Optional[dict] = None) -> dict:
    """Create standardized error response."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details
        }
    }


# Dependency injection - will be configured at app startup
_auth_service: Optional[AuthenticationService] = None


def set_auth_service(service: AuthenticationService):
    """Set the authentication service instance."""
    global _auth_service
    _auth_service = service


def get_auth_service() -> AuthenticationService:
    """Get authentication service dependency."""
    if _auth_service is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service not configured"
        )
    return _auth_service


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    fastapi_request: Request,
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """
    Register a new user.

    Creates a new user account with the provided information.
    """
    try:
        ip_address, user_agent = get_client_info(fastapi_request)

        user = auth_service.register(
            request=request,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=user.roles,
            created_at=user.created_at
        )

    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {e.retry_after} seconds.",
            headers={"Retry-After": str(e.retry_after)}
        )
    except UserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    fastapi_request: Request,
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """
    Authenticate user and generate tokens.

    Returns access and refresh tokens on successful authentication.
    """
    try:
        ip_address, user_agent = get_client_info(fastapi_request)

        response = auth_service.login(
            request=request,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return response

    except RateLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {e.retry_after} seconds.",
            headers={"Retry-After": str(e.retry_after)}
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    fastapi_request: Request,
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token.

    Returns a new access token.
    """
    try:
        ip_address, user_agent = get_client_info(fastapi_request)

        result = auth_service.refresh_token(
            refresh_token=request.refresh_token,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return RefreshResponse(
            access_token=result["access_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"]
        )

    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    fastapi_request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """
    Logout user by revoking access token.

    Adds the token to the blacklist.
    """
    try:
        ip_address, user_agent = get_client_info(fastapi_request)

        auth_service.logout(
            access_token=credentials.credentials,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return MessageResponse(message="Successfully logged out")

    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@router.get("/verify", response_model=VerifyResponse)
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """
    Verify access token validity.

    Returns token information if valid.
    """
    try:
        from datetime import datetime, timezone

        payload = auth_service.token_service.validate_token(
            token=credentials.credentials,
            token_type="access",
            check_blacklist=True
        )

        issued_at = datetime.fromtimestamp(payload.iat, tz=timezone.utc) if payload.iat else datetime.now(timezone.utc)
        expires_at = datetime.fromtimestamp(payload.exp, tz=timezone.utc) if payload.exp else datetime.now(timezone.utc)

        return VerifyResponse(
            valid=True,
            user_id=payload.user_id,
            issued_at=issued_at,
            expires_at=expires_at,
            token_id=payload.jti or ""
        )

    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}"
        )


@router.post("/revoke", response_model=MessageResponse)
async def revoke_token(
    request: RevokeTokenRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """
    Revoke a token (admin only).

    Adds the specified token to the blacklist.
    """
    try:
        # Verify admin token
        payload = auth_service.token_service.validate_token(
            token=credentials.credentials,
            token_type="access",
            check_blacklist=True
        )

        # Check admin role
        if "admin" not in payload.roles:
            raise InsufficientPermissionsError("Admin role required")

        # Revoke the target token
        # Note: We need to get the actual token from token_id
        # For now, we'll blacklist the token_id directly
        if auth_service.token_service.blacklist_service:
            # Calculate TTL - assuming 1 hour for access tokens
            ttl = 3600
            auth_service.token_service.blacklist_service.blacklist_token(
                request.token_id,
                ttl
            )

            # Log revocation
            auth_service.audit_logger.log_token_revoked(
                token_id=request.token_id,
                revoked_by=payload.user_id,
                reason=request.reason
            )

        return MessageResponse(message="Token revoked successfully")

    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token revocation failed: {str(e)}"
        )
