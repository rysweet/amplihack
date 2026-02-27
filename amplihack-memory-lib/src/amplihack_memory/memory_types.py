"""Cognitive memory type definitions.

Defines the six memory categories modeled after human cognition:
  SENSORY    - Raw, short-lived observations (auto-expire)
  WORKING    - Active task context with bounded capacity
  EPISODIC   - Autobiographical events (consolidatable)
  SEMANTIC   - Distilled facts and knowledge
  PROCEDURAL - Reusable step-by-step procedures
  PROSPECTIVE - Future-oriented trigger-action pairs
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryCategory(Enum):
    """Six cognitive memory types."""

    SENSORY = "sensory"
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PROSPECTIVE = "prospective"


@dataclass
class SensoryItem:
    """Short-lived raw observation.

    Attributes:
        node_id: Unique identifier in the graph.
        modality: Observation channel (e.g. "text", "code", "error", "log").
        raw_data: The raw observation content.
        observation_order: Monotonically increasing insertion order.
        expires_at: Unix timestamp after which this item may be pruned.
        created_at: When the item was recorded.
    """

    node_id: str
    modality: str
    raw_data: str
    observation_order: int
    expires_at: float
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class WorkingMemorySlot:
    """Active task-context slot (bounded capacity).

    Attributes:
        node_id: Unique identifier in the graph.
        slot_type: Categorisation of the slot (e.g. "goal", "constraint", "context").
        content: The payload stored in this slot.
        relevance: Priority weight (higher = more relevant). Defaults to 1.0.
        task_id: The task this slot is associated with.
        created_at: When the slot was created.
    """

    node_id: str
    slot_type: str
    content: str
    relevance: float
    task_id: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class EpisodicMemory:
    """Autobiographical event record.

    Attributes:
        node_id: Unique identifier in the graph.
        content: The episode description.
        source_label: Origin label (e.g. "user-session", "ci-run").
        temporal_index: Monotonic ordering index across episodes.
        compressed: Whether this episode has been consolidated.
        created_at: When the episode was stored.
        metadata: Optional structured data attached to the episode.
    """

    node_id: str
    content: str
    source_label: str
    temporal_index: int
    compressed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticFact:
    """Distilled knowledge fact.

    Attributes:
        node_id: Unique identifier in the graph.
        concept: The concept or topic this fact is about.
        content: The factual content.
        confidence: Confidence score (0.0 - 1.0).
        source_id: Reference to the source that produced this fact.
        tags: Categorisation tags.
        metadata: Additional structured metadata.
        created_at: When the fact was stored.
    """

    node_id: str
    concept: str
    content: str
    confidence: float
    source_id: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ProceduralMemory:
    """Reusable step-by-step procedure.

    Attributes:
        node_id: Unique identifier in the graph.
        name: Human-readable procedure name.
        steps: Ordered list of step descriptions.
        prerequisites: Conditions that must be met before execution.
        usage_count: How many times this procedure has been recalled.
        created_at: When the procedure was stored.
    """

    node_id: str
    name: str
    steps: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ProspectiveMemory:
    """Future-oriented trigger-action pair.

    Attributes:
        node_id: Unique identifier in the graph.
        description: What this prospective memory is about.
        trigger_condition: Text description of the trigger.
        action_on_trigger: What to do when the trigger fires.
        status: One of "pending", "triggered", "resolved".
        priority: Priority level (higher = more important). Defaults to 1.
        created_at: When this was stored.
    """

    node_id: str
    description: str
    trigger_condition: str
    action_on_trigger: str
    status: str = "pending"
    priority: int = 1
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ConsolidatedEpisode:
    """Summary produced by consolidating multiple episodes.

    Attributes:
        node_id: Unique identifier in the graph.
        summary: The consolidated summary text.
        original_count: How many episodes were consolidated.
        created_at: When consolidation was performed.
    """

    node_id: str
    summary: str
    original_count: int
    created_at: datetime = field(default_factory=datetime.now)
