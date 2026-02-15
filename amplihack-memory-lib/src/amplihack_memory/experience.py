"""Experience data model for agent memories."""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ExperienceType(Enum):
    """Types of experiences an agent can have."""

    SUCCESS = "success"
    FAILURE = "failure"
    PATTERN = "pattern"
    INSIGHT = "insight"


@dataclass
class Experience:
    """Single agent experience record.

    Represents a discrete memory of something that happened,
    a pattern observed, or an insight gained by an agent.

    Attributes:
        experience_type: Type of experience
        context: Situation description (max 500 chars)
        outcome: Result of action (max 1000 chars)
        confidence: Confidence score (0.0-1.0)
        timestamp: When experience occurred (defaults to now)
        experience_id: Unique identifier (auto-generated)
        metadata: Optional structured data
        tags: Optional categorization tags
    """

    experience_type: ExperienceType
    context: str
    outcome: str
    confidence: float
    timestamp: datetime = None
    experience_id: str = None
    metadata: dict[str, Any] = None
    tags: list[str] = None

    def __post_init__(self):
        """Validate fields and set defaults."""
        # Validate experience_type is enum
        if not isinstance(self.experience_type, ExperienceType):
            raise TypeError("experience_type must be ExperienceType enum")

        # Validate context
        if not self.context or not self.context.strip():
            raise ValueError("context cannot be empty")
        if len(self.context) > 500:
            raise ValueError("context exceeds 500 characters")

        # Validate outcome
        if not self.outcome or not self.outcome.strip():
            raise ValueError("outcome cannot be empty")
        if len(self.outcome) > 1000:
            raise ValueError("outcome exceeds 1000 characters")

        # Validate confidence range
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")

        # Default timestamp to now
        if self.timestamp is None:
            self.timestamp = datetime.now()

        # Validate timestamp is datetime
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be datetime object")

        # Generate experience_id if not provided
        if self.experience_id is None:
            self.experience_id = self._generate_id()

        # Default metadata to empty dict
        if self.metadata is None:
            self.metadata = {}

        # Default tags to empty list
        if self.tags is None:
            self.tags = []

    def _generate_id(self) -> str:
        """Generate unique experience ID.

        Format: exp_YYYYMMDD_HHMMSS_hash
        """
        # Timestamp components
        date_str = self.timestamp.strftime("%Y%m%d")
        time_str = self.timestamp.strftime("%H%M%S")

        # Hash of content for uniqueness
        content = f"{self.context}{self.outcome}{self.timestamp.isoformat()}"
        hash_bytes = hashlib.sha256(content.encode()).digest()
        hash_str = hash_bytes.hex()[:6]

        return f"exp_{date_str}_{time_str}_{hash_str}"

    def to_dict(self) -> dict[str, Any]:
        """Convert experience to dictionary.

        Returns:
            Dictionary representation of experience
        """
        return {
            "experience_id": self.experience_id,
            "experience_type": self.experience_type.value,
            "context": self.context,
            "outcome": self.outcome,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Experience":
        """Create experience from dictionary.

        Args:
            data: Dictionary with experience fields

        Returns:
            Experience instance
        """
        # Parse timestamp if string
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        # Parse experience_type if string
        exp_type = data["experience_type"]
        if isinstance(exp_type, str):
            exp_type = ExperienceType(exp_type)

        return cls(
            experience_id=data["experience_id"],
            experience_type=exp_type,
            context=data["context"],
            outcome=data["outcome"],
            confidence=data["confidence"],
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
        )

    def __eq__(self, other):
        """Check equality by experience_id."""
        if not isinstance(other, Experience):
            return False
        return self.experience_id == other.experience_id

    def __hash__(self):
        """Hash by experience_id."""
        return hash(self.experience_id)
