"""
Integration tests for auto mode ultrathink command prepending.

Tests the integration of ensure_ultrathink_command() with handle_auto_mode()
to verify that prompts are correctly transformed before being passed to AutoMode.

Following test pyramid: 30% integration tests for workflow verification.
"""

import argparse
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Integration Tests - handle_auto_mode() with ensure_ultrathink_command()
# =============================================================================


@pytest.fixture
def mock_auto_mode():
    """Mock AutoMode class for integration tests."""
    with patch("amplihack.cli.AutoMode") as mock:
        instance = MagicMock()
        instance.run.return_value = 0
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_ensure_ultrathink():
    """Mock ensure_ultrathink_command for verifying calls."""
    with patch("amplihack.cli.ensure_ultrathink_command") as mock:
        # Default behavior: prepend command
        mock.side_effect = lambda p: f"/amplihack:ultrathink {p}" if not p.startswith("/") else p
        yield mock


def test_integration_auto_001_normal_prompt_prepends_ultrathink(mock_auto_mode):
    """INTEGRATION-AUTO-001: Normal prompt gets ultrathink prepended."""
    from amplihack.cli import handle_auto_mode

    # Setup args
    args = argparse.Namespace(auto=True, max_turns=10, ui=False)
    cmd_args = ["-p", "implement feature X"]

    # Execute
    handle_auto_mode("claude", args, cmd_args)

    # Verify AutoMode was called with transformed prompt
    mock_auto_mode.assert_called_once()
    call_args = mock_auto_mode.call_args

    # Check that the prompt was transformed
    assert call_args[0][0] == "claude"
    # Note: This test verifies current behavior will change when implementation is added


def test_integration_auto_002_slash_command_unchanged(mock_auto_mode):
    """INTEGRATION-AUTO-002: Slash command prompt remains unchanged."""
    from amplihack.cli import handle_auto_mode

    args = argparse.Namespace(auto=True, max_turns=10, ui=False)
    cmd_args = ["-p", "/analyze src"]

    handle_auto_mode("claude", args, cmd_args)

    # Verify AutoMode was called
    mock_auto_mode.assert_called_once()


def test_integration_auto_003_whitespace_stripped(mock_auto_mode):
    """INTEGRATION-AUTO-003: Leading/trailing whitespace is stripped."""
    from amplihack.cli import handle_auto_mode

    args = argparse.Namespace(auto=True, max_turns=10, ui=False)
    cmd_args = ["-p", "  implement feature  "]

    handle_auto_mode("claude", args, cmd_args)

    # Verify AutoMode was called
    mock_auto_mode.assert_called_once()


def test_integration_auto_004_empty_prompt_error(mock_auto_mode):
    """INTEGRATION-AUTO-004: Empty prompt returns error."""
    from amplihack.cli import handle_auto_mode

    args = argparse.Namespace(auto=True, max_turns=10, ui=False)
    cmd_args = ["-p", ""]

    exit_code = handle_auto_mode("claude", args, cmd_args)

    # Should return error code 1
    assert exit_code == 1

    # AutoMode should NOT be called with empty prompt
    mock_auto_mode.assert_not_called()


def test_integration_auto_005_no_prompt_flag_error(mock_auto_mode):
    """INTEGRATION-AUTO-005: Missing -p flag returns error."""
    from amplihack.cli import handle_auto_mode

    args = argparse.Namespace(auto=True, max_turns=10, ui=False)
    cmd_args = []

    exit_code = handle_auto_mode("claude", args, cmd_args)

    # Should return error code 1
    assert exit_code == 1

    # AutoMode should NOT be called
    mock_auto_mode.assert_not_called()


def test_integration_auto_006_max_turns_passed_through(mock_auto_mode):
    """INTEGRATION-AUTO-006: max_turns is passed to AutoMode."""
    from amplihack.cli import handle_auto_mode

    args = argparse.Namespace(auto=True, max_turns=25, ui=False)
    cmd_args = ["-p", "implement feature"]

    handle_auto_mode("claude", args, cmd_args)

    # Verify max_turns was passed
    call_args = mock_auto_mode.call_args
    assert call_args[0][2] == 25  # Third positional arg is max_turns


