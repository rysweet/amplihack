"""Regression tests for CLI passthrough parsing."""

from __future__ import annotations

import pytest

from amplihack.cli import parse_args_with_passthrough


def test_copilot_unknown_flag_is_forwarded_without_separator():
    """Unknown subordinate CLI flags should be forwarded automatically."""
    args, forwarded = parse_args_with_passthrough(["copilot", "--resume"])

    assert args.command == "copilot"
    assert forwarded == ["--resume"]


def test_direct_claude_launch_forwards_unknown_flag_without_separator():
    """Bare amplihack invocation should still support launch-style passthrough."""
    args, forwarded = parse_args_with_passthrough(["--resume"])

    assert args.command is None
    assert forwarded == ["--resume"]


def test_known_amplihack_flags_stay_bound_while_unknown_args_forward():
    """Recognised amplihack flags must parse normally alongside passthrough args."""
    args, forwarded = parse_args_with_passthrough(["copilot", "--auto", "--resume", "session-123"])

    assert args.command == "copilot"
    assert args.auto is True
    assert forwarded == ["--resume", "session-123"]


def test_explicit_separator_still_works():
    """Existing -- passthrough semantics must remain intact."""
    args, forwarded = parse_args_with_passthrough(["copilot", "--", "--resume", "session-123"])

    assert args.command == "copilot"
    assert forwarded == ["--resume", "session-123"]


def test_non_passthrough_commands_still_error_on_unknown_args():
    """Management commands should remain strict about unknown flags."""
    with pytest.raises(SystemExit, match="2"):
        parse_args_with_passthrough(["install", "--resume"])
