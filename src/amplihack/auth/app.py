"""
FastAPI application factory for authentication.
Creates a standalone auth app for testing.
"""

from fastapi import FastAPI
from .routes import router, set_auth_service
from .middleware import AuthMiddleware
from . import create_auth_system


def create_app(testing: bool = False) -> FastAPI:
    """
    Create FastAPI application with authentication.

    Args:
        testing: Whether to run in testing mode

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(title="Authentication API", version="1.0.0")

    # Create auth system
    auth_service, token_service, AuthMiddlewareClass = create_auth_system()

    # Set auth service for routes
    set_auth_service(auth_service)

    # Add middleware with excluded public paths
    app.add_middleware(
        AuthMiddlewareClass,
        token_service=token_service,
        excluded_paths=[
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
        ]
    )

    # Include auth routes
    app.include_router(router)

    @app.get("/")
    async def root():
        return {"message": "Authentication API"}

    return app
