#!/usr/bin/env python3
"""
Integration tests for pre-push quality gate.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Add .claude to path
claude_dir = Path(__file__).parent.parent.parent.parent / ".claude"
sys.path.insert(0, str(claude_dir))


class TestPrePushIntegration:
    """Integration tests for the full pre-push workflow."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test_repo"
            repo_path.mkdir()

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
            )

            # Create initial commit
            readme = repo_path / "README.md"
            readme.write_text("# Test Repo\n")
            subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=repo_path,
                check=True,
            )

            yield repo_path

    @pytest.fixture
    def project_root(self):
        """Get the actual project root."""
        # Find project root by looking for .claude directory
        current = Path(__file__).resolve()
        for _ in range(10):
            if (current / ".claude").exists():
                return current
            if current == current.parent:
                break
            current = current.parent

        pytest.skip("Could not find project root")

    def test_quality_checker_with_clean_files(self, project_root):
        """Test quality checker with clean Python files."""
        from tools.amplihack.hooks.quality_checker import QualityChecker

        checker = QualityChecker(project_root)

        # Create a clean test file
        test_file = project_root / "test_clean.py"
        test_file.write_text("def hello():\n    return 'world'\n")

        try:
            results = checker.check_files(["test_clean.py"])

            # All checks should pass
            assert all(result.success for result in results)

            # No violations expected (though some checkers might not be installed)
            violations = checker.aggregate_violations(results)
            # We can't guarantee zero violations without all tools installed,
            # but we can check the structure works
            assert isinstance(violations, list)

        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()

    def test_quality_checker_with_violations(self, project_root):
        """Test quality checker detects violations."""
        from tools.amplihack.hooks.quality_checker import QualityChecker

        checker = QualityChecker(project_root)

        # Create a file with obvious violations
        test_file = project_root / "test_violations.py"
        test_file.write_text(
            "def hello():  \n"  # Trailing whitespace
            "<<<<<<< HEAD\n"  # Merge conflict marker
            "    return 'world'\n"
            "=======\n"
            "    return 'universe'\n"
            ">>>>>>> feature\n"
        )

        try:
            results = checker.check_files(["test_violations.py"])

            # Get all violations
            violations = checker.aggregate_violations(results)

            # Should detect whitespace and merge conflict violations
            assert len(violations) > 0

            # Check violation types
            violation_types = [v.type.value for v in violations]
            assert "whitespace" in violation_types
            assert "merge_conflict" in violation_types

        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()

    def test_quality_checker_parallel_execution(self, project_root):
        """Test that checkers run in parallel."""
        import time

        from tools.amplihack.hooks.quality_checker import QualityChecker

        checker = QualityChecker(project_root)

        # Create multiple test files
        test_files = []
        for i in range(3):
            test_file = project_root / f"test_parallel_{i}.py"
            test_file.write_text(f"def func_{i}():\n    return {i}\n")
            test_files.append(f"test_parallel_{i}.py")

        try:
            start_time = time.time()
            results = checker.check_files(test_files)
            elapsed = time.time() - start_time

            # Should complete reasonably quickly (parallel execution)
            # Even with 6 checkers on 3 files, should be under 10 seconds
            assert elapsed < 10.0

            # Should have results from all checkers
            assert len(results) == 6  # 6 checkers total

            # All should succeed (though some might not be installed)
            assert all(result.success or result.error_message for result in results)

        finally:
            # Cleanup
            for test_file_name in test_files:
                test_file = project_root / test_file_name
                if test_file.exists():
                    test_file.unlink()

    def test_emergency_override_detection(self, project_root):
        """Test FORCE_PUSH_UNVERIFIED override detection."""
        from tools.amplihack.hooks.pre_push import PrePushHook

        hook = PrePushHook()

        # Test without override
        os.environ.pop("FORCE_PUSH_UNVERIFIED", None)
        assert hook.check_emergency_override() is False

        # Test with override
        os.environ["FORCE_PUSH_UNVERIFIED"] = "1"
        assert hook.check_emergency_override() is True

        # Cleanup
        os.environ.pop("FORCE_PUSH_UNVERIFIED", None)

    def test_violation_report_formatting(self, project_root):
        """Test that violation reports are formatted correctly."""
        from tools.amplihack.hooks.check_runners.whitespace_checker import (
            WhitespaceChecker,
        )
        from tools.amplihack.hooks.quality_checker import QualityChecker

        checker = QualityChecker(project_root)

        # Create a file with violations
        test_file = project_root / "test_report.py"
        test_file.write_text("def foo():  \n    pass\n")

        try:
            # Run whitespace checker directly
            ws_checker = WhitespaceChecker(project_root)
            result = ws_checker.check(["test_report.py"])

            # Format report
            report = checker.format_violations_report([result])

            # Check report structure
            assert "QUALITY CHECK FAILURES" in report
            assert "test_report.py" in report
            assert "TO PROCEED" in report
            assert "FORCE_PUSH_UNVERIFIED=1" in report

        finally:
            if test_file.exists():
                test_file.unlink()


