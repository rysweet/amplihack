"""
Goal Agent Generator - Create specialized agents from natural language goals.

This module generates autonomous goal-seeking agents that can execute complex
objectives by assembling skills, plans, and execution strategies.

Phase 1: Match existing skills from .claude/agents directory
Phase 2: AI-powered custom skill generation using Claude SDK
"""

from .models import (
    GoalDefinition,
    ExecutionPlan,
    SkillDefinition,
    GoalAgentBundle,
    PlanPhase,
    # Phase 2 models
    SkillGapReport,
    GeneratedSkillDefinition,
    ValidationResult,
)
from .prompt_analyzer import PromptAnalyzer
from .objective_planner import ObjectivePlanner
from .skill_synthesizer import SkillSynthesizer
from .agent_assembler import AgentAssembler
from .packager import GoalAgentPackager

# Phase 2 components (lazy import)
try:
    from .phase2 import (
        SkillGapAnalyzer,
        SkillValidator,
        AISkillGenerator,
        SkillRegistry,
    )

    PHASE2_AVAILABLE = True
except ImportError:
    PHASE2_AVAILABLE = False
    SkillGapAnalyzer = None
    SkillValidator = None
    AISkillGenerator = None
    SkillRegistry = None

__version__ = "2.0.0"

__all__ = [
    # Phase 1 (Core)
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
    # Phase 2 (AI Skill Generation)
    "SkillGapReport",
    "GeneratedSkillDefinition",
    "ValidationResult",
    "SkillGapAnalyzer",
    "SkillValidator",
    "AISkillGenerator",
    "SkillRegistry",
    "PHASE2_AVAILABLE",
]
