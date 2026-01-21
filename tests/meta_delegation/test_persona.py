"""Unit tests for Persona Strategy Module.

Tests persona behavior strategies and decision-making logic.
These tests will FAIL until the persona module is implemented.
"""

from dataclasses import is_dataclass
from typing import List

import pytest

# These imports will fail until implementation exists
try:
    from amplihack.meta_delegation.persona import (
        ARCHITECT,
        GUIDE,
        JUNIOR_DEV,
        QA_ENGINEER,
        PersonaStrategy,
        get_persona_strategy,
        register_persona,
    )
except ImportError:
    pytest.skip("persona module not implemented yet", allow_module_level=True)


class TestPersonaStrategy:
    """Test PersonaStrategy dataclass."""

    def test_persona_strategy_is_dataclass(self):
        """Test PersonaStrategy is implemented as dataclass."""
        assert is_dataclass(PersonaStrategy)

    def test_persona_strategy_has_required_fields(self):
        """Test PersonaStrategy has all required fields."""
        required_fields = [
            "name",
            "communication_style",
            "thoroughness_level",
            "evidence_collection_priority",
            "prompt_template",
        ]

        persona = PersonaStrategy(
            name="test",
            communication_style="direct",
            thoroughness_level="balanced",
            evidence_collection_priority=["code_file"],
            prompt_template="Test: {goal}",
        )

        for field in required_fields:
            assert hasattr(persona, field), f"Missing required field: {field}"

    def test_persona_strategy_evidence_priority_is_list(self):
        """Test evidence_collection_priority is a list."""
        persona = PersonaStrategy(
            name="test",
            communication_style="direct",
            thoroughness_level="balanced",
            evidence_collection_priority=["code_file", "test_file"],
            prompt_template="Test",
        )

        assert isinstance(persona.evidence_collection_priority, list)
        assert len(persona.evidence_collection_priority) >= 1

    def test_persona_strategy_prompt_template_has_placeholders(self):
        """Test prompt_template contains required placeholders."""
        persona = PersonaStrategy(
            name="test",
            communication_style="direct",
            thoroughness_level="balanced",
            evidence_collection_priority=["code_file"],
            prompt_template="Goal: {goal}, Criteria: {success_criteria}",
        )

        assert "{goal}" in persona.prompt_template
        assert "{success_criteria}" in persona.prompt_template


class TestGuidePersona:
    """Test GUIDE persona configuration."""

    def test_guide_persona_exists(self):
        """Test GUIDE persona is defined."""
        assert GUIDE is not None
        assert isinstance(GUIDE, PersonaStrategy)

    def test_guide_persona_name(self):
        """Test GUIDE has correct name."""
        assert GUIDE.name == "guide"

    def test_guide_communication_style(self):
        """Test GUIDE uses socratic communication style."""
        assert GUIDE.communication_style == "socratic"

    def test_guide_thoroughness_level(self):
        """Test GUIDE has balanced thoroughness."""
        assert GUIDE.thoroughness_level == "balanced"

    def test_guide_evidence_priorities(self):
        """Test GUIDE prioritizes documentation and educational content."""
        priorities = GUIDE.evidence_collection_priority

        assert isinstance(priorities, list)
        assert len(priorities) > 0

        # Guide should prioritize documentation
        assert "documentation" in priorities or "docs" in str(priorities).lower()

    def test_guide_prompt_template_emphasizes_teaching(self):
        """Test GUIDE prompt template emphasizes teaching and learning."""
        template = GUIDE.prompt_template.lower()

        teaching_keywords = ["teach", "learn", "explain", "understand", "guide", "educate"]
        assert any(
            keyword in template for keyword in teaching_keywords
        ), "Guide prompt missing teaching emphasis"

    def test_guide_prompt_template_has_required_fields(self):
        """Test GUIDE prompt template has goal and success_criteria placeholders."""
        assert "{goal}" in GUIDE.prompt_template
        assert "{success_criteria}" in GUIDE.prompt_template


class TestQAEngineerPersona:
    """Test QA_ENGINEER persona configuration."""

    def test_qa_engineer_persona_exists(self):
        """Test QA_ENGINEER persona is defined."""
        assert QA_ENGINEER is not None
        assert isinstance(QA_ENGINEER, PersonaStrategy)

    def test_qa_engineer_persona_name(self):
        """Test QA_ENGINEER has correct name."""
        assert QA_ENGINEER.name == "qa_engineer"

    def test_qa_engineer_communication_style(self):
        """Test QA_ENGINEER uses precise communication style."""
        assert QA_ENGINEER.communication_style == "precise"

    def test_qa_engineer_thoroughness_level(self):
        """Test QA_ENGINEER has exhaustive thoroughness."""
        assert QA_ENGINEER.thoroughness_level == "exhaustive"

    def test_qa_engineer_evidence_priorities(self):
        """Test QA_ENGINEER prioritizes tests and validation."""
        priorities = QA_ENGINEER.evidence_collection_priority

        assert isinstance(priorities, list)
        assert len(priorities) > 0

        # QA should prioritize tests first
        assert (
            priorities[0] == "test_file"
            or "test" in priorities[0]
            or "validation" in priorities[0]
        )

    def test_qa_engineer_prompt_template_emphasizes_testing(self):
        """Test QA_ENGINEER prompt emphasizes testing and quality."""
        template = QA_ENGINEER.prompt_template.lower()

        qa_keywords = ["test", "quality", "validate", "verify", "qa", "edge case"]
        assert any(
            keyword in template for keyword in qa_keywords
        ), "QA Engineer prompt missing testing emphasis"

    def test_qa_engineer_prompt_template_has_required_fields(self):
        """Test QA_ENGINEER prompt template has goal and success_criteria."""
        assert "{goal}" in QA_ENGINEER.prompt_template
        assert "{success_criteria}" in QA_ENGINEER.prompt_template


