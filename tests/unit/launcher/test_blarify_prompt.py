"""Tests for blarify prompt integration in CLI launcher.

Tests the Week 4 implementation:
- Per-project consent caching
- 30s timeout with default yes
- Non-blocking behavior
- Integration with Kuzu code graph
"""

import hashlib
import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from amplihack.launcher.core import ClaudeLauncher


@pytest.fixture
def mock_project_path(tmp_path):
    """Create a temporary project directory."""
    project = tmp_path / "test_project"
    project.mkdir()
    return project


@pytest.fixture
def launcher():
    """Create launcher instance for testing."""
    return ClaudeLauncher()


class TestProjectConsentCaching:
    """Test per-project consent caching mechanism."""

    def test_get_project_consent_cache_path(self, launcher, mock_project_path):
        """Test cache path generation uses project hash."""
        cache_path = launcher._get_project_consent_cache_path(mock_project_path)

        # Verify path structure
        assert cache_path.parent == Path.home() / ".amplihack"
        assert cache_path.name.startswith(".blarify_consent_")

        # Verify hash is deterministic
        project_hash = hashlib.sha256(str(mock_project_path.resolve()).encode()).hexdigest()[:16]
        expected_name = f".blarify_consent_{project_hash}"
        assert cache_path.name == expected_name

    def test_has_blarify_consent_false_when_no_cache(self, launcher, mock_project_path):
        """Test consent check returns False when cache doesn't exist."""
        assert not launcher._has_blarify_consent(mock_project_path)

    def test_has_blarify_consent_true_when_cached(self, launcher, mock_project_path):
        """Test consent check returns True when cache exists."""
        # Save consent
        launcher._save_blarify_consent(mock_project_path)

        # Verify it's detected
        assert launcher._has_blarify_consent(mock_project_path)

    def test_save_blarify_consent_creates_cache_file(self, launcher, mock_project_path):
        """Test saving consent creates cache file."""
        cache_path = launcher._get_project_consent_cache_path(mock_project_path)

        # Should not exist initially
        assert not cache_path.exists()

        # Save consent
        launcher._save_blarify_consent(mock_project_path)

        # Should exist now
        assert cache_path.exists()

    def test_save_blarify_consent_handles_errors(self, launcher, mock_project_path, caplog):
        """Test saving consent handles permission errors gracefully."""
        with patch.object(Path, "touch", side_effect=PermissionError("Test error")):
            with caplog.at_level(logging.WARNING):
                launcher._save_blarify_consent(mock_project_path)

            # Should log warning but not crash
            assert "Failed to save blarify consent" in caplog.text


