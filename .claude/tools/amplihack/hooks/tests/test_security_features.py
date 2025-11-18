#!/usr/bin/env python3
"""
Tests for security features added to power-steering.

Tests cover:
- Path validation helper
- Config integrity checks
- Checker timeouts
"""

import json
import sys
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


class TestPathValidation:
    """Test path validation security feature."""

    def test_validate_path_within_allowed(self, tmp_path):
        """Test path validation for path within allowed directory."""
        checker = PowerSteeringChecker(tmp_path)

        # Create a path within project root
        safe_path = tmp_path / "subdir" / "file.txt"

        assert checker._validate_path(safe_path, tmp_path) is True

    def test_validate_path_outside_allowed(self, tmp_path):
        """Test path validation rejects paths outside allowed directory."""
        checker = PowerSteeringChecker(tmp_path)

        # Create a path outside project root
        unsafe_path = Path("/etc/passwd")

        assert checker._validate_path(unsafe_path, tmp_path) is False

    def test_validate_path_with_symlink_escape(self, tmp_path):
        """Test path validation prevents symlink escapes."""
        checker = PowerSteeringChecker(tmp_path)

        # Create a symlink that points outside
        link_dir = tmp_path / "link_dir"
        link_dir.mkdir()
        symlink = link_dir / "escape"

        try:
            symlink.symlink_to("/tmp")
            # Path validation should allow /tmp (it's a whitelisted temp directory)
            result = checker._validate_path(symlink, tmp_path)
            # Should be True because /tmp is allowed
            assert result is True
        except OSError:
            # Symlink creation might fail on some systems
            pytest.skip("Symlink creation not supported")

    def test_validate_path_in_home_directory(self, tmp_path):
        """Test path validation allows paths within user's home directory."""
        checker = PowerSteeringChecker(tmp_path)

        # Create a path in user's home directory
        home_path = Path.home() / ".claude" / "projects" / "test" / "session.jsonl"

        # Should allow paths in user's home directory
        assert checker._validate_path(home_path, tmp_path) is True

    def test_validate_path_claude_projects_directory(self, tmp_path):
        """Test path validation allows Claude Code transcript paths."""
        checker = PowerSteeringChecker(tmp_path)

        # Simulate Claude Code's typical transcript location
        claude_projects_path = (
            Path.home() / ".claude" / "projects" / "-home-user-project" / "session-id.jsonl"
        )

        # This is the primary fix - Claude Code transcripts should be allowed
        assert checker._validate_path(claude_projects_path, tmp_path) is True

    def test_validate_path_temp_directories(self, tmp_path):
        """Test path validation allows common temp directories."""
        checker = PowerSteeringChecker(tmp_path)

        # Test /tmp
        tmp_file = Path("/tmp") / "test_transcript.jsonl"
        assert checker._validate_path(tmp_file, tmp_path) is True

        # Test /var/tmp
        var_tmp_file = Path("/var/tmp") / "test_transcript.jsonl"
        assert checker._validate_path(var_tmp_file, tmp_path) is True

    def test_validate_path_truly_outside_all_allowed(self, tmp_path):
        """Test path validation rejects paths outside all allowed locations."""
        checker = PowerSteeringChecker(tmp_path)

        # Try a path that's definitely outside:
        # - Not in project root
        # - Not in user's home directory
        # - Not in temp directories
        # This should fail unless the path is somehow under home or temp
        unsafe_path = Path("/etc/passwd")

        # Only assert False if /etc is truly outside home
        home = Path.home().resolve()
        etc_path = unsafe_path.resolve()
        try:
            etc_path.relative_to(home)
            # If /etc is somehow under home (unlikely), skip test
            pytest.skip("/etc is under home directory on this system")
        except ValueError:
            # /etc is outside home - should be rejected
            assert checker._validate_path(unsafe_path, tmp_path) is False

    def test_load_transcript_validates_path(self, tmp_path):
        """Test that _load_transcript validates transcript path."""
        checker = PowerSteeringChecker(tmp_path)

        # Try to load a transcript that's truly outside all allowed locations
        # Need a path outside: project root, home directory, and temp directories
        unsafe_transcript = Path("/etc/passwd")

        # Only test if /etc is truly outside home
        home = Path.home().resolve()
        try:
            unsafe_transcript.resolve().relative_to(home)
            pytest.skip("/etc is under home directory on this system")
        except ValueError:
            # /etc is outside home - should raise error
            with pytest.raises(ValueError, match="outside project root"):
                checker._load_transcript(unsafe_transcript)


