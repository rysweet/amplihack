"""Unit tests for RecipeSessionTracker."""

import json
import tempfile
from pathlib import Path

import pytest


def test_imports():
    """Test that tracker imports work."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker, WorkflowRequirement

    assert RecipeSessionTracker is not None
    assert WorkflowRequirement is not None


def test_workflow_requirement_detection_implementation_keywords():
    """Test detection of implementation keywords."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker

    tracker = RecipeSessionTracker()

    # Should trigger
    test_cases = [
        "implement user authentication",
        "add feature for notifications",
        "create a new API endpoint",
        "build the dashboard",
        "refactor the data model",
        "fix bug in login flow",
        "modify the configuration",
        "change database schema",
        "update the API response",
    ]

    for prompt in test_cases:
        required, reason = tracker.is_workflow_required(prompt, {})
        assert required, f"Should require workflow for: {prompt}"
        assert "keyword" in reason.lower(), f"Reason should mention keyword: {reason}"


def test_workflow_requirement_detection_exempt_patterns():
    """Test that QA and investigation prompts are exempt."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker

    tracker = RecipeSessionTracker()

    # Should NOT trigger
    test_cases = [
        "what is the user authentication system?",
        "how does the API work?",
        "explain the database schema",
        "show me the configuration",
        "describe the architecture",
        "why did we choose this approach?",
    ]

    for prompt in test_cases:
        required, reason = tracker.is_workflow_required(prompt, {})
        assert not required, f"Should NOT require workflow for: {prompt}"
        assert "exempt" in reason.lower(), f"Reason should mention exempt: {reason}"


def test_workflow_state_management():
    """Test workflow active state tracking."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker

    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "test_state.json"
        tracker = RecipeSessionTracker(state_file=state_file)

        session_id = "test_session_123"

        # Initially no workflow active
        assert not tracker.is_workflow_active(session_id)

        # Mark workflow started
        tracker.mark_workflow_started("default-workflow", session_id)
        assert tracker.is_workflow_active(session_id)

        # Verify state persisted
        with open(state_file) as f:
            state = json.load(f)
        assert session_id in state["sessions"]
        assert state["sessions"][session_id]["status"] == "active"

        # Mark workflow completed
        tracker.mark_workflow_completed("default-workflow", session_id)
        assert not tracker.is_workflow_active(session_id)


def test_bypass_attempt_recording():
    """Test recording bypass attempts."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker

    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = Path(tmpdir) / "test_state.json"
        tracker = RecipeSessionTracker(state_file=state_file)

        session_id = "test_session_456"

        # Record bypass attempts
        tracker.record_bypass_attempt("write_file", session_id, blocked=True)
        tracker.record_bypass_attempt("edit_file", session_id, blocked=True)

        # Check count
        count = tracker.get_bypass_count(session_id)
        assert count == 2


def test_multi_file_detection():
    """Test detection of multi-file changes."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker

    tracker = RecipeSessionTracker()

    test_cases = [
        "update multiple files for the auth system",
        "change several files in the API module",
    ]

    for prompt in test_cases:
        required, reason = tracker.is_workflow_required(prompt, {})
        assert required, f"Should require workflow for multi-file: {prompt}"
        assert "multi-file" in reason.lower(), f"Reason should mention multi-file: {reason}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
