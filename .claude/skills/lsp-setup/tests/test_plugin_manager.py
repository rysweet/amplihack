"""
Unit tests for plugin_manager.py (60% - Unit Tests)

Tests Claude Code plugin installation and management via npx cclsp.
All tests should FAIL initially (TDD red phase).
"""

import subprocess
from unittest.mock import MagicMock, patch


class TestPluginManager:
    """Test suite for PluginManager class."""

    def test_check_plugin_installed_returns_true(self, mock_subprocess_run):
        """Test checking if a plugin is installed (returns True)."""
        from lsp_setup.plugin_manager import PluginManager

        # Mock successful plugin check
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "python\ntypescript\nrust\n"

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager()
            assert manager.is_plugin_installed("python") is True

    def test_check_plugin_installed_returns_false(self, mock_subprocess_run):
        """Test checking if a plugin is installed (returns False)."""
        from lsp_setup.plugin_manager import PluginManager

        # Mock plugin not in list
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "typescript\nrust\n"

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager()
            assert manager.is_plugin_installed("python") is False

    def test_install_plugin_success(self, mock_npx_cclsp_success):
        """Test successful plugin installation."""
        from lsp_setup.plugin_manager import PluginManager

        with patch("subprocess.run", mock_npx_cclsp_success):
            manager = PluginManager()
            result = manager.install_plugin("python")

            assert result is True

    def test_install_plugin_failure(self, mock_npx_cclsp_failure):
        """Test failed plugin installation."""
        from lsp_setup.plugin_manager import PluginManager

        with patch("subprocess.run", mock_npx_cclsp_failure):
            manager = PluginManager()
            result = manager.install_plugin("python")

            assert result is False

    def test_install_multiple_plugins(self, mock_npx_cclsp_success):
        """Test installing multiple plugins."""
        from lsp_setup.plugin_manager import PluginManager

        with patch("subprocess.run", mock_npx_cclsp_success):
            manager = PluginManager()
            results = manager.install_plugins(["python", "typescript", "rust"])

            assert results["python"] is True
            assert results["typescript"] is True
            assert results["rust"] is True

    def test_list_installed_plugins(self, mock_subprocess_run):
        """Test listing all installed plugins."""
        from lsp_setup.plugin_manager import PluginManager

        # Mock plugin list output
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "python\ntypescript\nrust\ngo\n"

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager()
            plugins = manager.list_installed_plugins()

            assert "python" in plugins
            assert "typescript" in plugins
            assert "rust" in plugins
            assert "go" in plugins
            assert len(plugins) == 4

    def test_list_installed_plugins_empty(self, mock_subprocess_run):
        """Test listing plugins when none are installed."""
        from lsp_setup.plugin_manager import PluginManager

        # Mock empty plugin list
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = ""

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager()
            plugins = manager.list_installed_plugins()

            assert len(plugins) == 0

    def test_uninstall_plugin_success(self, mock_subprocess_run):
        """Test successful plugin uninstallation."""
        from lsp_setup.plugin_manager import PluginManager

        # Mock successful uninstall
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "Successfully uninstalled"

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager()
            result = manager.uninstall_plugin("python")

            assert result is True

    def test_uninstall_plugin_failure(self, mock_subprocess_run):
        """Test failed plugin uninstallation."""
        from lsp_setup.plugin_manager import PluginManager

        # Mock failed uninstall
        mock_subprocess_run.return_value.returncode = 1
        mock_subprocess_run.return_value.stderr = "Plugin not found"

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager()
            result = manager.uninstall_plugin("python")

            assert result is False

    def test_check_npx_available(self, mock_shutil_which):
        """Test checking if npx is available."""
        from lsp_setup.plugin_manager import PluginManager

        mock_shutil_which.return_value = "/usr/local/bin/npx"

        with patch("shutil.which", mock_shutil_which):
            manager = PluginManager()
            assert manager.is_npx_available() is True

    def test_check_npx_unavailable(self, mock_shutil_which):
        """Test checking if npx is unavailable."""
        from lsp_setup.plugin_manager import PluginManager

        mock_shutil_which.return_value = None

        with patch("shutil.which", mock_shutil_which):
            manager = PluginManager()
            assert manager.is_npx_available() is False

    def test_get_plugin_installation_command(self):
        """Test getting the installation command for a plugin."""
        from lsp_setup.plugin_manager import PluginManager

        manager = PluginManager()
        cmd = manager.get_installation_command("python")

        assert "npx" in cmd
        assert "cclsp" in cmd
        assert "install" in cmd
        assert "python" in cmd

    def test_install_plugin_with_timeout(self, mock_subprocess_run):
        """Test plugin installation with timeout."""
        from lsp_setup.plugin_manager import PluginManager

        # Mock timeout
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd="npx", timeout=30)

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager(timeout=30)
            result = manager.install_plugin("python")

            assert result is False

    def test_install_plugin_with_retry_on_failure(self, mock_subprocess_run):
        """Test retrying plugin installation on transient failures."""
        from lsp_setup.plugin_manager import PluginManager

        # First call fails, second succeeds
        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.returncode = 1
                result.stderr = "Network error"
            else:
                result.returncode = 0
                result.stdout = "Successfully installed"
            return result

        mock_subprocess_run.side_effect = mock_run

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager(max_retries=2)
            result = manager.install_plugin("python")

            assert result is True
            assert call_count == 2

    def test_get_plugin_info(self, mock_subprocess_run):
        """Test getting detailed information about a plugin."""
        from lsp_setup.plugin_manager import PluginManager

        # Mock plugin info output
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = '{"name": "python", "version": "1.0.0"}'

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager()
            info = manager.get_plugin_info("python")

            assert info["name"] == "python"
            assert info["version"] == "1.0.0"

    def test_update_plugin(self, mock_subprocess_run):
        """Test updating an installed plugin."""
        from lsp_setup.plugin_manager import PluginManager

        # Mock successful update
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "Updated successfully"

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager()
            result = manager.update_plugin("python")

            assert result is True

    def test_check_plugin_updates_available(self, mock_subprocess_run):
        """Test checking if plugin updates are available."""
        from lsp_setup.plugin_manager import PluginManager

        # Mock update check
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "python: 1.0.0 -> 1.1.0\n"

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager()
            updates = manager.check_updates()

            assert "python" in updates
            assert updates["python"]["current"] == "1.0.0"
            assert updates["python"]["available"] == "1.1.0"

    def test_validate_plugin_name(self):
        """Test validating plugin names."""
        from lsp_setup.plugin_manager import PluginManager

        manager = PluginManager()

        assert manager.is_valid_plugin_name("python") is True
        assert manager.is_valid_plugin_name("typescript") is True
        assert manager.is_valid_plugin_name("invalid-plugin!!!") is False
        assert manager.is_valid_plugin_name("") is False

    def test_get_supported_plugins_list(self):
        """Test getting list of all supported plugins."""
        from lsp_setup.plugin_manager import PluginManager

        manager = PluginManager()
        supported = manager.get_supported_plugins()

        assert "python" in supported
        assert "typescript" in supported
        assert "rust" in supported
        assert "go" in supported
        assert len(supported) >= 16  # At least 16 languages

    def test_install_plugin_with_verbose_output(self, mock_subprocess_run):
        """Test plugin installation with verbose output."""
        from lsp_setup.plugin_manager import PluginManager

        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "Installing...\nSuccess!"

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager(verbose=True)
            result = manager.install_plugin("python")

            assert result is True

    def test_handle_permission_error_on_install(self, mock_subprocess_run):
        """Test handling permission errors during installation."""
        from lsp_setup.plugin_manager import PluginManager

        mock_subprocess_run.side_effect = PermissionError("No write access")

        with patch("subprocess.run", mock_subprocess_run):
            manager = PluginManager()
            result = manager.install_plugin("python")

            assert result is False

    def test_dry_run_install(self, mock_subprocess_run):
        """Test dry-run mode (doesn't actually install)."""
        from lsp_setup.plugin_manager import PluginManager

        manager = PluginManager(dry_run=True)
        result = manager.install_plugin("python")

        # In dry-run, should return True without calling subprocess
        assert result is True
        mock_subprocess_run.assert_not_called()

    def test_get_installation_log(self):
        """Test getting installation log for debugging."""
        from lsp_setup.plugin_manager import PluginManager

        manager = PluginManager()
        # After some operations, should have log entries
        log = manager.get_installation_log()

        assert isinstance(log, list)
