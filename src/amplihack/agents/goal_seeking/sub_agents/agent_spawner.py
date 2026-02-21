"""Agent Spawner: Dynamic sub-agent creation for complex tasks.

Philosophy:
- Single responsibility: Spawn and manage sub-agents
- Parent agents can dynamically create specialists for multi-hop reasoning
- Spawned agents share read access to parent's memory (shared storage_path)
- Each spawned agent has its own working context
- Results flow back to parent via collect_results()

Public API:
    SpawnedAgent: Dataclass representing a spawned sub-agent and its result
    AgentSpawner: Factory for creating and managing sub-agents
"""

from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

# Pre-compiled word-boundary check for classification
_WORD_BOUNDARY = re.compile(r"\b{}\b")

logger = logging.getLogger(__name__)


class SpecialistType(str, Enum):
    """Types of specialist sub-agents that can be spawned."""

    RETRIEVAL = "retrieval"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    CODE_GENERATION = "code_generation"
    RESEARCH = "research"


# Keywords used to auto-classify task type
# Order matters: more specific multi-word patterns checked first (research
# before retrieval) so "web search" matches research not retrieval.
_CLASSIFICATION_RULES: list[tuple[list[str], SpecialistType]] = [
    (["research", "web search", "look up online"], SpecialistType.RESEARCH),
    (["generate", "write code", "script", "implement", "create program", "create a program"], SpecialistType.CODE_GENERATION),
    (["combine", "synthesize", "summarize", "merge", "integrate"], SpecialistType.SYNTHESIS),
    (["analyze", "pattern", "detect", "compare", "trend", "correlation"], SpecialistType.ANALYSIS),
    (["find", "search", "retrieve", "lookup", "get facts", "what do we know"], SpecialistType.RETRIEVAL),
]


