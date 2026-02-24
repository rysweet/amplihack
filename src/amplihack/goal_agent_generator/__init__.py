"""
Goal Agent Generator - Create specialized agents from natural language goals.

This module generates autonomous goal-seeking agents that can execute complex
objectives by assembling skills, plans, and execution strategies.
"""

from .agent_assembler import AgentAssembler
from .models import (
    ExecutionPlan,
    GoalAgentBundle,
    GoalDefinition,
    PlanPhase,
    SDKToolConfig,
    SkillDefinition,
    SubAgentConfig,
)
from .objective_planner import ObjectivePlanner
from .packager import GoalAgentPackager
from .prompt_analyzer import PromptAnalyzer
from .skill_synthesizer import SkillSynthesizer

__version__ = "1.0.0"

__all__ = [
    "GoalDefinition",
    "ExecutionPlan",
    "SkillDefinition",
    "SDKToolConfig",
    "SubAgentConfig",
    "GoalAgentBundle",
    "PlanPhase",
    "PromptAnalyzer",
    "ObjectivePlanner",
    "SkillSynthesizer",
    "AgentAssembler",
    "GoalAgentPackager",
]
