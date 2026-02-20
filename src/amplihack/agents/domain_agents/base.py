"""Abstract base class for domain-specific goal-seeking agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from amplihack.agents.goal_seeking.action_executor import ActionExecutor


@dataclass
class EvalScenario:
    """A single evaluation scenario."""

    scenario_id: str
    name: str
    input_data: dict[str, Any]
    expected_output: dict[str, Any]
    grading_rubric: str


@dataclass
class EvalLevel:
    """An evaluation level with test scenarios."""

    level_id: str
    name: str
    description: str
    scenarios: list[EvalScenario]
    passing_threshold: float = 0.7


@dataclass
class TaskResult:
    """Result of executing a domain task."""

    success: bool
    output: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class TeachingResult:
    """Result of a teaching session."""

    lesson_plan: str
    instruction: str
    student_questions: list[str]
    agent_answers: list[str]
    student_attempt: str
    scores: dict[str, float] = field(default_factory=dict)


class DomainAgent(ABC):
    """Abstract base class for domain-specific goal-seeking agents."""

    def __init__(
        self,
        agent_name: str,
        domain: str,
        model: str = "gpt-4o-mini",
        skill_injector: Any | None = None,
    ):
        if not agent_name or not agent_name.strip():
            raise ValueError("agent_name cannot be empty")
        if not domain or not domain.strip():
            raise ValueError("domain cannot be empty")

        self.agent_name = agent_name.strip()
        self.domain = domain.strip()
        self.model = model
        self.executor = ActionExecutor()
        self.injected_skills: list[str] = []

        self._register_tools()

        if skill_injector:
            self._inject_skills(skill_injector)

    @abstractmethod
    def _register_tools(self) -> None:
        """Register domain-specific tools with the action executor."""

    @abstractmethod
    def execute_task(self, task: dict[str, Any]) -> TaskResult:
        """Execute a domain-specific task."""

    @abstractmethod
    def get_eval_levels(self) -> list[EvalLevel]:
        """Return evaluation levels for this domain."""

    @abstractmethod
    def teach(self, topic: str, student_level: str = "beginner") -> TeachingResult:
        """Teach a student about a domain topic."""

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this domain agent."""

    def _inject_skills(self, skill_injector) -> None:
        """Inject skills from the amplihack skill system."""
        domain_skills = skill_injector.get_skills_for_domain(self.domain)
        for skill_name, tool_fn in domain_skills.items():
            if not self.executor.has_action(skill_name):
                self.executor.register_action(skill_name, tool_fn)
                self.injected_skills.append(skill_name)

    def get_available_tools(self) -> list[str]:
        """Get all available tools including injected skills."""
        return self.executor.get_available_actions()
