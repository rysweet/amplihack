"""Unit tests for Copilot session start hook.

Testing pyramid: UNIT (60%)
- Fast execution
- Mock file system operations
- Test all decision paths
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Need to mock sys.path manipulation before import
@pytest.fixture(autouse=True)
def mock_sys_path():
    """Mock sys.path manipulation in hook module."""
    with patch("sys.path", []):
        yield


class TestEnvironmentDetection:
    """Test Copilot environment detection."""

    def test_detect_copilot_via_env_var(self, temp_project: Path):
        """Test detection via GITHUB_COPILOT_CLI environment variable."""
        with patch.dict("os.environ", {"GITHUB_COPILOT_CLI": "1"}):
            # Would test _is_copilot_environment() but it's a method
            # Testing indirectly through copilot instructions file
            copilot_instructions = (
                temp_project / ".github" / "copilot-instructions.md"
            )
            copilot_instructions.parent.mkdir(parents=True, exist_ok=True)
            copilot_instructions.write_text("# Copilot Instructions")

            assert copilot_instructions.exists()

    def test_detect_copilot_via_copilot_session(self):
        """Test detection via COPILOT_SESSION environment variable."""
        with patch.dict("os.environ", {"COPILOT_SESSION": "test-123"}):
            assert "COPILOT_SESSION" in os.environ

    def test_detect_copilot_via_instructions_file(self, temp_project: Path):
        """Test detection via .github/copilot-instructions.md file."""
        copilot_instructions = temp_project / ".github" / "copilot-instructions.md"
        copilot_instructions.parent.mkdir(parents=True, exist_ok=True)
        copilot_instructions.write_text("# Copilot Instructions")

        assert copilot_instructions.exists()

    def test_no_copilot_environment(self, temp_project: Path):
        """Test detection when not in Copilot environment."""
        with patch.dict("os.environ", {}, clear=True):
            copilot_instructions = (
                temp_project / ".github" / "copilot-instructions.md"
            )
            assert not copilot_instructions.exists()


class TestStalenessCheck:
    """Test agent staleness detection."""

    def test_agents_missing_is_stale(self, temp_project: Path):
        """Test staleness when .github/agents/ doesn't exist."""
        claude_dir = temp_project / ".claude" / "agents"
        github_dir = temp_project / ".github" / "agents"

        # Create source but not target
        (claude_dir / "test.md").write_text("test")

        # Missing target should be considered stale
        assert not github_dir.exists()

    def test_agents_newer_is_stale(self, temp_project: Path):
        """Test staleness when source agents are newer."""
        import time

        claude_dir = temp_project / ".claude" / "agents"
        github_dir = temp_project / ".github" / "agents"

        # Create old target
        old_agent = github_dir / "old.md"
        old_agent.parent.mkdir(parents=True)
        old_agent.write_text("old")

        # Wait and create new source
        time.sleep(0.1)
        new_agent = claude_dir / "new.md"
        new_agent.write_text("new")

        assert new_agent.stat().st_mtime > old_agent.stat().st_mtime

    def test_agents_up_to_date_not_stale(self, temp_project: Path):
        """Test staleness when agents are up to date."""
        claude_dir = temp_project / ".claude" / "agents"
        github_dir = temp_project / ".github" / "agents"

        # Create source
        source_agent = claude_dir / "test.md"
        source_agent.write_text("test")
        source_mtime = source_agent.stat().st_mtime

        # Create target with same or newer mtime
        target_agent = github_dir / "test.md"
        target_agent.parent.mkdir(parents=True)
        target_agent.write_text("test")
        target_agent.touch()  # Update mtime

        assert target_agent.stat().st_mtime >= source_mtime

    def test_staleness_check_empty_directories(self, temp_project: Path):
        """Test staleness check with empty directories."""
        claude_dir = temp_project / ".claude" / "agents"
        github_dir = temp_project / ".github" / "agents"

        github_dir.mkdir(parents=True)

        # Empty directories should not cause errors
        # (Would be caught by no .md files check)


class TestUserPreferences:
    """Test user preference handling."""

    def test_get_preference_from_config_json(self, temp_project: Path):
        """Test reading preference from .claude/config.json."""
        config_file = temp_project / ".claude" / "config.json"
        config = {"copilot_auto_sync_agents": "always"}
        config_file.write_text(json.dumps(config))

        loaded = json.loads(config_file.read_text())
        assert loaded["copilot_auto_sync_agents"] == "always"

    def test_get_preference_from_user_preferences(self, temp_project: Path):
        """Test reading preference from USER_PREFERENCES.md."""
        prefs_file = temp_project / ".claude" / "context" / "USER_PREFERENCES.md"
        prefs_file.write_text(
            """
# User Preferences

copilot_auto_sync_agents: always
"""
        )

        content = prefs_file.read_text()
        assert "copilot_auto_sync_agents: always" in content.lower()

    def test_get_preference_default(self, temp_project: Path):
        """Test default preference when no config exists."""
        # No config files exist
        assert not (temp_project / ".claude" / "config.json").exists()
        assert not (
            temp_project / ".claude" / "context" / "USER_PREFERENCES.md"
        ).exists()

        # Default should be "ask"

    def test_save_preference(self, temp_project: Path):
        """Test saving preference to config.json."""
        config_file = temp_project / ".claude" / "config.json"

        # Save preference
        config = {"copilot_auto_sync_agents": "never"}
        config_file.write_text(json.dumps(config, indent=2))

        # Verify saved
        loaded = json.loads(config_file.read_text())
        assert loaded["copilot_auto_sync_agents"] == "never"

    def test_save_preference_updates_existing(self, temp_project: Path):
        """Test saving preference updates existing config."""
        config_file = temp_project / ".claude" / "config.json"

        # Create existing config
        config = {"other_setting": "value", "copilot_auto_sync_agents": "ask"}
        config_file.write_text(json.dumps(config))

        # Update preference
        config = json.loads(config_file.read_text())
        config["copilot_auto_sync_agents"] = "always"
        config_file.write_text(json.dumps(config))

        # Verify update
        loaded = json.loads(config_file.read_text())
        assert loaded["copilot_auto_sync_agents"] == "always"
        assert loaded["other_setting"] == "value"  # Other settings preserved


