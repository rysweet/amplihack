"""Domain-specific goal-seeking agents.

Public API:
    DomainAgent: Abstract base class
    EvalLevel / EvalScenario: Evaluation types
    SkillInjector: Skill injection registry
"""

from .base import DomainAgent, EvalLevel, EvalScenario, TaskResult, TeachingResult
from .skill_injector import SkillInjector

__all__ = [
    "DomainAgent",
    "EvalLevel",
    "EvalScenario",
    "TaskResult",
    "TeachingResult",
    "SkillInjector",
]
