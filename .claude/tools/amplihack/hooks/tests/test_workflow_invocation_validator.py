#!/usr/bin/env python3
"""
Tests for workflow_invocation_validator.py

Comprehensive test suite verifying workflow invocation validation logic.
"""

import sys
from pathlib import Path

import pytest

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_invocation_validator import (
    ValidationResult,
    validate_workflow_invocation,
)


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating ValidationResult instances."""
        result = ValidationResult(
            valid=True,
            reason="Test reason",
            violation_type="none",
            evidence="Test evidence",
        )

        assert result.valid is True
        assert result.reason == "Test reason"
        assert result.violation_type == "none"
        assert result.evidence == "Test evidence"

    def test_validation_result_defaults(self):
        """Test ValidationResult default values."""
        result = ValidationResult(valid=False, reason="Test")

        assert result.violation_type == "none"
        assert result.evidence == ""


class TestUltrathinkTriggerDetection:
    """Test ultrathink trigger detection."""

    def test_explicit_ultrathink_command(self):
        """Test detection of explicit /ultrathink command."""
        transcript = """
        User: /ultrathink implement authentication
        Claude: Starting workflow orchestration...
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        # Should fail because no Skill invocation follows
        assert result.valid is False

    def test_skill_invocation_syntax(self):
        """Test detection of Skill(skill='ultrathink-orchestrator')."""
        transcript = """
        User: implement authentication
        Claude: Skill(skill="ultrathink-orchestrator")
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        # Should fail because ultrathink triggered but no workflow loaded
        assert result.valid is False

    def test_auto_activation_message(self):
        """Test detection of skill auto-activation."""
        transcript = """
        User: implement authentication
        Claude: ultrathink-orchestrator skill auto-activated for development task
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        # Should fail because no workflow invoked
        assert result.valid is False

    def test_command_tag_format(self):
        """Test detection of command tag format."""
        transcript = """
        <command-name>/ultrathink</command-name>
        User task: implement authentication
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        # Should fail because no workflow invoked
        assert result.valid is False


class TestSkillInvocationDetection:
    """Test Skill tool invocation detection."""

    def test_default_workflow_skill_invoked(self):
        """Test successful detection of default-workflow skill."""
        transcript = """
        User: /ultrathink implement authentication
        Claude: Skill(skill="default-workflow")
        Workflow loaded successfully
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        assert result.valid is True
        assert "default-workflow" in result.evidence

    def test_investigation_workflow_skill_invoked(self):
        """Test successful detection of investigation-workflow skill."""
        transcript = """
        User: /ultrathink investigate how auth works
        Claude: Skill(skill="investigation-workflow")
        Investigation workflow loaded
        """

        result = validate_workflow_invocation(transcript, "INVESTIGATION")
        assert result.valid is True
        assert "investigation-workflow" in result.evidence

    def test_skill_tool_xml_format(self):
        """Test detection of Skill tool in XML format."""
        transcript = """
        User: /ultrathink implement feature
        <function_calls>
        <invoke name="Skill">
        <parameter name="skill">default-workflow</parameter>
        </invoke>
        </function_calls>
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        assert result.valid is True


class TestReadWorkflowFallback:
    """Test Read tool fallback detection."""

    def test_default_workflow_read_fallback(self):
        """Test detection of Read tool loading DEFAULT_WORKFLOW.md."""
        transcript = """
        User: /ultrathink implement authentication
        Claude: Skill invocation failed, falling back to Read
        Read(.claude/workflow/DEFAULT_WORKFLOW.md)
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        assert result.valid is True
        assert "DEFAULT_WORKFLOW" in result.evidence

    def test_investigation_workflow_read_fallback(self):
        """Test detection of Read tool loading INVESTIGATION_WORKFLOW.md."""
        transcript = """
        User: /ultrathink investigate system
        Claude: Reading workflow directly
        Read(.claude/workflow/INVESTIGATION_WORKFLOW.md)
        """

        result = validate_workflow_invocation(transcript, "INVESTIGATION")
        assert result.valid is True
        assert "INVESTIGATION_WORKFLOW" in result.evidence

    def test_read_tool_xml_format(self):
        """Test detection of Read tool in XML format."""
        transcript = """
        User: /ultrathink implement feature
        <invoke name="Read">
        <parameter name="file_path">.claude/workflow/DEFAULT_WORKFLOW.md</parameter>
        </invoke>
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        assert result.valid is True


class TestViolationDetection:
    """Test violation detection."""

    def test_ultrathink_without_workflow_invocation(self):
        """Test violation when ultrathink triggered but no workflow loaded."""
        transcript = """
        User: /ultrathink implement authentication
        Claude: Starting implementation...
        [Implementation without workflow]
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        assert result.valid is False
        assert result.violation_type == "no_workflow_loaded"
        assert "not invoked" in result.reason.lower()

    def test_auto_activation_without_workflow(self):
        """Test violation on auto-activation without workflow."""
        transcript = """
        User: implement authentication
        Claude: ultrathink-orchestrator auto-activated
        Now implementing...
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        assert result.valid is False
        assert result.violation_type == "no_workflow_loaded"


class TestSessionTypeFiltering:
    """Test session type filtering."""

    def test_informational_session_skipped(self):
        """Test that INFORMATIONAL sessions skip validation."""
        transcript = """
        User: What is authentication?
        Claude: Authentication is...
        """

        result = validate_workflow_invocation(transcript, "INFORMATIONAL")
        assert result.valid is True
        assert "not required" in result.reason

    def test_maintenance_session_skipped(self):
        """Test that MAINTENANCE sessions skip validation."""
        transcript = """
        User: Update documentation
        Claude: Updating docs...
        """

        result = validate_workflow_invocation(transcript, "MAINTENANCE")
        assert result.valid is True
        assert "not required" in result.reason

    def test_development_session_validated(self):
        """Test that DEVELOPMENT sessions are validated."""
        transcript = """
        User: /ultrathink implement feature
        Claude: Starting...
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        # Should fail without proper invocation
        assert result.valid is False

    def test_investigation_session_validated(self):
        """Test that INVESTIGATION sessions are validated."""
        transcript = """
        User: /ultrathink investigate system
        Claude: Investigating...
        """

        result = validate_workflow_invocation(transcript, "INVESTIGATION")
        # Should fail without proper invocation
        assert result.valid is False


