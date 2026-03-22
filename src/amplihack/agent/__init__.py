"""amplihack.agent — Stable public API for the goal-seeking agent generator.

This module is the single import surface that external packages (agent-haymaker,
haymaker-workload-starter, etc.) should use.  Internal locations may reorganise
at any time; this façade guarantees a stable import path.

Public API:
    LearningAgent     -- Generic agent that learns content and answers questions.
    CognitiveAdapter  -- 6-type cognitive memory wrapper around LearningAgent.
    AgenticLoop       -- PERCEIVE → ORIENT → DECIDE → ACT (OODA) loop engine.
    Memory            -- High-level memory façade (remember / recall / facts).
    GoalAgentGenerator -- High-level orchestrator: analyse → plan → synthesise → assemble.

    # Goal-agent-generator pipeline components
    PromptAnalyzer, ObjectivePlanner, SkillSynthesizer, AgentAssembler,
    GoalAgentPackager

Usage:
    from amplihack.agent import LearningAgent, Memory
    from amplihack.agent import GoalAgentGenerator
    from amplihack.agent import PromptAnalyzer, ObjectivePlanner
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Core learning agent and cognitive adapter
# ---------------------------------------------------------------------------
from amplihack.agents.goal_seeking import (
    AgenticLoop,
    CognitiveAdapter,
    FlatRetrieverAdapter,
    HierarchicalMemory,
    LearningAgent,
)

# Backward-compatible alias retained from goal_seeking module
WikipediaLearningAgent = LearningAgent

# ---------------------------------------------------------------------------
# Memory façade
# ---------------------------------------------------------------------------
from amplihack.memory.facade import Memory

# ---------------------------------------------------------------------------
# Goal-agent-generator pipeline
# ---------------------------------------------------------------------------
from amplihack.goal_agent_generator import (
    AgentAssembler,
    GoalAgentPackager,
    ObjectivePlanner,
    PromptAnalyzer,
    SkillSynthesizer,
)
from amplihack.goal_agent_generator.models import (
    ExecutionPlan,
    GoalAgentBundle,
    GoalDefinition,
    PlanPhase,
    SDKToolConfig,
    SkillDefinition,
)


class GoalAgentGenerator:
    """High-level orchestrator that wraps the full goal-agent pipeline.

    Convenience class so callers need only one import instead of five.

    Example::

        gen = GoalAgentGenerator()
        agent_dir = gen.generate(goal_path=Path("goals/my-goal.md"), sdk="claude")
    """

    def __init__(self) -> None:
        self._analyzer = PromptAnalyzer()
        self._planner = ObjectivePlanner()
        self._synthesizer = SkillSynthesizer()
        self._assembler = AgentAssembler()

    def generate(
        self,
        goal_path: object,
        sdk: str = "claude",
        enable_memory: bool = False,
        output_dir: object = None,
        bundle_name: str = "agent",
    ) -> object:
        """Run the full pipeline: analyse → plan → synthesise → assemble → package.

        Args:
            goal_path: Path to a markdown goal file.
            sdk: SDK backend (``"claude"``, ``"copilot"``, ``"microsoft"``).
            enable_memory: Enable persistent memory for the generated agent.
            output_dir: Directory in which to write the agent bundle.
            bundle_name: Base name for the generated agent bundle.

        Returns:
            Path to the generated agent directory.
        """
        from pathlib import Path

        if output_dir is None:
            output_dir = Path(f".haymaker/agents/{bundle_name}")

        goal_def = self._analyzer.analyze(goal_path)
        plan = self._planner.generate_plan(goal_def)
        synthesis = self._synthesizer.synthesize_with_sdk_tools(plan, sdk=sdk)
        skills = synthesis.get("skills", [])
        sdk_tools = synthesis.get("sdk_tools", [])
        bundle = self._assembler.assemble(
            goal_def,
            plan,
            skills,
            bundle_name=bundle_name,
            enable_memory=enable_memory,
            sdk=sdk,
            sdk_tools=sdk_tools,
        )
        packager = GoalAgentPackager(output_dir=output_dir)
        return packager.package(bundle)


__all__ = [
    # Core agents
    "LearningAgent",
    "WikipediaLearningAgent",
    "CognitiveAdapter",
    "AgenticLoop",
    "FlatRetrieverAdapter",
    "HierarchicalMemory",
    # Memory
    "Memory",
    # Goal-agent generator pipeline
    "GoalAgentGenerator",
    "PromptAnalyzer",
    "ObjectivePlanner",
    "SkillSynthesizer",
    "AgentAssembler",
    "GoalAgentPackager",
    # Models
    "GoalDefinition",
    "ExecutionPlan",
    "PlanPhase",
    "SkillDefinition",
    "SDKToolConfig",
    "GoalAgentBundle",
]
