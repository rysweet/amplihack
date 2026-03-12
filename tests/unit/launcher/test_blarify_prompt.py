"""Tests for blarify prompt integration in CLI launcher.

Tests the Week 4 implementation:
- Per-project consent caching
- 30s timeout with default no (opt-in, not opt-out)
- Non-blocking behavior
- Integration with Kuzu code graph

TDD corrections (issue #3080):
- All tests calling _prompt_blarify_indexing need AMPLIHACK_ENABLE_BLARIFY=1
- Staleness detector and time estimator must be mocked for tests reaching the prompt
- Log message for cached consent is now 'don't ask again' (not 'Blarify consent already given')
- Non-interactive mode now skips blarify entirely (prepare_launch level)
- _run_blarify_and_import mocks updated: Orchestrator + PrerequisiteChecker + KuzuConnector
- _is_noninteractive must be mocked to False for prepare_launch tests
"""

import hashlib
import logging
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from amplihack.launcher.core import ClaudeLauncher


# ---------------------------------------------------------------------------
# Shared mock factories
# ---------------------------------------------------------------------------

def _make_stale_status():
    """Return a mock IndexStatus indicating a stale index that needs re-indexing."""
    status = MagicMock()
    status.needs_indexing = True
    status.reason = "Index is stale or missing"
    status.estimated_files = 100
    return status


def _make_time_estimate():
    """Return a mock TimeEstimate with 30-second total."""
    estimate = MagicMock()
    estimate.total_seconds = 30
    estimate.by_language = {"python": 15.0, "javascript": 15.0}
    estimate.file_counts = {"python": 30, "javascript": 30}
    return estimate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# TestProjectConsentCaching
# ---------------------------------------------------------------------------

class TestProjectConsentCaching:
    """Test per-project consent caching mechanism.

    These helper methods are NOT guarded by AMPLIHACK_ENABLE_BLARIFY so
    they do not need the env-var patch.
    """

    def test_get_project_consent_cache_path(self, launcher, mock_project_path):
        """Test cache path generation uses project hash."""
        cache_path = launcher._get_project_consent_cache_path(mock_project_path)

        assert cache_path.parent == Path.home() / ".amplihack"
        assert cache_path.name.startswith(".blarify_consent_")

        project_hash = hashlib.sha256(str(mock_project_path.resolve()).encode()).hexdigest()[:16]
        expected_name = f".blarify_consent_{project_hash}"
        assert cache_path.name == expected_name

    def test_has_blarify_consent_false_when_no_cache(self, launcher, mock_project_path):
        """Test consent check returns False when cache doesn't exist."""
        assert not launcher._has_blarify_consent(mock_project_path)

    def test_has_blarify_consent_true_when_cached(self, launcher, mock_project_path):
        """Test consent check returns True when cache exists."""
        launcher._save_blarify_consent(mock_project_path)
        assert launcher._has_blarify_consent(mock_project_path)

    def test_save_blarify_consent_creates_cache_file(self, launcher, mock_project_path):
        """Test saving consent creates cache file."""
        cache_path = launcher._get_project_consent_cache_path(mock_project_path)
        assert not cache_path.exists()

        launcher._save_blarify_consent(mock_project_path)

        assert cache_path.exists()

    def test_save_blarify_consent_handles_errors(self, launcher, mock_project_path, caplog):
        """Test saving consent handles permission errors gracefully."""
        with patch.object(Path, "touch", side_effect=PermissionError("Test error")):
            with caplog.at_level(logging.WARNING):
                launcher._save_blarify_consent(mock_project_path)

        assert "Failed to save blarify consent" in caplog.text


# ---------------------------------------------------------------------------
# TestBlarifyPromptLogic
# ---------------------------------------------------------------------------

