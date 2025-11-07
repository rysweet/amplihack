"""Data models for Neo4j code ingestion metadata tracking.

This module defines the core data structures for tracking codebase identity
and ingestion metadata in the Neo4j graph database.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional


class IngestionStatus(Enum):
    """Status of an ingestion operation."""

    NEW = "new"  # New codebase, first ingestion
    UPDATE = "update"  # Same codebase, new ingestion
    ERROR = "error"  # Ingestion failed


@dataclass
class CodebaseIdentity:
    """Identity of a codebase derived from Git metadata.

    This class provides a stable identifier for a codebase based on its Git
    repository information. The unique_key is used to determine if two ingestions
    are from the same codebase.

    Attributes:
        remote_url: Git remote URL (normalized, stripped of auth)
        branch: Current Git branch name
        commit_sha: Current Git commit SHA
        unique_key: Stable identifier derived from remote_url and branch
        metadata: Additional metadata about the codebase
    """

    remote_url: str
    branch: str
    commit_sha: str
    unique_key: str
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.remote_url:
            raise ValueError("remote_url is required")
        if not self.branch:
            raise ValueError("branch is required")
        if not self.commit_sha:
            raise ValueError("commit_sha is required")
        if not self.unique_key:
            raise ValueError("unique_key is required")

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for Neo4j storage.

        Returns:
            Dictionary representation suitable for Neo4j node properties
        """
        return {
            "remote_url": self.remote_url,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "unique_key": self.unique_key,
            **self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "CodebaseIdentity":
        """Create from dictionary.

        Args:
            data: Dictionary with codebase identity data

        Returns:
            CodebaseIdentity instance
        """
        metadata = {k: v for k, v in data.items() if k not in ("remote_url", "branch", "commit_sha", "unique_key")}
        return cls(
            remote_url=data["remote_url"],
            branch=data["branch"],
            commit_sha=data["commit_sha"],
            unique_key=data["unique_key"],
            metadata=metadata,
        )


@dataclass
class IngestionMetadata:
    """Metadata about a code ingestion operation.

    This class tracks when and how a codebase was ingested, forming an audit
    trail of all ingestions for a codebase.

    Attributes:
        ingestion_id: Unique identifier for this ingestion
        timestamp: When the ingestion occurred
        commit_sha: Git commit SHA at ingestion time
        ingestion_counter: Sequential counter for this codebase
        metadata: Additional metadata about the ingestion
    """

    ingestion_id: str
    timestamp: datetime
    commit_sha: str
    ingestion_counter: int
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.ingestion_id:
            raise ValueError("ingestion_id is required")
        if not self.commit_sha:
            raise ValueError("commit_sha is required")
        if self.ingestion_counter < 1:
            raise ValueError("ingestion_counter must be >= 1")

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for Neo4j storage.

        Returns:
            Dictionary representation suitable for Neo4j node properties
        """
        return {
            "ingestion_id": self.ingestion_id,
            "timestamp": self.timestamp.isoformat(),
            "commit_sha": self.commit_sha,
            "ingestion_counter": str(self.ingestion_counter),
            **self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "IngestionMetadata":
        """Create from dictionary.

        Args:
            data: Dictionary with ingestion metadata

        Returns:
            IngestionMetadata instance
        """
        metadata = {
            k: v for k, v in data.items() if k not in ("ingestion_id", "timestamp", "commit_sha", "ingestion_counter")
        }
        return cls(
            ingestion_id=data["ingestion_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            commit_sha=data["commit_sha"],
            ingestion_counter=int(data["ingestion_counter"]),
            metadata=metadata,
        )


@dataclass
class IngestionResult:
    """Result of an ingestion tracking operation.

    This class provides feedback about what happened during ingestion tracking,
    allowing callers to understand whether this was a new codebase or an update.

    Attributes:
        status: Status of the ingestion (NEW, UPDATE, ERROR)
        codebase_identity: Identity of the codebase
        ingestion_metadata: Metadata about this ingestion
        previous_ingestion_id: ID of previous ingestion if this is an update
        error_message: Error message if status is ERROR
    """

    status: IngestionStatus
    codebase_identity: CodebaseIdentity
    ingestion_metadata: IngestionMetadata
    previous_ingestion_id: Optional[str] = None
    error_message: Optional[str] = None

    def is_new(self) -> bool:
        """Check if this is a new codebase ingestion.

        Returns:
            True if this is the first ingestion of this codebase
        """
        return self.status == IngestionStatus.NEW

    def is_update(self) -> bool:
        """Check if this is an update to an existing codebase.

        Returns:
            True if this codebase has been ingested before
        """
        return self.status == IngestionStatus.UPDATE

    def is_error(self) -> bool:
        """Check if the ingestion failed.

        Returns:
            True if ingestion encountered an error
        """
        return self.status == IngestionStatus.ERROR

    def to_dict(self) -> Dict[str, object]:
        """Convert to dictionary for logging/serialization.

        Returns:
            Dictionary representation
        """
        return {
            "status": self.status.value,
            "codebase_identity": self.codebase_identity.to_dict(),
            "ingestion_metadata": self.ingestion_metadata.to_dict(),
            "previous_ingestion_id": self.previous_ingestion_id,
            "error_message": self.error_message,
        }