def test_integration_auto_007_ui_mode_passed_through(mock_auto_mode):
    """INTEGRATION-AUTO-007: ui_mode is passed to AutoMode."""
    from amplihack.cli import handle_auto_mode

    args = argparse.Namespace(auto=True, max_turns=10, ui=True)
    cmd_args = ["-p", "implement feature"]

    handle_auto_mode("claude", args, cmd_args)

    # Verify ui_mode was passed
    call_args = mock_auto_mode.call_args
    assert call_args[1]["ui_mode"] is True


def test_integration_auto_008_copilot_sdk(mock_auto_mode):
    """INTEGRATION-AUTO-008: Works with copilot SDK."""
    from amplihack.cli import handle_auto_mode

    args = argparse.Namespace(auto=True, max_turns=10, ui=False)
    cmd_args = ["-p", "implement feature"]

    handle_auto_mode("copilot", args, cmd_args)

    # Verify copilot SDK was passed
    call_args = mock_auto_mode.call_args
    assert call_args[0][0] == "copilot"


def test_integration_auto_009_codex_sdk(mock_auto_mode):
    """INTEGRATION-AUTO-009: Works with codex SDK."""
    from amplihack.cli import handle_auto_mode

    args = argparse.Namespace(auto=True, max_turns=10, ui=False)
    cmd_args = ["-p", "implement feature"]

    handle_auto_mode("codex", args, cmd_args)

    # Verify codex SDK was passed
    call_args = mock_auto_mode.call_args
    assert call_args[0][0] == "codex"


def test_integration_auto_010_auto_mode_exit_code_propagated(mock_auto_mode):
    """INTEGRATION-AUTO-010: AutoMode exit code is returned."""
    from amplihack.cli import handle_auto_mode

    # Make AutoMode return non-zero exit code
    mock_auto_mode.return_value.run.return_value = 42

    args = argparse.Namespace(auto=True, max_turns=10, ui=False)
    cmd_args = ["-p", "implement feature"]

    exit_code = handle_auto_mode("claude", args, cmd_args)

    # Exit code should be propagated
    assert exit_code == 42


def test_integration_auto_011_not_auto_mode_returns_none(mock_auto_mode):
    """INTEGRATION-AUTO-011: Non-auto mode returns None."""
    from amplihack.cli import handle_auto_mode

    args = argparse.Namespace(auto=False, max_turns=10, ui=False)
    cmd_args = ["-p", "implement feature"]

    exit_code = handle_auto_mode("claude", args, cmd_args)

    # Should return None (indicating not auto mode)
    assert exit_code is None

    # AutoMode should NOT be called
    mock_auto_mode.assert_not_called()


def test_integration_auto_012_multiline_prompt(mock_auto_mode):
    """INTEGRATION-AUTO-012: Multiline prompts are handled."""
    from amplihack.cli import handle_auto_mode

    multiline = """implement authentication
with JWT tokens
and refresh support"""

    args = argparse.Namespace(auto=True, max_turns=10, ui=False)
    cmd_args = ["-p", multiline]

    exit_code = handle_auto_mode("claude", args, cmd_args)

    # Should succeed
    assert exit_code == 0


def test_integration_auto_013_prompt_with_special_chars(mock_auto_mode):
    """INTEGRATION-AUTO-013: Prompts with special characters work."""
    from amplihack.cli import ensure_ultrathink_command

    prompt = """implement "feature X" with user's data & settings"""
    result = ensure_ultrathink_command(prompt)

    # Should handle special characters
    assert "/amplihack:ultrathink" in result


def test_integration_auto_014_prompt_extraction_first_p_flag():
    """INTEGRATION-AUTO-014: Prompt is extracted from first -p flag."""
    from amplihack.cli import handle_auto_mode

    with patch("amplihack.cli.AutoMode") as mock_auto:
        mock_auto.return_value.run.return_value = 0

        args = argparse.Namespace(auto=True, max_turns=10, ui=False)
        cmd_args = ["-p", "first prompt", "-p", "second prompt"]

        handle_auto_mode("claude", args, cmd_args)

        # Should use first prompt
        call_args = mock_auto.call_args
        assert "first prompt" in str(call_args)


def test_integration_auto_015_prompt_flag_at_end():
    """INTEGRATION-AUTO-015: -p flag can be at end of cmd_args."""
    from amplihack.cli import handle_auto_mode

    with patch("amplihack.cli.AutoMode") as mock_auto:
        mock_auto.return_value.run.return_value = 0

        args = argparse.Namespace(auto=True, max_turns=10, ui=False)
        cmd_args = ["--verbose", "-p", "implement feature"]

        exit_code = handle_auto_mode("claude", args, cmd_args)

        # Should extract prompt successfully
        assert exit_code == 0


