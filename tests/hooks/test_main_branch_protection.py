#!/usr/bin/env python3
"""
Tests for main/master branch commit protection in pre_tool_use hook.

Testing approach: TDD (Test-Driven Development)
- Tests are written BEFORE implementation
- Tests WILL FAIL initially (expected behavior)
- Tests WILL PASS once implementation is complete

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)

Coverage:
- Branch detection logic
- Commit blocking behavior
- Error handling and fail-open
- Security (subprocess safety)
- File synchronization
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add hooks directory to path for imports
hooks_dir = Path(__file__).parent.parent.parent / "amplifier-bundle" / "tools" / "amplihack" / "hooks"
sys.path.insert(0, str(hooks_dir))

from pre_tool_use import PreToolUseHook

# ============================================================================
# UNIT TESTS (60%) - Branch Detection Logic
# ============================================================================


class TestBranchDetection:
    """Unit tests for git branch detection logic.

    TDD: These tests WILL FAIL until branch detection is implemented.
    """

    def test_detect_main_branch(self, tmp_path):
        """Test detection of 'main' branch.

        TDD: WILL FAIL - branch detection not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            # Simulate git returning 'main'
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            # Should block commit to main
            assert result.get("block") is True
            assert "main" in result.get("message", "").lower()

            # Verify subprocess was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["git", "branch", "--show-current"]
            assert call_args[1]["timeout"] == 5
            assert call_args[1].get("shell") is not True

    def test_detect_master_branch(self, tmp_path):
        """Test detection of 'master' branch.

        TDD: WILL FAIL - branch detection not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            # Simulate git returning 'master'
            mock_run.return_value = Mock(returncode=0, stdout="master\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            # Should block commit to master
            assert result.get("block") is True
            assert "master" in result.get("message", "").lower()

    def test_allow_feature_branch(self, tmp_path):
        """Test that feature branches are allowed.

        TDD: WILL FAIL - branch detection not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            # Simulate git returning feature branch
            mock_run.return_value = Mock(returncode=0, stdout="feature/add-tests\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            # Should allow commit to feature branch
            assert result.get("block") is not True
            assert "message" not in result or "main" not in result["message"].lower()

    def test_strip_whitespace_from_branch_name(self, tmp_path):
        """Test that branch name whitespace is stripped.

        Git output includes newline - must be stripped for comparison.

        TDD: WILL FAIL - branch detection not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            # Simulate git returning 'main' with extra whitespace
            mock_run.return_value = Mock(returncode=0, stdout="  main  \n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            # Should still detect 'main' after stripping
            assert result.get("block") is True

    def test_subprocess_uses_timeout(self, tmp_path):
        """Test that subprocess.run uses 5-second timeout.

        Security requirement: prevent hangs.

        TDD: WILL FAIL - subprocess call not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="feature/test\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            hook.process(input_data)

            # Verify timeout parameter
            call_args = mock_run.call_args
            assert call_args[1]["timeout"] == 5

    def test_subprocess_uses_argument_list_not_shell(self, tmp_path):
        """Test that subprocess uses argument list (security requirement).

        SECURITY: Must NOT use shell=True to prevent command injection.

        TDD: WILL FAIL - subprocess call not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="feature/test\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            hook.process(input_data)

            # Verify argument list format (not string) and no shell=True
            call_args = mock_run.call_args
            assert isinstance(call_args[0][0], list)
            assert call_args[1].get("shell") is not True

    def test_subprocess_captures_output(self, tmp_path):
        """Test that subprocess captures stdout for branch name.

        TDD: WILL FAIL - subprocess call not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="feature/test\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            hook.process(input_data)

            # Verify stdout capture
            call_args = mock_run.call_args
            assert call_args[1]["capture_output"] is True or (
                call_args[1].get("stdout") == subprocess.PIPE
                and call_args[1].get("stderr") == subprocess.PIPE
            )


# ============================================================================
# INTEGRATION TESTS (30%) - Commit Blocking Behavior
# ============================================================================


class TestCommitBlocking:
    """Integration tests for commit blocking on main/master branches.

    TDD: These tests WILL FAIL until commit blocking is implemented.
    """

    def test_block_git_commit_on_main(self, tmp_path):
        """Test TC1: git commit -m 'msg' on main → BLOCKED.

        TDD: WILL FAIL - commit blocking not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {
                "toolUse": {"name": "Bash", "input": {"command": "git commit -m 'Add feature'"}}
            }

            result = hook.process(input_data)

            assert result.get("block") is True
            message = result.get("message", "")
            assert "main" in message.lower()
            assert "feature branch" in message.lower()

    def test_block_git_commit_on_master(self, tmp_path):
        """Test TC2: git commit -m 'msg' on master → BLOCKED.

        TDD: WILL FAIL - commit blocking not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="master\n", stderr="")

            input_data = {
                "toolUse": {"name": "Bash", "input": {"command": "git commit -m 'Fix bug'"}}
            }

            result = hook.process(input_data)

            assert result.get("block") is True
            message = result.get("message", "")
            assert "master" in message.lower()

    def test_block_git_commit_amend_on_main(self, tmp_path):
        """Test TC4: git commit --amend on main → BLOCKED.

        TDD: WILL FAIL - commit variant blocking not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {
                "toolUse": {"name": "Bash", "input": {"command": "git commit --amend --no-edit"}}
            }

            result = hook.process(input_data)

            assert result.get("block") is True

    def test_block_git_commit_fixup_on_main(self, tmp_path):
        """Test git commit --fixup on main → BLOCKED.

        TDD: WILL FAIL - commit variant blocking not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {
                "toolUse": {"name": "Bash", "input": {"command": "git commit --fixup HEAD"}}
            }

            result = hook.process(input_data)

            assert result.get("block") is True

    def test_allow_git_commit_on_feature_branch(self, tmp_path):
        """Test TC3: git commit -m 'msg' on feature/xyz → ALLOWED.

        TDD: WILL FAIL - branch detection not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="feature/add-tests\n", stderr="")

            input_data = {
                "toolUse": {"name": "Bash", "input": {"command": "git commit -m 'Add tests'"}}
            }

            result = hook.process(input_data)

            # Should allow - return empty dict or block=False
            assert result.get("block") is not True

    def test_allow_git_push_on_main(self, tmp_path):
        """Test TC7: git push on main → ALLOWED (only commits blocked).

        TDD: WILL FAIL - selective blocking not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git push origin main"}}}

            result = hook.process(input_data)

            # Push should be allowed (only commits are blocked)
            assert result.get("block") is not True

    def test_allow_git_status_on_main(self, tmp_path):
        """Test TC8: git status on main → ALLOWED.

        TDD: WILL FAIL - selective blocking not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git status"}}}

            result = hook.process(input_data)

            # git status should be allowed
            assert result.get("block") is not True

    def test_both_checks_active_for_no_verify_on_main(self, tmp_path):
        """Test TC5: git commit --no-verify on main → BLOCKED (both checks fire).

        Both main branch check AND --no-verify check should activate.
        Main branch error shown first (checked first in code).

        TDD: WILL FAIL - branch blocking not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {
                "toolUse": {
                    "name": "Bash",
                    "input": {"command": "git commit --no-verify -m 'test'"},
                }
            }

            result = hook.process(input_data)

            # Should block - main branch check fires first
            assert result.get("block") is True
            message = result.get("message", "")

            # Should mention main branch (not --no-verify, as that comes later)
            assert "main" in message.lower()

    def test_no_verify_blocked_on_feature_branch(self, tmp_path):
        """Test TC6: git commit --no-verify on feature/xyz → BLOCKED (--no-verify check).

        Main branch check passes (feature branch), but --no-verify check blocks.

        TDD: This should PASS (existing functionality).
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="feature/test\n", stderr="")

            input_data = {
                "toolUse": {
                    "name": "Bash",
                    "input": {"command": "git commit --no-verify -m 'test'"},
                }
            }

            result = hook.process(input_data)

            # Should block due to --no-verify check
            assert result.get("block") is True
            message = result.get("message", "")
            assert "--no-verify" in message.lower() or "no-verify" in message.lower()


# ============================================================================
# ERROR HANDLING TESTS - Fail-Open Behavior
# ============================================================================


class TestErrorHandling:
    """Error handling and fail-open tests.

    Philosophy: Gracefully degrade when git commands fail.
    Never block legitimate work due to environmental issues.

    TDD: These tests WILL FAIL until error handling is implemented.
    """

    def test_fail_open_when_not_in_git_repo(self, tmp_path):
        """Test EC1: Not in git repo → Fail-open with warning.

        When git command fails (not a git repo), allow the operation.

        TDD: WILL FAIL - error handling not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            # Simulate "not a git repository" error
            mock_run.side_effect = subprocess.CalledProcessError(
                128, ["git", "branch", "--show-current"], stderr="fatal: not a git repository"
            )

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            # Should allow (fail-open)
            assert result.get("block") is not True

    def test_fail_open_when_git_not_in_path(self, tmp_path):
        """Test EC2: Git not in PATH → Fail-open with warning.

        TDD: WILL FAIL - error handling not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            # Simulate git not found
            mock_run.side_effect = FileNotFoundError("git not found")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            # Should allow (fail-open)
            assert result.get("block") is not True

    def test_fail_open_when_subprocess_timeout(self, tmp_path):
        """Test git command timeout → Fail-open with warning.

        If git command takes >5 seconds, timeout and allow operation.

        TDD: WILL FAIL - timeout handling not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            # Simulate timeout
            mock_run.side_effect = subprocess.TimeoutExpired(
                ["git", "branch", "--show-current"], timeout=5
            )

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            # Should allow (fail-open)
            assert result.get("block") is not True

    def test_allow_detached_head_state(self, tmp_path):
        """Test EC3: Detached HEAD state → ALLOWED.

        Detached HEAD is intentionally allowed for legitimate workflows:
        - Cherry-picking
        - Bisecting
        - Reviewing history

        Git returns empty string for detached HEAD.

        TDD: WILL FAIL - detached HEAD handling not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            # Simulate detached HEAD (empty output)
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            # Should allow (empty branch != main/master)
            assert result.get("block") is not True

    def test_fail_open_on_generic_exception(self, tmp_path):
        """Test generic exception → Fail-open.

        Any unexpected error should fail-open.

        TDD: WILL FAIL - exception handling not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            # Simulate unexpected error
            mock_run.side_effect = RuntimeError("Unexpected error")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            # Should allow (fail-open)
            assert result.get("block") is not True