class TestBlarifyPromptLogic:
    """Test blarify prompt logic and user interaction."""

    @patch("amplihack.launcher.core.Path.cwd")
    def test_prompt_skips_when_consent_cached(self, mock_cwd, launcher, mock_project_path, caplog):
        """Test prompt is skipped when user already consented."""
        mock_cwd.return_value = mock_project_path

        # Save consent first
        launcher._save_blarify_consent(mock_project_path)

        with caplog.at_level(logging.DEBUG):
            result = launcher._prompt_blarify_indexing()

        # Should return True without prompting
        assert result is True
        assert "Blarify consent already given" in caplog.text

    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    def test_prompt_runs_by_default_in_non_interactive(
        self, mock_is_interactive, mock_cwd, launcher, mock_project_path, capsys
    ):
        """Test non-interactive mode runs blarify by default."""
        mock_cwd.return_value = mock_project_path
        mock_is_interactive.return_value = False

        # Mock the blarify execution
        with patch.object(launcher, "_run_blarify_and_import", return_value=True):
            result = launcher._prompt_blarify_indexing()

        assert result is True

        # Check output mentions non-interactive mode
        captured = capsys.readouterr()
        assert "non-interactive mode" in captured.out.lower()

        # Verify consent was saved
        assert launcher._has_blarify_consent(mock_project_path)

    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    @patch("amplihack.launcher.memory_config.get_user_input_with_timeout")
    @patch("amplihack.launcher.memory_config.parse_consent_response")
    def test_prompt_accepts_yes_response(
        self,
        mock_parse_response,
        mock_get_input,
        mock_is_interactive,
        mock_cwd,
        launcher,
        mock_project_path,
        capsys,
    ):
        """Test prompt handles yes response correctly."""
        mock_cwd.return_value = mock_project_path
        mock_is_interactive.return_value = True
        mock_get_input.return_value = "yes"
        mock_parse_response.return_value = True

        # Mock the blarify execution
        with patch.object(launcher, "_run_blarify_and_import", return_value=True):
            result = launcher._prompt_blarify_indexing()

        assert result is True

        # Verify timeout and logger passed correctly
        mock_get_input.assert_called_once()
        call_kwargs = mock_get_input.call_args
        assert call_kwargs.kwargs["timeout_seconds"] == 30

        # Verify consent was saved
        assert launcher._has_blarify_consent(mock_project_path)

    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    @patch("amplihack.launcher.memory_config.get_user_input_with_timeout")
    @patch("amplihack.launcher.memory_config.parse_consent_response")
    def test_prompt_accepts_no_response(
        self,
        mock_parse_response,
        mock_get_input,
        mock_is_interactive,
        mock_cwd,
        launcher,
        mock_project_path,
        capsys,
    ):
        """Test prompt handles no response correctly."""
        mock_cwd.return_value = mock_project_path
        mock_is_interactive.return_value = True
        mock_get_input.return_value = "no"
        mock_parse_response.return_value = False

        result = launcher._prompt_blarify_indexing()

        # Should still return True (non-blocking)
        assert result is True

        # Verify blarify was not run
        captured = capsys.readouterr()
        assert "Skipping code indexing" in captured.out

        # Verify consent was NOT saved
        assert not launcher._has_blarify_consent(mock_project_path)

    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    @patch("amplihack.launcher.memory_config.get_user_input_with_timeout")
    def test_prompt_handles_timeout_with_default_yes(
        self, mock_get_input, mock_is_interactive, mock_cwd, launcher, mock_project_path
    ):
        """Test prompt timeout defaults to yes."""
        mock_cwd.return_value = mock_project_path
        mock_is_interactive.return_value = True
        mock_get_input.return_value = None  # Timeout

        # Mock parse_consent_response to return default
        with patch("amplihack.launcher.memory_config.parse_consent_response", return_value=True):
            with patch.object(launcher, "_run_blarify_and_import", return_value=True):
                result = launcher._prompt_blarify_indexing()

        assert result is True

    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    def test_prompt_handles_keyboard_interrupt(
        self, mock_is_interactive, mock_cwd, launcher, mock_project_path, capsys
    ):
        """Test prompt handles Ctrl-C gracefully."""
        mock_cwd.return_value = mock_project_path
        mock_is_interactive.return_value = True

        # Simulate keyboard interrupt
        with patch(
            "amplihack.launcher.memory_config.get_user_input_with_timeout",
            side_effect=KeyboardInterrupt("Test interrupt"),
        ):
            result = launcher._prompt_blarify_indexing()

        # Should return True (non-blocking)
        assert result is True

        # Check output
        captured = capsys.readouterr()
        assert "interrupted" in captured.out.lower()

    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    def test_prompt_handles_unexpected_errors(
        self, mock_is_interactive, mock_cwd, launcher, mock_project_path, caplog, capsys
    ):
        """Test prompt handles unexpected errors gracefully."""
        mock_cwd.return_value = mock_project_path
        mock_is_interactive.return_value = True

        # Simulate unexpected error
        with patch(
            "amplihack.launcher.memory_config.get_user_input_with_timeout",
            side_effect=RuntimeError("Unexpected error"),
        ):
            with caplog.at_level(logging.WARNING):
                result = launcher._prompt_blarify_indexing()

        # Should return True (non-blocking)
        assert result is True

        # Should log warning
        assert "Blarify prompt failed" in caplog.text


