"""Tests for Claude CLI readiness verification after installation.

Verifies that after installing Claude CLI (especially on first launch in WSL),
the binary is validated before attempting to use it for plugin installation.

This prevents the bug where on first WSL launch, Claude is installed but the
plugin install command fails because the binary isn't ready yet.

Bug: Plugin not installed on first WSL launch after Claude installation
"""

import time
from unittest.mock import patch


def test_verify_claude_cli_ready_success_immediate():
    """Test successful verification on first attempt."""
    from amplihack.cli import _verify_claude_cli_ready

    with patch("amplihack.utils.prerequisites.safe_subprocess_call") as mock:
        # Simulate successful --version call
        mock.return_value = (0, "claude version 1.0.0\n", "")

        result = _verify_claude_cli_ready("/usr/bin/claude")

        assert result is True
        assert mock.call_count == 1
        mock.assert_called_with(
            ["/usr/bin/claude", "--version"],
            context="verifying Claude CLI is ready",
            timeout=5,
        )


def test_verify_claude_cli_ready_success_after_retry():
    """Test successful verification after retries (simulates fresh install)."""
    from amplihack.cli import _verify_claude_cli_ready

    with patch("amplihack.utils.prerequisites.safe_subprocess_call") as mock:
        # First two attempts fail, third succeeds (simulating installation delay)
        mock.side_effect = [
            (1, "", "Error: not ready"),  # First attempt fails
            (1, "", "Error: still not ready"),  # Second attempt fails
            (0, "claude version 1.0.0\n", ""),  # Third attempt succeeds
        ]

        start_time = time.time()
        result = _verify_claude_cli_ready("/usr/bin/claude", max_retries=3, retry_delay=0.1)
        elapsed = time.time() - start_time

        assert result is True
        assert mock.call_count == 3
        # Should have waited at least 2 delays (0.1s * 2 retries)
        assert elapsed >= 0.2


def test_verify_claude_cli_ready_failure_all_retries():
    """Test failure when all retries are exhausted."""
    from amplihack.cli import _verify_claude_cli_ready

    with patch("amplihack.utils.prerequisites.safe_subprocess_call") as mock:
        # All attempts fail
        mock.return_value = (1, "", "Error: binary not found")

        result = _verify_claude_cli_ready("/usr/bin/claude", max_retries=3, retry_delay=0.1)

        assert result is False
        assert mock.call_count == 3


def test_verify_claude_cli_ready_handles_exceptions():
    """Test handling of exceptions during verification."""
    from amplihack.cli import _verify_claude_cli_ready

    with patch("amplihack.utils.prerequisites.safe_subprocess_call") as mock:
        # First two attempts raise exceptions, third succeeds
        mock.side_effect = [
            Exception("Subprocess error"),
            Exception("Still failing"),
            (0, "claude version 1.0.0\n", ""),
        ]

        result = _verify_claude_cli_ready("/usr/bin/claude", max_retries=3, retry_delay=0.1)

        assert result is True
        assert mock.call_count == 3


def test_verify_claude_cli_ready_exception_all_retries():
    """Test failure when all retries raise exceptions."""
    from amplihack.cli import _verify_claude_cli_ready

    with patch("amplihack.utils.prerequisites.safe_subprocess_call") as mock:
        # All attempts raise exceptions
        mock.side_effect = Exception("Binary not executable")

        result = _verify_claude_cli_ready("/usr/bin/claude", max_retries=3, retry_delay=0.1)

        assert result is False
        assert mock.call_count == 3


def test_verify_claude_cli_ready_custom_retries():
    """Test custom retry configuration."""
    from amplihack.cli import _verify_claude_cli_ready

    with patch("amplihack.utils.prerequisites.safe_subprocess_call") as mock:
        mock.return_value = (1, "", "Error")

        result = _verify_claude_cli_ready(
            "/usr/bin/claude",
            max_retries=5,
            retry_delay=0.05,
        )

        assert result is False
        assert mock.call_count == 5
