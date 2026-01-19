"""
Unit tests for lsp_configurator.py (60% - Unit Tests)

Tests LSP configuration logic and .env file management.
All tests should FAIL initially (TDD red phase).
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open


class TestLSPConfigurator:
    """Test suite for LSPConfigurator class."""

    def test_enable_lsp_in_new_env_file(self, mock_project_root, mock_env_file):
        """Test enabling LSP in a new .env file."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        configurator = LSPConfigurator(mock_project_root)
        result = configurator.enable_lsp()

        assert result is True
        assert mock_env_file.exists()
        assert "ENABLE_LSP_TOOL=1" in mock_env_file.read_text()

    def test_enable_lsp_in_existing_env_file(self, mock_project_root, mock_env_file):
        """Test enabling LSP in an existing .env file."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        # Create existing .env with other content
        mock_env_file.write_text("API_KEY=secret\nDEBUG=true\n")

        configurator = LSPConfigurator(mock_project_root)
        result = configurator.enable_lsp()

        assert result is True
        content = mock_env_file.read_text()
        assert "ENABLE_LSP_TOOL=1" in content
        assert "API_KEY=secret" in content
        assert "DEBUG=true" in content

    def test_enable_lsp_when_already_enabled(self, mock_project_root, mock_env_file):
        """Test enabling LSP when it's already enabled."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        # Create .env with LSP already enabled
        mock_env_file.write_text("ENABLE_LSP_TOOL=1\nAPI_KEY=secret\n")

        configurator = LSPConfigurator(mock_project_root)
        result = configurator.enable_lsp()

        assert result is True
        # Should not duplicate the setting
        assert mock_env_file.read_text().count("ENABLE_LSP_TOOL=1") == 1

    def test_enable_lsp_updates_existing_disabled_setting(self, mock_project_root, mock_env_file):
        """Test updating ENABLE_LSP_TOOL from 0 to 1."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        # Create .env with LSP disabled
        mock_env_file.write_text("ENABLE_LSP_TOOL=0\nAPI_KEY=secret\n")

        configurator = LSPConfigurator(mock_project_root)
        result = configurator.enable_lsp()

        assert result is True
        content = mock_env_file.read_text()
        assert "ENABLE_LSP_TOOL=1" in content
        assert "ENABLE_LSP_TOOL=0" not in content

    def test_disable_lsp(self, mock_project_root, mock_env_file):
        """Test disabling LSP in .env file."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        # Create .env with LSP enabled
        mock_env_file.write_text("ENABLE_LSP_TOOL=1\nAPI_KEY=secret\n")

        configurator = LSPConfigurator(mock_project_root)
        result = configurator.disable_lsp()

        assert result is True
        content = mock_env_file.read_text()
        assert "ENABLE_LSP_TOOL=0" in content or "ENABLE_LSP_TOOL" not in content

    def test_is_lsp_enabled_returns_true(self, mock_project_root, mock_env_file):
        """Test checking if LSP is enabled (returns True)."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        mock_env_file.write_text("ENABLE_LSP_TOOL=1\n")

        configurator = LSPConfigurator(mock_project_root)
        assert configurator.is_lsp_enabled() is True

    def test_is_lsp_enabled_returns_false_when_disabled(self, mock_project_root, mock_env_file):
        """Test checking if LSP is enabled (returns False when disabled)."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        mock_env_file.write_text("ENABLE_LSP_TOOL=0\n")

        configurator = LSPConfigurator(mock_project_root)
        assert configurator.is_lsp_enabled() is False

    def test_is_lsp_enabled_returns_false_when_missing(self, mock_project_root):
        """Test checking if LSP is enabled (returns False when .env missing)."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        configurator = LSPConfigurator(mock_project_root)
        assert configurator.is_lsp_enabled() is False

    def test_get_env_file_path(self, mock_project_root):
        """Test getting the .env file path."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        configurator = LSPConfigurator(mock_project_root)
        env_path = configurator.get_env_file_path()

        assert env_path == mock_project_root / ".env"

    def test_backup_env_file_before_modification(self, mock_project_root, mock_env_file):
        """Test that .env is backed up before modification."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        # Create existing .env
        original_content = "API_KEY=secret\nDEBUG=true\n"
        mock_env_file.write_text(original_content)

        configurator = LSPConfigurator(mock_project_root)
        configurator.enable_lsp()

        # Check for backup file
        backup_file = mock_project_root / ".env.backup"
        assert backup_file.exists()
        assert backup_file.read_text() == original_content

    def test_validate_env_file_syntax(self, mock_project_root, mock_env_file):
        """Test validating .env file syntax."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        # Valid .env
        mock_env_file.write_text("KEY=value\nENABLE_LSP_TOOL=1\n")

        configurator = LSPConfigurator(mock_project_root)
        assert configurator.validate_env_syntax() is True

    def test_validate_env_file_syntax_invalid(self, mock_project_root, mock_env_file):
        """Test validating invalid .env file syntax."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        # Invalid .env (malformed)
        mock_env_file.write_text("KEY=value\nINVALID LINE WITHOUT EQUALS\n")

        configurator = LSPConfigurator(mock_project_root)
        assert configurator.validate_env_syntax() is False

    def test_get_all_env_variables(self, mock_project_root, mock_env_file):
        """Test getting all environment variables from .env."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        mock_env_file.write_text("API_KEY=secret\nENABLE_LSP_TOOL=1\nDEBUG=false\n")

        configurator = LSPConfigurator(mock_project_root)
        env_vars = configurator.get_all_env_variables()

        assert env_vars["API_KEY"] == "secret"
        assert env_vars["ENABLE_LSP_TOOL"] == "1"
        assert env_vars["DEBUG"] == "false"

    def test_set_env_variable(self, mock_project_root, mock_env_file):
        """Test setting a specific environment variable."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        mock_env_file.write_text("API_KEY=secret\n")

        configurator = LSPConfigurator(mock_project_root)
        configurator.set_env_variable("NEW_VAR", "new_value")

        content = mock_env_file.read_text()
        assert "NEW_VAR=new_value" in content
        assert "API_KEY=secret" in content

    def test_remove_env_variable(self, mock_project_root, mock_env_file):
        """Test removing an environment variable."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        mock_env_file.write_text("API_KEY=secret\nOLD_VAR=old_value\n")

        configurator = LSPConfigurator(mock_project_root)
        configurator.remove_env_variable("OLD_VAR")

        content = mock_env_file.read_text()
        assert "OLD_VAR" not in content
        assert "API_KEY=secret" in content

    def test_handle_permission_error_on_env_file(self, mock_project_root, mock_env_file):
        """Test handling permission errors when writing .env."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        configurator = LSPConfigurator(mock_project_root)

        with patch("pathlib.Path.write_text", side_effect=PermissionError):
            result = configurator.enable_lsp()
            assert result is False

    def test_handle_io_error_on_env_file(self, mock_project_root, mock_env_file):
        """Test handling I/O errors when reading .env."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        configurator = LSPConfigurator(mock_project_root)

        with patch("pathlib.Path.read_text", side_effect=IOError):
            result = configurator.is_lsp_enabled()
            assert result is False

    def test_preserve_comments_in_env_file(self, mock_project_root, mock_env_file):
        """Test that comments are preserved when modifying .env."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        original_content = "# API Configuration\nAPI_KEY=secret\n# Debug mode\nDEBUG=true\n"
        mock_env_file.write_text(original_content)

        configurator = LSPConfigurator(mock_project_root)
        configurator.enable_lsp()

        content = mock_env_file.read_text()
        assert "# API Configuration" in content
        assert "# Debug mode" in content

    def test_preserve_empty_lines_in_env_file(self, mock_project_root, mock_env_file):
        """Test that empty lines are preserved when modifying .env."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        original_content = "API_KEY=secret\n\nDEBUG=true\n\n"
        mock_env_file.write_text(original_content)

        configurator = LSPConfigurator(mock_project_root)
        configurator.enable_lsp()

        content = mock_env_file.read_text()
        # Should preserve structure
        assert content.count("\n\n") >= 1

    def test_get_lsp_status_summary(self, mock_project_root, mock_env_file):
        """Test getting a summary of LSP configuration status."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        mock_env_file.write_text("ENABLE_LSP_TOOL=1\n")

        configurator = LSPConfigurator(mock_project_root)
        status = configurator.get_status_summary()

        assert status["enabled"] is True
        assert status["env_file_exists"] is True
        assert "env_file_path" in status