class TestArchitectPersona:
    """Test ARCHITECT persona configuration."""

    def test_architect_persona_exists(self):
        """Test ARCHITECT persona is defined."""
        assert ARCHITECT is not None
        assert isinstance(ARCHITECT, PersonaStrategy)

    def test_architect_persona_name(self):
        """Test ARCHITECT has correct name."""
        assert ARCHITECT.name == "architect"

    def test_architect_communication_style(self):
        """Test ARCHITECT uses strategic communication style."""
        assert ARCHITECT.communication_style == "strategic"

    def test_architect_thoroughness_level(self):
        """Test ARCHITECT has holistic thoroughness."""
        assert ARCHITECT.thoroughness_level == "holistic"

    def test_architect_evidence_priorities(self):
        """Test ARCHITECT prioritizes design documents and specs."""
        priorities = ARCHITECT.evidence_collection_priority

        assert isinstance(priorities, list)
        assert len(priorities) > 0

        # Architect should prioritize architecture docs
        priority_str = " ".join(priorities).lower()
        assert any(
            keyword in priority_str for keyword in ["architecture", "design", "spec", "api"]
        )

    def test_architect_prompt_template_emphasizes_design(self):
        """Test ARCHITECT prompt emphasizes design and architecture."""
        template = ARCHITECT.prompt_template.lower()

        architect_keywords = [
            "design",
            "architecture",
            "system",
            "structure",
            "interface",
            "pattern",
        ]
        assert any(
            keyword in template for keyword in architect_keywords
        ), "Architect prompt missing design emphasis"

    def test_architect_prompt_template_has_required_fields(self):
        """Test ARCHITECT prompt template has goal and success_criteria."""
        assert "{goal}" in ARCHITECT.prompt_template
        assert "{success_criteria}" in ARCHITECT.prompt_template


class TestJuniorDevPersona:
    """Test JUNIOR_DEV persona configuration."""

    def test_junior_dev_persona_exists(self):
        """Test JUNIOR_DEV persona is defined."""
        assert JUNIOR_DEV is not None
        assert isinstance(JUNIOR_DEV, PersonaStrategy)

    def test_junior_dev_persona_name(self):
        """Test JUNIOR_DEV has correct name."""
        assert JUNIOR_DEV.name == "junior_dev"

    def test_junior_dev_communication_style(self):
        """Test JUNIOR_DEV uses task-focused communication style."""
        assert JUNIOR_DEV.communication_style == "task_focused"

    def test_junior_dev_thoroughness_level(self):
        """Test JUNIOR_DEV has adequate thoroughness."""
        assert JUNIOR_DEV.thoroughness_level == "adequate"

    def test_junior_dev_evidence_priorities(self):
        """Test JUNIOR_DEV prioritizes code implementation."""
        priorities = JUNIOR_DEV.evidence_collection_priority

        assert isinstance(priorities, list)
        assert len(priorities) > 0

        # Junior dev should prioritize code files
        assert priorities[0] == "code_file" or "code" in priorities[0]

    def test_junior_dev_prompt_template_emphasizes_implementation(self):
        """Test JUNIOR_DEV prompt emphasizes implementation and specs."""
        template = JUNIOR_DEV.prompt_template.lower()

        dev_keywords = ["implement", "code", "build", "develop", "create", "follow"]
        assert any(
            keyword in template for keyword in dev_keywords
        ), "Junior dev prompt missing implementation emphasis"

    def test_junior_dev_prompt_template_has_required_fields(self):
        """Test JUNIOR_DEV prompt template has goal and success_criteria."""
        assert "{goal}" in JUNIOR_DEV.prompt_template
        assert "{success_criteria}" in JUNIOR_DEV.prompt_template


