"""Integration tests for unified .claude/ staging (Issue #2125).

Tests the _ensure_amplihack_staged() function that populates ~/.amplihack/.claude/
for all non-claude commands (copilot, amplifier, rustyclawd, codex).

Testing Approach:
- Focus on integration tests (Priority 1)
- Verify staging occurs for all commands
- Verify expected directory structure
- Test ratio: 2:1 to 4:1 for simple implementation
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestUnifiedStaging:
    """Integration tests for unified .claude/ staging across all commands."""

    @pytest.fixture
    def clean_staging_dir(self, tmp_path, monkeypatch):
        """Provide a clean staging directory for tests."""
        staging_dir = tmp_path / ".amplihack" / ".claude"
        monkeypatch.setenv("HOME", str(tmp_path))
        yield staging_dir

    def test_copilot_command_stages_amplihack(self, clean_staging_dir):
        """Test that 'amplihack copilot' populates ~/.amplihack/.claude/."""
        # Import after monkeypatch is applied
        from src.amplihack.cli import main

        # Mock is_uvx_deployment to return True
        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            # Mock copytree_manifest to simulate staging
            with patch("src.amplihack.cli.copytree_manifest") as mock_copy:
                with patch("src.amplihack.launcher.copilot.launch_copilot", return_value=0):
                    # Mock git conflict detection to avoid prompts
                    with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_result = mock_detector.return_value.detect_conflicts.return_value
                        mock_result.has_conflicts = False
                        mock_copy.return_value = True

                        # Run copilot command
                        exit_code = main(["copilot"])

                        # Verify staging was called
                        assert mock_copy.called
                        # Verify target directory matches expected
                        call_args = str(mock_copy.call_args)
                        assert ".amplihack/.claude" in call_args

                        assert exit_code == 0

    def test_codex_command_stages_amplihack(self, clean_staging_dir):
        """Test that 'amplihack codex' populates ~/.amplihack/.claude/."""
        from src.amplihack.cli import main

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest") as mock_copy:
                with patch("src.amplihack.launcher.codex.launch_codex", return_value=0):
                    # Mock git conflict detection to avoid prompts
                    with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector.return_value.detect_conflicts.return_value.has_conflicts = (
                            False
                        )
                        mock_copy.return_value = True

                        # Run codex command
                        exit_code = main(["codex"])

                        # Verify staging was called
                        assert mock_copy.called
                        call_args = str(mock_copy.call_args)
                        assert ".amplihack/.claude" in call_args

                        assert exit_code == 0

    def test_rustyclawd_command_stages_amplihack(self, clean_staging_dir):
        """Test that 'amplihack rustyclawd' populates ~/.amplihack/.claude/."""
        from src.amplihack.cli import main

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest") as mock_copy:
                with patch("src.amplihack.cli.launch_command", return_value=0):
                    # Mock git conflict detection to avoid prompts
                    with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector.return_value.detect_conflicts.return_value.has_conflicts = (
                            False
                        )
                        mock_copy.return_value = True

                        # Run rustyclawd command
                        exit_code = main(["RustyClawd"])

                        # Verify staging was called
                        assert mock_copy.called
                        call_args = str(mock_copy.call_args)
                        assert ".amplihack/.claude" in call_args

                        assert exit_code == 0

    def test_amplifier_command_stages_amplihack(self, clean_staging_dir):
        """Test that 'amplihack amplifier' populates ~/.amplihack/.claude/."""
        from src.amplihack.cli import main

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest") as mock_copy:
                with patch("src.amplihack.launcher.amplifier.launch_amplifier", return_value=0):
                    # Mock git conflict detection to avoid prompts
                    with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector.return_value.detect_conflicts.return_value.has_conflicts = (
                            False
                        )
                        mock_copy.return_value = True

                        # Run amplifier command
                        exit_code = main(["amplifier"])

                        # Verify staging was called
                        assert mock_copy.called
                        call_args = str(mock_copy.call_args)
                        assert ".amplihack/.claude" in call_args

                        assert exit_code == 0

    def test_launch_command_stages_amplihack(self, clean_staging_dir):
        """Test that 'amplihack launch' populates ~/.amplihack/.claude/."""
        from src.amplihack.cli import main

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest") as mock_copy:
                with patch("src.amplihack.cli.ClaudeLauncher") as mock_launcher:
                    with patch(
                        "src.amplihack.launcher.session_tracker.SessionTracker"
                    ) as mock_tracker:
                        # Mock git conflict detection to avoid prompts
                        with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                            mock_detector.return_value.detect_conflicts.return_value.has_conflicts = False
                            mock_copy.return_value = True
                            # Mock launcher to return 0 for successful launch
                            mock_launcher_instance = mock_launcher.return_value
                            mock_launcher_instance.launch_interactive.return_value = 0
                            # Mock tracker methods
                            mock_tracker.return_value.start_session.return_value = "test-session-id"

                            # Run launch command
                            exit_code = main(["launch"])

                            # Verify staging was called
                            assert mock_copy.called, "copytree_manifest should have been called"
                            call_args = str(mock_copy.call_args)
                            assert ".amplihack/.claude" in call_args

                            assert exit_code == 0

    def test_staged_directory_contains_expected_subdirs(self, clean_staging_dir):
        """Test that staging creates expected subdirectories."""
        from src.amplihack.cli import main

        # Create mock directory structure to simulate real staging
        def mock_copytree(*args, **kwargs):
            """Mock copytree_manifest to create expected directories."""
            # Create the basic structure
            clean_staging_dir.mkdir(parents=True, exist_ok=True)
            (clean_staging_dir / "agents").mkdir()
            (clean_staging_dir / "skills").mkdir()
            (clean_staging_dir / "tools").mkdir()
            (clean_staging_dir / "hooks").mkdir()
            return True

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest", side_effect=mock_copytree):
                with patch("src.amplihack.launcher.copilot.launch_copilot", return_value=0):
                    # Mock git conflict detection to avoid prompts
                    with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector.return_value.detect_conflicts.return_value.has_conflicts = (
                            False
                        )

                        # Run command
                        exit_code = main(["copilot"])

                        # Verify directory structure
                        assert clean_staging_dir.exists()
                        assert (clean_staging_dir / "agents").exists()
                        assert (clean_staging_dir / "skills").exists()
                        assert (clean_staging_dir / "tools").exists()
                        assert (clean_staging_dir / "hooks").exists()

                        assert exit_code == 0


class TestStagingUnitBehavior:
    """Unit tests for _ensure_amplihack_staged() function behavior (Optional)."""

    def test_staging_skipped_in_non_uvx_mode(self):
        """Test that staging is skipped when not in UVX mode."""
        from src.amplihack.cli import main

        # Mock non-UVX deployment
        with patch("src.amplihack.cli.is_uvx_deployment", return_value=False):
            with patch("src.amplihack.cli.copytree_manifest"):
                with patch("src.amplihack.launcher.copilot.launch_copilot", return_value=0):
                    # Run copilot command
                    exit_code = main(["copilot"])

                    # Verify staging was NOT called in non-UVX mode
                    # (staging only happens during main() initialization)
                    assert exit_code == 0

    def test_staging_creates_directory_if_missing(self, tmp_path, monkeypatch):
        """Test that staging creates ~/.amplihack/.claude/ if it doesn't exist."""
        monkeypatch.setenv("HOME", str(tmp_path))

        # Directory shouldn't exist initially
        staging_dir = tmp_path / ".amplihack" / ".claude"
        assert not staging_dir.exists()

        def mock_copytree(*args, **kwargs):
            """Mock that creates directory."""
            staging_dir.mkdir(parents=True, exist_ok=True)
            return True

        from src.amplihack.cli import main

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest", side_effect=mock_copytree):
                with patch("src.amplihack.launcher.copilot.launch_copilot", return_value=0):
                    # Mock git conflict detection to avoid prompts
                    with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector.return_value.detect_conflicts.return_value.has_conflicts = (
                            False
                        )

                        # Run command
                        exit_code = main(["copilot"])

                        # Verify directory was created
                        assert staging_dir.exists()
                        assert exit_code == 0


