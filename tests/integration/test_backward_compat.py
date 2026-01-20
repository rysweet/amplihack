"""Integration tests for backward compatibility - TDD approach.

Tests dual-mode support for per-project .claude/ vs plugin installation.

Expected behavior:
- Detect local .claude/ directory in project
- Detect plugin .claude/ directory at ~/.amplihack/.claude/
- Prefer LOCAL over PLUGIN when both exist
- Provide migration helpers
- Support both modes simultaneously

These tests are written BEFORE implementation (TDD).
All tests should FAIL initially.
"""

import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import will fail until implementation exists
try:
    from amplihack.launcher import detect_claude_directory, ModeDetector
    from amplihack.migration import MigrationHelper
except ImportError:
    detect_claude_directory = None
    ModeDetector = None
    MigrationHelper = None


class TestClaudeDirectoryDetection:
    """Test detection of .claude directory (project vs plugin)."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create temporary project directory."""
        project = tmp_path / "test-project"
        project.mkdir()
        return project

    @pytest.fixture
    def local_claude_dir(self, project_dir):
        """Create local .claude directory in project."""
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()
        (claude_dir / "context").mkdir()
        (claude_dir / "context" / "PHILOSOPHY.md").write_text("# Philosophy")
        return claude_dir

    @pytest.fixture
    def plugin_claude_dir(self, tmp_path):
        """Create plugin .claude directory at ~/.amplihack/.claude/."""
        plugin_dir = tmp_path / ".amplihack" / ".claude"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "context").mkdir()
        (plugin_dir / "context" / "PHILOSOPHY.md").write_text("# Philosophy")
        return plugin_dir

    def test_detect_local_directory_only(self, project_dir, local_claude_dir):
        """Test detection when only local .claude exists."""
        # Arrange
        os.chdir(project_dir)

        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path("/nonexistent")

            # Act
            detected = detect_claude_directory()

            # Assert
            assert detected is not None
            assert detected == local_claude_dir
            assert "project" in str(detected).lower() or detected.name == ".claude"

    def test_detect_plugin_directory_only(self, project_dir, plugin_claude_dir):
        """Test detection when only plugin .claude exists."""
        # Arrange
        os.chdir(project_dir)

        with patch('pathlib.Path.home', return_value=plugin_claude_dir.parent.parent):
            # Act
            detected = detect_claude_directory()

            # Assert
            assert detected is not None
            assert detected == plugin_claude_dir

    def test_prefer_local_over_plugin(self, project_dir, local_claude_dir, plugin_claude_dir):
        """Test local directory is preferred when both exist (CRITICAL)."""
        # Arrange
        os.chdir(project_dir)

        with patch('pathlib.Path.home', return_value=plugin_claude_dir.parent.parent):
            # Act
            detected = detect_claude_directory()

            # Assert - LOCAL must take precedence
            assert detected == local_claude_dir, \
                "Local .claude must take precedence over plugin when both exist"

    def test_returns_none_when_neither_exists(self, project_dir):
        """Test returns None when no .claude directory found."""
        # Arrange
        os.chdir(project_dir)

        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path("/nonexistent")

            # Act
            detected = detect_claude_directory()

            # Assert
            assert detected is None

    def test_detection_prints_mode_message(self, project_dir, local_claude_dir, capsys):
        """Test detection prints message about which mode is used."""
        # Arrange
        os.chdir(project_dir)

        with patch('pathlib.Path.home', return_value=Path("/nonexistent")):
            # Act
            detect_claude_directory()
            captured = capsys.readouterr()

            # Assert
            assert "project" in captured.out.lower() or "local" in captured.out.lower()