class TestBlarifyPromptLogic:
    """Test blarify prompt logic and user interaction.

    All tests here call _prompt_blarify_indexing() and therefore require
    AMPLIHACK_ENABLE_BLARIFY=1 to be set (otherwise the method returns
    immediately before any interesting behaviour executes).
    """

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    def test_prompt_skips_when_consent_cached(self, mock_cwd, launcher, mock_project_path, caplog):
        """Test prompt is skipped when user already consented ('don't ask again').

        The log message changed from 'Blarify consent already given' to
        contain 'don't ask again'.  Assert on the new text.
        """
        mock_cwd.return_value = mock_project_path
        launcher._save_blarify_consent(mock_project_path)

        with caplog.at_level(logging.DEBUG):
            result = launcher._prompt_blarify_indexing()

        assert result is True
        # Log message now contains "don't ask again" (not "Blarify consent already given")
        assert "don't ask again" in caplog.text

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.memory.kuzu.indexing.staleness_detector.check_index_status")
    @patch("amplihack.memory.kuzu.indexing.time_estimator.estimate_time")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    def test_prompt_skips_in_non_interactive(
        self,
        mock_is_interactive,
        mock_estimate_time,
        mock_check_index_status,
        mock_cwd,
        launcher,
        mock_project_path,
    ):
        """Test non-interactive mode skips blarify (no run, no prompt).

        The old behaviour ran blarify automatically in non-interactive mode.
        The new behaviour skips entirely and returns True.
        """
        mock_cwd.return_value = mock_project_path
        mock_check_index_status.return_value = _make_stale_status()
        mock_estimate_time.return_value = _make_time_estimate()
        mock_is_interactive.return_value = False

        with patch.object(launcher, "_run_blarify_and_import") as mock_run:
            result = launcher._prompt_blarify_indexing()

        assert result is True
        # Must NOT run blarify in non-interactive mode
        mock_run.assert_not_called()
        # Must NOT have saved consent (user didn't consent)
        assert not launcher._has_blarify_consent(mock_project_path)

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.memory.kuzu.indexing.staleness_detector.check_index_status")
    @patch("amplihack.memory.kuzu.indexing.time_estimator.estimate_time")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    @patch("amplihack.launcher.memory_config.get_user_input_with_timeout")
    @patch("amplihack.launcher.memory_config.parse_consent_response")
    def test_prompt_accepts_yes_response(
        self,
        mock_parse_response,
        mock_get_input,
        mock_is_interactive,
        mock_estimate_time,
        mock_check_index_status,
        mock_cwd,
        launcher,
        mock_project_path,
        capsys,
    ):
        """Test prompt handles yes response correctly."""
        mock_cwd.return_value = mock_project_path
        mock_check_index_status.return_value = _make_stale_status()
        mock_estimate_time.return_value = _make_time_estimate()
        mock_is_interactive.return_value = True
        mock_get_input.return_value = "yes"
        mock_parse_response.return_value = True

        with patch.object(launcher, "_run_blarify_and_import", return_value=True):
            result = launcher._prompt_blarify_indexing()

        assert result is True
        mock_get_input.assert_called_once()
        call_kwargs = mock_get_input.call_args
        assert call_kwargs.kwargs["timeout_seconds"] == 30

        # A "yes" response runs indexing NOW but does NOT set "don't ask again" consent.
        # Only the "n/skip/never" response triggers _save_blarify_consent.
        assert not launcher._has_blarify_consent(mock_project_path)

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.memory.kuzu.indexing.staleness_detector.check_index_status")
    @patch("amplihack.memory.kuzu.indexing.time_estimator.estimate_time")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    @patch("amplihack.launcher.memory_config.get_user_input_with_timeout")
    @patch("amplihack.launcher.memory_config.parse_consent_response")
    def test_prompt_accepts_no_response(
        self,
        mock_parse_response,
        mock_get_input,
        mock_is_interactive,
        mock_estimate_time,
        mock_check_index_status,
        mock_cwd,
        launcher,
        mock_project_path,
        capsys,
    ):
        """Test prompt handles no response correctly."""
        mock_cwd.return_value = mock_project_path
        mock_check_index_status.return_value = _make_stale_status()
        mock_estimate_time.return_value = _make_time_estimate()
        mock_is_interactive.return_value = True
        mock_get_input.return_value = "no"
        mock_parse_response.return_value = False

        result = launcher._prompt_blarify_indexing()

        assert result is True

        captured = capsys.readouterr()
        assert "Skipping code indexing" in captured.out

        assert not launcher._has_blarify_consent(mock_project_path)

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.memory.kuzu.indexing.staleness_detector.check_index_status")
    @patch("amplihack.memory.kuzu.indexing.time_estimator.estimate_time")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    @patch("amplihack.launcher.memory_config.get_user_input_with_timeout")
    def test_prompt_handles_timeout_with_default_no(
        self,
        mock_get_input,
        mock_is_interactive,
        mock_estimate_time,
        mock_check_index_status,
        mock_cwd,
        launcher,
        mock_project_path,
    ):
        """Test prompt timeout defaults to no (opt-in behavior)."""
        mock_cwd.return_value = mock_project_path
        mock_check_index_status.return_value = _make_stale_status()
        mock_estimate_time.return_value = _make_time_estimate()
        mock_is_interactive.return_value = True
        mock_get_input.return_value = None  # Timeout

        with patch("amplihack.launcher.memory_config.parse_consent_response", return_value=False):
            result = launcher._prompt_blarify_indexing()

        assert result is True
        assert not launcher._has_blarify_consent(mock_project_path)

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.memory.kuzu.indexing.staleness_detector.check_index_status")
    @patch("amplihack.memory.kuzu.indexing.time_estimator.estimate_time")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    def test_prompt_handles_keyboard_interrupt(
        self,
        mock_is_interactive,
        mock_estimate_time,
        mock_check_index_status,
        mock_cwd,
        launcher,
        mock_project_path,
        capsys,
    ):
        """Test prompt handles Ctrl-C gracefully."""
        mock_cwd.return_value = mock_project_path
        mock_check_index_status.return_value = _make_stale_status()
        mock_estimate_time.return_value = _make_time_estimate()
        mock_is_interactive.return_value = True

        with patch(
            "amplihack.launcher.memory_config.get_user_input_with_timeout",
            side_effect=KeyboardInterrupt("Test interrupt"),
        ):
            result = launcher._prompt_blarify_indexing()

        assert result is True

        captured = capsys.readouterr()
        assert "interrupted" in captured.out.lower()

    @patch.dict("os.environ", {"AMPLIHACK_ENABLE_BLARIFY": "1"})
    @patch("amplihack.launcher.core.Path.cwd")
    @patch("amplihack.memory.kuzu.indexing.staleness_detector.check_index_status")
    @patch("amplihack.memory.kuzu.indexing.time_estimator.estimate_time")
    @patch("amplihack.launcher.memory_config.is_interactive_terminal")
    def test_prompt_handles_unexpected_errors(
        self,
        mock_is_interactive,
        mock_estimate_time,
        mock_check_index_status,
        mock_cwd,
        launcher,
        mock_project_path,
        caplog,
        capsys,
    ):
        """Test prompt handles unexpected errors gracefully."""
        mock_cwd.return_value = mock_project_path
        mock_check_index_status.return_value = _make_stale_status()
        mock_estimate_time.return_value = _make_time_estimate()
        mock_is_interactive.return_value = True

        with patch(
            "amplihack.launcher.memory_config.get_user_input_with_timeout",
            side_effect=RuntimeError("Unexpected error"),
        ):
            with caplog.at_level(logging.WARNING):
                result = launcher._prompt_blarify_indexing()

        assert result is True
        assert "Blarify prompt failed" in caplog.text


