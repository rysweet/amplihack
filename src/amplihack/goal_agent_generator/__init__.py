"""
Goal Agent Generator - Create specialized agents from natural language goals.

This module generates autonomous goal-seeking agents that can execute complex
objectives by assembling skills, plans, and execution strategies.
"""

from .models import (
    GoalDefinition,
    ExecutionPlan,
    SkillDefinition,
    GoalAgentBundle,
    PlanPhase,
)
from .prompt_analyzer import PromptAnalyzer
from .objective_planner import ObjectivePlanner
from .skill_synthesizer import SkillSynthesizer
from .agent_assembler import AgentAssembler
from .packager import GoalAgentPackager

__version__ = "1.0.0"

__all__ = [
    "GoalDefinition",
    "ExecutionPlan",
    "SkillDefinition",
    "GoalAgentBundle",
    "PlanPhase",
    "PromptAnalyzer",
    "ObjectivePlanner",
    "SkillSynthesizer",
    "AgentAssembler",
    "GoalAgentPackager",
]