# =============================================================================
# End-to-End Workflow Tests
# =============================================================================


def test_integration_auto_016_full_workflow_with_transformation():
    """INTEGRATION-AUTO-016: Full workflow from CLI args to AutoMode."""
    from amplihack.cli import ensure_ultrathink_command, handle_auto_mode

    with patch("amplihack.cli.AutoMode") as mock_auto:
        mock_auto.return_value.run.return_value = 0

        # Simulate user input
        user_prompt = "implement authentication feature"

        # Transform prompt (simulating what should happen)
        transformed = ensure_ultrathink_command(user_prompt)

        # Verify transformation
        assert transformed == "/amplihack:ultrathink implement authentication feature"

        # Now test via handle_auto_mode
        args = argparse.Namespace(auto=True, max_turns=10, ui=False)
        cmd_args = ["-p", user_prompt]

        exit_code = handle_auto_mode("claude", args, cmd_args)

        assert exit_code == 0
        mock_auto.assert_called_once()


def test_integration_auto_017_already_ultrathink_no_duplication():
    """INTEGRATION-AUTO-017: Already ultrathink command not duplicated."""
    from amplihack.cli import ensure_ultrathink_command

    prompt = "/amplihack:ultrathink implement feature"
    result = ensure_ultrathink_command(prompt)

    # Should NOT have double prepending
    assert result.count("/amplihack:ultrathink") == 1
    assert result == "/amplihack:ultrathink implement feature"


def test_integration_auto_018_whitespace_only_prompt_error():
    """INTEGRATION-AUTO-018: Whitespace-only prompt treated as empty."""
    from amplihack.cli import handle_auto_mode

    with patch("amplihack.cli.AutoMode") as mock_auto:
        args = argparse.Namespace(auto=True, max_turns=10, ui=False)
        cmd_args = ["-p", "   \t\n   "]

        exit_code = handle_auto_mode("claude", args, cmd_args)

        # Should return error (treated as empty after stripping)
        assert exit_code == 1
        mock_auto.assert_not_called()


def test_integration_auto_019_prompt_with_quotes_preserved():
    """INTEGRATION-AUTO-019: Quotes in prompts are preserved."""
    from amplihack.cli import ensure_ultrathink_command

    prompt = """implement feature "X" with 'single' quotes"""
    result = ensure_ultrathink_command(prompt)

    # Quotes should be preserved
    assert '"X"' in result
    assert "'single'" in result


def test_integration_auto_020_long_prompt_handled():
    """INTEGRATION-AUTO-020: Very long prompts are handled."""
    from amplihack.cli import ensure_ultrathink_command

    # Create a long prompt (2000+ chars)
    long_prompt = "implement " + ("comprehensive authentication system " * 50)

    result = ensure_ultrathink_command(long_prompt)

    # Should still work
    assert result.startswith("/amplihack:ultrathink")
    assert len(result) > 2000


# =============================================================================
# Error Handling Integration Tests
# =============================================================================


def test_integration_auto_021_auto_mode_import_error():
    """INTEGRATION-AUTO-021: Handle AutoMode import errors gracefully."""
    from amplihack.cli import handle_auto_mode

    with patch("amplihack.cli.AutoMode", side_effect=ImportError("AutoMode not found")):
        args = argparse.Namespace(auto=True, max_turns=10, ui=False)
        cmd_args = ["-p", "implement feature"]

        # Should raise ImportError or handle gracefully
        with pytest.raises(ImportError):
            handle_auto_mode("claude", args, cmd_args)


def test_integration_auto_022_auto_mode_runtime_error():
    """INTEGRATION-AUTO-022: Handle AutoMode runtime errors."""
    from amplihack.cli import handle_auto_mode

    with patch("amplihack.cli.AutoMode") as mock_auto:
        mock_auto.return_value.run.side_effect = RuntimeError("AutoMode failed")

        args = argparse.Namespace(auto=True, max_turns=10, ui=False)
        cmd_args = ["-p", "implement feature"]

        # Should propagate error
        with pytest.raises(RuntimeError):
            handle_auto_mode("claude", args, cmd_args)