@dataclass
class SpawnedAgent:
    """Represents a spawned sub-agent and its lifecycle.

    Attributes:
        name: Unique name for this spawned agent
        specialist_type: What kind of specialist this is
        task: The task description assigned to this agent
        parent_memory_path: Path to shared memory (read access)
        result: The result string once completed
        status: Lifecycle status (pending, running, completed, failed)
        error: Error message if status is 'failed'
        elapsed_seconds: Time taken to complete
        metadata: Additional metadata about the execution
    """

    name: str
    specialist_type: str
    task: str
    parent_memory_path: str
    result: str | None = None
    status: str = "pending"
    error: str = ""
    elapsed_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentSpawner:
    """Enables generated agents to create sub-agents for complex tasks.

    The spawner manages the lifecycle of sub-agents:
    1. Spawn: Create a sub-agent with a specific task and specialist type
    2. Execute: Run the sub-agent (using executor functions)
    3. Collect: Wait for results and return them to the parent

    Spawned agents share read access to the parent's memory via the
    shared storage_path, but have their own working context.

    Args:
        parent_agent_name: Name of the parent agent
        parent_memory_path: Path to the parent's memory storage
        sdk_type: SDK type hint for tool injection
        max_concurrent: Maximum number of concurrent sub-agents

    Example:
        >>> spawner = AgentSpawner("parent_agent", "/tmp/memory")
        >>> spawned = spawner.spawn("Find all facts about Sarah Chen", "retrieval")
        >>> results = spawner.collect_results(timeout=30.0)
        >>> print(results[0].result)
    """

    def __init__(
        self,
        parent_agent_name: str,
        parent_memory_path: str | Path,
        sdk_type: str = "mini",
        max_concurrent: int = 4,
    ):
        if not parent_agent_name or not parent_agent_name.strip():
            raise ValueError("parent_agent_name cannot be empty")

        self.parent_agent_name = parent_agent_name.strip()
        self.parent_memory_path = str(parent_memory_path)
        self.sdk_type = sdk_type
        self.max_concurrent = max(1, min(max_concurrent, 16))

        self._spawned: list[SpawnedAgent] = []
        self._spawn_counter = 0
        self._executors: dict[str, Callable[[SpawnedAgent], str]] = {}

        # Register default executors for each specialist type
        self._register_default_executors()

    def _register_default_executors(self) -> None:
        """Register default executor functions for each specialist type.

        Each executor takes a SpawnedAgent and returns a result string.
        These can be overridden via register_executor().
        """
        self._executors[SpecialistType.RETRIEVAL] = self._execute_retrieval
        self._executors[SpecialistType.ANALYSIS] = self._execute_analysis
        self._executors[SpecialistType.SYNTHESIS] = self._execute_synthesis
        self._executors[SpecialistType.CODE_GENERATION] = self._execute_code_generation
        self._executors[SpecialistType.RESEARCH] = self._execute_research

    def register_executor(
        self, specialist_type: str, executor: Callable[[SpawnedAgent], str]
    ) -> None:
        """Register a custom executor for a specialist type.

        Args:
            specialist_type: The specialist type to handle
            executor: Callable that takes SpawnedAgent and returns result string
        """
        self._executors[specialist_type] = executor

    def spawn(self, task: str, specialist_type: str = "auto") -> SpawnedAgent:
        """Spawn a sub-agent to handle a specific task.

        The spawned agent:
        1. Gets read access to parent's memory (shared storage_path)
        2. Has its own working context
        3. Returns results to parent
        4. Can use SDK-specific tools based on parent's SDK type

        Args:
            task: Description of the task for the sub-agent
            specialist_type: Type of specialist ("retrieval", "analysis",
                "synthesis", "code_generation", "research", or "auto")

        Returns:
            SpawnedAgent instance (status="pending")

        Raises:
            ValueError: If task is empty
        """
        if not task or not task.strip():
            raise ValueError("Task cannot be empty")

        task = task.strip()

        # Auto-classify if needed
        if specialist_type == "auto":
            specialist_type = self._classify_task(task)

        self._spawn_counter += 1
        name = f"{self.parent_agent_name}_sub_{self._spawn_counter}_{specialist_type}"

        spawned = SpawnedAgent(
            name=name,
            specialist_type=specialist_type,
            task=task,
            parent_memory_path=self.parent_memory_path,
        )

        self._spawned.append(spawned)
        logger.info(
            "Spawned sub-agent '%s' (type=%s) for task: %s",
            name,
            specialist_type,
            task[:80],
        )

        return spawned

    def collect_results(self, timeout: float = 60.0) -> list[SpawnedAgent]:
        """Execute all pending spawned agents and wait for results.

        Runs pending agents concurrently (up to max_concurrent) using
        a thread pool. Each agent is executed by the registered executor
        for its specialist type.

        Args:
            timeout: Maximum seconds to wait for all agents to complete

        Returns:
            List of all SpawnedAgent instances with updated status/result
        """
        pending = [s for s in self._spawned if s.status == "pending"]

        if not pending:
            return self._spawned

        with ThreadPoolExecutor(max_workers=self.max_concurrent) as pool:
            futures = {}
            for agent in pending:
                agent.status = "running"
                future = pool.submit(self._execute_agent, agent)
                futures[future] = agent

            for future in as_completed(futures, timeout=timeout):
                agent = futures[future]
                try:
                    result = future.result(timeout=max(1.0, timeout))
                    agent.result = result
                    agent.status = "completed"
                except TimeoutError:
                    agent.status = "failed"
                    agent.error = f"Timed out after {timeout}s"
                    logger.warning("Sub-agent '%s' timed out", agent.name)
                except Exception as e:
                    agent.status = "failed"
                    agent.error = str(e)
                    logger.warning("Sub-agent '%s' failed: %s", agent.name, e)

        return self._spawned

    def get_pending_count(self) -> int:
        """Return the number of pending (not yet executed) agents."""
        return sum(1 for s in self._spawned if s.status == "pending")

    def get_completed_results(self) -> list[SpawnedAgent]:
        """Return only completed agents with results."""
        return [s for s in self._spawned if s.status == "completed"]

    def clear(self) -> None:
        """Clear all spawned agents (reset state)."""
        self._spawned.clear()

    def _execute_agent(self, agent: SpawnedAgent) -> str:
        """Execute a single spawned agent using the registered executor.

        Args:
            agent: The SpawnedAgent to execute

        Returns:
            Result string from the executor
        """
        start = time.monotonic()

        executor = self._executors.get(agent.specialist_type)
        if not executor:
            raise ValueError(f"No executor registered for type: {agent.specialist_type}")

        try:
            result = executor(agent)
            agent.elapsed_seconds = time.monotonic() - start
            return result
        except Exception:
            agent.elapsed_seconds = time.monotonic() - start
            raise

    def _classify_task(self, task: str) -> str:
        """Auto-detect specialist type from task description.

        Uses word-boundary keyword matching against classification rules
        to determine the most appropriate specialist type. Multi-word
        keywords use substring matching; single words use word boundaries
        to avoid false matches (e.g., "find" in "findings").

        Args:
            task: Task description text

        Returns:
            SpecialistType string value
        """
        task_lower = task.lower()

        for keywords, specialist_type in _CLASSIFICATION_RULES:
            for kw in keywords:
                if " " in kw:
                    # Multi-word keywords: use substring match
                    if kw in task_lower:
                        return specialist_type.value
                else:
                    # Single-word keywords: use word boundary match
                    if re.search(rf"\b{re.escape(kw)}\b", task_lower):
                        return specialist_type.value

        # Default to retrieval for unclassified tasks
        return SpecialistType.RETRIEVAL.value

    # ----------------------------------------------------------------
    # Default executor implementations
    # ----------------------------------------------------------------

    def _execute_retrieval(self, agent: SpawnedAgent) -> str:
        """Execute a retrieval specialist: search parent's memory.

        Opens a read-only connection to the parent's memory and searches
        for facts related to the task.
        """
        try:
            from ..memory_retrieval import MemoryRetriever

            retriever = MemoryRetriever(
                agent_name=self.parent_agent_name,
                storage_path=Path(agent.parent_memory_path),
            )
            try:
                results = retriever.search(query=agent.task, limit=20)
                if not results:
                    return "No relevant facts found."

                facts = []
                for r in results:
                    facts.append(f"- {r.get('context', '')}: {r.get('outcome', '')}")
                return f"Retrieved {len(results)} facts:\n" + "\n".join(facts)
            finally:
                retriever.close()
        except ImportError:
            return "Memory library not available for retrieval."
        except Exception as e:
            return f"Retrieval failed: {e}"

    def _execute_analysis(self, agent: SpawnedAgent) -> str:
        """Execute an analysis specialist: detect patterns in facts.

        Retrieves facts and summarizes patterns found.
        """
        try:
            from ..memory_retrieval import MemoryRetriever

            retriever = MemoryRetriever(
                agent_name=self.parent_agent_name,
                storage_path=Path(agent.parent_memory_path),
            )
            try:
                results = retriever.search(query=agent.task, limit=30)
                if not results:
                    return "No facts available for analysis."

                # Simple pattern detection: group by context
                contexts: dict[str, list[str]] = {}
                for r in results:
                    ctx = r.get("context", "unknown")
                    outcome = r.get("outcome", "")
                    contexts.setdefault(ctx, []).append(outcome)

                analysis_parts = [f"Analysis of {len(results)} facts:"]
                for ctx, outcomes in sorted(contexts.items(), key=lambda x: -len(x[1])):
                    analysis_parts.append(f"  [{ctx}] ({len(outcomes)} facts)")

                return "\n".join(analysis_parts)
            finally:
                retriever.close()
        except ImportError:
            return "Memory library not available for analysis."
        except Exception as e:
            return f"Analysis failed: {e}"

    def _execute_synthesis(self, agent: SpawnedAgent) -> str:
        """Execute a synthesis specialist: combine multiple facts."""
        try:
            from ..memory_retrieval import MemoryRetriever

            retriever = MemoryRetriever(
                agent_name=self.parent_agent_name,
                storage_path=Path(agent.parent_memory_path),
            )
            try:
                results = retriever.search(query=agent.task, limit=20)
                if not results:
                    return "No facts available for synthesis."

                # Build a combined summary
                facts = [r.get("outcome", "") for r in results if r.get("outcome")]
                combined = " | ".join(f[:100] for f in facts[:10])
                return f"Synthesis of {len(facts)} facts: {combined}"
            finally:
                retriever.close()
        except ImportError:
            return "Memory library not available for synthesis."
        except Exception as e:
            return f"Synthesis failed: {e}"

    def _execute_code_generation(self, agent: SpawnedAgent) -> str:
        """Execute a code generation specialist.

        Generates a simple code template based on the task description.
        In production, this would call an LLM for code generation.
        """
        task = agent.task
        # Simple template-based code generation
        if "script" in task.lower() or "python" in task.lower():
            return f'# Generated script for: {task}\n\ndef main():\n    """Auto-generated."""\n    pass\n\nif __name__ == "__main__":\n    main()\n'
        return f"Code generation for: {task} (requires LLM integration)"

    def _execute_research(self, agent: SpawnedAgent) -> str:
        """Execute a research specialist.

        In production, this would do web searches. Currently returns
        a placeholder indicating research capability.
        """
        return f"Research task queued: {agent.task} (external search not implemented)"


__all__ = ["AgentSpawner", "SpawnedAgent", "SpecialistType"]
