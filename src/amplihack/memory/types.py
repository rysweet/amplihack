"""Five psychological memory types for agent memory system.

This module implements the 5 psychological memory types based on human memory research:
- Episodic: What happened when (conversations, events)
- Semantic: Important learnings (patterns, facts, knowledge)
- Prospective: Future intentions (TODOs, reminders)
- Procedural: How to do something (workflows, processes)
- Working: Active task details (current context, variables)

Philosophy:
- Ruthless simplicity: Direct implementations without over-engineering
- Clear contracts: Each type has explicit required fields
- Self-contained: All validation logic within type classes
- Performance: Fast validation and type checking

Public API:
    MemoryType: Enum of 5 memory types
    EpisodicMemory: What happened when
    SemanticMemory: Important learnings
    ProspectiveMemory: Future intentions
    ProceduralMemory: How to do something
    WorkingMemory: Active task details
    MemorySchema: Generic schema validation
    classify_memory_type: Automatic type classification
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryType(Enum):
    """Five psychological memory types."""

    EPISODIC = "episodic"  # What happened when
    SEMANTIC = "semantic"  # Important learnings
    PROSPECTIVE = "prospective"  # Future intentions
    PROCEDURAL = "procedural"  # How to do something
    WORKING = "working"  # Active task details


@dataclass
class EpisodicMemory:
    """Episodic memory: What happened when.

    Captures conversations, events, and interactions with temporal context.
    Requires timestamp and participants to establish "what happened when with whom".
    """

    timestamp: datetime | None = None
    participants: list[str] | None = None
    content: str = ""
    context: str = ""
    outcome: str = ""
    memory_type: MemoryType = field(default=MemoryType.EPISODIC, init=False)

    def __post_init__(self):
        """Validate required fields."""
        if not self.timestamp:
            raise ValueError("Episodic memory requires timestamp fer when event occurred")
        if not self.participants:
            raise ValueError("Episodic memory requires participants to track who was involved")

    def is_in_time_range(self, start: datetime, end: datetime) -> bool:
        """Check if memory falls within time range."""
        if self.timestamp is None:
            return False
        return start <= self.timestamp <= end


@dataclass
class SemanticMemory:
    """Semantic memory: Important learnings.

    Captures patterns, facts, and knowledge that transcend specific events.
    Requires concept definition and confidence score for quality tracking.
    """

    concept: str = ""
    description: str = ""
    examples: list[str] | None = None
    confidence: float | None = None
    memory_type: MemoryType = field(default=MemoryType.SEMANTIC, init=False)

    def __post_init__(self):
        """Validate required fields and bounds."""
        if not self.concept:
            raise ValueError("Semantic memory requires concept definition")
        if self.confidence is None:
            raise ValueError("Semantic memory requires confidence score fer quality tracking")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class ProspectiveMemory:
    """Prospective memory: Future intentions.

    Captures TODOs, reminders, and planned actions.
    Requires task definition and trigger condition.
    """

    task: str = ""
    trigger: str = ""
    deadline: datetime | None = None
    memory_type: MemoryType = field(default=MemoryType.PROSPECTIVE, init=False)

    def __post_init__(self):
        """Validate required fields."""
        if not self.task:
            raise ValueError("Prospective memory requires task definition")
        if not self.trigger:
            raise ValueError("Prospective memory requires trigger condition")

    def is_overdue(self) -> bool:
        """Check if memory is past deadline."""
        if self.deadline is None:
            return False
        return datetime.now() > self.deadline


@dataclass
class ProceduralMemory:
    """Procedural memory: How to do something.

    Captures workflows, processes, and step-by-step procedures.
    Tracks usage count and strengthens with repeated successful use.
    """

    procedure_name: str = ""
    steps: list[str] | None = None
    success_criteria: str = ""
    usage_count: int = 0
    strength: float = 0.5  # Starts at medium strength
    memory_type: MemoryType = field(default=MemoryType.PROCEDURAL, init=False)

    def __post_init__(self):
        """Validate required fields."""
        if not self.procedure_name:
            raise ValueError("Procedural memory requires procedure_name")
        if self.steps is None:
            raise ValueError("Procedural memory requires steps")
        if len(self.steps) == 0:
            raise ValueError("Procedural memory must have at least one step")

    def record_usage(self) -> None:
        """Record successful usage and strengthen memory."""
        self.usage_count += 1
        # Strengthen memory with usage (asymptotic to 1.0)
        self.strength = min(1.0, self.strength + (1.0 - self.strength) * 0.1)


@dataclass
class WorkingMemory:
    """Working memory: Active task details.

    Captures current task context, variables, and dependencies.
    Cleared when task completes (short-lived by design).
    """

    task_id: str = ""
    context: dict[str, Any] | None = None
    dependencies: list[str] | None = None
    is_cleared: bool = False
    memory_type: MemoryType = field(default=MemoryType.WORKING, init=False)

    def __post_init__(self):
        """Validate required fields."""
        if not self.task_id:
            raise ValueError("Working memory requires task_id")
        if self.context is None:
            raise ValueError("Working memory requires context variables")
        # Initialize dependencies if not provided
        if self.dependencies is None:
            self.dependencies = []

    def mark_task_complete(self) -> None:
        """Clear working memory when task completes."""
        self.is_cleared = True
        self.context = {}


@dataclass
class MemorySchema:
    """Generic schema validation fer memory types.

    Validates required fields and type checking fer any memory type.
    """

    memory_type: MemoryType
    required_fields: list[str]
    field_types: dict[str, type] | None = None

    def validate(self, data: dict[str, Any]) -> bool:
        """Validate data against schema."""
        # Check required fields
        for field_name in self.required_fields:
            if field_name not in data:
                return False

        # Check field types if specified
        if self.field_types:
            for field_name, expected_type in self.field_types.items():
                if field_name in data:
                    if not isinstance(data[field_name], expected_type):
                        return False

        return True


def classify_memory_type(content: str, context: dict[str, Any]) -> MemoryType:
    """Automatically classify memory type based on content and context.

    Uses context hints and content analysis to determine appropriate memory type.
    Defaults to EPISODIC when unclear (safest choice - preserves temporal info).

    Args:
        content: Memory content text
        context: Context dict with type hints and metadata

    Returns:
        Appropriate MemoryType fer the content
    """
    # Check explicit type hint
    context_type = context.get("type", "").lower()

    if context_type == "conversation":
        return MemoryType.EPISODIC
    if context_type == "pattern" or context_type == "learning":
        return MemoryType.SEMANTIC
    if context_type == "todo" or context_type == "reminder":
        return MemoryType.PROSPECTIVE
    if context_type == "procedure" or context_type == "workflow":
        return MemoryType.PROCEDURAL
    if context_type == "task_state":
        return MemoryType.WORKING

    # Default to episodic (safest - preserves temporal info)
    return MemoryType.EPISODIC


__all__ = [
    "MemoryType",
    "EpisodicMemory",
    "SemanticMemory",
    "ProspectiveMemory",
    "ProceduralMemory",
    "WorkingMemory",
    "MemorySchema",
    "classify_memory_type",
]
