"""Unit tests for plugin CLI commands - TDD approach.

Tests the CLI command parsing and execution for plugin management:
- amplihack plugin install [source]
- amplihack plugin uninstall [name]
- amplihack plugin verify [name]

These tests are written BEFORE implementation (TDD).
All tests should FAIL initially.
"""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import will fail until implementation exists
try:
    from amplihack.plugin_cli import (
        plugin_install_command,
        plugin_uninstall_command,
        plugin_verify_command,
        setup_plugin_commands,
    )
except ImportError:
    # Create mock functions for TDD - tests will fail
    plugin_install_command = None
    plugin_uninstall_command = None
    plugin_verify_command = None
    setup_plugin_commands = None


class TestPluginInstallCommand:
    """Test amplihack plugin install command."""

    def test_install_from_git_url_success(self):
        """Test installing plugin from git URL succeeds."""
        # Arrange
        args = argparse.Namespace(source="https://github.com/example/plugin.git", force=False)

        with patch("amplihack.plugin_cli.PluginManager") as mock_manager:
            mock_result = MagicMock(
                success=True,
                plugin_name="plugin",
                installed_path=Path("/home/user/.amplihack/.claude/plugins/plugin"),
                message="Plugin installed successfully: plugin",
            )
            mock_manager.return_value.install.return_value = mock_result

            # Act
            exit_code = plugin_install_command(args)

            # Assert
            assert exit_code == 0
            mock_manager.return_value.install.assert_called_once_with(
                "https://github.com/example/plugin.git", force=False
            )

    def test_install_from_local_path_success(self):
        """Test installing plugin from local directory succeeds."""
        # Arrange
        args = argparse.Namespace(source="/path/to/local/plugin", force=False)

        with patch("amplihack.plugin_cli.PluginManager") as mock_manager:
            mock_result = MagicMock(
                success=True,
                plugin_name="plugin",
                installed_path=Path("/home/user/.amplihack/.claude/plugins/plugin"),
                message="Plugin installed successfully: plugin",
            )
            mock_manager.return_value.install.return_value = mock_result

            # Act
            exit_code = plugin_install_command(args)

            # Assert
            assert exit_code == 0

    def test_install_with_force_flag(self):
        """Test force flag overwrites existing plugin."""
        # Arrange
        args = argparse.Namespace(source="https://github.com/example/plugin.git", force=True)

        with patch("amplihack.plugin_cli.PluginManager") as mock_manager:
            mock_result = MagicMock(success=True, plugin_name="plugin")
            mock_manager.return_value.install.return_value = mock_result

            # Act
            exit_code = plugin_install_command(args)

            # Assert
            assert exit_code == 0
            mock_manager.return_value.install.assert_called_with(
                "https://github.com/example/plugin.git", force=True
            )

    def test_install_failure_returns_error_code(self):
        """Test failed installation returns non-zero exit code."""
        # Arrange
        args = argparse.Namespace(source="https://github.com/example/plugin.git", force=False)

        with patch("amplihack.plugin_cli.PluginManager") as mock_manager:
            mock_result = MagicMock(success=False, plugin_name="plugin", message="Invalid manifest")
            mock_manager.return_value.install.return_value = mock_result

            # Act
            exit_code = plugin_install_command(args)

            # Assert
            assert exit_code == 1

    def test_install_prints_success_message(self, capsys):
        """Test success message is printed to stdout."""
        # Arrange
        args = argparse.Namespace(source="https://github.com/example/plugin.git", force=False)

        with patch("amplihack.plugin_cli.PluginManager") as mock_manager:
            mock_result = MagicMock(
                success=True,
                plugin_name="my-plugin",
                installed_path=Path("/home/user/.amplihack/.claude/plugins/my-plugin"),
                message="Plugin installed successfully: my-plugin",
            )
            mock_manager.return_value.install.return_value = mock_result

            # Act
            plugin_install_command(args)
            captured = capsys.readouterr()

            # Assert
            assert "my-plugin" in captured.out
            assert "installed" in captured.out.lower()

    def test_install_prints_error_message(self, capsys):
        """Test error message is printed to stdout."""
        # Arrange
        args = argparse.Namespace(source="https://github.com/example/plugin.git", force=False)

        with patch("amplihack.plugin_cli.PluginManager") as mock_manager:
            mock_result = MagicMock(
                success=False, message="Invalid manifest: missing required field 'name'"
            )
            mock_manager.return_value.install.return_value = mock_result

            # Act
            plugin_install_command(args)
            captured = capsys.readouterr()

            # Assert
            assert "failed" in captured.out.lower() or "error" in captured.out.lower()
            assert "Invalid manifest" in captured.out


