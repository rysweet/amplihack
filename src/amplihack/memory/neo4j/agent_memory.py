"""Agent-aware memory interface for cross-agent learning.

Provides high-level API for agents to store and retrieve memories
with automatic agent type detection and cross-agent learning support.
"""

import logging
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .connector import Neo4jConnector
from .memory_store import MemoryStore

logger = logging.getLogger(__name__)


class AgentMemoryManager:
    """High-level memory interface for agents with type-based sharing.

    Features:
    - Automatic agent type detection
    - Memory sharing within agent type
    - Cross-agent learning queries
    - Project and global scoping
    - Quality-based filtering
    """

    # Supported agent types from amplihack
    AGENT_TYPES = {
        "architect",
        "builder",
        "reviewer",
        "tester",
        "optimizer",
        "security",
        "database",
        "api-designer",
        "integration",
        "analyzer",
        "cleanup",
        "pre-commit-diagnostic",
        "ci-diagnostic",
        "fix-agent",
    }

    def __init__(
        self,
        agent_type: str,
        project_id: Optional[str] = None,
        connector: Optional[Neo4jConnector] = None,
    ):
        """Initialize agent memory manager.

        Args:
            agent_type: Type of agent (architect, builder, etc.)
            project_id: Optional project scope (defaults to current project)
            connector: Optional Neo4jConnector instance (creates default if None)

        Raises:
            ValueError: If agent_type not recognized
        """
        if agent_type not in self.AGENT_TYPES:
            logger.warning("Unknown agent type: %s", agent_type)

        self.agent_type = agent_type
        self.project_id = project_id or self._detect_project_id()
        self.instance_id = f"{agent_type}_{uuid4().hex[:8]}"

        # Initialize connector if not provided
        if connector is None:
            from .lifecycle import ensure_neo4j_running

            ensure_neo4j_running(blocking=True)
            connector = Neo4jConnector()
            connector.connect()

        self.store = MemoryStore(connector)
        logger.info(
            "Initialized AgentMemoryManager for %s (project: %s, instance: %s)",
            agent_type,
            self.project_id,
            self.instance_id,
        )

    def remember(
        self,
        content: str,
        category: str = "general",
        memory_type: str = "procedural",
        tags: Optional[List[str]] = None,
        confidence: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
        global_scope: bool = False,
    ) -> str:
        """Store a memory for this agent type.

        Automatically links memory to agent type and project scope.

        Args:
            content: Memory content (pattern, decision, lesson learned)
            category: Category (design_pattern, error_handling, etc.)
            memory_type: Type (procedural, declarative, meta, anti_pattern)
            tags: Searchable tags
            confidence: Agent's confidence in this memory (0-1)
            metadata: Additional structured data
            global_scope: If True, makes memory globally available (not project-specific)

        Returns:
            Memory ID

        Example:
            >>> mgr = AgentMemoryManager("architect", project_id="amplihack")
            >>> memory_id = mgr.remember(
            ...     content="Always design for modularity",
            ...     category="principle",
            ...     tags=["design", "modularity"]
            ... )
        """
        project_scope = None if global_scope else self.project_id

        memory_id = self.store.create_memory(
            content=content,
            agent_type=self.agent_type,
            category=category,
            memory_type=memory_type,
            project_id=project_scope,
            metadata=metadata or {},
            tags=tags or [],
            quality_score=confidence * 0.7,  # Initial quality based on confidence
            confidence=confidence,
        )

        logger.info(
            "Agent %s stored memory %s (category: %s, scope: %s)",
            self.agent_type,
            memory_id,
            category,
            "global" if global_scope else self.project_id,
        )

        return memory_id

    def recall(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_quality: float = 0.6,
        include_global: bool = True,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Retrieve memories for this agent type.

        Returns memories from:
        - Current project (if project_id set)
        - Global scope (if include_global=True)
        - Same agent type only

        Args:
            category: Optional category filter
            tags: Optional tag filter
            min_quality: Minimum quality score
            include_global: Include globally-scoped memories
            limit: Maximum results

        Returns:
            List of memory dictionaries sorted by quality

        Example:
            >>> mgr = AgentMemoryManager("architect", project_id="amplihack")
            >>> memories = mgr.recall(category="design_pattern", min_quality=0.8)
            >>> for mem in memories:
            ...     print(mem['content'])
        """
        project_filter = self.project_id if not include_global else None

        memories = self.store.get_memories_by_agent_type(
            agent_type=self.agent_type,
            project_id=project_filter,
            category=category,
            min_quality=min_quality,
            limit=limit,
        )

        # Filter by tags if provided
        if tags:
            memories = [m for m in memories if any(tag in m.get("tags", []) for tag in tags)]

        logger.info(
            "Agent %s recalled %d memories (category: %s, min_quality: %.2f)",
            self.agent_type,
            len(memories),
            category or "all",
            min_quality,
        )

        return memories

    def learn_from_others(
        self,
        topic: Optional[str] = None,
        category: Optional[str] = None,
        min_quality: float = 0.75,
        min_validations: int = 2,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Learn from other agents of the same type.

        Queries high-quality, well-validated memories from other
        agent instances of the same type.

        Args:
            topic: Optional search topic
            category: Optional category filter
            min_quality: Minimum quality score (default higher for learning)
            min_validations: Minimum validation count
            limit: Maximum results

        Returns:
            List of high-quality memories from other agents

        Example:
            >>> mgr = AgentMemoryManager("architect")
            >>> patterns = mgr.learn_from_others(
            ...     topic="authentication",
            ...     category="design_pattern"
            ... )
            >>> print(f"Found {len(patterns)} proven patterns")
        """
        if topic:
            # Search-based learning
            memories = self.store.search_memories(
                query=topic,
                agent_type=self.agent_type,
                project_id=None,  # Search globally
                limit=limit * 2,  # Get more for filtering
            )

            # Filter by quality and validations
            memories = [
                m
                for m in memories
                if m.get("quality_score", 0) >= min_quality
                and m.get("validation_count", 0) >= min_validations
            ]

            # Apply category filter
            if category:
                memories = [m for m in memories if m.get("category") == category]

            memories = memories[:limit]

        else:
            # Get high-quality memories
            memories = self.store.get_high_quality_memories(
                agent_type=self.agent_type,
                min_quality=min_quality,
                min_validations=min_validations,
                limit=limit,
            )

            # Apply category filter
            if category:
                memories = [m for m in memories if m.get("category") == category]

        logger.info(
            "Agent %s learned from others: %d memories (topic: %s, category: %s)",
            self.agent_type,
            len(memories),
            topic or "all",
            category or "all",
        )

        return memories

    def apply_memory(
        self,
        memory_id: str,
        outcome: str = "successful",
        feedback_score: Optional[float] = None,
    ) -> bool:
        """Record that this agent applied a memory.

        Updates usage statistics and quality scores based on outcome.

        Args:
            memory_id: Memory that was applied
            outcome: Application outcome (successful, failed, partial)
            feedback_score: Optional feedback score (0-1)

        Returns:
            True if recorded successfully

        Example:
            >>> mgr = AgentMemoryManager("builder")
            >>> memories = mgr.recall(category="error_handling")
            >>> memory_id = memories[0]['id']
            >>> # Apply the pattern...
            >>> mgr.apply_memory(memory_id, outcome="successful", feedback_score=0.9)
        """
        success = self.store.record_usage(
            memory_id=memory_id,
            agent_instance_id=self.instance_id,
            outcome=outcome,
            feedback_score=feedback_score,
        )

        if success:
            logger.info(
                "Agent %s applied memory %s (outcome: %s, feedback: %.2f)",
                self.instance_id,
                memory_id,
                outcome,
                feedback_score or 0.0,
            )

        return success

    def validate_memory(
        self,
        memory_id: str,
        feedback_score: float,
        outcome: str = "successful",
        notes: Optional[str] = None,
    ) -> bool:
        """Validate a memory after using it.

        Provides feedback on memory quality and usefulness.

        Args:
            memory_id: Memory to validate
            feedback_score: Validation score (0-1)
            outcome: Validation outcome
            notes: Optional validation notes

        Returns:
            True if recorded successfully

        Example:
            >>> mgr = AgentMemoryManager("reviewer")
            >>> # Use a memory from another reviewer agent...
            >>> mgr.validate_memory(
            ...     memory_id=mem_id,
            ...     feedback_score=0.85,
            ...     notes="Pattern worked well for API review"
            ... )
        """
        success = self.store.validate_memory(
            memory_id=memory_id,
            agent_instance_id=self.instance_id,
            feedback_score=feedback_score,
            outcome=outcome,
            notes=notes,
        )

        if success:
            logger.info(
                "Agent %s validated memory %s (score: %.2f)",
                self.instance_id,
                memory_id,
                feedback_score,
            )

        return success

    def search(
        self,
        query: str,
        include_global: bool = True,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search memories by content and tags.

        Args:
            query: Search query
            include_global: Include globally-scoped memories
            limit: Maximum results

        Returns:
            List of matching memories

        Example:
            >>> mgr = AgentMemoryManager("security")
            >>> memories = mgr.search("SQL injection")
            >>> for mem in memories:
            ...     print(mem['content'], mem['quality_score'])
        """
        project_filter = self.project_id if not include_global else None

        memories = self.store.search_memories(
            query=query,
            agent_type=self.agent_type,
            project_id=project_filter,
            limit=limit,
        )

        logger.info(
            "Agent %s searched for '%s': %d results",
            self.agent_type,
            query,
            len(memories),
        )

        return memories

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics for this agent type.

        Returns:
            Dictionary with statistics (total, avg quality, etc.)

        Example:
            >>> mgr = AgentMemoryManager("optimizer")
            >>> stats = mgr.get_stats()
            >>> print(f"Total memories: {stats['total_memories']}")
            >>> print(f"Average quality: {stats['avg_quality']:.2f}")
        """
        stats = self.store.get_memory_stats(agent_type=self.agent_type)

        logger.info(
            "Agent %s stats: %d memories, avg quality %.2f",
            self.agent_type,
            stats.get("total_memories", 0),
            stats.get("avg_quality", 0.0),
        )

        return stats

    def get_best_practices(
        self,
        category: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get best practices (highest quality memories).

        Args:
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of best practice memories

        Example:
            >>> mgr = AgentMemoryManager("architect")
            >>> practices = mgr.get_best_practices(category="api_design")
            >>> for practice in practices:
            ...     print(f"✓ {practice['content']}")
        """
        memories = self.learn_from_others(
            category=category,
            min_quality=0.85,
            min_validations=3,
            limit=limit,
        )

        return memories

    @staticmethod
    def _detect_project_id() -> str:
        """Detect current project ID from environment or git.

        Returns:
            Project identifier
        """
        # Try environment variable
        project_id = os.environ.get("AMPLIHACK_PROJECT_ID")
        if project_id:
            return project_id

        # Try to detect from git
        try:
            import subprocess

            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                repo_path = result.stdout.strip()
                return os.path.basename(repo_path)
        except Exception:
            pass

        # Default fallback
        return "default"

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Could add cleanup here if needed

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"AgentMemoryManager(agent_type='{self.agent_type}', "
            f"project_id='{self.project_id}', instance_id='{self.instance_id}')"
        )