# ============================================================================
# SECURITY TESTS - Subprocess Safety
# ============================================================================


class TestSubprocessSecurity:
    """Security tests for subprocess execution.

    CRITICAL: These tests verify security requirements are met.

    TDD: These tests WILL FAIL until subprocess security is implemented.
    """

    def test_no_shell_injection_vulnerability(self, tmp_path):
        """Test ST-01: Verify no shell=True (command injection protection).

        SECURITY: shell=True allows command injection attacks.

        TDD: WILL FAIL - subprocess call not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            hook.process(input_data)

            # Verify shell=True is NOT used
            call_args = mock_run.call_args
            assert call_args[1].get("shell") is not True

    def test_hardcoded_subprocess_arguments(self, tmp_path):
        """Test ST-02: Verify hardcoded subprocess arguments.

        SECURITY: Never pass user input to subprocess.run().

        TDD: WILL FAIL - subprocess call not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            # Try to inject malicious command via user input
            input_data = {
                "toolUse": {"name": "Bash", "input": {"command": "git commit -m '; rm -rf /'"}}
            }

            hook.process(input_data)

            # Verify subprocess args are hardcoded
            call_args = mock_run.call_args
            command_list = call_args[0][0]

            # Must be exactly ["git", "branch", "--show-current"]
            assert command_list == ["git", "branch", "--show-current"]

            # User input should NOT appear in subprocess args
            assert "rm -rf" not in str(command_list)

    def test_subprocess_timeout_is_set(self, tmp_path):
        """Test ST-03: Verify 5-second timeout is set.

        SECURITY: Prevent hangs from malicious/broken git commands.

        TDD: WILL FAIL - timeout not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            hook.process(input_data)

            # Verify timeout is set
            call_args = mock_run.call_args
            assert call_args[1]["timeout"] == 5

    def test_subprocess_uses_argument_list_not_string(self, tmp_path):
        """Test ST-04: Verify argument list format (not string).

        SECURITY: Argument list prevents shell injection.

        TDD: WILL FAIL - subprocess call not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            hook.process(input_data)

            # Verify first argument is a list, not a string
            call_args = mock_run.call_args
            assert isinstance(call_args[0][0], list)
            assert not isinstance(call_args[0][0], str)

    def test_safe_defaults_for_dict_access(self, tmp_path):
        """Test ST-05: Verify .get() with safe defaults for dict access.

        SECURITY: Prevent KeyError exceptions that could leak information.

        TDD: This should PASS (defensive programming check).
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        # Test with missing keys - should not raise KeyError
        input_data = {}  # Empty input

        try:
            result = hook.process(input_data)
            # Should handle gracefully
            assert result is not None
        except KeyError:
            pytest.fail("Code should use .get() with defaults, not direct dict access")

    def test_branch_name_sanitization(self, tmp_path):
        """Test ST-06: Verify branch name is sanitized (.strip()).

        SECURITY: Prevent whitespace injection attacks.

        TDD: WILL FAIL - branch name sanitization not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            # Simulate malicious whitespace in output
            mock_run.return_value = Mock(
                returncode=0,
                stdout="main\n\n\n",  # Extra newlines
                stderr="",
            )

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            # Should still detect 'main' after stripping
            assert result.get("block") is True

    def test_exact_match_not_regex(self, tmp_path):
        """Test ST-07: Verify exact match (in [...]) not regex.

        SECURITY: Regex can have vulnerabilities (ReDoS).
        Simple exact match is safer.

        TDD: WILL FAIL - branch checking not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            # Test branch name that contains 'main' but isn't 'main'
            mock_run.return_value = Mock(
                returncode=0, stdout="feature/main-improvements\n", stderr=""
            )

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            # Should allow (exact match: branch != 'main')
            assert result.get("block") is not True

    def test_no_command_logging_in_error_messages(self, tmp_path):
        """Test ST-08: Verify no full command logging (may contain secrets).

        SECURITY: Commit messages might contain sensitive data.
        Log metadata only, not full command text.

        TDD: This is a guideline test - validates logging best practices.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        # This test is more of a code review checkpoint
        # Implementation should log metadata (tool name, branch) but not full commands
        # We can't easily test logging without inspecting log output
        # Mark as informational