class TestNoUltrathinkTrigger:
    """Test scenarios where ultrathink is not triggered."""

    def test_simple_question(self):
        """Test simple Q&A doesn't trigger validation."""
        transcript = """
        User: How do I run tests?
        Claude: Run pytest in the root directory
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        assert result.valid is True
        assert "not triggered" in result.reason

    def test_direct_implementation(self):
        """Test direct implementation without ultrathink."""
        transcript = """
        User: Add a function to calculate sum
        Claude: Here's the function:
        def sum(a, b): return a + b
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        assert result.valid is True
        assert "not triggered" in result.reason


class TestCompleteWorkflows:
    """Test complete workflow scenarios."""

    def test_complete_development_workflow(self):
        """Test complete development workflow with proper invocation."""
        transcript = """
        User: /ultrathink implement JWT authentication
        Claude: ultrathink-orchestrator skill auto-activated
        Skill(skill="default-workflow")

        Step 1: Understanding Requirements
        Step 2: Architecture Design
        ...
        Step 22: Cleanup and Merge
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        assert result.valid is True
        assert "default-workflow" in result.evidence

    def test_complete_investigation_workflow(self):
        """Test complete investigation workflow with proper invocation."""
        transcript = """
        User: /ultrathink investigate authentication system
        Claude: Detected investigation task
        Skill(skill="investigation-workflow")

        Phase 1: Scope Definition
        Phase 2: Exploration Strategy
        ...
        Phase 6: Knowledge Capture
        """

        result = validate_workflow_invocation(transcript, "INVESTIGATION")
        assert result.valid is True
        assert "investigation-workflow" in result.evidence

    def test_hybrid_workflow_with_both_skills(self):
        """Test hybrid workflow invoking both investigation and development."""
        transcript = """
        User: /ultrathink investigate auth then add OAuth
        Claude: Hybrid workflow detected
        Skill(skill="investigation-workflow")

        Investigation complete, transitioning to development
        Skill(skill="default-workflow")
        """

        result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        assert result.valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