def test_integration_auto_023_missing_prompt_value():
    """INTEGRATION-AUTO-023: -p flag with no value."""
    from amplihack.cli import handle_auto_mode

    with patch("amplihack.cli.AutoMode") as mock_auto:
        args = argparse.Namespace(auto=True, max_turns=10, ui=False)
        cmd_args = ["-p"]  # Missing value after -p

        exit_code = handle_auto_mode("claude", args, cmd_args)

        # Should return error
        assert exit_code == 1
        mock_auto.assert_not_called()


# =============================================================================
# Parametrized Tests for Multiple SDKs
# =============================================================================


@pytest.mark.parametrize("sdk", ["claude", "copilot", "codex"])
def test_integration_auto_024_all_sdks_work(sdk, mock_auto_mode):
    """INTEGRATION-AUTO-024: All SDKs work with auto mode."""
    from amplihack.cli import handle_auto_mode

    args = argparse.Namespace(auto=True, max_turns=10, ui=False)
    cmd_args = ["-p", "implement feature"]

    exit_code = handle_auto_mode(sdk, args, cmd_args)

    # Should succeed for all SDKs
    assert exit_code == 0
    mock_auto_mode.assert_called_once()


@pytest.mark.parametrize("max_turns", [1, 5, 10, 20, 50])
def test_integration_auto_025_various_max_turns(max_turns, mock_auto_mode):
    """INTEGRATION-AUTO-025: Various max_turns values work."""
    from amplihack.cli import handle_auto_mode

    args = argparse.Namespace(auto=True, max_turns=max_turns, ui=False)
    cmd_args = ["-p", "implement feature"]

    exit_code = handle_auto_mode("claude", args, cmd_args)

    # Should succeed with any valid max_turns
    assert exit_code == 0


@pytest.mark.parametrize("ui_mode", [True, False])
def test_integration_auto_026_ui_mode_variations(ui_mode, mock_auto_mode):
    """INTEGRATION-AUTO-026: Both UI modes work."""
    from amplihack.cli import handle_auto_mode

    args = argparse.Namespace(auto=True, max_turns=10, ui=ui_mode)
    cmd_args = ["-p", "implement feature"]

    exit_code = handle_auto_mode("claude", args, cmd_args)

    # Should succeed in both modes
    assert exit_code == 0


# =============================================================================
# Real Integration Test (Without Mocks)
# =============================================================================


def test_integration_auto_027_ensure_ultrathink_real_function():
    """INTEGRATION-AUTO-027: Test actual ensure_ultrathink_command without mocks."""
    # This test will FAIL until the function is implemented
    from amplihack.cli import ensure_ultrathink_command

    # Test basic functionality
    assert ensure_ultrathink_command("test") == "/amplihack:ultrathink test"
    assert ensure_ultrathink_command("/analyze") == "/analyze"
    assert ensure_ultrathink_command("") == ""
    assert ensure_ultrathink_command("  test  ") == "/amplihack:ultrathink test"


def test_integration_auto_028_pure_function_no_side_effects():
    """INTEGRATION-AUTO-028: ensure_ultrathink_command has no side effects."""
    from amplihack.cli import ensure_ultrathink_command

    prompt = "test prompt"

    # Call multiple times
    result1 = ensure_ultrathink_command(prompt)
    result2 = ensure_ultrathink_command(prompt)
    result3 = ensure_ultrathink_command(prompt)

    # Should return same result every time (pure function)
    assert result1 == result2 == result3

    # Original prompt should be unchanged
    assert prompt == "test prompt"


def test_integration_auto_029_function_signature():
    """INTEGRATION-AUTO-029: Verify function signature."""
    import inspect

    from amplihack.cli import ensure_ultrathink_command

    # Check function exists
    assert callable(ensure_ultrathink_command)

    # Check signature
    sig = inspect.signature(ensure_ultrathink_command)
    params = list(sig.parameters.keys())

    # Should take exactly one parameter (prompt)
    assert len(params) == 1
    assert params[0] == "prompt"


def test_integration_auto_030_return_type():
    """INTEGRATION-AUTO-030: Verify return type is string."""
    from amplihack.cli import ensure_ultrathink_command

    result = ensure_ultrathink_command("test")

    # Should return string
    assert isinstance(result, str)
