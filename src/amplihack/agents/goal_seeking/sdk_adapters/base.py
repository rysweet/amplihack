"""Base abstraction for SDK-agnostic goal-seeking agents.

Defines the interface that all SDK implementations must satisfy.
The GoalSeekingAgent ABC provides:
- Goal formation from user intent
- Iterative reasoning toward goals
- Learning from content (extract, store, organize)
- Teaching other agents (multi-turn conversation)
- Applying knowledge to novel situations
- Memory persistence via amplihack-memory-lib
- Tool registration (native SDK tools + custom learning tools)

Each SDK implementation fills in the _run_sdk_agent method and
maps native tools to the AgentTool interface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SDKType(str, Enum):
    """Supported SDK types for agent generation."""

    COPILOT = "copilot"  # GitHub Copilot SDK (default)
    CLAUDE = "claude"  # Claude Agent SDK (Anthropic)
    MICROSOFT = "microsoft"  # Microsoft Agent Framework
    MINI = "mini"  # Current mini-framework (LearningAgent + litellm)


@dataclass
class AgentTool:
    """SDK-agnostic tool definition.

    Each SDK implementation converts this to its native tool format:
    - Claude: Tool(name, description, input_schema, function)
    - Copilot: defineTool(name, {description, parameters, handler})
    - Microsoft: @function_tool decorated function

    Attributes:
        name: Unique tool identifier
        description: What the tool does (for LLM context)
        parameters: JSON Schema for input parameters
        function: Callable that implements the tool
        requires_approval: Whether to prompt for human approval
        category: Tool category (core, learning, memory, teaching, applying)
    """

    name: str
    description: str
    parameters: dict[str, Any]
    function: Any  # Callable
    requires_approval: bool = False
    category: str = "core"  # core, learning, memory, teaching, applying


@dataclass
class AgentResult:
    """Result from an agent run.

    Attributes:
        response: Final text response
        goal_achieved: Whether the goal was met
        tools_used: List of tool names invoked
        turns: Number of agent loop iterations
        reasoning_trace: Optional trace of reasoning steps
        metadata: Additional SDK-specific metadata
    """

    response: str = ""
    goal_achieved: bool = False
    tools_used: list[str] = field(default_factory=list)
    turns: int = 0
    reasoning_trace: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Goal:
    """An evaluable goal formed from user intent.

    Attributes:
        description: What the agent is trying to achieve
        success_criteria: How to determine if the goal is met
        plan: Steps to achieve the goal
        status: pending, in_progress, achieved, failed
    """

    description: str
    success_criteria: str = ""
    plan: list[str] = field(default_factory=list)
    status: str = "pending"


class GoalSeekingAgent(ABC):
    """Abstract base class for SDK-agnostic goal-seeking agents.

    All SDK implementations must implement:
    - _create_sdk_agent(): Initialize the SDK-specific agent
    - _run_sdk_agent(task): Execute a task through the SDK agent loop
    - _get_native_tools(): Return SDK-native tools (bash, file, web, etc.)
    - _register_tool(tool): Register a custom tool with the SDK

    The base class provides shared logic for:
    - Goal formation from intent
    - Memory management (amplihack-memory-lib)
    - Learning tool registration (explain, verify, find_gaps, etc.)
    - Teaching sessions between agents
    - Eval harness integration
    """

    def __init__(
        self,
        name: str,
        instructions: str = "",
        sdk_type: SDKType = SDKType.COPILOT,
        model: str | None = None,
        storage_path: Path | None = None,
        enable_memory: bool = True,
        enable_eval: bool = False,
    ):
        """Initialize goal-seeking agent.

        Args:
            name: Agent identifier
            instructions: System prompt / agent instructions
            sdk_type: Which SDK to use
            model: LLM model (SDK-specific default if None)
            storage_path: Path for memory database
            enable_memory: Whether to initialize amplihack-memory-lib
            enable_eval: Whether to include eval harness
        """
        self.name = name
        self.instructions = instructions
        self.sdk_type = sdk_type
        self.model = model
        self.storage_path = storage_path or Path.home() / ".amplihack" / "agents" / name
        self.enable_memory = enable_memory
        self.enable_eval = enable_eval

        # Memory (shared across all SDKs via amplihack-memory-lib)
        self.memory = None
        if enable_memory:
            self._init_memory()

        # Tools registry
        self._tools: list[AgentTool] = []
        self._register_learning_tools()

        # Current goal
        self.current_goal: Goal | None = None

        # SDK-specific initialization
        self._sdk_agent = None
        self._create_sdk_agent()

    def _init_memory(self) -> None:
        """Initialize amplihack-memory-lib (Kuzu backend)."""
        try:
            from ..cognitive_adapter import CognitiveAdapter

            self.memory = CognitiveAdapter(
                agent_name=self.name,
                db_path=self.storage_path,
            )
            logger.info("Memory initialized for agent '%s' at %s", self.name, self.storage_path)
        except Exception as e:
            logger.warning("Failed to initialize memory: %s. Continuing without memory.", e)

    def _register_learning_tools(self) -> None:
        """Register the 7 learning/teaching/applying tools."""
        learning_tools = [
            AgentTool(
                name="learn_from_content",
                description="Learn from text content by extracting and storing facts in memory",
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
                description="Identify what's unknown or uncertain about a topic",
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

        for tool in learning_tools:
            self._tools.append(tool)

    # ------------------------------------------------------------------
    # Tool implementations (shared across all SDKs)
    # ------------------------------------------------------------------

    def _tool_learn(self, content: str) -> dict[str, Any]:
        """Learn from content by extracting and storing facts."""
        if not self.memory:
            return {"error": "Memory not initialized"}
        # Use the memory adapter's store_fact for each extracted concept
        # In a full implementation, this would use LLM extraction
        self.memory.store_fact(context="learned", fact=content[:500], confidence=0.8)
        return {"status": "learned", "content_length": len(content)}

    def _tool_search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search memory for relevant facts."""
        if not self.memory:
            return []
        return self.memory.search(query=query, limit=limit)

    def _tool_explain(self, topic: str, depth: str = "overview") -> str:
        """Generate topic explanation from memory."""
        if not self.memory:
            return f"No knowledge about '{topic}'."
        facts = self.memory.search(query=topic, limit=20)
        if not facts:
            return f"No knowledge stored about '{topic}'."
        facts_text = "\n".join(f"- {f.get('outcome', '')[:150]}" for f in facts[:10])
        return f"Knowledge about '{topic}':\n{facts_text}"

    def _tool_find_gaps(self, topic: str) -> dict[str, Any]:
        """Identify knowledge gaps about a topic."""
        if not self.memory:
            return {"gaps": ["No memory initialized"], "total_facts": 0}
        facts = self.memory.search(query=topic, limit=20)
        return {
            "topic": topic,
            "total_facts": len(facts),
            "gaps": [] if facts else ["No knowledge"],
        }

    def _tool_verify(self, fact: str) -> dict[str, Any]:
        """Verify fact against stored knowledge."""
        if not self.memory:
            return {"verified": False, "reason": "No memory"}
        related = self.memory.search(query=fact, limit=10)
        return {"fact": fact, "related_facts": len(related), "verified": len(related) > 0}

    def _tool_store(self, context: str, fact: str, confidence: float = 0.8) -> dict[str, Any]:
        """Store a fact in memory."""
        if not self.memory:
            return {"error": "Memory not initialized"}
        node_id = self.memory.store_fact(context=context, fact=fact, confidence=confidence)
        return {"stored": True, "node_id": node_id}

    def _tool_summary(self) -> dict[str, Any]:
        """Get memory statistics."""
        if not self.memory:
            return {"error": "Memory not initialized"}
        return self.memory.get_statistics()

    # ------------------------------------------------------------------
    # Goal-seeking behavior (shared across all SDKs)
    # ------------------------------------------------------------------

    def form_goal(self, user_intent: str) -> Goal:
        """Form an evaluable goal from user intent.

        Args:
            user_intent: What the user wants to achieve

        Returns:
            Goal with description, success criteria, and initial plan
        """
        self.current_goal = Goal(
            description=user_intent,
            success_criteria=f"Successfully completed: {user_intent}",
            plan=[],
            status="in_progress",
        )
        return self.current_goal

    # ------------------------------------------------------------------
    # Abstract methods (SDK-specific implementations)
    # ------------------------------------------------------------------

    @abstractmethod
    def _create_sdk_agent(self) -> None:
        """Initialize the SDK-specific agent. Called during __init__."""

    @abstractmethod
    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Execute a task through the SDK's agent loop.

        This is where each SDK's native agent loop runs.
        The SDK handles tool calling, iteration, and response generation.

        Args:
            task: The task/prompt to execute
            max_turns: Maximum agent loop iterations

        Returns:
            AgentResult with response and metadata
        """

    @abstractmethod
    def _get_native_tools(self) -> list[str]:
        """Return list of native SDK tool names available.

        E.g., Claude SDK: ["bash", "read_file", "write_file", "glob", "grep"]
        Copilot SDK: ["file_system", "git", "web"]
        Microsoft: depends on configuration
        """

    @abstractmethod
    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        """Register a custom AgentTool with the SDK's tool system."""

    # ------------------------------------------------------------------
    # Public API (works the same regardless of SDK)
    # ------------------------------------------------------------------

    async def run(self, task: str, max_turns: int = 10) -> AgentResult:
        """Run the agent on a task.

        Forms a goal, executes via the SDK's agent loop, evaluates result.

        Args:
            task: What to accomplish
            max_turns: Maximum iterations

        Returns:
            AgentResult with response and goal achievement status
        """
        self.form_goal(task)
        result = await self._run_sdk_agent(task, max_turns)

        if self.current_goal:
            self.current_goal.status = "achieved" if result.goal_achieved else "failed"

        return result

    def close(self) -> None:
        """Release resources."""
        if self.memory:
            self.memory.close()


__all__ = ["GoalSeekingAgent", "AgentTool", "AgentResult", "Goal", "SDKType"]
