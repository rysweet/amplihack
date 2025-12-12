"""User service for managing user operations."""

from typing import Any, Dict, Optional

from ..models.user import User
from .database_service import DatabaseService


class UserService:
    """Service for user-related operations.

    Handles user creation, retrieval, updates, and deletion.
    """

    def __init__(self, db_service: DatabaseService):
        """Initialize user service.

        Args:
            db_service: Database service for persistence
        """
        self.db = db_service

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID.

        Args:
            user_id: User identifier

        Returns:
            User data if found, None otherwise
        """
        return self.db.query("users", {"id": user_id})

    def create_user(self, username: str, email: str) -> User:
        """Create a new user.

        Args:
            username: User's username
            email: User's email address

        Returns:
            Created user object
        """
        user = User(username=username, email=email)
        self.db.insert("users", user.to_dict())
        return user

    def update_user(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Update user information.

        Args:
            user_id: User identifier
            data: Fields to update

        Returns:
            True if successful
        """
        return self.db.update("users", {"id": user_id}, data)

    def delete_user(self, user_id: str) -> bool:
        """Delete a user.

        Args:
            user_id: User identifier

        Returns:
            True if successful
        """
        return self.db.delete("users", {"id": user_id})

    def list_users(self, limit: int = 100) -> list[Dict[str, Any]]:
        """List all users.

        Args:
            limit: Maximum number of users to return

        Returns:
            List of user data
        """
        return self.db.query_all("users", limit=limit)