class TestModeDetector:
    """Test mode detection logic."""

    def test_detect_returns_local_mode(self, tmp_path):
        """Test mode detector returns LOCAL when project has .claude."""
        # Arrange
        detector = ModeDetector()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".claude").mkdir()

        # Act
        mode = detector.detect(project_dir)

        # Assert
        assert mode == "LOCAL"

    def test_detect_returns_plugin_mode(self, tmp_path):
        """Test mode detector returns PLUGIN when using ~/.amplihack."""
        # Arrange
        detector = ModeDetector()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch('pathlib.Path.home') as mock_home:
            home = tmp_path / "home"
            home.mkdir()
            (home / ".amplihack" / ".claude").mkdir(parents=True)
            mock_home.return_value = home

            # Act
            mode = detector.detect(project_dir)

            # Assert
            assert mode == "PLUGIN"

    def test_detect_returns_none_when_neither(self, tmp_path):
        """Test mode detector returns None when no .claude found."""
        # Arrange
        detector = ModeDetector()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch('pathlib.Path.home', return_value=Path("/nonexistent")):
            # Act
            mode = detector.detect(project_dir)

            # Assert
            assert mode is None

    def test_detect_returns_dual_when_both_exist(self, tmp_path):
        """Test mode detector identifies DUAL mode when both exist."""
        # Arrange
        detector = ModeDetector()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".claude").mkdir()

        with patch('pathlib.Path.home') as mock_home:
            home = tmp_path / "home"
            home.mkdir()
            (home / ".amplihack" / ".claude").mkdir(parents=True)
            mock_home.return_value = home

            # Act
            mode = detector.detect(project_dir)

            # Assert
            # Should detect both exist (even if LOCAL takes precedence)
            assert mode == "DUAL" or mode == "LOCAL"


class TestPrecedenceRules:
    """Test precedence rules for LOCAL vs PLUGIN."""

    def test_local_context_files_override_plugin(self, tmp_path):
        """Test local context files take precedence over plugin."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create local context
        local_claude = project_dir / ".claude"
        local_claude.mkdir()
        local_context = local_claude / "context"
        local_context.mkdir()
        (local_context / "PHILOSOPHY.md").write_text("# Local Philosophy")

        # Create plugin context
        with patch('pathlib.Path.home') as mock_home:
            home = tmp_path / "home"
            home.mkdir()
            plugin_claude = home / ".amplihack" / ".claude"
            plugin_claude.mkdir(parents=True)
            plugin_context = plugin_claude / "context"
            plugin_context.mkdir()
            (plugin_context / "PHILOSOPHY.md").write_text("# Plugin Philosophy")
            mock_home.return_value = home

            # Act
            os.chdir(project_dir)
            detected = detect_claude_directory()
            philosophy_path = detected / "context" / "PHILOSOPHY.md"
            content = philosophy_path.read_text()

            # Assert
            assert "Local Philosophy" in content
            assert "Plugin Philosophy" not in content

    def test_local_hooks_override_plugin(self, tmp_path):
        """Test local hooks take precedence over plugin hooks."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create local hooks
        local_claude = project_dir / ".claude"
        (local_claude / "tools" / "amplihack" / "hooks").mkdir(parents=True)
        hooks_json = local_claude / "tools" / "amplihack" / "hooks" / "hooks.json"
        hooks_json.write_text(json.dumps({"source": "local"}))

        # Create plugin hooks
        with patch('pathlib.Path.home') as mock_home:
            home = tmp_path / "home"
            plugin_claude = home / ".amplihack" / ".claude"
            (plugin_claude / "tools" / "amplihack" / "hooks").mkdir(parents=True)
            plugin_hooks_json = plugin_claude / "tools" / "amplihack" / "hooks" / "hooks.json"
            plugin_hooks_json.write_text(json.dumps({"source": "plugin"}))
            mock_home.return_value = home

            # Act
            os.chdir(project_dir)
            detected = detect_claude_directory()
            hooks_path = detected / "tools" / "amplihack" / "hooks" / "hooks.json"
            config = json.loads(hooks_path.read_text())

            # Assert
            assert config["source"] == "local"