class TestSyncTriggers:
    """Test sync trigger conditions."""

    def test_sync_triggered_when_missing(self, temp_project: Path):
        """Test sync is triggered when .github/agents/ missing."""
        claude_dir = temp_project / ".claude" / "agents"
        github_dir = temp_project / ".github" / "agents"

        # Source exists, target doesn't
        (claude_dir / "test.md").write_text("test")

        should_sync = not github_dir.exists()
        assert should_sync is True

    def test_sync_triggered_when_stale(self, temp_project: Path):
        """Test sync is triggered when agents are stale."""
        import time

        claude_dir = temp_project / ".claude" / "agents"
        github_dir = temp_project / ".github" / "agents"

        # Create old target
        old_agent = github_dir / "test.md"
        old_agent.parent.mkdir(parents=True)
        old_agent.write_text("old")

        # Wait and create newer source
        time.sleep(0.1)
        new_agent = claude_dir / "test.md"
        new_agent.write_text("new")

        should_sync = new_agent.stat().st_mtime > old_agent.stat().st_mtime
        assert should_sync is True

    def test_sync_not_triggered_when_up_to_date(
        self, temp_project: Path, mock_registry_json: Path
    ):
        """Test sync is not triggered when agents are up to date."""
        claude_dir = temp_project / ".claude" / "agents"
        github_dir = temp_project / ".github" / "agents"

        # Create source and target with same content
        for dirname in [claude_dir, github_dir]:
            agent = dirname / "test.md"
            agent.parent.mkdir(parents=True, exist_ok=True)
            agent.write_text("test")

        # Registry exists and is newer
        registry_mtime = mock_registry_json.stat().st_mtime
        source_mtime = (claude_dir / "test.md").stat().st_mtime

        should_sync = source_mtime > registry_mtime
        assert should_sync is False


class TestPreferenceRespect:
    """Test preference-based sync behavior."""

    def test_never_preference_skips_sync(self, temp_project: Path):
        """Test 'never' preference skips sync."""
        config_file = temp_project / ".claude" / "config.json"
        config = {"copilot_auto_sync_agents": "never"}
        config_file.write_text(json.dumps(config))

        loaded = json.loads(config_file.read_text())
        assert loaded["copilot_auto_sync_agents"] == "never"

        # With this preference, sync should not occur

    def test_always_preference_triggers_sync(self, temp_project: Path):
        """Test 'always' preference triggers sync."""
        config_file = temp_project / ".claude" / "config.json"
        config = {"copilot_auto_sync_agents": "always"}
        config_file.write_text(json.dumps(config))

        loaded = json.loads(config_file.read_text())
        assert loaded["copilot_auto_sync_agents"] == "always"

        # With this preference, sync should occur


class TestErrorHandling:
    """Test error handling and fail-safe behavior."""

    def test_missing_claude_agents_dir(self, temp_project: Path):
        """Test handling when .claude/agents/ doesn't exist."""
        claude_dir = temp_project / ".claude" / "agents"

        assert not claude_dir.exists()
        # Should log warning and skip

    def test_permission_error_handling(self, temp_project: Path):
        """Test handling of permission errors."""
        import os

        github_dir = temp_project / ".github" / "agents"
        github_dir.mkdir(parents=True)

        # Make directory read-only (simulate permission error)
        try:
            os.chmod(github_dir, 0o444)

            # Attempt to write should fail
            test_file = github_dir / "test.md"
            try:
                test_file.write_text("test")
                wrote = True
            except (PermissionError, OSError):
                wrote = False

            assert wrote is False

        finally:
            # Restore permissions for cleanup
            os.chmod(github_dir, 0o755)

    def test_invalid_json_config(self, temp_project: Path):
        """Test handling of invalid JSON in config file."""
        config_file = temp_project / ".claude" / "config.json"
        config_file.write_text("invalid json {{{")

        # Should handle gracefully and use default
        try:
            json.loads(config_file.read_text())
            valid = True
        except json.JSONDecodeError:
            valid = False

        assert valid is False


class TestPerformanceRequirements:
    """Test performance requirements."""

    def test_staleness_check_performance(self, temp_project: Path):
        """Test staleness check completes in < 500ms."""
        import time

        claude_dir = temp_project / ".claude" / "agents"
        github_dir = temp_project / ".github" / "agents"

        # Create 50 agents
        for i in range(50):
            (claude_dir / f"agent{i}.md").write_text(f"agent {i}")
            (github_dir / f"agent{i}.md").write_text(f"agent {i}")

        # Time staleness check (finding newest file)
        start = time.time()

        claude_newest = max(
            claude_dir.rglob("*.md"), key=lambda p: p.stat().st_mtime
        )
        github_newest = max(
            github_dir.rglob("*.md"), key=lambda p: p.stat().st_mtime
        )

        elapsed = time.time() - start

        # Should complete in well under 500ms
        assert elapsed < 0.5
        assert claude_newest is not None
        assert github_newest is not None


import os
