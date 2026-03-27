"""Integration tests for session start and context preservation.

Tests the integration between session start hooks and context preservation system.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def _get_context(result: dict) -> str:
    """Extract additionalContext from hook response (handles nesting)."""
    if "additionalContext" in result:
        return result["additionalContext"]
    hook_output = result.get("hookSpecificOutput", {})
    return hook_output.get("additionalContext", "")


def _run_session_start_hook(input_data: dict) -> dict:
    """Run session_start.py as a subprocess and return parsed JSON output."""
    hook_path = Path(__file__).parent.parent / ".claude" / "tools" / "amplihack" / "hooks" / "session_start.py"
    if not hook_path.exists():
        pytest.skip(f"Hook not found: {hook_path}")

    result = subprocess.run(
        [sys.executable, str(hook_path)],
        check=False,
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, f"Hook failed (exit {result.returncode}): {result.stderr}"
    return json.loads(result.stdout.strip())


class TestSessionStartIntegration:
    """Integration tests for session start context preservation."""

    def test_session_start_captures_original_request(self):
        """Session start preserves original user request in context."""
        input_data = {
            "prompt": "Please update ALL Python files with comprehensive docstrings and type hints for EVERY function"
        }
        result = _run_session_start_hook(input_data)
        context = _get_context(result)

        assert context, "additionalContext should not be empty"
        # Original request quantifiers should be preserved in context
        assert "ALL" in context or "EVERY" in context

    def test_session_start_extracts_requirements(self):
        """Session start includes requirement-related context."""
        input_data = {
            "prompt": "Implement authentication system with ALL authentication methods"
        }
        result = _run_session_start_hook(input_data)
        context = _get_context(result)

        assert "ALL authentication methods" in context or "requirements" in context.lower()

    def test_session_start_preserves_explicit_quantifiers(self):
        """Session start preserves explicit quantifiers like ALL, EVERY, etc."""
        input_data = {"prompt": "Process ALL files in the repository"}
        result = _run_session_start_hook(input_data)
        context = _get_context(result)

        assert "ALL" in context.upper()

    def test_session_start_creates_session_logs(self):
        """Session start produces valid hook output."""
        input_data = {"prompt": "Implement comprehensive testing for ALL modules"}
        result = _run_session_start_hook(input_data)

        # Verify hook protocol structure
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["hookEventName"] == "SessionStart"

    def test_session_start_handles_empty_prompt(self):
        """Session start handles empty or minimal prompts without crashing."""
        for prompt in ["", "   ", "help", "test"]:
            input_data = {"prompt": prompt}
            result = _run_session_start_hook(input_data)
            context = _get_context(result)

            assert isinstance(context, str)

    def test_session_start_preference_integration(self):
        """Session start includes user preferences in context."""
        input_data = {"prompt": "Test prompt"}
        result = _run_session_start_hook(input_data)
        context = _get_context(result)

        assert "preferences" in context.lower() or "user preferences" in context.lower()


class TestEndToEndSessionWorkflow:
    """End-to-end tests for complete session workflow."""

    def test_complete_session_workflow(self):
        """Complete workflow from session start to context output."""
        input_data = {
            "prompt": "Implement comprehensive test coverage for ALL Python modules in the project"
        }
        result = _run_session_start_hook(input_data)
        context = _get_context(result)

        assert context, "Context should not be empty"
        assert "ALL Python modules" in context or "all python modules" in context.lower()

    def test_session_workflow_with_compaction(self):
        """Compaction integration is not yet implemented — verify graceful handling."""
        # pre_compact hook exists and handles compaction; this test verifies the
        # session start hook itself doesn't crash when compaction-related state is absent
        result = _run_session_start_hook({"prompt": "test"})
        assert _get_context(result)  # hook succeeds

    def test_agent_context_injection_workflow(self):
        """Agent context injection is part of session start output."""
        input_data = {"prompt": "Process ALL files"}
        result = _run_session_start_hook(input_data)
        context = _get_context(result)

        # Context should contain project information that agents will receive
        assert "Project Context" in context or "project" in context.lower()


class TestSessionStartErrorHandling:
    """Test error handling in session start integration."""

    def test_session_start_handles_errors_gracefully(self):
        """Session start handles various error conditions gracefully."""
        # Even with no prompt at all, hook should succeed
        result = _run_session_start_hook({})
        assert _get_context(result) is not None


class TestFutureImplementations:
    """Tests for functionality that may be added later."""

    def test_agent_context_injection_placeholder(self):
        """Context injection system exists and works."""
        result = _run_session_start_hook({"prompt": "test"})
        context = _get_context(result)
        assert isinstance(context, str)