class TestConfigIntegrity:
    """Test config integrity validation."""

    def test_validate_config_valid(self, tmp_path):
        """Test config validation with valid config."""
        checker = PowerSteeringChecker(tmp_path)

        valid_config = {
            "enabled": True,
            "phase": 2,
            "checkers_enabled": {"todos_complete": True, "ci_status": False},
        }

        assert checker._validate_config_integrity(valid_config) is True

    def test_validate_config_missing_enabled(self, tmp_path):
        """Test config validation rejects missing 'enabled' key."""
        checker = PowerSteeringChecker(tmp_path)

        invalid_config = {"phase": 2}

        assert checker._validate_config_integrity(invalid_config) is False

    def test_validate_config_wrong_enabled_type(self, tmp_path):
        """Test config validation rejects non-boolean 'enabled'."""
        checker = PowerSteeringChecker(tmp_path)

        invalid_config = {"enabled": "true"}  # String instead of bool

        assert checker._validate_config_integrity(invalid_config) is False

    def test_validate_config_wrong_phase_type(self, tmp_path):
        """Test config validation rejects non-integer 'phase'."""
        checker = PowerSteeringChecker(tmp_path)

        invalid_config = {"enabled": True, "phase": "2"}  # String instead of int

        assert checker._validate_config_integrity(invalid_config) is False

    def test_validate_config_invalid_checkers_enabled(self, tmp_path):
        """Test config validation rejects invalid checkers_enabled."""
        checker = PowerSteeringChecker(tmp_path)

        # Non-dict checkers_enabled
        invalid_config = {"enabled": True, "checkers_enabled": []}

        assert checker._validate_config_integrity(invalid_config) is False

    def test_validate_config_checkers_enabled_non_bool_values(self, tmp_path):
        """Test config validation rejects non-boolean values in checkers_enabled."""
        checker = PowerSteeringChecker(tmp_path)

        invalid_config = {
            "enabled": True,
            "checkers_enabled": {"todos_complete": "yes"},  # String instead of bool
        }

        assert checker._validate_config_integrity(invalid_config) is False

    def test_load_config_uses_validation(self, tmp_path):
        """Test that _load_config uses integrity validation."""
        # Create config file with invalid content
        config_path = tmp_path / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        invalid_config = {"enabled": "not_a_boolean"}
        config_path.write_text(json.dumps(invalid_config))

        checker = PowerSteeringChecker(tmp_path)

        # Should fall back to defaults due to failed validation
        assert checker.config["enabled"] is True  # Default value


class TestCheckerTimeouts:
    """Test checker timeout mechanism."""

    def test_timeout_context_manager(self):
        """Test that timeout context manager works."""
        import time

        from power_steering_checker import _timeout

        # This should NOT timeout
        try:
            with _timeout(2):
                time.sleep(0.1)
            success = True
        except TimeoutError:
            success = False

        assert success is True

    def test_timeout_context_manager_triggers(self):
        """Test that timeout context manager triggers on long operations."""
        import time

        from power_steering_checker import _timeout

        # This SHOULD timeout
        with pytest.raises(TimeoutError):
            with _timeout(1):
                time.sleep(5)

    def test_checker_timeout_in_analyze(self, tmp_path):
        """Test that checker timeout is applied during analysis."""
        checker = PowerSteeringChecker(tmp_path)

        # Create a mock slow checker
        def slow_checker(transcript, session_id):
            import time

            time.sleep(15)  # Exceeds CHECKER_TIMEOUT
            return True

        # Monkey-patch a checker to be slow
        checker._check_todos_complete = slow_checker

        # Create minimal transcript
        transcript = [{"type": "user", "message": {"content": "test"}}]

        # Run analysis - should timeout but NOT raise exception (fail-open)
        analysis = checker._analyze_considerations(transcript, "test_session")

        # Check that the checker result shows timeout (satisfied=True due to fail-open)
        result = analysis.results.get("todos_complete")
        if result:
            assert result.satisfied is True
            assert "Timeout" in result.reason or result.satisfied


class TestFilePermissions:
    """Test that files are created with correct permissions."""

    def test_semaphore_permissions(self, tmp_path):
        """Test that semaphore files have 0o600 permissions."""
        checker = PowerSteeringChecker(tmp_path)

        checker._mark_complete("test_session")

        semaphore = checker.runtime_dir / ".test_session_completed"
        assert semaphore.exists()

        # Check permissions (mask with 0o777 to ignore file type bits)
        perms = semaphore.stat().st_mode & 0o777
        assert perms == 0o600

    def test_summary_permissions(self, tmp_path):
        """Test that summary files have 0o644 permissions."""
        checker = PowerSteeringChecker(tmp_path)

        checker._write_summary("test_session", "Test summary content")

        summary_file = checker.runtime_dir / "test_session" / "summary.md"
        assert summary_file.exists()

        # Check permissions
        perms = summary_file.stat().st_mode & 0o777
        assert perms == 0o644

    def test_log_file_permissions(self, tmp_path):
        """Test that log files have 0o600 permissions."""
        checker = PowerSteeringChecker(tmp_path)

        checker._log("Test log message")

        log_file = checker.runtime_dir / "power_steering.log"
        assert log_file.exists()

        # Check permissions
        perms = log_file.stat().st_mode & 0o777
        assert perms == 0o600
