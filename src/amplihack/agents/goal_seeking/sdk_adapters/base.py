"""Base abstraction for SDK-agnostic goal-seeking agents.

Philosophy:
- SDK-agnostic: same interface regardless of underlying SDK
- Goal-oriented: agents form evaluable goals
- Spawnable: agents can dynamically create sub-agents for complex tasks
- Memory-shared: spawned agents share read access to parent memory
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SDKType(str, Enum):
    """Supported SDK types for agent generation."""

    CLAUDE = "claude"
    COPILOT = "copilot"
    MICROSOFT = "microsoft"
    MINI = "mini"


@dataclass
class AgentTool:
    """SDK-agnostic tool definition."""

    name: str
    description: str
    parameters: dict[str, Any]
    function: Any
    requires_approval: bool = False
    category: str = "core"


@dataclass
class AgentResult:
    """Result from an agent run."""

    response: str = ""
    goal_achieved: bool = False
    tools_used: list[str] = field(default_factory=list)
    turns: int = 0
    reasoning_trace: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Goal:
    """An evaluable goal formed from user intent."""

    description: str
    success_criteria: str = ""
    plan: list[str] = field(default_factory=list)
    status: str = "pending"


class GoalSeekingAgent(ABC):
    """Abstract base class for SDK-agnostic goal-seeking agents.

    When enable_spawning=True, the agent gains a spawn_agent tool (#8)
    that allows it to dynamically create sub-agents for complex tasks.
    Spawned agents share read access to the parent's memory.
    """

    def __init__(
        self,
        name: str,
        instructions: str = "",
        sdk_type: SDKType = SDKType.MICROSOFT,
        model: str | None = None,
        storage_path: Path | None = None,
        enable_memory: bool = True,
        enable_eval: bool = False,
        enable_spawning: bool = False,
    ):
        if not name or not name.strip():
            raise ValueError("Agent name cannot be empty")

        self.name = name.strip()
        self.instructions = instructions
        self.sdk_type = sdk_type
        self.model = model or os.environ.get("EVAL_MODEL", "gpt-4o")
        self.storage_path = storage_path or Path.home() / ".amplihack" / "agents" / name
        self.enable_memory = enable_memory
        self.enable_eval = enable_eval
        self.enable_spawning = enable_spawning

        self.memory: Any = None
        if enable_memory:
            self._init_memory()

        # Initialize spawner if enabled
        self.spawner: Any = None
        if enable_spawning:
            self._init_spawner()

        self._tools: list[AgentTool] = []
        self._register_learning_tools()

        self.current_goal: Goal | None = None
        self._sdk_agent: Any = None
        self._create_sdk_agent()

    def _init_memory(self) -> None:
        """Initialize amplihack-memory-lib for persistent knowledge storage."""
        try:
            from amplihack.agents.goal_seeking.memory_retrieval import MemoryRetriever

            self.memory = MemoryRetriever(agent_name=self.name, storage_path=self.storage_path)
            logger.info("Memory initialized for agent '%s'", self.name)
        except ImportError:
            logger.warning(
                "amplihack-memory-lib not installed. Continuing without persistent memory."
            )
        except Exception as e:
            logger.warning("Failed to initialize memory: %s. Continuing without memory.", e)

    def _init_spawner(self) -> None:
        """Initialize the AgentSpawner for dynamic sub-agent creation."""
        try:
            from amplihack.agents.goal_seeking.sub_agents.agent_spawner import AgentSpawner

            self.spawner = AgentSpawner(
                parent_agent_name=self.name,
                parent_memory_path=str(self.storage_path),
                sdk_type=self.sdk_type.value if isinstance(self.sdk_type, SDKType) else self.sdk_type,
            )
            logger.info("Spawner initialized for agent '%s'", self.name)
        except ImportError:
            logger.warning("AgentSpawner not available. Continuing without spawning.")
        except Exception as e:
            logger.warning("Failed to initialize spawner: %s", e)

    def _register_learning_tools(self) -> None:
        """Register the 7 learning/teaching/applying tools + optional spawn_agent (tool #8)."""
        tools: list[AgentTool] = [
            AgentTool(
                name="learn_from_content",
                description="Learn from text by extracting and storing facts",
                parameters={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Content to learn from"}
                    },
                    "required": ["content"],
                },
                function=self._tool_learn,
                category="learning",
            ),
            AgentTool(
                name="search_memory",
                description="Search stored knowledge for relevant facts",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Max results", "default": 10},
                    },
                    "required": ["query"],
                },
                function=self._tool_search,
                category="memory",
            ),
            AgentTool(
                name="explain_knowledge",
                description="Generate an explanation of a topic from stored knowledge",
                parameters={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Topic to explain"},
                        "depth": {
                            "type": "string",
                            "enum": ["brief", "overview", "comprehensive"],
                            "default": "overview",
                        },
                    },
                    "required": ["topic"],
                },
                function=self._tool_explain,
                category="teaching",
            ),
            AgentTool(
                name="find_knowledge_gaps",
                description="Identify what is unknown about a topic",
                parameters={
                    "type": "object",
                    "properties": {"topic": {"type": "string", "description": "Topic to analyze"}},
                    "required": ["topic"],
                },
                function=self._tool_find_gaps,
                category="learning",
            ),
            AgentTool(
                name="verify_fact",
                description="Check if a fact is consistent with stored knowledge",
                parameters={
                    "type": "object",
                    "properties": {"fact": {"type": "string", "description": "Fact to verify"}},
                    "required": ["fact"],
                },
                function=self._tool_verify,
                category="applying",
            ),
            AgentTool(
                name="store_fact",
                description="Store a fact in memory with context and confidence",
                parameters={
                    "type": "object",
                    "properties": {
                        "context": {"type": "string", "description": "Topic/context"},
                        "fact": {"type": "string", "description": "The fact to store"},
                        "confidence": {
                            "type": "number",
                            "description": "Confidence 0-1",
                            "default": 0.8,
                        },
                    },
                    "required": ["context", "fact"],
                },
                function=self._tool_store,
                category="memory",
            ),
            AgentTool(
                name="get_memory_summary",
                description="Get an overview of what the agent knows",
                parameters={"type": "object", "properties": {}},
                function=self._tool_summary,
                category="memory",
            ),
        ]

        # Tool #8: spawn_agent (only when spawning is enabled)
        if self.enable_spawning and self.spawner:
            tools.append(
                AgentTool(
                    name="spawn_agent",
                    description=(
                        "Spawn a sub-agent to handle a specific task. "
                        "Types: retrieval, analysis, synthesis, code_generation, research, auto"
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "task": {
                                "type": "string",
                                "description": "Task description for the sub-agent",
                            },
                            "specialist_type": {
                                "type": "string",
                                "enum": [
                                    "retrieval",
                                    "analysis",
                                    "synthesis",
                                    "code_generation",
                                    "research",
                                    "auto",
                                ],
                                "default": "auto",
                                "description": "Type of specialist to spawn",
                            },
                        },
                        "required": ["task"],
                    },
                    function=self._tool_spawn_agent,
                    category="spawning",
                )
            )

        for t in tools:
            self._tools.append(t)

    def _tool_spawn_agent(self, task: str, specialist_type: str = "auto") -> str:
        """Tool function: spawn a sub-agent for complex tasks.

        Creates a sub-agent, executes it, and returns the result.
        The sub-agent shares read access to the parent's memory.

        Args:
            task: Task description for the sub-agent
            specialist_type: Type of specialist (auto, retrieval, etc.)

        Returns:
            Result string from the sub-agent, or error message
        """
        if not self.spawner:
            return "Spawning not enabled for this agent"
        if not task or not task.strip():
            return "Error: Task cannot be empty"

        try:
            self.spawner.spawn(task, specialist_type)
            results = self.spawner.collect_results(timeout=30.0)
            completed = [r for r in results if r.status == "completed" and r.task == task]
            if completed:
                return completed[-1].result or "Sub-agent completed with no result"
            failed = [r for r in results if r.status == "failed" and r.task == task]
            if failed:
                return f"Sub-agent failed: {failed[-1].error}"
            return "Sub-agent did not complete"
        except Exception as e:
            return f"Spawning failed: {e}"

    def _tool_learn(self, content: str) -> dict[str, Any]:
        if not self.memory:
            return {"error": "Memory not initialized"}
        if not content or not content.strip():
            return {"error": "Content cannot be empty"}
        content = content[:50_000]
        self.memory.store_fact(
            context=f"learned_content_{self.name}", fact=content[:2000], confidence=0.8
        )
        return {"status": "learned", "content_length": len(content)}

    def _tool_search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        if not self.memory:
            return []
        if not query or not query.strip():
            return []
        limit = min(max(1, limit), 100)
        return self.memory.search(query=query.strip(), limit=limit)

    def _tool_explain(self, topic: str, depth: str = "overview") -> str:
        if not self.memory:
            return f"No knowledge about '{topic}'."
        results = self.memory.search(query=topic, limit=20)
        if not results:
            return f"No knowledge stored about '{topic}'."
        facts_text = "\n".join(f"- {r.get('outcome', '')[:150]}" for r in results[:10])
        return f"Knowledge about '{topic}':\n{facts_text}"

    def _tool_find_gaps(self, topic: str) -> dict[str, Any]:
        if not self.memory:
            return {"gaps": ["No memory initialized"], "total_facts": 0}
        results = self.memory.search(query=topic, limit=20)
        return {
            "topic": topic,
            "total_facts": len(results),
            "gaps": [] if results else ["No knowledge"],
        }

    def _tool_verify(self, fact: str) -> dict[str, Any]:
        if not self.memory:
            return {"verified": False, "reason": "No memory"}
        related = self.memory.search(query=fact, limit=10)
        return {"fact": fact, "related_facts": len(related), "verified": len(related) > 0}

    def _tool_store(self, context: str, fact: str, confidence: float = 0.8) -> dict[str, Any]:
        if not self.memory:
            return {"error": "Memory not initialized"}
        if not context or not fact:
            return {"error": "Context and fact are required"}
        confidence = max(0.0, min(1.0, confidence))
        self.memory.store_fact(
            context=context.strip()[:500], fact=fact.strip()[:2000], confidence=confidence
        )
        return {"stored": True}

    def _tool_summary(self) -> dict[str, Any]:
        if not self.memory:
            return {"error": "Memory not initialized"}
        try:
            return self.memory.get_statistics()
        except Exception:
            return {"total_experiences": 0}

    def form_goal(self, user_intent: str) -> Goal:
        self.current_goal = Goal(
            description=user_intent,
            success_criteria=f"Successfully completed: {user_intent}",
            plan=[],
            status="in_progress",
        )
        return self.current_goal

    @abstractmethod
    def _create_sdk_agent(self) -> None:
        """Initialize the SDK-specific agent."""

    @abstractmethod
    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Execute a task through the SDK agent loop."""

    @abstractmethod
    def _get_native_tools(self) -> list[str]:
        """Return list of native SDK tool names available."""

    @abstractmethod
    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        """Register a custom AgentTool with the SDK tool system."""

    async def run(self, task: str, max_turns: int = 10) -> AgentResult:
        if not task or not task.strip():
            return AgentResult(response="Error: Task cannot be empty", goal_achieved=False)
        self.form_goal(task)
        result = await self._run_sdk_agent(task, max_turns)
        if self.current_goal:
            self.current_goal.status = "achieved" if result.goal_achieved else "failed"
        return result

    def close(self) -> None:
        """Close the agent and release resources."""
        if self.memory:
            try:
                self.memory.close()
            except Exception as e:
                logger.debug("Error closing memory: %s", e)
        if self.spawner:
            try:
                self.spawner.clear()
            except Exception as e:
                logger.debug("Error clearing spawner: %s", e)


__all__ = ["GoalSeekingAgent", "AgentTool", "AgentResult", "Goal", "SDKType"]
