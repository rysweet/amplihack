"""Integration tests for persona strategies with other modules.

Tests how persona strategies integrate with platform CLI, evidence collector,
and success evaluator.
"""

from unittest.mock import Mock, patch

import pytest

# These imports will fail until implementation exists
try:
    from amplihack.meta_delegation.evidence_collector import EvidenceCollector
    from amplihack.meta_delegation.persona import (
        ARCHITECT,
        GUIDE,
        JUNIOR_DEV,
        QA_ENGINEER,
        get_persona_strategy,
    )
    from amplihack.meta_delegation.platform_cli import ClaudeCodeCLI
    from amplihack.meta_delegation.success_evaluator import SuccessCriteriaEvaluator
except ImportError:
    pytest.skip("Required modules not implemented yet", allow_module_level=True)


@pytest.mark.integration
class TestPersonaPlatformIntegration:
    """Test persona strategies with platform CLI."""

    def test_guide_persona_with_claude_code(self):
        """Test GUIDE persona generates correct Claude Code prompts."""
        cli = ClaudeCodeCLI()
        persona = GUIDE

        goal = "Teach user about REST APIs"
        context = "Beginner level"

        prompt = cli.format_prompt(goal, persona.name, context)

        # Prompt should reflect guide's teaching style
        prompt_lower = prompt.lower()
        assert any(
            keyword in prompt_lower
            for keyword in ["teach", "learn", "understand", "explain"]
        )

    def test_qa_engineer_persona_with_claude_code(self):
        """Test QA_ENGINEER persona generates testing-focused prompts."""
        cli = ClaudeCodeCLI()
        persona = QA_ENGINEER

        goal = "Validate API endpoints"
        context = "REST API with auth"

        prompt = cli.format_prompt(goal, persona.name, context)

        prompt_lower = prompt.lower()
        assert any(keyword in prompt_lower for keyword in ["test", "validate", "qa", "quality"])

    def test_architect_persona_with_claude_code(self):
        """Test ARCHITECT persona generates design-focused prompts."""
        cli = ClaudeCodeCLI()
        persona = ARCHITECT

        goal = "Design microservices system"
        context = "E-commerce platform"

        prompt = cli.format_prompt(goal, persona.name, context)

        prompt_lower = prompt.lower()
        assert any(
            keyword in prompt_lower
            for keyword in ["design", "architecture", "system", "structure"]
        )

    def test_junior_dev_persona_with_claude_code(self):
        """Test JUNIOR_DEV persona generates implementation-focused prompts."""
        cli = ClaudeCodeCLI()
        persona = JUNIOR_DEV

        goal = "Implement user registration"
        context = "Following provided spec"

        prompt = cli.format_prompt(goal, persona.name, context)

        prompt_lower = prompt.lower()
        assert any(keyword in prompt_lower for keyword in ["implement", "code", "build"])


@pytest.mark.integration
class TestPersonaEvidenceCollectorIntegration:
    """Test persona strategies with evidence collector."""

    @pytest.fixture
    def working_dir_with_files(self, tmp_path):
        """Create working directory with various file types."""
        # Code files
        (tmp_path / "app.py").write_text("def main(): pass")
        (tmp_path / "models.py").write_text("class User: pass")

        # Test files
        (tmp_path / "test_app.py").write_text("def test_main(): assert True")
        (tmp_path / "test_models.py").write_text("def test_user(): pass")

        # Documentation
        (tmp_path / "README.md").write_text("# Documentation")
        (tmp_path / "TUTORIAL.md").write_text("# Tutorial")

        # Architecture docs
        (tmp_path / "architecture.md").write_text("# Architecture")
        (tmp_path / "api_spec.yaml").write_text("openapi: 3.0.0")

        # Diagrams
        (tmp_path / "diagram.mmd").write_text("graph TD")

        return tmp_path

    def test_guide_persona_evidence_priority(self, working_dir_with_files):
        """Test GUIDE persona prioritizes educational content."""
        collector = EvidenceCollector(
            working_directory=str(working_dir_with_files),
            evidence_priorities=GUIDE.evidence_collection_priority,
        )

        evidence = collector.collect_evidence()

        # Guide should collect documentation prominently
        doc_evidence = [e for e in evidence if e.type in ["documentation", "docs"]]
        assert len(doc_evidence) > 0

    def test_qa_engineer_persona_evidence_priority(self, working_dir_with_files):
        """Test QA_ENGINEER persona prioritizes tests."""
        collector = EvidenceCollector(
            working_directory=str(working_dir_with_files),
            evidence_priorities=QA_ENGINEER.evidence_collection_priority,
        )

        evidence = collector.collect_evidence()

        # QA should collect test files prominently
        test_evidence = [e for e in evidence if e.type == "test_file"]
        assert len(test_evidence) >= 2

    def test_architect_persona_evidence_priority(self, working_dir_with_files):
        """Test ARCHITECT persona prioritizes design docs."""
        collector = EvidenceCollector(
            working_directory=str(working_dir_with_files),
            evidence_priorities=ARCHITECT.evidence_collection_priority,
        )

        evidence = collector.collect_evidence()

        # Architect should collect architecture docs and specs
        arch_evidence = [
            e for e in evidence if e.type in ["architecture_doc", "api_spec", "diagram"]
        ]
        assert len(arch_evidence) >= 2

    def test_junior_dev_persona_evidence_priority(self, working_dir_with_files):
        """Test JUNIOR_DEV persona prioritizes code files."""
        collector = EvidenceCollector(
            working_directory=str(working_dir_with_files),
            evidence_priorities=JUNIOR_DEV.evidence_collection_priority,
        )

        evidence = collector.collect_evidence()

        # Junior dev should collect code files first
        code_evidence = [e for e in evidence if e.type == "code_file"]
        assert len(code_evidence) >= 2


