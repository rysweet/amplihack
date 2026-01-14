"""Agent status tracking model.

Represents the state of an agent working on a sub-issue.

Philosophy:
- Simple data model with validation
- JSON serialization for file-based protocol
- Immutable updates via update() method

Public API:
    AgentStatus: Main status model
    AgentState: Enum of valid states
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class AgentState(Enum):
    """Valid agent states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AgentStatus:
    """Status of an agent working on a sub-issue.

    Args:
        agent_id: Unique identifier for the agent
        issue_number: GitHub issue number being worked on
        status: Current agent state (must be valid AgentState value)
        pr_number: PR number if created (optional)
        completion_percentage: Progress percentage 0-100 (optional)
        start_time: ISO timestamp when agent started (optional)
        last_update: ISO timestamp of last status update (optional)
        errors: List of error messages (optional)

    Raises:
        ValueError: If status is invalid or completion_percentage out of range
    """

    agent_id: str
    issue_number: int
    status: str
    pr_number: Optional[int] = None
    completion_percentage: Optional[int] = None
    start_time: Optional[str] = None
    last_update: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate status and completion_percentage after initialization."""
        # Validate status is one of the valid enum values
        valid_statuses = {state.value for state in AgentState}
        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{self.status}'. Must be one of: {valid_statuses}"
            )

        # Validate completion_percentage if provided
        if self.completion_percentage is not None:
            if not (0 <= self.completion_percentage <= 100):
                raise ValueError(
                    f"Invalid completion percentage {self.completion_percentage}. "
                    f"Must be between 0 and 100."
                )

    def to_json(self) -> str:
        """Serialize to JSON string.

        Returns:
            JSON string representation of the status
        """
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentStatus":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with agent status fields

        Returns:
            AgentStatus instance
        """
        return cls(**data)

    def update(self, **kwargs) -> "AgentStatus":
        """Create updated copy with new field values.

        Args:
            **kwargs: Fields to update

        Returns:
            New AgentStatus instance with updated values
        """
        current_data = asdict(self)
        current_data.update(kwargs)
        return AgentStatus.from_dict(current_data)


__all__ = ["AgentStatus", "AgentState"]
