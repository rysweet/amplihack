"""Unit tests for ToolGate."""

import tempfile
from pathlib import Path

import pytest


def test_imports():
    """Test that gate imports work."""
    from amplifier_hook_tool_gate import EnforcementLevel, GateDecision, ToolGate

    assert ToolGate is not None
    assert EnforcementLevel is not None
    assert GateDecision is not None


def test_enforcement_levels():
    """Test that enforcement levels exist and have correct values."""
    from amplifier_hook_tool_gate import EnforcementLevel

    assert EnforcementLevel.SOFT.value == "soft"
    assert EnforcementLevel.MEDIUM.value == "medium"
    assert EnforcementLevel.HARD.value == "hard"


def test_non_implementation_tools_allowed():
    """Test that non-implementation tools are always allowed."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker
    from amplifier_hook_tool_gate import EnforcementLevel, ToolGate

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = RecipeSessionTracker(state_file=Path(tmpdir) / "state.json")
        gate = ToolGate(tracker, enforcement_level=EnforcementLevel.HARD)

        # These tools should always be allowed
        non_impl_tools = ["read_file", "glob", "grep", "web_search", "web_fetch"]

        for tool_name in non_impl_tools:
            decision = gate.check_tool_allowed(tool_name, {}, {})
            assert decision.allowed, f"{tool_name} should be allowed"
            assert decision.severity == "info"


def test_documentation_exempt():
    """Test that documentation files are exempt from workflow requirement."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker
    from amplifier_hook_tool_gate import EnforcementLevel, ToolGate

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = RecipeSessionTracker(state_file=Path(tmpdir) / "state.json")
        gate = ToolGate(tracker, enforcement_level=EnforcementLevel.HARD)

        # Documentation files should be allowed
        doc_files = ["README.md", "CONTRIBUTING.txt", "docs/api.rst", "notes.adoc"]

        for file_path in doc_files:
            decision = gate.check_tool_allowed(
                "write_file", {"file_path": file_path}, {"session_id": "test_123"}
            )
            assert decision.allowed, f"Should allow documentation: {file_path}"


def test_hard_enforcement_blocks_without_workflow():
    """Test that HARD enforcement blocks implementation tools without active workflow."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker
    from amplifier_hook_tool_gate import EnforcementLevel, ToolGate

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = RecipeSessionTracker(state_file=Path(tmpdir) / "state.json")
        gate = ToolGate(tracker, enforcement_level=EnforcementLevel.HARD)

        session_id = "test_session_789"

        # Without active workflow, should block
        decision = gate.check_tool_allowed(
            "write_file", {"file_path": "src/auth.py", "content": "..."}, {"session_id": session_id}
        )

        assert not decision.allowed, "Should block write_file without workflow"
        assert decision.severity == "error"
        assert "workflow required" in decision.reason.lower()


def test_hard_enforcement_allows_with_active_workflow():
    """Test that HARD enforcement allows tools when workflow is active."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker
    from amplifier_hook_tool_gate import EnforcementLevel, ToolGate

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = RecipeSessionTracker(state_file=Path(tmpdir) / "state.json")
        gate = ToolGate(tracker, enforcement_level=EnforcementLevel.HARD)

        session_id = "test_session_999"

        # Start workflow
        tracker.mark_workflow_started("default-workflow", session_id)

        # With active workflow, should allow
        decision = gate.check_tool_allowed(
            "write_file", {"file_path": "src/auth.py", "content": "..."}, {"session_id": session_id}
        )

        assert decision.allowed, "Should allow write_file with active workflow"
        assert decision.severity == "info"


def test_soft_enforcement_allows_with_warning():
    """Test that SOFT enforcement allows but warns."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker
    from amplifier_hook_tool_gate import EnforcementLevel, ToolGate

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = RecipeSessionTracker(state_file=Path(tmpdir) / "state.json")
        gate = ToolGate(tracker, enforcement_level=EnforcementLevel.SOFT)

        decision = gate.check_tool_allowed(
            "write_file", {"file_path": "src/auth.py"}, {"session_id": "test_soft"}
        )

        assert decision.allowed, "SOFT enforcement should allow"
        assert decision.severity == "info"


def test_medium_enforcement_tracks_bypasses():
    """Test that MEDIUM enforcement tracks bypass attempts."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker
    from amplifier_hook_tool_gate import EnforcementLevel, ToolGate

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = RecipeSessionTracker(state_file=Path(tmpdir) / "state.json")
        gate = ToolGate(tracker, enforcement_level=EnforcementLevel.MEDIUM)

        session_id = "test_medium"

        # Make a bypass attempt
        decision = gate.check_tool_allowed(
            "write_file", {"file_path": "src/auth.py"}, {"session_id": session_id}
        )

        assert decision.allowed, "MEDIUM enforcement should allow"
        assert decision.severity == "warning"

        # Verify bypass was recorded
        assert tracker.get_bypass_count(session_id) == 1


def test_git_commands_require_workflow():
    """Test that git commit/push commands require workflow."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker
    from amplifier_hook_tool_gate import EnforcementLevel, ToolGate

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = RecipeSessionTracker(state_file=Path(tmpdir) / "state.json")
        gate = ToolGate(tracker, enforcement_level=EnforcementLevel.HARD)

        git_commands = [
            "git commit -m 'test'",
            "git push origin main",
            "git merge feature-branch",
        ]

        for command in git_commands:
            decision = gate.check_tool_allowed(
                "bash", {"command": command}, {"session_id": "test_git"}
            )
            assert not decision.allowed, f"Should block: {command}"


def test_read_only_bash_commands_allowed():
    """Test that read-only bash commands are allowed."""
    from amplifier_hook_recipe_tracker import RecipeSessionTracker
    from amplifier_hook_tool_gate import EnforcementLevel, ToolGate

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = RecipeSessionTracker(state_file=Path(tmpdir) / "state.json")
        gate = ToolGate(tracker, enforcement_level=EnforcementLevel.HARD)

        read_only_commands = [
            "git status",
            "git log",
            "ls -la",
            "cat README.md",
        ]

        for command in read_only_commands:
            decision = gate.check_tool_allowed(
                "bash", {"command": command}, {"session_id": "test_readonly"}
            )
            assert decision.allowed, f"Should allow: {command}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