# ============================================================================
# MESSAGE CONTENT TESTS
# ============================================================================


class TestErrorMessage:
    """Test error message content and formatting.

    TDD: These tests WILL FAIL until error messages are implemented.
    """

    def test_error_message_mentions_branch_name(self, tmp_path):
        """Test error message includes the specific branch name.

        TDD: WILL FAIL - error message not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            message = result.get("message", "")
            assert "main" in message.lower()

    def test_error_message_mentions_feature_branch_workflow(self, tmp_path):
        """Test error message provides actionable guidance.

        TDD: WILL FAIL - error message not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            message = result.get("message", "")
            assert "feature branch" in message.lower()
            assert "git checkout -b" in message.lower()

    def test_error_message_mentions_no_verify_bypass(self, tmp_path):
        """Test error message states protection cannot be bypassed.

        TDD: WILL FAIL - error message not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            message = result.get("message", "")
            assert "--no-verify" in message.lower() or "no-verify" in message.lower()
            assert "cannot be bypassed" in message.lower()

    def test_error_message_has_emoji_for_visibility(self, tmp_path):
        """Test error message includes emoji for visual scanning.

        Consistent with existing error messages in hook.

        TDD: WILL FAIL - error message not yet implemented.
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="main\n", stderr="")

            input_data = {"toolUse": {"name": "Bash", "input": {"command": "git commit -m 'test'"}}}

            result = hook.process(input_data)

            message = result.get("message", "")
            # Should have an emoji (⛔ or similar)
            assert "⛔" in message or "🚫" in message