# ---------------------------------------------------------------------------
# TestBlarifyExecution
# ---------------------------------------------------------------------------

class TestBlarifyExecution:
    """Test blarify execution and Kuzu import.

    These tests call _run_blarify_and_import directly so they do NOT need
    the AMPLIHACK_ENABLE_BLARIFY env var patch.  They DO need the correct
    mock paths: Orchestrator + PrerequisiteChecker + KuzuConnector
    (not the old KuzuCodeGraph).
    """

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
        """Test successful blarify run via Orchestrator/PrerequisiteChecker/KuzuConnector.

        This test replaces the old version that mocked KuzuCodeGraph (which no
        longer exists in this code path).
        """
        # --- PrerequisiteChecker ---
        mock_checker = Mock()
        mock_checker_class.return_value = mock_checker
        mock_check_result = Mock()
        mock_check_result.can_proceed = True
        mock_check_result.available_languages = ["python"]
        mock_check_result.unavailable_languages = []
        mock_check_result.language_statuses = {}
        mock_checker.check_all.return_value = mock_check_result

        # --- KuzuConnector ---
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector

        # --- Orchestrator ---
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_index_result = Mock()
        mock_index_result.success = True
        mock_index_result.total_files = 10
        mock_index_result.errors = []
        mock_orchestrator.run.return_value = mock_index_result

        # Mock _count_files_by_language so we don't hit the filesystem
        with patch.object(launcher, "_count_files_by_language", return_value={"python": 10}):
            result = launcher._run_blarify_and_import(mock_project_path)

        assert result is True

        # Verify PrerequisiteChecker was instantiated and called
        mock_checker_class.assert_called_once()
        mock_checker.check_all.assert_called_once()

        # Verify KuzuConnector was created and connected
        mock_connector_class.assert_called_once()
        mock_connector.connect.assert_called_once()

        # Verify Orchestrator was created with the connector and run was called
        mock_orchestrator_class.assert_called_once_with(connector=mock_connector)
        mock_orchestrator.run.assert_called_once()

    @patch("amplihack.memory.kuzu.connector.KuzuConnector")
    def test_run_blarify_and_import_handles_errors(
        self, mock_connector_class, launcher, mock_project_path, caplog
    ):
        """Test blarify execution handles errors gracefully."""
        mock_connector_class.side_effect = RuntimeError("Connection failed")

        with caplog.at_level(logging.ERROR):
            result = launcher._run_blarify_and_import(mock_project_path)

        assert result is False
        assert "Blarify indexing failed" in caplog.text


