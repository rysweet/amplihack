"""Example API application with JWT authentication."""
# ruff: noqa: B008  # Depends() in argument defaults is the FastAPI pattern

import os
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Import authentication components
from amplihack.auth import (
    User,
    UserResponse,
    auth_router,
    get_current_active_user,
    get_current_admin_user,
    get_optional_current_user,
    user_store,
)

# Create FastAPI application
app = FastAPI(
    title="JWT Authentication API Example",
    description="Example API with JWT authentication",
    version="1.0.0",
)

# Add CORS middleware (configure as needed for your application)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication routes
app.include_router(auth_router)


# ============= Public Routes (No Authentication Required) =============


@app.get("/")
async def root():
    """Public root endpoint."""
    return {
        "message": "Welcome to the JWT Authentication API",
        "endpoints": {
            "public": ["/", "/health", "/public/data"],
            "authentication": [
                "/auth/register",
                "/auth/login",
                "/auth/refresh",
                "/auth/logout",
                "/auth/me",
            ],
            "protected": ["/protected", "/admin"],
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/public/data")
async def get_public_data(user: User = Depends(get_optional_current_user)):
    """
    Public endpoint that shows different data based on authentication status.

    Args:
        user: Optional current user (if authenticated)

    Returns:
        Public data with optional user-specific information
    """
    data = {
        "message": "This is public data accessible to everyone",
        "timestamp": "2024-11-25T10:00:00Z",
    }

    if user:
        data["personalized_message"] = f"Welcome back, {user.username}!"
        data["user_specific"] = {
            "last_login": "2024-11-25T09:00:00Z",
            "preferences": {"theme": "dark", "language": "en"},
        }

    return data


# ============= Protected Routes (Authentication Required) =============


@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_active_user)):
    """
    Protected endpoint that requires authentication.

    Args:
        current_user: The authenticated user

    Returns:
        Protected data for the authenticated user
    """
    return {
        "message": f"Hello {current_user.username}! This is protected data.",
        "user_id": current_user.id,
        "user_data": {
            "username": current_user.username,
            "email": current_user.email,
            "is_admin": current_user.is_admin,
        },
        "secret_data": "This data is only visible to authenticated users",  # pragma: allowlist secret
    }


@app.get("/protected/profile")
async def get_user_profile(current_user: User = Depends(get_current_active_user)):
    """
    Get the current user's full profile.

    Args:
        current_user: The authenticated user

    Returns:
        User profile information
    """
    return {
        "profile": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "created_at": current_user.created_at.isoformat(),
            "is_active": current_user.is_active,
            "is_admin": current_user.is_admin,
        },
        "statistics": {
            "posts_count": 42,
            "followers": 128,
            "following": 64,
        },
    }


@app.post("/protected/action")
async def perform_protected_action(
    action: str, current_user: User = Depends(get_current_active_user)
):
    """
    Perform a protected action.

    Args:
        action: The action to perform
        current_user: The authenticated user

    Returns:
        Action result
    """
    allowed_actions = ["create", "update", "delete", "share"]

    if action not in allowed_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action. Allowed actions: {allowed_actions}",
        )

    return {
        "message": f"Action '{action}' performed successfully",
        "user": current_user.username,
        "timestamp": "2024-11-25T10:30:00Z",
        "result": {"status": "success", "action_id": "12345"},
    }


# ============= Admin Routes (Admin Authentication Required) =============


@app.get("/admin")
async def admin_dashboard(admin_user: User = Depends(get_current_admin_user)):
    """
    Admin dashboard endpoint (requires admin privileges).

    Args:
        admin_user: The authenticated admin user

    Returns:
        Admin dashboard data
    """
    return {
        "message": f"Welcome to admin dashboard, {admin_user.username}!",
        "admin_data": {
            "total_users": len(user_store.list_users()),
            "system_status": "operational",
            "last_backup": "2024-11-25T00:00:00Z",
            "pending_tasks": 5,
        },
    }


@app.get("/admin/users", response_model=List[UserResponse])
async def list_all_users(admin_user: User = Depends(get_current_admin_user)):
    """
    List all users (admin only).

    Args:
        admin_user: The authenticated admin user

    Returns:
        List of all users
    """
    return user_store.list_users()


@app.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, admin_user: User = Depends(get_current_admin_user)):
    """
    Delete a user (admin only).

    Args:
        user_id: The ID of the user to delete
        admin_user: The authenticated admin user

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If user not found or cannot delete self
    """
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself"
        )

    if user_store.delete_user(user_id):
        return {"message": f"User {user_id} deleted successfully"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@app.put("/admin/users/{user_id}/admin")
async def toggle_admin_status(
    user_id: str, is_admin: bool, admin_user: User = Depends(get_current_admin_user)
):
    """
    Toggle admin status for a user (admin only).

    Args:
        user_id: The ID of the user to update
        is_admin: Whether to make the user an admin
        admin_user: The authenticated admin user

    Returns:
        Updated user information

    Raises:
        HTTPException: If user not found
    """
    updated_user = user_store.update_user(user_id, {"is_admin": is_admin})

    if updated_user:
        return {
            "message": "User admin status updated successfully",
            "user": {
                "id": updated_user.id,
                "username": updated_user.username,
                "is_admin": updated_user.is_admin,
            },
        }
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


# ============= Main Entry Point =============

if __name__ == "__main__":
    import uvicorn

    # Set JWT secret key if not already set (for development only)
    if not os.getenv("JWT_SECRET_KEY"):
        print("⚠️  WARNING: Using default JWT secret key. Set JWT_SECRET_KEY in production!")
        os.environ["JWT_SECRET_KEY"] = (
            "development-secret-key-change-in-production"  # pragma: allowlist secret
        )

    # Create a default admin user for testing (remove in production)
    try:
        from amplihack.auth import UserCreate

        admin_data = UserCreate(
            username="admin",
            email="admin@example.com",
            password="Admin123!",  # pragma: allowlist secret
            full_name="System Administrator",
        )
        admin_user = user_store.create_user(admin_data)
        user_store.update_user(admin_user.id, {"is_admin": True})
        print("✅ Created default admin user: admin / Admin123!")
    except ValueError:
        print("ℹ️  Admin user already exists")

    # Run the application
    print("🚀 Starting JWT Authentication API on http://127.0.0.1:8000")
    print("📚 API Documentation: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)
