"""Session data model."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any
import uuid


@dataclass
class Session:
    """Session model.

    Represents an active user session with authentication token.
    """

    user_id: str
    token: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=24))
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "token": self.token,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_valid": self.is_valid,
        }

    def is_expired(self) -> bool:
        """Check if session is expired.

        Returns:
            True if expired
        """
        return datetime.now() > self.expires_at
