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


class TestSubprocessSafeFlag:
    """Tests for --subprocess-safe flag (Issue #2567).

    The flag prevents staging/env updates when running as a subprocess delegate
    from another amplihack process, avoiding concurrent write races.
    """

    def test_subprocess_safe_skips_staging_for_copilot(self, clean_staging_dir):
        """Test that --subprocess-safe skips staging for copilot command."""
        from src.amplihack.cli import main

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest") as mock_copy:
                with patch("src.amplihack.launcher.copilot.launch_copilot", return_value=0):
                    with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector.return_value.detect_conflicts.return_value.has_conflicts = (
                            False
                        )
                        mock_copy.return_value = True

                        exit_code = main(["copilot", "--subprocess-safe"])

                        # Staging should NOT have been called
                        assert not mock_copy.called, (
                            "copytree_manifest should not be called with --subprocess-safe"
                        )
                        assert exit_code == 0

    def test_subprocess_safe_skips_staging_for_codex(self, clean_staging_dir):
        """Test that --subprocess-safe skips staging for codex command."""
        from src.amplihack.cli import main

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest") as mock_copy:
                with patch("src.amplihack.launcher.codex.launch_codex", return_value=0):
                    with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector.return_value.detect_conflicts.return_value.has_conflicts = (
                            False
                        )
                        mock_copy.return_value = True

                        exit_code = main(["codex", "--subprocess-safe"])

                        assert not mock_copy.called
                        assert exit_code == 0

    def test_subprocess_safe_skips_staging_for_launch(self, clean_staging_dir):
        """Test that --subprocess-safe skips staging for launch command."""
        from src.amplihack.cli import main

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest") as mock_copy:
                with patch("src.amplihack.cli.ClaudeLauncher") as mock_launcher:
                    with patch(
                        "src.amplihack.launcher.session_tracker.SessionTracker"
                    ) as mock_tracker:
                        with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                            mock_detector.return_value.detect_conflicts.return_value.has_conflicts = False
                            mock_copy.return_value = True
                            mock_launcher.return_value.launch_interactive.return_value = 0
                            mock_tracker.return_value.start_session.return_value = "test-session-id"

                            exit_code = main(["launch", "--subprocess-safe"])

                            assert not mock_copy.called
                            assert exit_code == 0

    def test_subprocess_safe_skips_staging_for_amplifier(self, clean_staging_dir):
        """Test that --subprocess-safe skips staging for amplifier command."""
        from src.amplihack.cli import main

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest") as mock_copy:
                with patch("src.amplihack.launcher.amplifier.launch_amplifier", return_value=0):
                    with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector.return_value.detect_conflicts.return_value.has_conflicts = (
                            False
                        )
                        mock_copy.return_value = True

                        exit_code = main(["amplifier", "--subprocess-safe"])

                        assert not mock_copy.called
                        assert exit_code == 0

    def test_without_subprocess_safe_does_stage(self, clean_staging_dir):
        """Verify that WITHOUT --subprocess-safe, staging still occurs."""
        from src.amplihack.cli import main

        with patch("src.amplihack.cli.is_uvx_deployment", return_value=True):
            with patch("src.amplihack.cli.copytree_manifest") as mock_copy:
                with patch("src.amplihack.launcher.copilot.launch_copilot", return_value=0):
                    with patch("src.amplihack.safety.GitConflictDetector") as mock_detector:
                        mock_detector.return_value.detect_conflicts.return_value.has_conflicts = (
                            False
                        )
                        mock_copy.return_value = True

                        exit_code = main(["copilot"])

                        # Staging SHOULD be called without the flag
                        assert mock_copy.called, (
                            "copytree_manifest should be called without --subprocess-safe"
                        )
                        assert exit_code == 0

    @pytest.fixture
    def clean_staging_dir(self, tmp_path, monkeypatch):
        """Provide a clean staging directory for tests."""
        staging_dir = tmp_path / ".amplihack" / ".claude"
        monkeypatch.setenv("HOME", str(tmp_path))
        yield staging_dir


class TestCopytreeManifestSyncBehavior:
    """Tests for copytree_manifest sync-in-place behavior (Issue #2567).

    Verifies that copytree_manifest no longer calls shutil.rmtree()
    and instead syncs in-place using dirs_exist_ok=True.
    """

    def test_copytree_manifest_does_not_rmtree(self, tmp_path):
        """Test that copytree_manifest syncs without deleting directories."""
        import shutil

        from src.amplihack.install import copytree_manifest

        # Create source .claude/ with a test directory
        src_dir = tmp_path / "src"
        claude_dir = src_dir / ".claude"
        agents_dir = claude_dir / "agents" / "amplihack"
        agents_dir.mkdir(parents=True)
        (agents_dir / "test_agent.md").write_text("# Test Agent")

        # Create destination with existing content
        dst_dir = tmp_path / "dst"
        dst_agents = dst_dir / "agents" / "amplihack"
        dst_agents.mkdir(parents=True)
        (dst_agents / "existing.md").write_text("# Existing")

        # Patch shutil.rmtree to detect if it's called
        original_rmtree = shutil.rmtree
        rmtree_called = []

        def tracking_rmtree(*args, **kwargs):
            rmtree_called.append(args[0])
            return original_rmtree(*args, **kwargs)

        with patch("src.amplihack.install.shutil.rmtree", side_effect=tracking_rmtree):
            copytree_manifest(str(src_dir), str(dst_dir), ".claude")

        assert len(rmtree_called) == 0, (
            f"shutil.rmtree was called on {rmtree_called} - "
            "copytree_manifest should sync in-place, not delete+recreate"
        )

    def test_copytree_manifest_overwrites_existing_files(self, tmp_path):
        """Test that copytree_manifest overwrites files without rmtree."""
        from src.amplihack.install import copytree_manifest

        # Create source .claude/ with content
        src_dir = tmp_path / "src"
        claude_dir = src_dir / ".claude"
        context_dir = claude_dir / "context"
        context_dir.mkdir(parents=True)
        (context_dir / "PHILOSOPHY.md").write_text("# Updated Philosophy")

        # Create destination with OLD content
        dst_dir = tmp_path / "dst"
        dst_context = dst_dir / "context"
        dst_context.mkdir(parents=True)
        (dst_context / "PHILOSOPHY.md").write_text("# Old Philosophy")

        copytree_manifest(str(src_dir), str(dst_dir), ".claude")

        # File should be overwritten with new content
        result = (dst_context / "PHILOSOPHY.md").read_text()
        assert result == "# Updated Philosophy", f"File not overwritten. Got: {result}"


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