class TestPluginUninstallCommand:
    """Test amplihack plugin uninstall command."""

    def test_uninstall_existing_plugin_success(self):
        """Test uninstalling existing plugin succeeds."""
        # Arrange
        args = argparse.Namespace(plugin_name="my-plugin")

        with patch("amplihack.plugin_cli.PluginManager") as mock_manager:
            mock_manager.return_value.uninstall.return_value = True

            # Act
            exit_code = plugin_uninstall_command(args)

            # Assert
            assert exit_code == 0
            mock_manager.return_value.uninstall.assert_called_once_with("my-plugin")

    def test_uninstall_nonexistent_plugin_failure(self):
        """Test uninstalling non-existent plugin fails."""
        # Arrange
        args = argparse.Namespace(plugin_name="nonexistent-plugin")

        with patch("amplihack.plugin_cli.PluginManager") as mock_manager:
            mock_manager.return_value.uninstall.return_value = False

            # Act
            exit_code = plugin_uninstall_command(args)

            # Assert
            assert exit_code == 1

    def test_uninstall_removes_from_settings_json(self):
        """Test uninstall also removes plugin from settings.json."""
        # Arrange
        args = argparse.Namespace(plugin_name="my-plugin")

        with patch("amplihack.plugin_cli.PluginManager") as mock_manager:
            mock_manager.return_value.uninstall.return_value = True
            # Check that uninstall method is called which should handle settings cleanup

            # Act
            plugin_uninstall_command(args)

            # Assert
            # PluginManager.uninstall should handle settings.json cleanup internally
            assert mock_manager.return_value.uninstall.called

    def test_uninstall_prints_success_message(self, capsys):
        """Test success message printed after uninstall."""
        # Arrange
        args = argparse.Namespace(plugin_name="my-plugin")

        with patch("amplihack.plugin_cli.PluginManager") as mock_manager:
            mock_manager.return_value.uninstall.return_value = True

            # Act
            plugin_uninstall_command(args)
            captured = capsys.readouterr()

            # Assert
            assert "my-plugin" in captured.out
            assert "removed" in captured.out.lower() or "uninstalled" in captured.out.lower()


class TestPluginVerifyCommand:
    """Test amplihack plugin verify command."""

    def test_verify_installed_plugin_success(self):
        """Test verifying installed plugin succeeds."""
        # Arrange
        args = argparse.Namespace(plugin_name="amplihack")

        with (
            patch("amplihack.cli.PluginManager") as mock_manager,
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", create=True),
        ):
            # Act
            exit_code = plugin_verify_command(args)

            # Assert
            assert exit_code == 0

    def test_verify_checks_plugin_directory_exists(self):
        """Test verify checks plugin directory exists."""
        # Arrange
        args = argparse.Namespace(plugin_name="my-plugin")
        plugin_path = Path.home() / ".amplihack" / ".claude" / "plugins" / "my-plugin"

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            # Act
            exit_code = plugin_verify_command(args)

            # Assert
            assert exit_code == 1

    def test_verify_checks_settings_json_entry(self):
        """Test verify checks enabledPlugins in settings.json."""
        # Arrange
        args = argparse.Namespace(plugin_name="my-plugin")

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", create=True) as mock_open,
            patch("json.loads") as mock_json,
        ):
            # Mock settings.json without plugin entry
            mock_json.return_value = {"enabledPlugins": []}

            # Act
            exit_code = plugin_verify_command(args)

            # Assert
            # Should fail if plugin not in enabledPlugins
            assert exit_code == 1

    def test_verify_checks_hooks_json_exists(self):
        """Test verify checks hooks.json exists and is valid."""
        # Arrange
        args = argparse.Namespace(plugin_name="my-plugin")

        with patch("amplihack.plugin_cli.PluginManager") as mock_manager:
            # Setup mock to check hooks file
            mock_manager.return_value.verify_hooks.return_value = True

            # Act
            exit_code = plugin_verify_command(args)

            # Assert
            assert exit_code == 0

    def test_verify_prints_detailed_report(self, capsys):
        """Test verify prints detailed verification report."""
        # Arrange
        args = argparse.Namespace(plugin_name="amplihack")

        with (
            patch("amplihack.cli.PluginManager") as mock_manager,
            patch("pathlib.Path.exists", return_value=True),
        ):
            # Act
            plugin_verify_command(args)
            captured = capsys.readouterr()

            # Assert
            # Should print checks for: directory, settings.json, hooks
            assert "amplihack" in captured.out
            assert any(word in captured.out.lower() for word in ["check", "verify", "status"])


class TestSetupPluginCommands:
    """Test plugin command setup in argument parser."""

    def test_setup_adds_plugin_subcommand(self):
        """Test setup adds 'plugin' subcommand to parser."""
        # Arrange
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        # Act
        setup_plugin_commands(subparsers)

        # Assert
        # Should be able to parse 'plugin' subcommand
        args = parser.parse_args(["plugin", "install", "source"])
        assert hasattr(args, "plugin_command")

    def test_setup_adds_install_subcommand(self):
        """Test setup adds 'install' subcommand under plugin."""
        # Arrange
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        # Act
        setup_plugin_commands(subparsers)

        # Assert
        args = parser.parse_args(["plugin", "install", "https://github.com/example/plugin"])
        assert args.source == "https://github.com/example/plugin"

    def test_setup_adds_uninstall_subcommand(self):
        """Test setup adds 'uninstall' subcommand under plugin."""
        # Arrange
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        # Act
        setup_plugin_commands(subparsers)

        # Assert
        args = parser.parse_args(["plugin", "uninstall", "my-plugin"])
        assert args.plugin_name == "my-plugin"

    def test_setup_adds_verify_subcommand(self):
        """Test setup adds 'verify' subcommand under plugin."""
        # Arrange
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        # Act
        setup_plugin_commands(subparsers)

        # Assert
        args = parser.parse_args(["plugin", "verify", "amplihack"])
        assert args.plugin_name == "amplihack"

    def test_install_has_force_flag(self):
        """Test install command has --force flag."""
        # Arrange
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        # Act
        setup_plugin_commands(subparsers)

        # Assert
        args = parser.parse_args(["plugin", "install", "source", "--force"])
        assert args.force is True