# ============================================================================
# FILE SYNCHRONIZATION TESTS
# ============================================================================


class TestFileSynchronization:
    """Test that both file copies remain synchronized.

    CRITICAL: Both .claude/tools/amplihack/hooks/pre_tool_use.py
    and amplifier-bundle/tools/amplihack/hooks/pre_tool_use.py
    must be byte-identical.

    TDD: This test will FAIL if files are not synchronized.
    """

    def test_workspace_and_bundle_files_are_identical(self):
        """Test that workspace and bundle copies are byte-identical.

        This is a critical requirement - both files must be updated
        identically in a single commit.

        TDD: WILL FAIL until both files are updated identically.
        """
        workspace_file = Path(".claude/tools/amplihack/hooks/pre_tool_use.py")
        bundle_file = Path("amplifier-bundle/tools/amplihack/hooks/pre_tool_use.py")

        # Both files must exist
        assert workspace_file.exists(), "Workspace file missing"
        assert bundle_file.exists(), "Bundle file missing"

        # Read both files
        workspace_content = workspace_file.read_text()
        bundle_content = bundle_file.read_text()

        # Must be byte-identical
        assert workspace_content == bundle_content, (
            "Files are not identical!\n"
            "workspace: .claude/tools/amplihack/hooks/pre_tool_use.py\n"
            "bundle: amplifier-bundle/tools/amplihack/hooks/pre_tool_use.py\n"
            "\nBoth files must be updated identically."
        )


