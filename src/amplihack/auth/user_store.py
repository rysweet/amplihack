"""User storage and management."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import bcrypt

from .models import User, UserCreate, UserResponse


class UserStore:
    """Simple file-based user storage."""

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize user store with optional storage path."""
        if storage_path:
            self.storage_file = Path(storage_path)
        else:
            # Default storage location
            self.storage_file = Path.home() / ".amplihack" / "users.json"

        # Ensure directory exists
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize storage file if it doesn't exist
        if not self.storage_file.exists():
            self._save_users({})

    def _load_users(self) -> Dict[str, Dict]:
        """Load users from storage file."""
        try:
            with open(self.storage_file) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_users(self, users: Dict[str, Dict]) -> None:
        """Save users to storage file."""
        with open(self.storage_file, "w") as f:
            json.dump(users, f, indent=2, default=str)

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            The created user

        Raises:
            ValueError: If username or email already exists
        """
        users = self._load_users()

        # Check if username exists
        if any(u["username"] == user_data.username for u in users.values()):
            raise ValueError("Username already exists")

        # Check if email exists
        if any(u["email"] == user_data.email for u in users.values()):
            raise ValueError("Email already exists")

        # Create new user
        user_id = str(uuid.uuid4())
        now = datetime.utcnow()

        user = User(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=self.hash_password(user_data.password),
            created_at=now,
            updated_at=now,
            is_active=True,
            is_admin=False,
        )

        # Save user
        users[user_id] = user.model_dump()
        self._save_users(users)

        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        users = self._load_users()
        user_data = users.get(user_id)

        if user_data:
            # Convert datetime strings back to datetime objects
            if isinstance(user_data["created_at"], str):
                user_data["created_at"] = datetime.fromisoformat(user_data["created_at"])
            if isinstance(user_data["updated_at"], str):
                user_data["updated_at"] = datetime.fromisoformat(user_data["updated_at"])
            return User(**user_data)

        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        users = self._load_users()

        for user_data in users.values():
            if user_data["username"] == username:
                # Convert datetime strings back to datetime objects
                if isinstance(user_data["created_at"], str):
                    user_data["created_at"] = datetime.fromisoformat(user_data["created_at"])
                if isinstance(user_data["updated_at"], str):
                    user_data["updated_at"] = datetime.fromisoformat(user_data["updated_at"])
                return User(**user_data)

        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        users = self._load_users()

        for user_data in users.values():
            if user_data["email"] == email:
                # Convert datetime strings back to datetime objects
                if isinstance(user_data["created_at"], str):
                    user_data["created_at"] = datetime.fromisoformat(user_data["created_at"])
                if isinstance(user_data["updated_at"], str):
                    user_data["updated_at"] = datetime.fromisoformat(user_data["updated_at"])
                return User(**user_data)

        return None

    def update_user(self, user_id: str, update_data: Dict) -> Optional[User]:
        """Update a user."""
        users = self._load_users()

        if user_id not in users:
            return None

        # Update user data
        users[user_id].update(update_data)
        users[user_id]["updated_at"] = datetime.utcnow().isoformat()

        self._save_users(users)
        return self.get_user(user_id)

    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        users = self._load_users()

        if user_id in users:
            del users[user_id]
            self._save_users(users)
            return True

        return False

    def list_users(self) -> List[UserResponse]:
        """List all users (without sensitive data)."""
        users = self._load_users()
        result = []

        for user_data in users.values():
            # Convert datetime strings back to datetime objects
            if isinstance(user_data["created_at"], str):
                user_data["created_at"] = datetime.fromisoformat(user_data["created_at"])
            if isinstance(user_data["updated_at"], str):
                user_data["updated_at"] = datetime.fromisoformat(user_data["updated_at"])

            # Create response without sensitive data
            result.append(
                UserResponse(
                    id=user_data["id"],
                    username=user_data["username"],
                    email=user_data["email"],
                    full_name=user_data.get("full_name"),
                    created_at=user_data["created_at"],
                    is_active=user_data.get("is_active", True),
                    is_admin=user_data.get("is_admin", False),
                )
            )

        return result

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user.

        Args:
            username: Username or email
            password: Plain text password

        Returns:
            The authenticated user or None
        """
        # Try to get user by username or email
        user = self.get_user_by_username(username)
        if not user:
            user = self.get_user_by_email(username)

        if not user:
            return None

        # Verify password
        if not self.verify_password(password, user.hashed_password):
            return None

        # Check if user is active
        if not user.is_active:
            return None

        return user


# Create a singleton instance
user_store = UserStore()
