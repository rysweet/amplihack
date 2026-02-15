"""Outside-in test for NestedSessionAdapter - verify it works inside Claude Code session."""

import os
import subprocess
import tempfile
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None


def test_nested_session_adapter_basic():
    """Test that NestedSessionAdapter can invoke claude CLI inside Claude Code session."""
    from amplihack.recipes.adapters.nested_session import NestedSessionAdapter

    # Verify we're IN a Claude Code session (CLAUDECODE should be set)
    assert "CLAUDECODE" in os.environ, "This test must run inside Claude Code session"

    # Create adapter
    adapter = NestedSessionAdapter(cli="claude")

    # Test simple agent invocation
    prompt = "What is 2+2? Answer with just the number."

    try:
        result = adapter.execute_agent_step(prompt=prompt)
        print(f"✅ Agent execution succeeded!")
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
    print(f"✅ Bash execution works: {result}")


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
        print(f"✅ Agent executed in temp dir")
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


def test_get_adapter_auto_detects_nested():
    """Test that get_adapter() automatically uses NestedSessionAdapter when nested."""
    from amplihack.recipes.adapters import get_adapter

    # We're in a Claude Code session (CLAUDECODE env var set)
    assert "CLAUDECODE" in os.environ

    # get_adapter() should automatically return NestedSessionAdapter
    adapter = get_adapter()

    print(f"✅ Auto-selected adapter: {adapter.name}")
    assert "nested-session" in adapter.name, f"Expected nested-session adapter, got {adapter.name}"


def test_nested_session_isolated_from_parent():
    """Test that nested session doesn't interfere with parent session."""
    from amplihack.recipes.adapters.nested_session import NestedSessionAdapter

    adapter = NestedSessionAdapter(use_temp_dirs=True)

    # Parent session has CLAUDECODE set
    parent_claudecode = os.environ.get("CLAUDECODE")
    assert parent_claudecode, "Parent should have CLAUDECODE"

    # Execute agent step
    # The subprocess should NOT have CLAUDECODE
    prompt = """
    import os
    print("CLAUDECODE=" + os.environ.get("CLAUDECODE", "NOT_SET"))
    """

    try:
        result = adapter.execute_agent_step(prompt=prompt)
        print(f"Nested session CLAUDECODE: {result}")

        # Nested session should NOT have CLAUDECODE
        assert "CLAUDECODE=NOT_SET" in result or "CLAUDECODE" not in result

    except RuntimeError as e:
        # If error, verify it's not the nested session error
        assert "cannot be launched inside another Claude Code session" not in str(
            e
        ), "Nested session check should be bypassed"

    # Parent session should still have CLAUDECODE unchanged
    assert os.environ.get("CLAUDECODE") == parent_claudecode, "Parent env should be unchanged"
    print("✅ Parent session isolated from nested session")


if __name__ == "__main__":
    print("🧪 Running Outside-In Tests for NestedSessionAdapter\n")

    # Run tests
    tests = [
        ("Basic agent invocation", test_nested_session_adapter_basic),
        ("Bash step execution", test_nested_session_adapter_bash),
        ("Temp directory cleanup", test_nested_session_adapter_temp_dirs),
        ("Auto-detection of nested session", test_get_adapter_auto_detects_nested),
        ("Isolation from parent session", test_nested_session_isolated_from_parent),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Test: {test_name}")
        print(f"{'='*60}")
        try:
            test_func()
            print(f"✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1
            import traceback

            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print(f"{'='*60}")
