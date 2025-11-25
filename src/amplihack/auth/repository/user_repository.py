"""
User Repository - handles database operations for users.
Simple in-memory implementation that can be replaced with SQLAlchemy later.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict
from ..models import User


class UserRepository:
    """Repository for user data operations."""

    def __init__(self):
        """Initialize repository with in-memory storage."""
        self._users: Dict[str, User] = {}
        self._email_index: Dict[str, str] = {}  # email -> user_id
        self._username_index: Dict[str, str] = {}  # username -> user_id

    def save(self, user: User) -> User:
        """
        Save or update a user.

        Args:
            user: User object to save

        Returns:
            Saved user object
        """
        # Generate ID if not present
        if not user.id:
            user.id = str(uuid.uuid4())

        # Update timestamp
        user.updated_at = datetime.now(timezone.utc)

        # Save user
        self._users[user.id] = user

        # Update indexes
        self._email_index[user.email.lower()] = user.id
        self._username_index[user.username.lower()] = user.id

        return user

    def find_by_id(self, user_id: str) -> Optional[User]:
        """
        Find user by ID.

        Args:
            user_id: User ID to find

        Returns:
            User object or None if not found
        """
        return self._users.get(user_id)

    def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email (case-insensitive).

        Args:
            email: Email to find

        Returns:
            User object or None if not found
        """
        user_id = self._email_index.get(email.lower())
        if user_id:
            return self._users.get(user_id)
        return None

    def find_by_username(self, username: str) -> Optional[User]:
        """
        Find user by username (case-insensitive).

        Args:
            username: Username to find

        Returns:
            User object or None if not found
        """
        user_id = self._username_index.get(username.lower())
        if user_id:
            return self._users.get(user_id)
        return None

    def update_last_login(self, user_id: str):
        """
        Update user's last login timestamp.

        Args:
            user_id: User ID to update
        """
        user = self.find_by_id(user_id)
        if user:
            user.last_login_at = datetime.now(timezone.utc)
            user.updated_at = datetime.now(timezone.utc)

    def increment_failed_attempts(self, user_id: str):
        """
        Increment failed login attempts counter.

        Args:
            user_id: User ID to update
        """
        user = self.find_by_id(user_id)
        if user:
            user.failed_login_attempts += 1
            user.updated_at = datetime.now(timezone.utc)

    def reset_failed_attempts(self, user_id: str):
        """
        Reset failed login attempts counter.

        Args:
            user_id: User ID to update
        """
        user = self.find_by_id(user_id)
        if user:
            user.failed_login_attempts = 0
            user.updated_at = datetime.now(timezone.utc)

    def lock_account(self, user_id: str, duration_minutes: int = 30):
        """
        Lock user account for specified duration.

        Args:
            user_id: User ID to lock
            duration_minutes: Duration to lock account
        """
        user = self.find_by_id(user_id)
        if user:
            user.is_locked = True
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
            user.updated_at = datetime.now(timezone.utc)

    def unlock_account(self, user_id: str):
        """
        Unlock user account.

        Args:
            user_id: User ID to unlock
        """
        user = self.find_by_id(user_id)
        if user:
            user.is_locked = False
            user.locked_until = None
            user.failed_login_attempts = 0
            user.updated_at = datetime.now(timezone.utc)

    def is_account_locked(self, user_id: str) -> bool:
        """
        Check if account is locked.

        Args:
            user_id: User ID to check

        Returns:
            True if account is locked, False otherwise
        """
        user = self.find_by_id(user_id)
        if not user:
            return False

        # Check if lock has expired
        if user.is_locked and user.locked_until:
            if datetime.now(timezone.utc) > user.locked_until:
                # Lock expired, unlock account
                self.unlock_account(user_id)
                return False

        return user.is_locked

    def delete(self, user_id: str):
        """
        Delete user by ID.

        Args:
            user_id: User ID to delete
        """
        user = self.find_by_id(user_id)
        if user:
            # Remove from indexes
            self._email_index.pop(user.email.lower(), None)
            self._username_index.pop(user.username.lower(), None)
            # Remove user
            self._users.pop(user_id, None)

    def count(self) -> int:
        """
        Get total user count.

        Returns:
            Number of users
        """
        return len(self._users)

    def clear(self):
        """Clear all users (for testing only)."""
        self._users.clear()
        self._email_index.clear()
        self._username_index.clear()
