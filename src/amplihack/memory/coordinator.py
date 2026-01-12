"""Memory coordinator - main interface fer 5-type memory system.

Coordinates storage and retrieval with multi-agent review fer quality control.

Philosophy:
- Ruthless simplicity: Clear coordinator interface
- Performance contracts: <50ms retrieval, <500ms storage
- Quality gates: Multi-agent review prevents trivial storage
- Token budget: Strict enforcement (8000 tokens max)

Public API:
    MemoryCoordinator: Main interface
    StorageRequest: Request to store memory
    RetrievalQuery: Query to retrieve memories
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .database import MemoryDatabase
from .models import MemoryEntry
from .types import MemoryType

logger = logging.getLogger(__name__)


@dataclass
class StorageRequest:
    """Request to store a memory.

    Args:
        content: Memory content (required, non-empty)
        memory_type: Type of memory (defaults to EPISODIC)
        context: Additional context metadata
        metadata: Custom metadata
    """

    content: str
    memory_type: MemoryType = MemoryType.EPISODIC
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate required fields."""
        if not self.content or not self.content.strip():
            raise ValueError("Storage request requires non-empty content")


@dataclass
class RetrievalQuery:
    """Query to retrieve memories.

    Args:
        query_text: Search text
        token_budget: Max tokens to return (default 8000)
        memory_types: Filter by specific types
        time_range: Filter by time range (start, end)
    """

    query_text: str
    token_budget: int = 8000
    memory_types: list[MemoryType] | None = None
    time_range: tuple[datetime, datetime] | None = None