class TestPrePushHookScript:
    """Test the actual pre-push hook script."""

    @pytest.fixture
    def project_root(self):
        """Get the actual project root."""
        current = Path(__file__).resolve()
        for _ in range(10):
            if (current / ".claude").exists():
                return current
            if current == current.parent:
                break
            current = current.parent

        pytest.skip("Could not find project root")

    def test_hook_script_exists(self, project_root):
        """Test that pre-push hook script exists."""
        hook_script = project_root / ".claude" / "tools" / "amplihack" / "hooks" / "pre_push.py"

        assert hook_script.exists()
        assert hook_script.is_file()

        # Check that it's executable or can be run with python
        content = hook_script.read_text()
        assert "#!/usr/bin/env python3" in content
        assert "class PrePushHook" in content

    def test_git_hook_wrapper_exists(self, project_root):
        """Test that Git hook wrapper exists."""
        # Look for git directory
        git_dir = project_root / ".git"

        if not git_dir.exists():
            pytest.skip("Not in a git repository")

        hook_wrapper = git_dir / "hooks" / "pre-push"

        assert hook_wrapper.exists()
        assert hook_wrapper.is_file()

        # Check executable permissions
        assert os.access(hook_wrapper, os.X_OK)

        # Check content
        content = hook_wrapper.read_text()
        assert "#!/usr/bin/env bash" in content
        assert "pre_push.py" in content


class TestPrePushFailClosed:
    """Test fail-closed behavior of pre-push hook."""

    @pytest.fixture
    def project_root(self):
        """Get the actual project root."""
        current = Path(__file__).resolve()
        for _ in range(10):
            if (current / ".claude").exists():
                return current
            if current == current.parent:
                break
            current = current.parent

        pytest.skip("Could not find project root")

    def test_non_blocking_errors_allow_push(self, project_root):
        """Test that non-blocking errors (timeout, file not found) allow push."""
        import subprocess
        from io import StringIO
        from unittest.mock import patch

        from tools.amplihack.hooks.pre_push import PrePushHook

        hook = PrePushHook()

        # Test TimeoutExpired
        with patch.object(hook, "read_push_refs", return_value=[("refs/heads/test", "abc123", "refs/heads/test", "def456")]):
            with patch.object(hook.quality_checker, "check_commits", side_effect=subprocess.TimeoutExpired("test", 30)):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    result = hook.process({})
                    assert result == {}
                    assert "⚠️" in mock_stderr.getvalue()
                    assert "non-critical" in mock_stderr.getvalue()

        # Test FileNotFoundError
        with patch.object(hook, "read_push_refs", return_value=[("refs/heads/test", "abc123", "refs/heads/test", "def456")]):
            with patch.object(hook.quality_checker, "check_commits", side_effect=FileNotFoundError("checker not found")):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    result = hook.process({})
                    assert result == {}
                    assert "⚠️" in mock_stderr.getvalue()

    def test_unexpected_errors_block_push(self, project_root):
        """Test that unexpected errors block push (fail-closed)."""
        from io import StringIO
        from unittest.mock import patch

        from tools.amplihack.hooks.pre_push import PrePushHook

        hook = PrePushHook()

        # Test ValueError (unexpected error)
        with patch.object(hook, "read_push_refs", return_value=[("refs/heads/test", "abc123", "refs/heads/test", "def456")]):
            with patch.object(hook.quality_checker, "check_commits", side_effect=ValueError("unexpected")):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    with pytest.raises(SystemExit) as exc_info:
                        hook.process({})

                    assert exc_info.value.code == 1
                    assert "❌" in mock_stderr.getvalue()
                    assert "Blocking push for safety" in mock_stderr.getvalue()

    def test_logic_errors_block_push(self, project_root):
        """Test that logic errors (AttributeError, KeyError, etc.) block push."""
        from io import StringIO
        from unittest.mock import patch

        from tools.amplihack.hooks.pre_push import PrePushHook

        hook = PrePushHook()

        # Test AttributeError (logic bug)
        with patch.object(hook, "read_push_refs", return_value=[("refs/heads/test", "abc123", "refs/heads/test", "def456")]):
            with patch.object(hook.quality_checker, "check_commits", side_effect=AttributeError("missing attr")):
                with patch("sys.stderr", new_callable=StringIO):
                    with pytest.raises(SystemExit) as exc_info:
                        hook.process({})

                    assert exc_info.value.code == 1

        # Test KeyError (logic bug)
        with patch.object(hook, "read_push_refs", return_value=[("refs/heads/test", "abc123", "refs/heads/test", "def456")]):
            with patch.object(hook.quality_checker, "check_commits", side_effect=KeyError("missing key")):
                with patch("sys.stderr", new_callable=StringIO):
                    with pytest.raises(SystemExit) as exc_info:
                        hook.process({})

                    assert exc_info.value.code == 1

    @pytest.mark.skip(reason="KeyboardInterrupt propagates through pytest")
    def test_keyboard_interrupt_blocks_push(self, project_root):
        """Test that KeyboardInterrupt blocks push (security)."""
        # Note: KeyboardInterrupt is caught by Exception handler in fail-closed mode
        # This test is skipped because it interferes with pytest
        pass

    def test_emergency_override_still_works(self, project_root):
        """Test that FORCE_PUSH_UNVERIFIED=1 bypasses fail-closed behavior."""
        from io import StringIO
        from unittest.mock import patch

        from tools.amplihack.hooks.pre_push import PrePushHook

        hook = PrePushHook()

        with patch.object(hook, "check_emergency_override", return_value=True):
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                result = hook.process({})
                assert result == {}
                assert "Quality checks bypassed" in mock_stderr.getvalue()
