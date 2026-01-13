"""API Contracts for 5-Type Memory System.

This module defines clean, minimal API contracts for the memory system following
the brick & studs philosophy. Each interface is a "stud" - a stable connection
point that other modules can depend on.

Philosophy:
- Single responsibility per interface
- Ruthlessly simple method signatures
- Clear performance contracts (<50ms retrieval, <500ms storage)
- Standard library types only in signatures

Public API (the "studs"):
    MemoryCoordinator: Main interface for all memory operations
    StoragePipeline: Handle storage with multi-agent review
    RetrievalPipeline: Handle retrieval with scoring
    AgentReview: Coordinate parallel agent reviews
    HookIntegration: Hook handlers for automatic memory

Five Memory Types:
    1. EPISODIC - What happened when (events, conversations)
    2. SEMANTIC - Important learnings to retain (patterns, facts)
    3. PROSPECTIVE - Future intentions (TODOs, reminders)
    4. PROCEDURAL - How to do something (workflows, procedures)
    5. WORKING - Details for staying on task (active context)
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol


# ============================================================================
# Core Types
# ============================================================================


class MemoryType(Enum):
    """Five psychological memory types for intelligent classification."""

    EPISODIC = "episodic"  # What happened when
    SEMANTIC = "semantic"  # Important learnings
    PROSPECTIVE = "prospective"  # Future intentions
    PROCEDURAL = "procedural"  # How to do something
    WORKING = "working"  # Active task details


@dataclass
class MemoryEntry:
    """A single memory entry.

    Minimal data structure for storing and retrieving memories.
    """

    id: str
    memory_type: MemoryType
    content: str
    importance: int  # 1-10 scale
    created_at: datetime
    metadata: dict[str, Any]

    # Optional fields
    tags: list[str] | None = None
    expires_at: datetime | None = None


@dataclass
class StorageRequest:
    """Request to store a memory.

    Simple input contract for storage operations.
    """

    content: str
    memory_type: MemoryType
    agent_id: str
    importance: int | None = None  # Auto-scored if None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class RetrievalQuery:
    """Query parameters for memory retrieval.

    Minimal query interface with sensible defaults.
    """

    memory_type: MemoryType | None = None
    agent_id: str | None = None
    min_importance: int = 7  # Default threshold
    limit: int = 10
    tags: list[str] | None = None
    search_text: str | None = None


@dataclass
class ReviewScore:
    """Agent's evaluation of memory importance or relevance.

    Used for both storage and retrieval scoring.
    """

    agent_id: str
    score: int  # 1-10 scale
    reasoning: str


@dataclass
class ReviewResult:
    """Result of multi-agent review.

    Contains consensus score and individual agent opinions.
    """

    average_score: float
    should_store: bool  # True if avg >4
    individual_scores: list[ReviewScore]


# ============================================================================
# Primary Interface: MemoryCoordinator
# ============================================================================


class MemoryCoordinator(Protocol):
    """Main interface for all memory operations.

    This is the primary "stud" - other modules interact through this contract.

    Performance Contracts:
    - store(): <500ms (includes multi-agent review)
    - retrieve(): <50ms (excludes agent review)
    - retrieve_with_review(): <300ms (includes relevance scoring)
    """

    def store(self, request: StorageRequest) -> str | None:
        """Store memory after multi-agent quality review.

        Coordinates parallel agent reviews to evaluate importance.
        Only stores if consensus score >4/10.

        Args:
            request: Storage request with content and metadata

        Returns:
            Memory ID if stored, None if rejected by review

        Example:
            >>> request = StorageRequest(
            ...     content="Decided to use REST API",
            ...     memory_type=MemoryType.SEMANTIC,
            ...     agent_id="architect",
            ...     importance=8
            ... )
            >>> memory_id = coordinator.store(request)
        """
        ...

    def retrieve(self, query: RetrievalQuery) -> list[MemoryEntry]:
        """Retrieve memories by query parameters.

        Fast retrieval without agent review. Use for batch operations
        or when agent review not needed.

        Args:
            query: Query parameters with filters

        Returns:
            List of matching memories

        Performance: <50ms

        Example:
            >>> query = RetrievalQuery(
            ...     memory_type=MemoryType.SEMANTIC,
            ...     min_importance=7,
            ...     limit=5
            ... )
            >>> memories = coordinator.retrieve(query)
        """
        ...

    def retrieve_with_review(
        self, query: RetrievalQuery, context: str
    ) -> list[MemoryEntry]:
        """Retrieve memories with relevance scoring.

        Uses parallel agent evaluation to score relevance to context.
        Only returns memories with score >7/10.

        Args:
            query: Query parameters
            context: Current context for relevance evaluation

        Returns:
            List of relevant memories

        Performance: <300ms

        Example:
            >>> memories = coordinator.retrieve_with_review(
            ...     query=RetrievalQuery(memory_type=MemoryType.PROCEDURAL),
            ...     context="Building authentication system"
            ... )
        """
        ...

    def delete(self, memory_id: str) -> bool:
        """Delete memory by ID.

        Args:
            memory_id: Memory identifier

        Returns:
            True if deleted, False if not found
        """
        ...

    def clear_working_memory(self) -> int:
        """Clear all WORKING memory entries.

        Working memory is temporary and should be cleared after task completion.

        Returns:
            Number of entries deleted
        """
        ...


# ============================================================================
# Storage Pipeline
# ============================================================================


class StoragePipeline(Protocol):
    """Handle storage with multi-agent review.

    Coordinates the storage workflow:
    1. Review content importance (parallel agents)
    2. Store if consensus >4/10
    3. Return result

    Performance Contract: <500ms total
    """

    def process(self, request: StorageRequest) -> str | None:
        """Process storage request through review pipeline.

        Args:
            request: Storage request

        Returns:
            Memory ID if stored, None if rejected

        Example:
            >>> request = StorageRequest(...)
            >>> memory_id = pipeline.process(request)
        """
        ...

    def review_importance(self, content: str, memory_type: MemoryType) -> ReviewResult:
        """Get multi-agent review of content importance.

        Uses 3 parallel agents: analyzer, patterns, knowledge-archaeologist

        Args:
            content: Content to review
            memory_type: Type of memory

        Returns:
            Review result with consensus score

        Performance: <400ms (parallel execution)
        """
        ...


# ============================================================================
# Retrieval Pipeline
# ============================================================================


class RetrievalPipeline(Protocol):
    """Handle retrieval with optional relevance scoring.

    Two modes:
    1. Fast mode: No agent review (<50ms)
    2. Smart mode: Agent relevance scoring (<300ms)

    Performance Contracts:
    - query(): <50ms
    - query_with_scoring(): <300ms
    """

    def query(self, query: RetrievalQuery) -> list[MemoryEntry]:
        """Fast retrieval without agent review.

        Args:
            query: Query parameters

        Returns:
            List of memories

        Performance: <50ms
        """
        ...

    def query_with_scoring(
        self, query: RetrievalQuery, context: str
    ) -> list[MemoryEntry]:
        """Retrieval with relevance scoring.

        Uses 2 parallel agents to score relevance.

        Args:
            query: Query parameters
            context: Context for relevance evaluation

        Returns:
            List of relevant memories (score >7/10)

        Performance: <300ms
        """
        ...

    def score_relevance(
        self, memories: list[MemoryEntry], context: str
    ) -> dict[str, float]:
        """Score relevance of memories to context.

        Args:
            memories: Memories to score
            context: Context string

        Returns:
            Dict mapping memory_id to relevance score (0-10)

        Performance: <250ms for 10 memories
        """
        ...


# ============================================================================
# Agent Review
# ============================================================================


class AgentReview(Protocol):
    """Coordinate parallel agent reviews for consensus.

    Executes multiple agents in parallel and combines their scores.
    Used for both storage (importance) and retrieval (relevance).

    Performance Contract: <400ms for 3 parallel agents
    """

    def review_importance(self, content: str, memory_type: MemoryType) -> ReviewResult:
        """Get agent consensus on content importance.

        Uses 3 agents: analyzer, patterns, knowledge-archaeologist

        Args:
            content: Content to review
            memory_type: Type of memory

        Returns:
            Review result with consensus

        Performance: <400ms (parallel execution)
        """
        ...

    def review_relevance(
        self, memories: list[MemoryEntry], context: str
    ) -> dict[str, ReviewResult]:
        """Get agent consensus on memory relevance.

        Uses 2 agents for efficiency: analyzer, patterns

        Args:
            memories: Memories to review
            context: Context for relevance

        Returns:
            Dict mapping memory_id to ReviewResult

        Performance: <250ms for 10 memories (parallel execution)
        """
        ...


# ============================================================================
# Hook Integration
# ============================================================================


class HookIntegration(Protocol):
    """Hook handlers for automatic memory capture.

    Integrates with amplihack hooks system:
    - UserPromptSubmit: Inject relevant memories
    - SessionStop: Extract learnings
    - TaskCompletion: Extract learnings

    All methods are async for non-blocking execution.
    """

    async def on_user_prompt(self, prompt: str, session_id: str) -> list[MemoryEntry]:
        """Inject relevant memories before agent invocation.

        Called by UserPromptSubmit hook.

        Args:
            prompt: User's prompt text
            session_id: Current session ID

        Returns:
            List of relevant memories to inject

        Performance: <300ms (includes agent review)
        """
        ...

    async def on_session_stop(self, session_id: str) -> int:
        """Extract and store learnings at session end.

        Called by SessionStop hook.

        Args:
            session_id: Session being closed

        Returns:
            Number of memories stored

        Performance: <1000ms (less critical)
        """
        ...

    async def on_task_complete(self, task_id: str, result: dict[str, Any]) -> str | None:
        """Extract learnings after task completion.

        Called by TaskCompletion hook.

        Args:
            task_id: Completed task ID
            result: Task result data

        Returns:
            Memory ID if stored, None otherwise

        Performance: <500ms
        """
        ...


# ============================================================================
# Error Types
# ============================================================================


class MemoryError(Exception):
    """Base exception for memory operations."""

    pass


class StorageError(MemoryError):
    """Failed to store memory."""

    pass


class RetrievalError(MemoryError):
    """Failed to retrieve memory."""

    pass


class ReviewError(MemoryError):
    """Agent review failed."""

    pass


# ============================================================================
# Export Public Interface
# ============================================================================

__all__ = [
    # Core types
    "MemoryType",
    "MemoryEntry",
    "StorageRequest",
    "RetrievalQuery",
    "ReviewScore",
    "ReviewResult",
    # Primary interface
    "MemoryCoordinator",
    # Pipelines
    "StoragePipeline",
    "RetrievalPipeline",
    # Components
    "AgentReview",
    "HookIntegration",
    # Errors
    "MemoryError",
    "StorageError",
    "RetrievalError",
    "ReviewError",
]