# ---------------------------------------------------------------------------
# TestIntegrationWithPrepareLaunch
# ---------------------------------------------------------------------------

class TestIntegrationWithPrepareLaunch:
    """Test integration with prepare_launch method.

    prepare_launch checks _is_noninteractive() and only calls
    _prompt_blarify_indexing() when running interactively.
    All tests must patch _is_noninteractive to control this gate.
    """

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
        """Test prepare_launch calls blarify prompt when running interactively."""
        mock_prereqs.return_value = True
        mock_blarify_prompt.return_value = True

        with patch.multiple(
            launcher,
            _find_target_directory=lambda: Path.cwd(),
            _ensure_runtime_directories=lambda x: True,
            _fix_hook_paths_in_settings=lambda x: True,
            _handle_directory_change=lambda x: True,
            _start_proxy_if_needed=lambda: True,
            _configure_lsp_auto=lambda x: None,
        ):
            launcher.prepare_launch()

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
        mock_prereqs.return_value = True
        mock_blarify_prompt.return_value = False  # Simulate failure

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

        assert result is True
        assert "Blarify indexing skipped" in caplog.text

    @patch("amplihack.launcher.core._is_noninteractive", return_value=True)
    @patch.object(ClaudeLauncher, "_prompt_blarify_indexing")
    @patch("amplihack.launcher.core.check_prerequisites")
    def test_prepare_launch_skips_blarify_in_noninteractive(
        self,
        mock_prereqs,
        mock_blarify_prompt,
        mock_noninteractive,
        launcher,
    ):
        """Test prepare_launch does NOT call blarify prompt in non-interactive mode.

        New test added to verify the non-interactive gate at the prepare_launch level.
        blarify requires user interaction so it must be entirely skipped when
        _is_noninteractive() returns True.
        """
        mock_prereqs.return_value = True

        with patch.object(launcher, "_check_prerequisites_noninteractive", return_value=True):
            with patch.multiple(
                launcher,
                _find_target_directory=lambda: Path.cwd(),
                _ensure_runtime_directories=lambda x: True,
                _fix_hook_paths_in_settings=lambda x: True,
                _handle_directory_change=lambda x: True,
                _start_proxy_if_needed=lambda: True,
                _configure_lsp_auto=lambda x: None,
            ):
                launcher.prepare_launch()

        # _prompt_blarify_indexing must NOT be called in non-interactive mode
        mock_blarify_prompt.assert_not_called()