class TestMigrationHelper:
    """Test migration from per-project to plugin."""

    def test_detect_eligible_for_migration(self, tmp_path):
        """Test detection of projects eligible for migration."""
        # Arrange
        helper = MigrationHelper()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".claude").mkdir()

        # Act
        eligible = helper.is_eligible_for_migration(project_dir)

        # Assert
        assert eligible is True

    def test_not_eligible_without_local_claude(self, tmp_path):
        """Test project without .claude is not eligible."""
        # Arrange
        helper = MigrationHelper()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Act
        eligible = helper.is_eligible_for_migration(project_dir)

        # Assert
        assert eligible is False

    def test_migration_creates_plugin_directory(self, tmp_path):
        """Test migration creates ~/.amplihack/.claude/ directory."""
        # Arrange
        helper = MigrationHelper()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".claude").mkdir()

        with patch('pathlib.Path.home') as mock_home:
            home = tmp_path / "home"
            home.mkdir()
            mock_home.return_value = home

            # Act
            result = helper.migrate_to_plugin(project_dir)

            # Assert
            assert result.success is True
            plugin_dir = home / ".amplihack" / ".claude"
            assert plugin_dir.exists()

    def test_migration_preserves_local_customizations(self, tmp_path):
        """Test migration preserves project-specific customizations."""
        # Arrange
        helper = MigrationHelper()
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create local .claude with custom content
        local_claude = project_dir / ".claude"
        local_claude.mkdir()
        (local_claude / "context").mkdir()
        (local_claude / "context" / "PROJECT.md").write_text("# Custom Project")

        with patch('pathlib.Path.home') as mock_home:
            home = tmp_path / "home"
            home.mkdir()
            mock_home.return_value = home

            # Act
            result = helper.migrate_to_plugin(project_dir, preserve_local=True)

            # Assert
            # Local customizations should remain
            assert (local_claude / "context" / "PROJECT.md").exists()
            # Plugin should also be installed
            plugin_dir = home / ".amplihack" / ".claude"
            assert plugin_dir.exists()

    def test_migration_offers_remove_local_option(self, tmp_path):
        """Test migration can optionally remove local .claude."""
        # Arrange
        helper = MigrationHelper()
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        local_claude = project_dir / ".claude"
        local_claude.mkdir()

        with patch('pathlib.Path.home') as mock_home:
            home = tmp_path / "home"
            home.mkdir()
            mock_home.return_value = home

            # Act
            result = helper.migrate_to_plugin(project_dir, remove_local=True)

            # Assert
            assert result.success is True
            assert not local_claude.exists()


class TestDualModeScenarios:
    """Test scenarios where both LOCAL and PLUGIN exist."""

    def test_dual_mode_warning_printed(self, tmp_path, capsys):
        """Test warning printed when both directories exist."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".claude").mkdir()

        with patch('pathlib.Path.home') as mock_home:
            home = tmp_path / "home"
            (home / ".amplihack" / ".claude").mkdir(parents=True)
            mock_home.return_value = home

            os.chdir(project_dir)

            # Act
            detect_claude_directory()
            captured = capsys.readouterr()

            # Assert
            assert "warning" in captured.out.lower() or "both" in captured.out.lower()

    def test_dual_mode_uses_local_by_default(self, tmp_path):
        """Test dual mode defaults to LOCAL precedence."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        local_claude = project_dir / ".claude"
        local_claude.mkdir()
        (local_claude / "marker.txt").write_text("local")

        with patch('pathlib.Path.home') as mock_home:
            home = tmp_path / "home"
            plugin_claude = home / ".amplihack" / ".claude"
            plugin_claude.mkdir(parents=True)
            (plugin_claude / "marker.txt").write_text("plugin")
            mock_home.return_value = home

            os.chdir(project_dir)

            # Act
            detected = detect_claude_directory()
            marker_content = (detected / "marker.txt").read_text()

            # Assert
            assert marker_content == "local"

    def test_environment_variable_override(self, tmp_path):
        """Test AMPLIHACK_FORCE_PLUGIN_MODE environment variable."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".claude").mkdir()

        with patch('pathlib.Path.home') as mock_home:
            home = tmp_path / "home"
            plugin_claude = home / ".amplihack" / ".claude"
            plugin_claude.mkdir(parents=True)
            (plugin_claude / "marker.txt").write_text("plugin")
            mock_home.return_value = home

            os.chdir(project_dir)
            os.environ["AMPLIHACK_FORCE_PLUGIN_MODE"] = "1"

            try:
                # Act
                detected = detect_claude_directory()

                # Assert
                assert detected == plugin_claude
            finally:
                del os.environ["AMPLIHACK_FORCE_PLUGIN_MODE"]
