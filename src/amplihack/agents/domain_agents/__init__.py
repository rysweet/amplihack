"""Domain-specific goal-seeking agents.

Public API:
    DomainAgent: Abstract base class
    EvalLevel / EvalScenario: Evaluation types
    SkillInjector: Skill injection registry

Concrete agents:
    CodeReviewAgent: Reviews code for quality, security, and style
    MeetingSynthesizerAgent: Synthesizes meeting transcripts
    DocumentCreatorAgent: Creates and evaluates structured documents
    DataAnalysisAgent: Analyzes data, detects trends, generates insights
    ProjectPlanningAgent: Decomposes projects, identifies dependencies, assesses risks
"""

from .base import DomainAgent, EvalLevel, EvalScenario, TaskResult, TeachingResult
from .code_review import CodeReviewAgent
from .data_analysis import DataAnalysisAgent
from .document_creator import DocumentCreatorAgent
from .meeting_synthesizer import MeetingSynthesizerAgent
from .project_planning import ProjectPlanningAgent
from .skill_injector import SkillInjector

__all__ = [
    "DomainAgent",
    "EvalLevel",
    "EvalScenario",
    "TaskResult",
    "TeachingResult",
    "SkillInjector",
    "CodeReviewAgent",
    "MeetingSynthesizerAgent",
    "DocumentCreatorAgent",
    "DataAnalysisAgent",
    "ProjectPlanningAgent",
]