class TestPersonaRegistry:
    """Test persona registration and retrieval."""

    def test_get_persona_strategy_returns_guide_by_default(self):
        """Test get_persona_strategy returns GUIDE by default."""
        persona = get_persona_strategy()
        assert persona.name == "guide"

    def test_get_persona_strategy_returns_specific_persona(self):
        """Test get_persona_strategy returns requested persona."""
        guide = get_persona_strategy("guide")
        assert guide.name == "guide"

        qa = get_persona_strategy("qa_engineer")
        assert qa.name == "qa_engineer"

        arch = get_persona_strategy("architect")
        assert arch.name == "architect"

        junior = get_persona_strategy("junior_dev")
        assert junior.name == "junior_dev"

    def test_get_persona_strategy_raises_on_unknown_persona(self):
        """Test get_persona_strategy raises ValueError for unknown persona."""
        with pytest.raises(ValueError, match="Unknown persona"):
            get_persona_strategy("nonexistent_persona")

    def test_register_persona_adds_custom_persona(self):
        """Test register_persona allows custom persona registration."""
        custom_persona = PersonaStrategy(
            name="researcher",
            communication_style="analytical",
            thoroughness_level="deep",
            evidence_collection_priority=["documentation", "analysis_report"],
            prompt_template="Research: {goal}\nCriteria: {success_criteria}",
        )

        register_persona("researcher", custom_persona)

        retrieved = get_persona_strategy("researcher")
        assert retrieved.name == "researcher"
        assert retrieved.communication_style == "analytical"

    def test_register_persona_overwrites_existing(self):
        """Test register_persona can overwrite existing persona."""
        modified_guide = PersonaStrategy(
            name="guide",
            communication_style="modified",
            thoroughness_level="modified",
            evidence_collection_priority=["modified"],
            prompt_template="Modified: {goal}",
        )

        register_persona("guide", modified_guide)

        retrieved = get_persona_strategy("guide")
        assert retrieved.communication_style == "modified"


class TestPersonaPromptGeneration:
    """Test prompt generation from persona strategies."""

    def test_guide_generates_educational_prompt(self):
        """Test GUIDE generates educational-focused prompt."""
        goal = "Create a user authentication system"
        success_criteria = "System has login/logout, uses JWT tokens"

        prompt = GUIDE.prompt_template.format(goal=goal, success_criteria=success_criteria)

        assert goal in prompt
        assert success_criteria in prompt
        assert len(prompt) > len(goal) + len(success_criteria)

    def test_qa_engineer_generates_testing_prompt(self):
        """Test QA_ENGINEER generates testing-focused prompt."""
        goal = "Validate API endpoints"
        success_criteria = "All endpoints return correct status codes"

        prompt = QA_ENGINEER.prompt_template.format(goal=goal, success_criteria=success_criteria)

        assert goal in prompt
        assert success_criteria in prompt

    def test_architect_generates_design_prompt(self):
        """Test ARCHITECT generates design-focused prompt."""
        goal = "Design microservices architecture"
        success_criteria = "Services are loosely coupled, use message queue"

        prompt = ARCHITECT.prompt_template.format(goal=goal, success_criteria=success_criteria)

        assert goal in prompt
        assert success_criteria in prompt

    def test_junior_dev_generates_implementation_prompt(self):
        """Test JUNIOR_DEV generates implementation-focused prompt."""
        goal = "Implement user registration endpoint"
        success_criteria = "Endpoint accepts POST, validates email, returns user ID"

        prompt = JUNIOR_DEV.prompt_template.format(goal=goal, success_criteria=success_criteria)

        assert goal in prompt
        assert success_criteria in prompt


class TestPersonaBehaviorCharacteristics:
    """Test persona behavior characteristics match documentation."""

    def test_all_personas_have_unique_names(self):
        """Test all built-in personas have unique names."""
        personas = [GUIDE, QA_ENGINEER, ARCHITECT, JUNIOR_DEV]
        names = [p.name for p in personas]

        assert len(names) == len(set(names)), "Persona names must be unique"

    def test_all_personas_have_valid_thoroughness_levels(self):
        """Test all personas use valid thoroughness levels."""
        valid_levels = ["minimal", "adequate", "balanced", "thorough", "exhaustive", "holistic"]
        personas = [GUIDE, QA_ENGINEER, ARCHITECT, JUNIOR_DEV]

        for persona in personas:
            assert (
                persona.thoroughness_level in valid_levels
            ), f"{persona.name} has invalid thoroughness level"

    def test_qa_engineer_has_highest_thoroughness(self):
        """Test QA_ENGINEER has most exhaustive thoroughness."""
        # QA should be exhaustive
        assert QA_ENGINEER.thoroughness_level == "exhaustive"

    def test_junior_dev_has_adequate_thoroughness(self):
        """Test JUNIOR_DEV has adequate (not excessive) thoroughness."""
        assert JUNIOR_DEV.thoroughness_level in ["adequate", "minimal", "balanced"]

    def test_evidence_priorities_are_non_empty(self):
        """Test all personas have non-empty evidence priorities."""
        personas = [GUIDE, QA_ENGINEER, ARCHITECT, JUNIOR_DEV]

        for persona in personas:
            assert (
                len(persona.evidence_collection_priority) > 0
            ), f"{persona.name} has empty evidence priorities"

    def test_prompt_templates_are_substantial(self):
        """Test all persona prompts are substantial (not trivial)."""
        personas = [GUIDE, QA_ENGINEER, ARCHITECT, JUNIOR_DEV]

        for persona in personas:
            # Prompt should be more than just the placeholders
            assert (
                len(persona.prompt_template) > 100
            ), f"{persona.name} prompt template too short"