class TestBlarifyExecution:
    """Test blarify execution and Kuzu import."""

    @patch("amplihack.memory.kuzu.code_graph.KuzuCodeGraph")
    @patch("amplihack.memory.kuzu.connector.KuzuConnector")
    def test_run_blarify_and_import_success(
        self, mock_connector_class, mock_code_graph_class, launcher, mock_project_path
    ):
        """Test successful blarify run and import."""
        # Setup mocks
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector

        mock_code_graph = Mock()
        mock_code_graph.run_blarify.return_value = {
            "files": 10,
            "classes": 5,
            "functions": 20,
        }
        mock_code_graph_class.return_value = mock_code_graph

        # Run blarify
        result = launcher._run_blarify_and_import(mock_project_path)

        # Verify success
        assert result is True

        # Verify connector was created and connected
        mock_connector_class.assert_called_once()
        mock_connector.connect.assert_called_once()

        # Verify code graph was created and run_blarify called
        mock_code_graph_class.assert_called_once_with(mock_connector)
        mock_code_graph.run_blarify.assert_called_once_with(
            codebase_path=str(mock_project_path), languages=None
        )

        # Verify connector was disconnected
        mock_connector.disconnect.assert_called_once()

    @patch("amplihack.memory.kuzu.connector.KuzuConnector")
    def test_run_blarify_and_import_handles_errors(
        self, mock_connector_class, launcher, mock_project_path, caplog
    ):
        """Test blarify execution handles errors gracefully."""
        # Simulate connection error
        mock_connector_class.side_effect = RuntimeError("Connection failed")

        with caplog.at_level(logging.ERROR):
            result = launcher._run_blarify_and_import(mock_project_path)

        # Should return False on error
        assert result is False

        # Should log error
        assert "Blarify indexing failed" in caplog.text


class TestIntegrationWithPrepareLaunch:
    """Test integration with prepare_launch method."""

    @patch.object(ClaudeLauncher, "_prompt_blarify_indexing")
    @patch("amplihack.launcher.core.check_prerequisites")
    def test_prepare_launch_calls_blarify_prompt(
        self,
        mock_prereqs,
        mock_blarify_prompt,
        launcher,
    ):
        """Test prepare_launch calls blarify prompt at correct point."""
        # Setup mocks to pass early checks
        mock_prereqs.return_value = True
        mock_blarify_prompt.return_value = True

        # Mock other methods to prevent side effects
        with patch.multiple(
            launcher,
            _find_target_directory=lambda: Path.cwd(),
            _ensure_runtime_directories=lambda x: True,
            _fix_hook_paths_in_settings=lambda x: True,
            _handle_directory_change=lambda x: True,
            _start_proxy_if_needed=lambda: True,
            _configure_lsp_auto=lambda x: None,
        ):
            result = launcher.prepare_launch()

        # Verify blarify prompt was called
        mock_blarify_prompt.assert_called_once()

    @patch.object(ClaudeLauncher, "_prompt_blarify_indexing")
    @patch("amplihack.launcher.core.check_prerequisites")
    def test_prepare_launch_continues_if_blarify_fails(
        self,
        mock_prereqs,
        mock_blarify_prompt,
        launcher,
        caplog,
    ):
        """Test prepare_launch continues even if blarify prompt returns False."""
        # Setup mocks
        mock_prereqs.return_value = True
        mock_blarify_prompt.return_value = False  # Simulate failure

        # Mock other methods
        with patch.multiple(
            launcher,
            _find_target_directory=lambda: Path.cwd(),
            _ensure_runtime_directories=lambda x: True,
            _fix_hook_paths_in_settings=lambda x: True,
            _handle_directory_change=lambda x: True,
            _start_proxy_if_needed=lambda: True,
            _configure_lsp_auto=lambda x: None,
        ):
            with caplog.at_level(logging.INFO):
                result = launcher.prepare_launch()

        # Should still succeed
        assert result is True

        # Should log that blarify was skipped
        assert "Blarify indexing skipped" in caplog.text
