"""Tests for domain agent base classes."""

from __future__ import annotations

from typing import Any

import pytest

from amplihack.agents.domain_agents.base import (
    DomainAgent,
    EvalLevel,
    EvalScenario,
    TaskResult,
    TeachingResult,
)


class ConcreteDomainAgent(DomainAgent):
    """Concrete implementation for testing the ABC."""

    def _register_tools(self) -> None:
        self.executor.register_action("echo", lambda text: text)

    def execute_task(self, task: dict[str, Any]) -> TaskResult:
        text = task.get("text", "")
        result = self.executor.execute("echo", text=text)
        return TaskResult(success=result.success, output=result.output)

    def get_eval_levels(self) -> list[EvalLevel]:
        return [
            EvalLevel(
                level_id="L1",
                name="Basic",
                description="Basic test",
                scenarios=[
                    EvalScenario(
                        scenario_id="L1-001",
                        name="Echo test",
                        input_data={"text": "hello"},
                        expected_output={"equals": "hello"},
                        grading_rubric="Check output equals input",
                    )
                ],
            )
        ]

    def teach(self, topic: str, student_level: str = "beginner") -> TeachingResult:
        return TeachingResult(
            lesson_plan=f"Plan for {topic}",
            instruction=f"Learn about {topic}",
            student_questions=["What is this?"],
            agent_answers=["This is a test answer."],
            student_attempt="Student tried and found something.",
        )

    def get_system_prompt(self) -> str:
        return "You are a test agent."


class TestDomainAgentBase:
    """Test the DomainAgent ABC contract."""

    def test_init_valid(self):
        agent = ConcreteDomainAgent("test_agent", "test_domain")
        assert agent.agent_name == "test_agent"
        assert agent.domain == "test_domain"

    def test_init_empty_name_raises(self):
        with pytest.raises(ValueError, match="agent_name cannot be empty"):
            ConcreteDomainAgent("", "test_domain")

    def test_init_empty_domain_raises(self):
        with pytest.raises(ValueError, match="domain cannot be empty"):
            ConcreteDomainAgent("test_agent", "")

    def test_tools_registered(self):
        agent = ConcreteDomainAgent("test_agent", "test_domain")
        assert "echo" in agent.get_available_tools()

    def test_execute_task(self):
        agent = ConcreteDomainAgent("test_agent", "test_domain")
        result = agent.execute_task({"text": "hello world"})
        assert result.success is True
        assert result.output == "hello world"

    def test_get_eval_levels(self):
        agent = ConcreteDomainAgent("test_agent", "test_domain")
        levels = agent.get_eval_levels()
        assert len(levels) == 1
        assert levels[0].level_id == "L1"
        assert len(levels[0].scenarios) == 1

    def test_teach(self):
        agent = ConcreteDomainAgent("test_agent", "test_domain")
        result = agent.teach("test topic")
        assert "test topic" in result.lesson_plan
        assert result.instruction
        assert len(result.student_questions) > 0
        assert len(result.agent_answers) > 0

    def test_get_system_prompt(self):
        agent = ConcreteDomainAgent("test_agent", "test_domain")
        prompt = agent.get_system_prompt()
        assert "test agent" in prompt.lower()


class TestEvalScenario:
    """Test EvalScenario dataclass."""

    def test_create_scenario(self):
        scenario = EvalScenario(
            scenario_id="S-001",
            name="Test Scenario",
            input_data={"code": "print('hi')"},
            expected_output={"min_issues": 0},
            grading_rubric="Check for issues",
        )
        assert scenario.scenario_id == "S-001"
        assert scenario.input_data["code"] == "print('hi')"


class TestEvalLevel:
    """Test EvalLevel dataclass."""

    def test_create_level(self):
        level = EvalLevel(
            level_id="L2",
            name="Intermediate",
            description="Tests intermediate skills",
            scenarios=[],
            passing_threshold=0.6,
        )
        assert level.level_id == "L2"
        assert level.passing_threshold == 0.6

    def test_default_threshold(self):
        level = EvalLevel(
            level_id="L1",
            name="Basic",
            description="Basic",
            scenarios=[],
        )
        assert level.passing_threshold == 0.7


class TestTaskResult:
    """Test TaskResult dataclass."""

    def test_success_result(self):
        result = TaskResult(success=True, output={"data": 42})
        assert result.success is True
        assert result.output["data"] == 42
        assert result.error is None

    def test_failure_result(self):
        result = TaskResult(success=False, output=None, error="Something broke")
        assert result.success is False
        assert result.error == "Something broke"


class TestTeachingResult:
    """Test TeachingResult dataclass."""

    def test_create_result(self):
        result = TeachingResult(
            lesson_plan="Plan",
            instruction="Instruction",
            student_questions=["Q1"],
            agent_answers=["A1"],
            student_attempt="Attempt",
        )
        assert result.lesson_plan == "Plan"
        assert len(result.student_questions) == 1
        assert result.scores == {}