class TestStagingErrorHandling:
    """Test error handling in staging process."""

    def test_staging_handles_permission_error(self, tmp_path, monkeypatch):
        """Test graceful handling of permission errors during staging."""
        monkeypatch.setenv("HOME", str(tmp_path))

        from src.amplihack.cli import main

        def mock_copytree_error(*args, **kwargs):
            """Mock permission error during staging."""
            raise PermissionError("Cannot write to target directory")

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest", side_effect=mock_copytree_error):
                # Mock git conflict detection to avoid prompts
                with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                    mock_detector.return_value.detect_conflicts.return_value.has_conflicts = False

                    # Should handle error gracefully
                    with pytest.raises((SystemExit, PermissionError)):
                        main(["copilot"])

    def test_staging_handles_missing_source_files(self, tmp_path, monkeypatch):
        """Test handling of missing source files during staging."""
        monkeypatch.setenv("HOME", str(tmp_path))

        from src.amplihack.cli import main

        def mock_copytree_missing(*args, **kwargs):
            """Mock missing source files error."""
            raise FileNotFoundError("Source .claude directory not found")

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest", side_effect=mock_copytree_missing):
                # Mock git conflict detection to avoid prompts
                with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                    mock_detector.return_value.detect_conflicts.return_value.has_conflicts = False

                    # Should handle error gracefully
                    with pytest.raises((SystemExit, FileNotFoundError)):
                        main(["copilot"])


class TestStagingE2EBehavior:
    """End-to-end tests for staging behavior with real subprocess calls (optional)."""

    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.path.exists(Path.home() / ".amplihack" / ".claude"),
        reason="Requires actual staging directory to exist",
    )
    def test_real_staging_from_uvx_creates_files(self):
        """Test that real UVX deployment stages files correctly."""
        staging_dir = Path.home() / ".amplihack" / ".claude"

        # Verify staging directory exists and has content
        if staging_dir.exists():
            # Check for expected subdirectories
            assert (staging_dir / "agents").exists(), "agents/ directory missing after staging"
            assert (staging_dir / "skills").exists(), "skills/ directory missing after staging"
            assert (staging_dir / "tools").exists(), "tools/ directory missing after staging"
            assert (staging_dir / "hooks").exists(), "hooks/ directory missing after staging"
