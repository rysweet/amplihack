"""Outside-in test for NestedSessionAdapter and CLISubprocessAdapter.

Verifies that agent steps run in isolated temp directories and that
CLAUDECODE is stripped from the child env, which is the fix for issue #2758.
"""

import os
import tempfile
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None


def test_nested_session_adapter_basic():
    """Test that NestedSessionAdapter can invoke claude CLI."""
    from amplihack.recipes.adapters.nested_session import NestedSessionAdapter

    # Create adapter
    adapter = NestedSessionAdapter(cli="claude")

    # Test simple agent invocation
    prompt = "What is 2+2? Answer with just the number."

    try:
        result = adapter.execute_agent_step(prompt=prompt)
        print("Agent execution succeeded!")
        print(f"Result: {result}")

        # Verify we got a response
        assert result, "Agent should return non-empty result"
        assert len(result) > 0, "Result should have content"

    except RuntimeError as e:
        if "cannot be launched inside another Claude Code session" in str(e):
            error_msg = (
                "NestedSessionAdapter still blocked by nested session check. "
                "CLAUDECODE was not properly unset in subprocess."
            )
            if pytest:
                pytest.fail(error_msg)
            else:
                raise AssertionError(error_msg) from e
        raise


def test_nested_session_adapter_bash():
    """Test that bash steps work correctly."""
    from amplihack.recipes.adapters.nested_session import NestedSessionAdapter

    adapter = NestedSessionAdapter()

    # Simple bash command
    result = adapter.execute_bash_step(command='echo "Hello from bash"')

    assert result == "Hello from bash"
    print(f"Bash execution works: {result}")


def test_nested_session_adapter_temp_dirs():
    """Test that temp directories are created and cleaned up."""
    from amplihack.recipes.adapters.nested_session import NestedSessionAdapter

    adapter = NestedSessionAdapter(use_temp_dirs=True)

    # Track temp directories before
    temp_root = Path(tempfile.gettempdir())
    before = set(temp_root.glob("recipe-agent-*"))

    # Execute agent step (creates temp dir)
    try:
        result = adapter.execute_agent_step(prompt="Say hello")
        print("Agent executed in temp dir")
    except Exception as e:
        print(f"Agent execution error (may be expected): {e}")

    # Check temp directories after
    after = set(temp_root.glob("recipe-agent-*"))

    # Temp directory should be cleaned up
    created = after - before
    print(f"Temp dirs created during test: {len(created)}")
    print(f"Temp dirs remaining: {len(after)}")

    # Should be cleaned up automatically
    assert len(created) == 0, "Temp directory should be cleaned up after execution"


def test_get_adapter_returns_adapter():
    """Test that get_adapter() returns a usable adapter."""
    from amplihack.recipes.adapters import get_adapter

    adapter = get_adapter()

    print(f"Auto-selected adapter: {adapter.name}")
    assert adapter.name, "Adapter should have a name"


def test_nested_session_isolated_from_parent():
    """Test that nested session env does not leak back into the parent."""
    from amplihack.recipes.adapters.nested_session import NestedSessionAdapter

    from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter

    # Record parent env snapshot
    parent_env_snapshot = dict(os.environ)

    try:
        result = adapter.execute_agent_step(prompt="Say hello")
        print(f"Nested session result: {result}")
    except RuntimeError as e:
        # If error, verify it's not the nested session blocking error
        assert "cannot be launched inside another Claude Code session" not in str(e), (
            "Nested session should not be blocked"
        )

    # Parent env should be unchanged after nested session
    assert dict(os.environ) == parent_env_snapshot, "Parent env should be unchanged"
    print("Parent session isolated from nested session")


if __name__ == "__main__":
    print("Running Outside-In Tests for NestedSessionAdapter\n")

    tests = [
        ("Basic agent invocation", test_nested_session_adapter_basic),
        ("Bash step execution", test_nested_session_adapter_bash),
        ("Temp directory cleanup", test_nested_session_adapter_temp_dirs),
        ("Adapter auto-selection", test_get_adapter_returns_adapter),
        ("Isolation from parent session", test_nested_session_isolated_from_parent),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Test: {test_name}")
        print(f"{'=' * 60}")
        try:
            test_func()
            print("PASSED")
            passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1
            import traceback

            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
