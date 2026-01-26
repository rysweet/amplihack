"""
Unit tests for status_tracker.py (60% - Unit Tests)

Tests three-layer status tracking and user guidance generation.
All tests should FAIL initially (TDD red phase).
"""

from unittest.mock import patch


class TestStatusTracker:
    """Test suite for StatusTracker class."""

    def test_check_all_layers_fully_configured(
        self, mock_project_root, installed_lsp_binaries, mock_subprocess_run, mock_env_file
    ):
        """Test status when all 3 layers are configured."""
        from lsp_setup.status_tracker import StatusTracker

        # Layer 1: LSP binaries installed
        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            # Layer 2: Plugins installed
            mock_subprocess_run.return_value.stdout = "python\ntypescript\nrust\n"

            # Layer 3: .env configured
            mock_env_file.write_text("ENABLE_LSP_TOOL=1\n")

            with patch("subprocess.run", mock_subprocess_run):
                tracker = StatusTracker(mock_project_root, ["python", "typescript"])
                status = tracker.get_full_status()

                assert status["layer_1"]["python"]["installed"] is True
                assert status["layer_2"]["python"]["installed"] is True
                assert status["layer_3"]["enabled"] is True
                assert status["overall_ready"] is True

    def test_check_layer_1_missing_binaries(self, mock_project_root, missing_lsp_binaries):
        """Test status when Layer 1 (LSP binaries) are missing."""
        from lsp_setup.status_tracker import StatusTracker

        with patch("shutil.which", return_value=None):
            tracker = StatusTracker(mock_project_root, ["python"])
            status = tracker.check_layer_1()

            assert status["python"]["installed"] is False
            assert "install_guide" in status["python"]

    def test_check_layer_1_with_installed_binaries(self, mock_project_root, installed_lsp_binaries):
        """Test status when Layer 1 (LSP binaries) are installed."""
        from lsp_setup.status_tracker import StatusTracker

        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            tracker = StatusTracker(mock_project_root, ["python", "rust"])
            status = tracker.check_layer_1()

            assert status["python"]["installed"] is True
            assert status["python"]["path"] == "/usr/local/bin/pyright"
            assert status["rust"]["installed"] is True

    def test_check_layer_2_missing_plugins(self, mock_project_root, mock_subprocess_run):
        """Test status when Layer 2 (Claude Code plugins) are missing."""
        from lsp_setup.status_tracker import StatusTracker

        # Mock no plugins installed
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = ""

        with patch("subprocess.run", mock_subprocess_run):
            tracker = StatusTracker(mock_project_root, ["python", "typescript"])
            status = tracker.check_layer_2()

            assert status["python"]["installed"] is False
            assert status["typescript"]["installed"] is False

    def test_check_layer_2_with_installed_plugins(self, mock_project_root, mock_subprocess_run):
        """Test status when Layer 2 (Claude Code plugins) are installed."""
        from lsp_setup.status_tracker import StatusTracker

        # Mock plugins installed
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = "python\ntypescript\n"

        with patch("subprocess.run", mock_subprocess_run):
            tracker = StatusTracker(mock_project_root, ["python", "typescript"])
            status = tracker.check_layer_2()

            assert status["python"]["installed"] is True
            assert status["typescript"]["installed"] is True

    def test_check_layer_3_enabled(self, mock_project_root, mock_env_file):
        """Test status when Layer 3 (.env) is configured."""
        from lsp_setup.status_tracker import StatusTracker

        mock_env_file.write_text("ENABLE_LSP_TOOL=1\n")

        tracker = StatusTracker(mock_project_root, ["python"])
        status = tracker.check_layer_3()

        assert status["enabled"] is True
        assert status["env_file_exists"] is True

    def test_check_layer_3_disabled(self, mock_project_root, mock_env_file):
        """Test status when Layer 3 (.env) is not configured."""
        from lsp_setup.status_tracker import StatusTracker

        mock_env_file.write_text("ENABLE_LSP_TOOL=0\n")

        tracker = StatusTracker(mock_project_root, ["python"])
        status = tracker.check_layer_3()

        assert status["enabled"] is False

    def test_check_layer_3_missing(self, mock_project_root):
        """Test status when .env file doesn't exist."""
        from lsp_setup.status_tracker import StatusTracker

        tracker = StatusTracker(mock_project_root, ["python"])
        status = tracker.check_layer_3()

        assert status["enabled"] is False
        assert status["env_file_exists"] is False

    def test_generate_user_guidance_all_missing(self, mock_project_root):
        """Test generating guidance when all layers need setup."""
        from lsp_setup.status_tracker import StatusTracker

        with patch("shutil.which", return_value=None):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = ""

                tracker = StatusTracker(mock_project_root, ["python"])
                guidance = tracker.generate_user_guidance()

                assert "Layer 1" in guidance
                assert "Layer 2" in guidance
                assert "Layer 3" in guidance
                assert "pyright" in guidance.lower()

    def test_generate_user_guidance_only_layer_3_missing(
        self, mock_project_root, installed_lsp_binaries, mock_subprocess_run
    ):
        """Test generating guidance when only .env needs setup."""
        from lsp_setup.status_tracker import StatusTracker

        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            mock_subprocess_run.return_value.stdout = "python\n"

            with patch("subprocess.run", mock_subprocess_run):
                tracker = StatusTracker(mock_project_root, ["python"])
                guidance = tracker.generate_user_guidance()

                assert "Layer 1" in guidance
                assert "✓" in guidance  # Should show checkmarks for completed layers
                assert "Layer 3" in guidance
                assert "ENABLE_LSP_TOOL=1" in guidance

    def test_generate_user_guidance_fully_configured(
        self, mock_project_root, installed_lsp_binaries, mock_subprocess_run, mock_env_file
    ):
        """Test generating guidance when everything is configured."""
        from lsp_setup.status_tracker import StatusTracker

        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            mock_subprocess_run.return_value.stdout = "python\n"
            mock_env_file.write_text("ENABLE_LSP_TOOL=1\n")

            with patch("subprocess.run", mock_subprocess_run):
                tracker = StatusTracker(mock_project_root, ["python"])
                guidance = tracker.generate_user_guidance()

                assert "ready" in guidance.lower() or "configured" in guidance.lower()
                assert "✓" in guidance

    def test_get_next_action(self, mock_project_root):
        """Test getting the next action user should take."""
        from lsp_setup.status_tracker import StatusTracker

        with patch("shutil.which", return_value=None):
            tracker = StatusTracker(mock_project_root, ["python"])
            next_action = tracker.get_next_action()

            assert "install" in next_action.lower()
            assert "pyright" in next_action.lower()

    def test_get_missing_components(self, mock_project_root):
        """Test identifying all missing components."""
        from lsp_setup.status_tracker import StatusTracker

        with patch("shutil.which", return_value=None):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = ""

                tracker = StatusTracker(mock_project_root, ["python", "rust"])
                missing = tracker.get_missing_components()

                assert "binaries" in missing
                assert "python" in missing["binaries"]
                assert "rust" in missing["binaries"]
                assert "plugins" in missing
                assert "env_config" in missing

    def test_get_completion_percentage(
        self, mock_project_root, installed_lsp_binaries, mock_subprocess_run
    ):
        """Test calculating setup completion percentage."""
        from lsp_setup.status_tracker import StatusTracker

        # Layer 1 complete, Layer 2 and 3 incomplete
        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            mock_subprocess_run.return_value.stdout = ""

            with patch("subprocess.run", mock_subprocess_run):
                tracker = StatusTracker(mock_project_root, ["python"])
                percentage = tracker.get_completion_percentage()

                # 1 out of 3 layers complete = ~33%
                assert 30 <= percentage <= 40

    def test_validate_layer_dependencies(self, mock_project_root):
        """Test validating that layers are set up in correct order."""
        from lsp_setup.status_tracker import StatusTracker

        # Layer 2 can't be complete without Layer 1
        with patch("shutil.which", return_value=None):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = "python\n"

                tracker = StatusTracker(mock_project_root, ["python"])
                issues = tracker.validate_layer_dependencies()

                assert len(issues) > 0
                assert any("Layer 1" in issue for issue in issues)

    def test_export_status_report(self, mock_project_root, installed_lsp_binaries):
        """Test exporting detailed status report."""
        from lsp_setup.status_tracker import StatusTracker

        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            tracker = StatusTracker(mock_project_root, ["python"])
            report = tracker.export_status_report()

            assert "timestamp" in report
            assert "languages" in report
            assert "layer_1" in report
            assert "layer_2" in report
            assert "layer_3" in report

    def test_get_troubleshooting_tips(self, mock_project_root):
        """Test generating troubleshooting tips based on status."""
        from lsp_setup.status_tracker import StatusTracker

        with patch("shutil.which", return_value=None):
            tracker = StatusTracker(mock_project_root, ["python"])
            tips = tracker.get_troubleshooting_tips()

            assert isinstance(tips, list)
            assert len(tips) > 0
            assert any("install" in tip.lower() for tip in tips)

    def test_check_platform_specific_requirements_macos(
        self, mock_project_root, mock_platform_system
    ):
        """Test platform-specific requirements on macOS."""
        from lsp_setup.status_tracker import StatusTracker

        mock_platform_system.return_value = "Darwin"

        with patch("platform.system", mock_platform_system):
            tracker = StatusTracker(mock_project_root, ["python"])
            platform_reqs = tracker.get_platform_requirements()

            assert "macos" in platform_reqs.lower() or "darwin" in platform_reqs.lower()

    def test_check_platform_specific_requirements_linux(
        self, mock_project_root, mock_platform_system
    ):
        """Test platform-specific requirements on Linux."""
        from lsp_setup.status_tracker import StatusTracker

        mock_platform_system.return_value = "Linux"

        with patch("platform.system", mock_platform_system):
            tracker = StatusTracker(mock_project_root, ["python"])
            platform_reqs = tracker.get_platform_requirements()

            assert "linux" in platform_reqs.lower()

    def test_get_install_commands_for_language(self, mock_project_root):
        """Test getting installation commands for specific language."""
        from lsp_setup.status_tracker import StatusTracker

        tracker = StatusTracker(mock_project_root, ["python"])
        commands = tracker.get_install_commands("python")

        assert "layer_1" in commands
        assert "layer_2" in commands
        assert "npx cclsp install" in commands["layer_2"]

    def test_estimate_setup_time(self, mock_project_root):
        """Test estimating time required for remaining setup."""
        from lsp_setup.status_tracker import StatusTracker

        with patch("shutil.which", return_value=None):
            tracker = StatusTracker(mock_project_root, ["python", "rust", "typescript"])
            estimate = tracker.estimate_setup_time()

            assert isinstance(estimate, dict)
            assert "minutes" in estimate or "seconds" in estimate

    def test_track_multiple_languages(self, mock_project_root):
        """Test tracking status for multiple languages simultaneously."""
        from lsp_setup.status_tracker import StatusTracker

        languages = ["python", "typescript", "rust", "go"]
        tracker = StatusTracker(mock_project_root, languages)

        with patch("shutil.which", return_value=None):
            status = tracker.check_layer_1()

            for lang in languages:
                assert lang in status
                assert "installed" in status[lang]