# ============================================================================
# EXISTING FUNCTIONALITY PRESERVATION TESTS
# ============================================================================


class TestExistingFunctionality:
    """Test that existing --no-verify protection is preserved.

    TDD: These tests should PASS (existing functionality).
    """

    def test_no_verify_protection_still_works(self, tmp_path):
        """Test existing --no-verify blocking is not broken.

        This should PASS (existing functionality).
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="feature/test\n", stderr="")

            input_data = {
                "toolUse": {
                    "name": "Bash",
                    "input": {"command": "git commit --no-verify -m 'test'"},
                }
            }

            result = hook.process(input_data)

            # Should block due to --no-verify
            assert result.get("block") is True

    def test_non_git_commands_still_allowed(self, tmp_path):
        """Test non-git commands are not affected.

        This should PASS (existing functionality).
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        input_data = {"toolUse": {"name": "Bash", "input": {"command": "ls -la"}}}

        result = hook.process(input_data)

        # Should allow
        assert result.get("block") is not True

    def test_non_bash_tools_not_affected(self, tmp_path):
        """Test non-Bash tools are not affected.

        This should PASS (existing functionality).
        """
        hook = PreToolUseHook()
        hook.project_root = tmp_path

        input_data = {"toolUse": {"name": "ReadFile", "input": {"path": "/test/file.txt"}}}

        result = hook.process(input_data)

        # Should allow
        assert result.get("block") is not True


# ============================================================================
# TEST DISCOVERY
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
