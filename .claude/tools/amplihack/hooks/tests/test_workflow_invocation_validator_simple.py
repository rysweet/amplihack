#!/usr/bin/env python3
"""
Simple test runner for workflow_invocation_validator.py (no pytest required)
"""

import sys
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_invocation_validator import (
    ValidationResult,
    validate_workflow_invocation,
)


def test_validation_result_creation():
    """Test creating ValidationResult instances."""
    result = ValidationResult(
        valid=True,
        reason="Test reason",
        violation_type="none",
        evidence="Test evidence",
    )
    assert result.valid is True
    assert result.reason == "Test reason"
    print("✓ test_validation_result_creation")


def test_explicit_ultrathink_command():
    """Test detection of explicit /ultrathink command."""
    transcript = """
    User: /ultrathink implement authentication
    Claude: Starting workflow orchestration...
    """
    result = validate_workflow_invocation(transcript, "DEVELOPMENT")
    assert result.valid is False
    print("✓ test_explicit_ultrathink_command")


def test_default_workflow_skill_invoked():
    """Test successful detection of default-workflow skill."""
    transcript = """
    User: /ultrathink implement authentication
    Claude: Skill(skill="default-workflow")
    Workflow loaded successfully
    """
    result = validate_workflow_invocation(transcript, "DEVELOPMENT")
    assert result.valid is True
    assert "default-workflow" in result.evidence
    print("✓ test_default_workflow_skill_invoked")


def test_investigation_workflow_skill_invoked():
    """Test successful detection of investigation-workflow skill."""
    transcript = """
    User: /ultrathink investigate how auth works
    Claude: Skill(skill="investigation-workflow")
    Investigation workflow loaded
    """
    result = validate_workflow_invocation(transcript, "INVESTIGATION")
    assert result.valid is True
    assert "investigation-workflow" in result.evidence
    print("✓ test_investigation_workflow_skill_invoked")


def test_default_workflow_read_fallback():
    """Test detection of Read tool loading DEFAULT_WORKFLOW.md."""
    transcript = """
    User: /ultrathink implement authentication
    Claude: Skill invocation failed, falling back to Read
    Read(.claude/workflow/DEFAULT_WORKFLOW.md)
    """
    result = validate_workflow_invocation(transcript, "DEVELOPMENT")
    assert result.valid is True
    assert "DEFAULT_WORKFLOW" in result.evidence
    print("✓ test_default_workflow_read_fallback")


def test_ultrathink_without_workflow_invocation():
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
    print("✓ test_ultrathink_without_workflow_invocation")


def test_informational_session_skipped():
    """Test that INFORMATIONAL sessions skip validation."""
    transcript = """
    User: What is authentication?
    Claude: Authentication is...
    """
    result = validate_workflow_invocation(transcript, "INFORMATIONAL")
    assert result.valid is True
    assert "not required" in result.reason
    print("✓ test_informational_session_skipped")


def test_simple_question_no_trigger():
    """Test simple Q&A doesn't trigger validation."""
    transcript = """
    User: How do I run tests?
    Claude: Run pytest in the root directory
    """
    result = validate_workflow_invocation(transcript, "DEVELOPMENT")
    assert result.valid is True
    assert "not triggered" in result.reason
    print("✓ test_simple_question_no_trigger")


def test_complete_development_workflow():
    """Test complete development workflow with proper invocation."""
    transcript = """
    User: /ultrathink implement JWT authentication
    Claude: ultrathink-orchestrator skill auto-activated
    Skill(skill="default-workflow")

    Step 1: Understanding Requirements
    Step 2: Architecture Design
    """
    result = validate_workflow_invocation(transcript, "DEVELOPMENT")
    assert result.valid is True
    assert "default-workflow" in result.evidence
    print("✓ test_complete_development_workflow")


def test_skill_tool_xml_format():
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
    print("✓ test_skill_tool_xml_format")


def run_all_tests():
    """Run all tests."""
    print("\nRunning workflow_invocation_validator tests...\n")

    tests = [
        test_validation_result_creation,
        test_explicit_ultrathink_command,
        test_default_workflow_skill_invoked,
        test_investigation_workflow_skill_invoked,
        test_default_workflow_read_fallback,
        test_ultrathink_without_workflow_invocation,
        test_informational_session_skipped,
        test_simple_question_no_trigger,
        test_complete_development_workflow,
        test_skill_tool_xml_format,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    print(f"{'='*60}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
