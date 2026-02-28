"""Agent memory integration for AutoMode.

Provides persistent memory for goal-seeking agents using the
amplihack-memory-lib ExperienceStore. Memory persists across agent
runs, enabling learning from past executions.

When memory is enabled:
- Goals, plans, and decisions are stored after each turn
- Past experiences are recalled before executing new turns
- Agents build domain knowledge across multiple runs

Requires: pip install amplihack-memory-lib
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import memory lib, degrade gracefully
_MEMORY_AVAILABLE = False
try:
    from amplihack_memory import Experience, ExperienceStore, ExperienceType

    _MEMORY_AVAILABLE = True
except ImportError:
    pass


class AgentMemory:
    """Memory interface for AutoMode agents.

    Wraps amplihack-memory-lib ExperienceStore with agent-specific
    convenience methods. All operations are no-ops if the library
    is not installed.
    """

    def __init__(self, store: ExperienceStore) -> None:
        self._store = store

    @classmethod
    def create(
        cls,
        agent_name: str = "auto_mode",
        storage_path: Path | None = None,
    ) -> AgentMemory | None:
        """Create an AgentMemory instance. Returns None if unavailable."""
        if not _MEMORY_AVAILABLE:
            logger.debug("amplihack-memory-lib not installed")
            return None

        if os.environ.get("AMPLIHACK_MEMORY_ENABLED", "true").lower() == "false":
            logger.debug("Memory disabled via AMPLIHACK_MEMORY_ENABLED=false")
            return None

        try:
            path = storage_path or Path.home() / ".amplihack" / "agent-memory"
            store = ExperienceStore(
                agent_name=agent_name,
                storage_path=path,
            )  # Uses kuzu graph backend by default
            return cls(store)
        except Exception as e:
            logger.debug(f"Failed to init memory: {e}")
            return None

    def store_goal(self, goal: str) -> None:
        """Store the agent's goal at session start."""
        self._safe_add(
            ExperienceType.INSIGHT,
            context=f"Goal: {goal[:500]}",
            outcome="Session started",
            confidence=1.0,
            tags=["goal", "session_start"],
        )

    def store_objective(self, objective: str) -> None:
        """Store the clarified objective (after Turn 1)."""
        self._safe_add(
            ExperienceType.INSIGHT,
            context="Clarified objective",
            outcome=objective[:500],
            confidence=0.9,
            tags=["objective", "turn_1"],
        )

    def store_plan(self, plan: str) -> None:
        """Store the execution plan (after Turn 2)."""
        self._safe_add(
            ExperienceType.PATTERN,
            context="Execution plan",
            outcome=plan[:500],
            confidence=0.8,
            tags=["plan", "turn_2"],
        )

    def store_turn_result(self, turn: int, output: str) -> None:
        """Store execution output from a turn."""
        self._safe_add(
            ExperienceType.SUCCESS,
            context=f"Turn {turn} execution",
            outcome=output[:500],
            confidence=0.7,
            tags=[f"turn_{turn}", "execution"],
        )

    def store_evaluation(self, turn: int, eval_result: str) -> None:
        """Store evaluation result from a turn."""
        self._safe_add(
            ExperienceType.INSIGHT,
            context=f"Turn {turn} evaluation",
            outcome=eval_result[:500],
            confidence=0.8,
            tags=[f"turn_{turn}", "evaluation"],
        )

    def store_learning(self, summary: str) -> None:
        """Store a session learning at completion."""
        self._safe_add(
            ExperienceType.INSIGHT,
            context="Session summary and learnings",
            outcome=summary[:500],
            confidence=0.9,
            tags=["learning", "session_end"],
        )

    def recall_relevant(self, query: str, limit: int = 5) -> str:
        """Recall relevant past experiences. Returns formatted string for prompts."""
        try:
            results = self._store.search(query=query, limit=limit)
            if not results:
                return ""
            lines = ["## Relevant Past Experiences"]
            for exp in results:
                lines.append(
                    f"- **{exp.experience_type.name}** (confidence: {exp.confidence:.1f}): "
                    f"{exp.context[:100]} -> {exp.outcome[:100]}"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.debug(f"Memory recall failed: {e}")
            return ""

    def close(self) -> None:
        """Clean up the memory store (no-op if store has no close method)."""
        pass  # ExperienceStore handles cleanup internally

    def _safe_add(
        self,
        exp_type: ExperienceType,
        context: str,
        outcome: str,
        confidence: float,
        tags: list[str] | None = None,
    ) -> None:
        """Store an experience, silently handling errors."""
        try:
            exp = Experience(
                experience_type=exp_type,
                context=context,
                outcome=outcome,
                confidence=confidence,
                tags=tags or [],
            )
            self._store.add(exp)
        except Exception as e:
            logger.debug(f"Memory store failed: {e}")