@pytest.mark.integration
class TestPersonaSuccessEvaluatorIntegration:
    """Test persona strategies with success evaluator."""

    def test_guide_persona_evaluation_emphasizes_clarity(self, sample_evidence_items):
        """Test GUIDE persona evaluation emphasizes clear documentation."""
        evaluator = SuccessCriteriaEvaluator()

        criteria = "Create educational tutorial with examples"

        # Add tutorial documentation to evidence
        from datetime import datetime

        from amplihack.meta_delegation.evidence_collector import EvidenceItem

        evidence_with_tutorial = sample_evidence_items + [
            EvidenceItem(
                type="documentation",
                path="TUTORIAL.md",
                content="# Step-by-step tutorial with examples",
                excerpt="# Step-by-step...",
                size_bytes=100,
                timestamp=datetime.now(),
                metadata={"format": "markdown"},
            )
        ]

        result = evaluator.evaluate(criteria, evidence_with_tutorial, "")

        # Should score well due to tutorial presence
        assert result.score >= 70

    def test_qa_engineer_persona_evaluation_emphasizes_tests(self, sample_evidence_items):
        """Test QA_ENGINEER persona evaluation emphasizes test coverage."""
        evaluator = SuccessCriteriaEvaluator()

        criteria = "Comprehensive test coverage with edge cases"

        execution_log = """
PASS test_app.py::test_main
PASS test_app.py::test_edge_case_1
PASS test_app.py::test_edge_case_2
PASS test_app.py::test_boundary_condition
All tests passed (4/4)
"""

        result = evaluator.evaluate(criteria, sample_evidence_items, execution_log)

        # Should score high for passing comprehensive tests
        assert result.score >= 80

    def test_architect_persona_evaluation_emphasizes_design(self):
        """Test ARCHITECT persona evaluation emphasizes architecture."""
        from datetime import datetime

        from amplihack.meta_delegation.evidence_collector import EvidenceItem

        evaluator = SuccessCriteriaEvaluator()

        criteria = "System design with clear component boundaries and interfaces"

        evidence = [
            EvidenceItem(
                type="architecture_doc",
                path="architecture.md",
                content="# System Architecture\n\n## Components\n\n## Interfaces",
                excerpt="# System...",
                size_bytes=100,
                timestamp=datetime.now(),
                metadata={},
            ),
            EvidenceItem(
                type="api_spec",
                path="api.yaml",
                content="openapi: 3.0.0\npaths:\n  /api/users:",
                excerpt="openapi...",
                size_bytes=80,
                timestamp=datetime.now(),
                metadata={},
            ),
            EvidenceItem(
                type="diagram",
                path="system.mmd",
                content="graph TD\n  A[Component A] --> B[Component B]",
                excerpt="graph...",
                size_bytes=60,
                timestamp=datetime.now(),
                metadata={},
            ),
        ]

        result = evaluator.evaluate(criteria, evidence, "")

        # Should score high for comprehensive architecture artifacts
        assert result.score >= 75


@pytest.mark.integration
class TestPersonaWorkflowIntegration:
    """Test complete workflow with different personas."""

    def test_guide_persona_complete_workflow(
        self, temp_working_dir, mock_platform_cli, sample_goal_and_criteria
    ):
        """Test complete workflow with GUIDE persona."""
        persona = GUIDE

        # Format prompt
        prompt = mock_platform_cli.format_prompt(
            sample_goal_and_criteria["goal"], persona.name, ""
        )

        assert prompt is not None

        # Simulate evidence collection with guide priorities
        collector = EvidenceCollector(
            working_directory=str(temp_working_dir),
            evidence_priorities=persona.evidence_collection_priority,
        )

        # Workflow should emphasize documentation
        assert "documentation" in persona.evidence_collection_priority

    def test_qa_engineer_persona_complete_workflow(
        self, temp_working_dir, mock_platform_cli, sample_goal_and_criteria
    ):
        """Test complete workflow with QA_ENGINEER persona."""
        persona = QA_ENGINEER

        # Format prompt
        prompt = mock_platform_cli.format_prompt(
            sample_goal_and_criteria["goal"], persona.name, ""
        )

        assert prompt is not None

        # Simulate evidence collection with QA priorities
        collector = EvidenceCollector(
            working_directory=str(temp_working_dir),
            evidence_priorities=persona.evidence_collection_priority,
        )

        # Workflow should emphasize tests
        assert "test_file" in persona.evidence_collection_priority[0:2]

    def test_architect_persona_complete_workflow(
        self, temp_working_dir, mock_platform_cli, sample_goal_and_criteria
    ):
        """Test complete workflow with ARCHITECT persona."""
        persona = ARCHITECT

        # Format prompt
        prompt = mock_platform_cli.format_prompt(
            sample_goal_and_criteria["goal"], persona.name, ""
        )

        assert prompt is not None

        # Simulate evidence collection with architect priorities
        collector = EvidenceCollector(
            working_directory=str(temp_working_dir),
            evidence_priorities=persona.evidence_collection_priority,
        )

        # Workflow should emphasize architecture docs
        priority_str = " ".join(persona.evidence_collection_priority).lower()
        assert "architecture" in priority_str or "design" in priority_str
