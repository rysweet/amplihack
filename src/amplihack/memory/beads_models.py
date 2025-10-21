"""
Beads Memory System Data Models.

Provides type-safe data structures for beads integration:
- BeadsIssue: Core issue tracking model
- BeadsRelationship: Dependency and relationship model
- BeadsWorkstream: Workflow organization model
- BeadsStatus: Status enumeration
- Result: Type-safe error handling

Philosophy:
- Zero-BS: All fields validated on construction
- Standard library only: No external dependencies
- Regeneratable: Clear specifications enable AI reconstruction
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import re


# =============================================================================
# Status Enumerations
# =============================================================================


class BeadsStatus(Enum):
    """Valid issue status values."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CLOSED = "closed"


class BeadsWorkstreamStatus(Enum):
    """Valid workstream status values."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class BeadsRelationshipType(Enum):
    """Valid relationship type values."""

    BLOCKS = "blocks"
    BLOCKED_BY = "blocked_by"
    RELATED = "related"
    PARENT = "parent"
    CHILD = "child"
    DISCOVERED_FROM = "discovered-from"


# =============================================================================
# Result Type for Error Handling
# =============================================================================


@dataclass
class Result:
    """
    Generic result type for safe error handling (like Rust Result<T, E>).

    Enables Railway-Oriented Programming without exceptions.
    """

    value: Optional[Any] = None
    error: Optional[Exception] = None

    @property
    def is_ok(self) -> bool:
        """Check if result is successful."""
        return self.error is None

    @property
    def is_err(self) -> bool:
        """Check if result is error."""
        return self.error is not None

    def unwrap(self) -> Any:
        """
        Get value or raise error.

        Raises:
            Exception: If result is error
        """
        if self.is_err:
            assert self.error is not None  # Type guard for pyright
            raise self.error
        return self.value

    def unwrap_or(self, default: Any) -> Any:
        """Get value or return default."""
        return self.value if self.is_ok else default


# =============================================================================
# BeadsIssue Model
# =============================================================================


@dataclass
class BeadsIssue:
    """
    Beads issue with full metadata.

    Represents a single issue in the beads memory system with validation
    and conversion methods for CLI integration.

    Validation:
    - ID: Non-empty, alphanumeric with dashes/underscores only
    - Title: Non-empty, max 500 characters
    - Status: Must be valid BeadsStatus value
    - Description: Optional, no max length
    """

    id: str
    title: str
    description: str
    status: str
    created_at: str
    updated_at: str
    labels: List[str] = field(default_factory=list)
    assignee: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    relationships: List["BeadsRelationship"] = field(default_factory=list)

    # Validation patterns
    ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-_]+$")
    MAX_TITLE_LENGTH = 500

    def __post_init__(self):
        """Validate fields after initialization."""
        # Validate ID
        if not self.id or not self.id.strip():
            raise ValueError("Issue id cannot be empty")

        if not self.ID_PATTERN.match(self.id):
            raise ValueError(
                f"Issue id format invalid: '{self.id}'. "
                "Must contain only alphanumeric characters, dashes, and underscores."
            )

        # Validate title
        if not self.title or not self.title.strip():
            raise ValueError("Issue title cannot be empty")

        if len(self.title) > self.MAX_TITLE_LENGTH:
            raise ValueError(
                f"Issue title too long: {len(self.title)} characters (max {self.MAX_TITLE_LENGTH})"
            )

        # Validate status
        valid_statuses = [s.value for s in BeadsStatus]
        if self.status not in valid_statuses:
            raise ValueError(f"Issue status must be one of {valid_statuses}, got '{self.status}'")

        # Ensure lists are not None
        if self.labels is None:
            self.labels = []
        if self.metadata is None:
            self.metadata = {}
        if self.relationships is None:
            self.relationships = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "labels": self.labels,
            "assignee": self.assignee,
            "metadata": self.metadata,
            "relationships": [
                r.to_dict() if hasattr(r, "to_dict") else r for r in self.relationships
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BeadsIssue":
        """Create BeadsIssue from dictionary."""
        # Handle relationships if present
        relationships = data.get("relationships", [])
        if relationships and isinstance(relationships[0], dict):
            relationships = [BeadsRelationship.from_dict(r) for r in relationships]

        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            labels=data.get("labels", []),
            assignee=data.get("assignee"),
            metadata=data.get("metadata", {}),
            relationships=relationships,
        )

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "BeadsIssue":
        """Create BeadsIssue from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_cli_output(cls, data: Dict[str, Any]) -> "BeadsIssue":
        """
        Create BeadsIssue from beads CLI JSON output.

        Alias for from_dict to make CLI integration explicit.
        """
        return cls.from_dict(data)

    def to_cli_input(self) -> Dict[str, Any]:
        """
        Convert to CLI input format (excludes read-only fields).

        Returns only fields that can be provided to CLI commands.
        Excludes: id, created_at, updated_at, relationships
        """
        return {
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "labels": self.labels,
            "assignee": self.assignee,
            "metadata": self.metadata,
        }

    def __eq__(self, other: object) -> bool:
        """Check equality based on ID."""
        if not isinstance(other, BeadsIssue):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for set/dict usage."""
        return hash(self.id)


# =============================================================================
# BeadsRelationship Model
# =============================================================================


@dataclass
class BeadsRelationship:
    """
    Dependency relationship between issues.

    Represents directional relationships like "ISSUE-001 blocks ISSUE-002".

    Validation:
    - Type: Must be valid BeadsRelationshipType
    - Source and target IDs: Cannot be the same (no self-reference)
    """

    type: str
    source_id: str
    target_id: str
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate fields after initialization."""
        # Validate type
        valid_types = [t.value for t in BeadsRelationshipType]
        if self.type not in valid_types:
            raise ValueError(
                f"Relationship type invalid: '{self.type}'. Must be one of {valid_types}"
            )

        # Prevent self-reference
        if self.source_id == self.target_id:
            raise ValueError(f"Cannot relate issue to itself: {self.source_id}")

        # Ensure metadata is not None
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BeadsRelationship":
        """Create BeadsRelationship from dictionary."""
        return cls(
            type=data["type"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            created_at=data["created_at"],
            metadata=data.get("metadata", {}),
        )

    def create_inverse(self) -> "BeadsRelationship":
        """
        Create inverse relationship.

        Example: "blocks" → "blocked_by" with swapped source/target
        """
        inverse_types = {
            "blocks": "blocked_by",
            "blocked_by": "blocks",
            "parent": "child",
            "child": "parent",
            "related": "related",  # Symmetric
            "discovered-from": "discovered-from",  # Symmetric
        }

        inverse_type = inverse_types.get(self.type, "related")

        return BeadsRelationship(
            type=inverse_type,
            source_id=self.target_id,
            target_id=self.source_id,
            created_at=self.created_at,
            metadata=self.metadata.copy(),
        )

    def __eq__(self, other: object) -> bool:
        """Check equality based on type, source, and target."""
        if not isinstance(other, BeadsRelationship):
            return NotImplemented
        return (
            self.type == other.type
            and self.source_id == other.source_id
            and self.target_id == other.target_id
        )

    def __hash__(self) -> int:
        """Hash based on type, source, target."""
        return hash((self.type, self.source_id, self.target_id))


# =============================================================================
# BeadsWorkstream Model
# =============================================================================


@dataclass
class BeadsWorkstream:
    """
    Workstream for organizing related issues.

    Groups issues into logical workflows or feature streams.
    """

    id: str
    name: str
    description: str
    status: str
    created_at: str
    issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate fields after initialization."""
        # Validate ID
        if not self.id or not self.id.strip():
            raise ValueError("Workstream id cannot be empty")

        # Validate name
        if not self.name or not self.name.strip():
            raise ValueError("Workstream name cannot be empty")

        # Validate status
        valid_statuses = [s.value for s in BeadsWorkstreamStatus]
        if self.status not in valid_statuses:
            raise ValueError(
                f"Workstream status must be one of {valid_statuses}, got '{self.status}'"
            )

        # Ensure lists are not None
        if self.issues is None:
            self.issues = []
        if self.metadata is None:
            self.metadata = {}

    def add_issue(self, issue_id: str):
        """
        Add issue to workstream (prevents duplicates).

        Args:
            issue_id: Issue ID to add
        """
        if issue_id not in self.issues:
            self.issues.append(issue_id)

    def remove_issue(self, issue_id: str):
        """
        Remove issue from workstream.

        Args:
            issue_id: Issue ID to remove
        """
        if issue_id in self.issues:
            self.issues.remove(issue_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "issues": self.issues,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BeadsWorkstream":
        """Create BeadsWorkstream from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            status=data["status"],
            created_at=data["created_at"],
            issues=data.get("issues", []),
            metadata=data.get("metadata", {}),
        )

    def __eq__(self, other: object) -> bool:
        """Check equality based on ID."""
        if not isinstance(other, BeadsWorkstream):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)


# =============================================================================
# Error Types
# =============================================================================


class BeadsError(Exception):
    """Base error for beads operations."""


class BeadsNotInstalledError(BeadsError):
    """bd CLI not found in PATH."""


class BeadsNotInitializedError(BeadsError):
    """Project not initialized with beads."""


class BeadsCLIError(BeadsError):
    """CLI command failed."""

    def __init__(self, cmd: str, returncode: int, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command '{cmd}' failed with code {returncode}: {stderr}")


class BeadsParseError(BeadsError):
    """Failed to parse CLI output."""


class BeadsTimeoutError(BeadsError):
    """Command exceeded timeout."""


class ProviderError(BeadsError):
    """Memory provider operation failed."""


class WorkflowError(BeadsError):
    """Workflow integration error."""


class SyncError(BeadsError):
    """Git sync coordination error."""
