"""User data model."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class User:
    """User model.

    Represents a user in the system with authentication and profile data.
    """

    username: str
    email: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    role: str = "user"

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Create user from dictionary.

        Args:
            data: User data

        Returns:
            User instance
        """
        return cls(
            id=data["id"],
            username=data["username"],
            email=data["email"],
            created_at=datetime.fromisoformat(data["created_at"]),
            is_active=data.get("is_active", True),
            role=data.get("role", "user"),
        )
