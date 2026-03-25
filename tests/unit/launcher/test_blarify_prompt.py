"""Tests for blarify prompt integration in CLI launcher.

Tests the Week 4 implementation:
- Per-project consent caching
- 30s timeout with default no (opt-in, not opt-out)
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

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
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
        assert "don't ask again" in caplog.text

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    @patch("amplihack.memory.kuzu.indexing.staleness_detector.check_index_status")
    @patch("amplihack.memory.kuzu.indexing.time_estimator.estimate_time")
    def test_prompt_runs_by_default_in_non_interactive(
        self,
        mock_estimate_time,
        mock_check_index_status,
        mock_is_interactive,
        mock_cwd,
        launcher,
        mock_project_path,
        caplog,
    ):
        """Test non-interactive mode skips blarify (requires interactive terminal)."""
        mock_cwd.return_value = mock_project_path
        mock_is_interactive.return_value = False

        # Mock staleness detector - index needs updating
        mock_status = Mock()
        mock_status.needs_indexing = True
        mock_status.reason = "Index missing"
        mock_status.estimated_files = 100
        mock_check_index_status.return_value = mock_status

        # Mock time estimator
        mock_estimate = Mock()
        mock_estimate.total_seconds = 10.0
        mock_estimate.by_language = {}
        mock_estimate.file_counts = {}
        mock_estimate_time.return_value = mock_estimate

        with caplog.at_level(logging.INFO):
            result = launcher._prompt_blarify_indexing()

        # Should return True (non-blocking) and skip in non-interactive mode
        assert result is True
        assert "non-interactive" in caplog.text.lower()

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    @patch("amplihack.launcher.memory_config.get_user_input_with_timeout")
    @patch("amplihack.launcher.memory_config.parse_consent_response")
    @patch("amplihack.memory.kuzu.indexing.staleness_detector.check_index_status")
    @patch("amplihack.memory.kuzu.indexing.time_estimator.estimate_time")
    def test_prompt_accepts_yes_response(
        self,
        mock_estimate_time,
        mock_check_index_status,
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

        # Mock staleness detector - index needs updating
        mock_status = Mock()
        mock_status.needs_indexing = True
        mock_status.reason = "Index missing"
        mock_status.estimated_files = 100
        mock_check_index_status.return_value = mock_status

        # Mock time estimator
        mock_estimate = Mock()
        mock_estimate.total_seconds = 10.0
        mock_estimate.by_language = {}
        mock_estimate.file_counts = {}
        mock_estimate_time.return_value = mock_estimate

        # Mock the blarify execution
        with patch.object(launcher, "_run_blarify_and_import", return_value=True):
            result = launcher._prompt_blarify_indexing()

        assert result is True

        # Verify timeout and logger passed correctly
        mock_get_input.assert_called_once()
        call_kwargs = mock_get_input.call_args
        assert call_kwargs.kwargs["timeout_seconds"] == 30

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    @patch("amplihack.launcher.memory_config.get_user_input_with_timeout")
    @patch("amplihack.launcher.memory_config.parse_consent_response")
    @patch("amplihack.memory.kuzu.indexing.staleness_detector.check_index_status")
    @patch("amplihack.memory.kuzu.indexing.time_estimator.estimate_time")
    def test_prompt_accepts_no_response(
        self,
        mock_estimate_time,
        mock_check_index_status,
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

        # Mock staleness detector - index needs updating
        mock_status = Mock()
        mock_status.needs_indexing = True
        mock_status.reason = "Index missing"
        mock_status.estimated_files = 100
        mock_check_index_status.return_value = mock_status

        # Mock time estimator
        mock_estimate = Mock()
        mock_estimate.total_seconds = 10.0
        mock_estimate.by_language = {}
        mock_estimate.file_counts = {}
        mock_estimate_time.return_value = mock_estimate

        result = launcher._prompt_blarify_indexing()

        # Should still return True (non-blocking)
        assert result is True

        # Verify blarify was not run
        captured = capsys.readouterr()
        assert "Skipping code indexing" in captured.out

        # Verify consent was NOT saved
        assert not launcher._has_blarify_consent(mock_project_path)

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    @patch("amplihack.launcher.memory_config.get_user_input_with_timeout")
    @patch("amplihack.memory.kuzu.indexing.staleness_detector.check_index_status")
    @patch("amplihack.memory.kuzu.indexing.time_estimator.estimate_time")
    def test_prompt_handles_timeout_with_default_no(
        self,
        mock_estimate_time,
        mock_check_index_status,
        mock_get_input,
        mock_is_interactive,
        mock_cwd,
        launcher,
        mock_project_path,
    ):
        """Test prompt timeout defaults to no (opt-in behavior)."""
        mock_cwd.return_value = mock_project_path
        mock_is_interactive.return_value = True
        mock_get_input.return_value = None  # Timeout

        # Mock staleness detector - index needs updating
        mock_status = Mock()
        mock_status.needs_indexing = True
        mock_status.reason = "Index missing"
        mock_status.estimated_files = 100
        mock_check_index_status.return_value = mock_status

        # Mock time estimator
        mock_estimate = Mock()
        mock_estimate.total_seconds = 10.0
        mock_estimate.by_language = {}
        mock_estimate.file_counts = {}
        mock_estimate_time.return_value = mock_estimate

        # Mock parse_consent_response to return default (False)
        with patch("amplihack.launcher.memory_config.parse_consent_response", return_value=False):
            result = launcher._prompt_blarify_indexing()

        # Should return True (non-blocking) but not run blarify
        assert result is True
        # Verify blarify was not run (no consent saved)
        assert not launcher._has_blarify_consent(mock_project_path)

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    @patch("amplihack.memory.kuzu.indexing.staleness_detector.check_index_status")
    @patch("amplihack.memory.kuzu.indexing.time_estimator.estimate_time")
    def test_prompt_handles_keyboard_interrupt(
        self,
        mock_estimate_time,
        mock_check_index_status,
        mock_is_interactive,
        mock_cwd,
        launcher,
        mock_project_path,
        capsys,
    ):
        """Test prompt handles Ctrl-C gracefully."""
        mock_cwd.return_value = mock_project_path
        mock_is_interactive.return_value = True

        # Mock staleness detector - index needs updating
        mock_status = Mock()
        mock_status.needs_indexing = True
        mock_status.reason = "Index missing"
        mock_status.estimated_files = 100
        mock_check_index_status.return_value = mock_status

        # Mock time estimator
        mock_estimate = Mock()
        mock_estimate.total_seconds = 10.0
        mock_estimate.by_language = {}
        mock_estimate.file_counts = {}
        mock_estimate_time.return_value = mock_estimate

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

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    @patch("amplihack.memory.kuzu.indexing.staleness_detector.check_index_status")
    @patch("amplihack.memory.kuzu.indexing.time_estimator.estimate_time")
    def test_prompt_handles_unexpected_errors(
        self,
        mock_estimate_time,
        mock_check_index_status,
        mock_is_interactive,
        mock_cwd,
        launcher,
        mock_project_path,
        caplog,
        capsys,
    ):
        """Test prompt handles unexpected errors gracefully."""
        mock_cwd.return_value = mock_project_path
        mock_is_interactive.return_value = True

        # Mock staleness detector - index needs updating
        mock_status = Mock()
        mock_status.needs_indexing = True
        mock_status.reason = "Index missing"
        mock_status.estimated_files = 100
        mock_check_index_status.return_value = mock_status

        # Mock time estimator
        mock_estimate = Mock()
        mock_estimate.total_seconds = 10.0
        mock_estimate.by_language = {}
        mock_estimate.file_counts = {}
        mock_estimate_time.return_value = mock_estimate

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

    @patch("amplihack.memory.kuzu.indexing.prerequisite_checker.PrerequisiteChecker")
    @patch("amplihack.memory.kuzu.connector.KuzuConnector")
    @patch("amplihack.memory.kuzu.indexing.orchestrator.Orchestrator")
    def test_run_blarify_and_import_success(
        self,
        mock_orchestrator_class,
        mock_connector_class,
        mock_checker_class,
        launcher,
        mock_project_path,
    ):
        """Test successful blarify run and import using current Orchestrator API."""
        # Setup PrerequisiteChecker mock
        mock_checker = Mock()
        mock_checker_class.return_value = mock_checker
        mock_prereq_result = Mock()
        mock_prereq_result.can_proceed = True
        mock_prereq_result.available_languages = ["python"]
        mock_prereq_result.unavailable_languages = []
        mock_prereq_result.language_statuses = {}
        mock_checker.check_all.return_value = mock_prereq_result

        # Setup KuzuConnector mock
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector

        # Setup Orchestrator mock
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_indexing_result = Mock()
        mock_indexing_result.success = True
        mock_indexing_result.total_files = 10
        mock_indexing_result.errors = []
        mock_orchestrator.run.return_value = mock_indexing_result

        # Run blarify
        result = launcher._run_blarify_and_import(mock_project_path)

        # Verify success
        assert result is True

        # Verify connector was created and connected
        mock_connector_class.assert_called_once()
        mock_connector.connect.assert_called_once()

        # Verify orchestrator was created and run called
        mock_orchestrator_class.assert_called_once_with(connector=mock_connector)
        mock_orchestrator.run.assert_called_once()

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

    @patch("amplihack.launcher.core._is_noninteractive", return_value=False)
    @patch.object(ClaudeLauncher, "_prompt_blarify_indexing")
    @patch("amplihack.launcher.core.check_prerequisites")
    def test_prepare_launch_calls_blarify_prompt(
        self,
        mock_prereqs,
        mock_blarify_prompt,
        mock_noninteractive,
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
            _configure_lsp_auto=lambda x: None,
        ):
            launcher.prepare_launch()

        # Verify blarify prompt was called
        mock_blarify_prompt.assert_called_once()

    @patch("amplihack.launcher.core._is_noninteractive", return_value=False)
    @patch.object(ClaudeLauncher, "_prompt_blarify_indexing")
    @patch("amplihack.launcher.core.check_prerequisites")
    def test_prepare_launch_continues_if_blarify_fails(
        self,
        mock_prereqs,
        mock_blarify_prompt,
        mock_noninteractive,
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
            _configure_lsp_auto=lambda x: None,
        ):
            with caplog.at_level(logging.INFO):
                result = launcher.prepare_launch()

        # Should still succeed
        assert result is True

        # Should log that blarify was skipped
        assert "Blarify indexing skipped" in caplog.text