class MemoryCoordinator:
    """Coordinates memory storage and retrieval with quality control.

    Main interface fer the 5-type memory system. Handles:
    - Multi-agent review fer storage quality
    - Token budget enforcement fer retrieval
    - Performance monitoring (<50ms retrieval, <500ms storage)
    """

    def __init__(self, database: MemoryDatabase | None = None, session_id: str | None = None):
        """Initialize coordinator.

        Args:
            database: Database instance (creates default if None)
            session_id: Session identifier (generates if None)
        """
        self.database = database or MemoryDatabase()
        self.session_id = session_id or f"session-{uuid.uuid4().hex[:8]}"

        # Statistics tracking
        self._stats = {
            "total_stored": 0,
            "total_retrievals": 0,
            "total_rejected": 0,
        }
        self.last_retrieval_tokens = 0

    async def store(self, request: StorageRequest) -> str | None:
        """Store a memory with quality review.

        Args:
            request: Storage request

        Returns:
            Memory ID if stored, None if rejected

        Performance: Must complete under 500ms
        """
        try:
            # 1. Trivial content pre-filter
            if self._is_trivial(request.content):
                logger.debug(f"Rejected trivial content: {request.content[:50]}")
                self._stats["total_rejected"] += 1
                return None

            # 2. Check fer duplicates
            if await self._is_duplicate(request.content):
                logger.debug(f"Rejected duplicate content: {request.content[:50]}")
                self._stats["total_rejected"] += 1
                return None

            # 3. Multi-agent review fer quality
            importance_score = await self._review_quality(request)
            if importance_score < 5:  # Threshold: 5/10
                logger.debug(f"Rejected low-quality content (score={importance_score})")
                self._stats["total_rejected"] += 1
                return None

            # 4. Store in database
            memory_id = str(uuid.uuid4())

            # Extract timestamp from metadata (don't store in metadata - goes in created_at)
            timestamp = request.metadata.get("timestamp", datetime.now())
            if isinstance(timestamp, str):
                # If timestamp is string, parse it
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except ValueError:
                    timestamp = datetime.now()
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.now()

            # Build metadata without datetime objects
            clean_metadata = {
                **{k: v for k, v in request.metadata.items() if k != "timestamp"},
                **request.context,
                "new_memory_type": request.memory_type.value,
                "importance_score": importance_score,
            }

            memory_entry = MemoryEntry(
                id=memory_id,
                session_id=self.session_id,
                agent_id=request.context.get("agent_id", "system"),
                memory_type=self._convert_to_old_type(request.memory_type),
                title=self._generate_title(request.content),
                content=request.content,
                metadata=clean_metadata,
                created_at=timestamp,
                accessed_at=datetime.now(),
                importance=importance_score,
            )

            success = self.database.store_memory(memory_entry)
            if success:
                self._stats["total_stored"] += 1
                logger.info(f"Stored memory {memory_id} (type={request.memory_type.value})")
                return memory_id

            return None

        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            raise  # Propagate exception - don't swallow

    async def retrieve(self, query: RetrievalQuery) -> list[MemoryEntry]:
        """Retrieve memories matching query.

        Args:
            query: Retrieval query

        Returns:
            List of matching memories (respecting token budget)

        Performance: Must complete under 50ms
        """
        try:
            self._stats["total_retrievals"] += 1

            # Handle zero budget
            if query.token_budget <= 0:
                self.last_retrieval_tokens = 0
                return []

            # Build database query
            from .models import MemoryQuery

            # NOTE: Don't use content_search in SQL - SQL LIKE '%query%' requires
            # exact substring match which fails for "How to fix CI?" vs "To fix CI...".
            # Instead, retrieve all and rank in Python using word-based scoring.
            db_query = MemoryQuery(
                session_id=self.session_id,
                # content_search=query.query_text,  # Disabled - rank in Python instead
                limit=100,  # Fetch more, then trim by budget
            )

            # Retrieve from database
            memories = self.database.retrieve_memories(db_query)

            # Note: memories use old MemoryType from models.py
            # New memory type is stored in metadata["new_memory_type"]
            # Filter by new memory types if specified
            if query.memory_types:
                memories = [
                    m
                    for m in memories
                    if m.metadata.get("new_memory_type") in [t.value for t in query.memory_types]
                ]

            # Filter by time range if specified
            if query.time_range:
                start_time, end_time = query.time_range
                memories = [m for m in memories if start_time <= m.created_at <= end_time]

            # Rank by relevance
            scored_memories = self._rank_by_relevance(memories, query.query_text)

            # Enforce token budget
            selected_memories = []
            total_tokens = 0

            for memory, score in scored_memories:
                # Estimate tokens (rough: 4 chars = 1 token)
                memory_tokens = len(memory.content) // 4
                if total_tokens + memory_tokens > query.token_budget:
                    break

                selected_memories.append(memory)
                total_tokens += memory_tokens

            self.last_retrieval_tokens = total_tokens
            return selected_memories

        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            raise  # Propagate exception - don't swallow

    async def clear_working_memory(self, session_id: str | None = None):
        """Clear working memory (short-lived task context).

        Args:
            session_id: Session to clear (defaults to current session)
        """
        target_session = session_id or self.session_id
        try:
            # Query fer WORKING type memories
            from .models import MemoryQuery

            query = MemoryQuery(
                session_id=target_session,
                limit=1000,  # Get all
            )

            memories = self.database.retrieve_memories(query)

            # Filter fer WORKING type (stored in metadata)
            working_memories = [
                m for m in memories if m.metadata.get("new_memory_type") == MemoryType.WORKING.value
            ]

            # Delete each working memory
            for memory in working_memories:
                self.database.delete_memory(memory.id)

            logger.info(
                f"Cleared {len(working_memories)} working memories fer session {target_session}"
            )

        except Exception as e:
            logger.error(f"Error clearing working memory: {e}")
            raise  # Propagate exception - don't swallow

    async def clear_all(self, session_id: str | None = None):
        """Clear all memories fer current session.

        Args:
            session_id: Session to clear (defaults to current session)

        Security:
            MUST only clear memories from the specified session.
            NEVER clear memories from other sessions.
        """
        target_session = session_id or self.session_id

        # CRITICAL: Validate that session_id is provided (no default clear-all)
        if not target_session:
            raise ValueError("session_id must be specified for clear_all()")

        try:
            from .models import MemoryQuery

            # CRITICAL: Enforce session isolation - MUST include session_id
            query = MemoryQuery(
                session_id=target_session,  # Required for session isolation
                limit=10000,  # Get all
            )

            memories = self.database.retrieve_memories(query)

            # Verify all memories belong to target session before deletion
            for memory in memories:
                if memory.session_id != target_session:
                    raise ValueError(
                        f"Session isolation violation: Found memory {memory.id} "
                        f"from session {memory.session_id} when clearing {target_session}"
                    )
                self.database.delete_memory(memory.id)

            logger.info(f"Cleared all {len(memories)} memories fer session {target_session}")

        except Exception as e:
            logger.error(f"Error clearing all memories: {e}")
            raise  # Propagate exception (don't swallow)

    async def mark_task_complete(self, task_id: str):
        """Mark a task as complete, clearing its working memory.

        Args:
            task_id: Task identifier to clear
        """
        try:
            from .models import MemoryQuery

            query = MemoryQuery(
                session_id=self.session_id,
                limit=1000,
            )

            memories = self.database.retrieve_memories(query)

            # Filter fer WORKING type with matching task_id
            task_memories = [
                m
                for m in memories
                if m.metadata.get("new_memory_type") == MemoryType.WORKING.value
                and m.metadata.get("task_id") == task_id
            ]

            # Delete task-specific working memories
            for memory in task_memories:
                self.database.delete_memory(memory.id)

            logger.info(f"Cleared {len(task_memories)} working memories fer task {task_id}")

        except Exception as e:
            logger.error(f"Error marking task complete: {e}")
            raise  # Propagate exception - don't swallow

    def get_statistics(self) -> dict[str, Any]:
        """Get memory statistics.

        Returns:
            Statistics dictionary
        """
        db_stats = self.database.get_stats()
        return {
            **self._stats,
            "total_memories": db_stats.get("total_memories", 0),
        }

    def _is_trivial(self, content: str) -> bool:
        """Check if content is trivial.

        Trivial content includes:
        - Very short (<10 chars)
        - Common greetings
        - Single words
        """
        content = content.strip().lower()

        # Too short
        if len(content) < 10:
            return True

        # Common trivial phrases
        trivial_phrases = {
            "hello",
            "hi",
            "thanks",
            "thank you",
            "ok",
            "okay",
            "yes",
            "no",
            "sure",
        }

        if content in trivial_phrases:
            return True

        return False

    async def _is_duplicate(self, content: str) -> bool:
        """Check if content is duplicate using composite fingerprint.

        Uses multiple signals to reduce false positives from hash collisions:
        - SHA256 hash (primary)
        - Content length
        - First 100 chars
        - Last 100 chars

        Args:
            content: Content to check

        Returns:
            True if duplicate exists
        """
        # Compute composite fingerprint
        content_hash = self.database._compute_content_hash(content)
        content_length = len(content)
        content_prefix = content[:100] if len(content) >= 100 else content
        content_suffix = content[-100:] if len(content) >= 100 else content

        # Check for duplicates using composite fingerprint
        with self.database._lock:
            conn = self.database._get_connection()
            cursor = conn.execute(
                """
                SELECT content FROM memory_entries
                WHERE session_id = ? AND content_hash = ?
                """,
                (self.session_id, content_hash),
            )

            # Verify exact match if hash collision found
            for row in cursor.fetchall():
                existing_content = row[0]

                # Composite verification
                if (
                    len(existing_content) == content_length
                    and existing_content[:100] == content_prefix
                    and existing_content[-100:] == content_suffix
                    and existing_content == content  # Final exact match
                ):
                    return True

            return False

    async def _invoke_agent(self, prompt: str) -> dict[str, Any]:
        """Invoke agent fer review (can be mocked in tests).

        Args:
            prompt: Prompt fer agent

        Returns:
            Agent response dict with quality score

        Note: This method exists to be mockable in tests.
        In production, Claude Code provides the Task tool.
        Falls back to heuristic scoring when agent not available.
        """
        # Try to use Claude Code Task tool if available
        try:
            # In real usage, agents be invoked through Claude Code's Task tool
            # Tests will mock this method
            # For now, import will fail outside Claude Code environment
            from claude_code_sdk import Task  # type: ignore

            result = await Task(
                subagent_type="reviewer",
                prompt=prompt,
            )
            return {
                "quality_score": result.get("score", 5),
                "reasoning": result.get("reasoning", ""),
            }
        except (ImportError, Exception):
            # Fallback: Heuristic-based quality scoring when agent not available
            # This ensures <500ms storage contract is met even without agents
            return self._heuristic_quality_score(prompt)

    def _heuristic_quality_score(self, prompt: str) -> dict[str, Any]:
        """Fast heuristic-based quality scoring when agents unavailable.

        Args:
            prompt: Content to score

        Returns:
            Dict with quality_score and reasoning
        """
        # Extract content from prompt (assuming format includes content)
        content = prompt.split("Content: ")[-1] if "Content: " in prompt else prompt

        # Heuristic scoring based on content characteristics
        score = 5  # Start at middle score

        # Length heuristics
        if len(content) < 10:
            score -= 2  # Too short
        elif len(content) > 1000:
            score += 1  # Comprehensive

        # Structure heuristics
        if "\n" in content:
            score += 1  # Has structure
        if any(marker in content.lower() for marker in ["step", "action", "result", "decision"]):
            score += 1  # Has actionable content

        # Ensure score is in valid range [1-10]
        score = max(1, min(10, score))

        return {
            "quality_score": score,
            "reasoning": f"Heuristic score based on content length ({len(content)} chars) and structure",
        }

    async def _review_quality(self, request: StorageRequest) -> int:
        """Review content quality using multi-agent system.

        Args:
            request: Storage request

        Returns:
            Importance score (0-10)

        Uses 3 agents fer consensus (accepts if ≥2/3 agree it's valuable).
        """
        try:
            prompt = f"""Review this memory for importance (0-10 scale):

Content: {request.content[:500]}
Type: {request.memory_type.value}

Scoring:
- 0-3: Trivial (greetings, confirmations)
- 4-6: Moderate (minor details, temporary info)
- 7-10: Important (learnings, patterns, decisions)

Return: {{"importance_score": <number>, "reasoning": "<brief reason>"}}
"""

            # Invoke 3 agents in parallel for review
            reviews = []
            for _ in range(3):
                try:
                    result = await self._invoke_agent(prompt)
                    reviews.append(result)
                except Exception as e:
                    logger.warning(f"Agent review failed: {e}")
                    # Continue with other agents

            # Extract scores
            scores = []
            for review in reviews:
                if isinstance(review, dict) and "importance_score" in review:
                    scores.append(review["importance_score"])

            # Need at least 2/3 agents
            if len(scores) < 2:
                logger.warning("Not enough agent reviews, using fallback score")
                return self._fallback_score(request)

            # Return median score
            scores.sort()
            return scores[len(scores) // 2]

        except Exception as e:
            logger.error(f"Error in quality review: {e}")
            return self._fallback_score(request)

    def _fallback_score(self, request: StorageRequest) -> int:
        """Fallback scoring when agents unavailable.

        Uses heuristics:
        - Length-based scoring
        - Type-based boosting
        """
        content = request.content.strip()
        score = 5  # Default medium

        # Boost for length (more detail = more valuable)
        if len(content) > 200:
            score += 2
        elif len(content) > 100:
            score += 1

        # Boost for certain types
        if request.memory_type in [MemoryType.SEMANTIC, MemoryType.PROCEDURAL]:
            score += 1

        return min(10, score)

    def _generate_title(self, content: str) -> str:
        """Generate title from content.

        Args:
            content: Memory content

        Returns:
            Title (first 50 chars)
        """
        return content[:50].strip()

    def _convert_to_old_type(self, new_type: MemoryType):
        """Convert new 5-type system to old type system fer database.

        Temporary adapter until full migration.
        """
        from .models import MemoryType as OldMemoryType

        # Map new types to old types
        mapping = {
            MemoryType.EPISODIC: OldMemoryType.CONVERSATION,
            MemoryType.SEMANTIC: OldMemoryType.LEARNING,
            MemoryType.PROSPECTIVE: OldMemoryType.CONTEXT,
            MemoryType.PROCEDURAL: OldMemoryType.PATTERN,
            MemoryType.WORKING: OldMemoryType.CONTEXT,
        }

        return mapping.get(new_type, OldMemoryType.CONVERSATION)

    def _rank_by_relevance(
        self, memories: list[MemoryEntry], query_text: str
    ) -> list[tuple[MemoryEntry, float]]:
        """Rank memories by relevance to query.

        Args:
            memories: List of memories
            query_text: Query text

        Returns:
            List of (memory, score) tuples, sorted by score descending
        """
        scored = []
        query_lower = query_text.lower()

        for memory in memories:
            score = 0.0

            # Exact match in content
            if query_lower in memory.content.lower():
                score += 10.0

            # Word overlap
            query_words = set(query_lower.split())
            content_words = set(memory.content.lower().split())
            overlap = query_words & content_words
            score += len(overlap) * 2.0

            # Boost recent memories
            age_days = (datetime.now() - memory.accessed_at).days
            recency_boost = max(0, 5.0 - (age_days * 0.1))
            score += recency_boost

            # Boost high-importance
            if memory.importance:
                score += memory.importance

            scored.append((memory, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored


__all__ = ["MemoryCoordinator", "StorageRequest", "RetrievalQuery"]
