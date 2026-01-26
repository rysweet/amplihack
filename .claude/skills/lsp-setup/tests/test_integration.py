"""
Integration tests for LSP Auto-Configuration (30% - Integration Tests)

Tests interactions between multiple modules.
All tests should FAIL initially (TDD red phase).
"""

from unittest.mock import patch


class TestLanguageDetectionIntegration:
    """Integration tests for language detection with configurator."""

    def test_detect_languages_and_check_status(self, mock_project_root, sample_python_files):
        """Test detecting languages and checking their LSP status."""
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.status_tracker import StatusTracker

        # Detect languages
        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        # Check status for detected languages
        with patch("shutil.which", return_value=None):
            tracker = StatusTracker(mock_project_root, languages)
            status = tracker.check_layer_1()

            assert "python" in status
            assert status["python"]["installed"] is False

    def test_detect_languages_and_configure_env(
        self, mock_project_root, sample_mixed_language_files, mock_env_file
    ):
        """Test detecting languages and configuring .env."""
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.lsp_configurator import LSPConfigurator

        # Detect languages
        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert len(languages) > 0

        # Configure LSP
        configurator = LSPConfigurator(mock_project_root)
        result = configurator.enable_lsp()

        assert result is True
        assert mock_env_file.exists()


class TestPluginInstallationIntegration:
    """Integration tests for plugin installation flow."""

    def test_check_binaries_then_install_plugins(
        self, mock_project_root, installed_lsp_binaries, mock_npx_cclsp_success
    ):
        """Test checking Layer 1 before installing Layer 2."""
        from lsp_setup.plugin_manager import PluginManager
        from lsp_setup.status_tracker import StatusTracker

        # Check Layer 1
        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            tracker = StatusTracker(mock_project_root, ["python"])
            layer_1_status = tracker.check_layer_1()

            assert layer_1_status["python"]["installed"] is True

            # Install plugins if binaries exist
            with patch("subprocess.run", mock_npx_cclsp_success):
                manager = PluginManager()
                result = manager.install_plugin("python")

                assert result is True

    def test_install_plugins_for_detected_languages(
        self, mock_project_root, sample_mixed_language_files, mock_npx_cclsp_success
    ):
        """Test installing plugins for all detected languages."""
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.plugin_manager import PluginManager

        # Detect languages
        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        # Install plugins for detected languages
        with patch("subprocess.run", mock_npx_cclsp_success):
            manager = PluginManager()
            results = manager.install_plugins(languages)

            for lang in languages:
                assert results[lang] is True


class TestFullSetupWorkflow:
    """Integration tests for complete setup workflows."""

    def test_full_auto_setup_workflow(
        self,
        mock_project_root,
        sample_python_files,
        installed_lsp_binaries,
        mock_npx_cclsp_success,
        mock_env_file,
    ):
        """Test complete auto-setup workflow: detect -> install -> configure."""
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.lsp_configurator import LSPConfigurator
        from lsp_setup.plugin_manager import PluginManager
        from lsp_setup.status_tracker import StatusTracker

        # Step 1: Detect languages
        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()
        assert "python" in languages

        # Step 2: Check status
        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            tracker = StatusTracker(mock_project_root, languages)
            initial_status = tracker.get_full_status()

            # Layer 1 should be ready
            assert initial_status["layer_1"]["python"]["installed"] is True

            # Step 3: Install plugins
            with patch("subprocess.run", mock_npx_cclsp_success):
                manager = PluginManager()
                plugin_results = manager.install_plugins(languages)
                assert plugin_results["python"] is True

                # Step 4: Configure .env
                configurator = LSPConfigurator(mock_project_root)
                config_result = configurator.enable_lsp()
                assert config_result is True

                # Step 5: Verify final status
                final_status = tracker.get_full_status()
                assert final_status["overall_ready"] is True

    def test_manual_setup_workflow_with_user_guidance(self, mock_project_root, sample_python_files):
        """Test manual setup workflow with user guidance generation."""
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.status_tracker import StatusTracker

        # Detect languages
        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        # Generate guidance for manual setup
        with patch("shutil.which", return_value=None):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = ""

                tracker = StatusTracker(mock_project_root, languages)
                guidance = tracker.generate_user_guidance()

                # Guidance should include all layers
                assert "Layer 1" in guidance
                assert "Layer 2" in guidance
                assert "Layer 3" in guidance
                assert "pyright" in guidance.lower()

    def test_partial_setup_recovery(
        self,
        mock_project_root,
        sample_python_files,
        installed_lsp_binaries,
        mock_subprocess_run,
    ):
        """Test recovering from partial setup (Layer 1 complete, Layer 2 failed)."""
        from lsp_setup.status_tracker import StatusTracker

        # Layer 1 complete
        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            # Layer 2 incomplete
            mock_subprocess_run.return_value.stdout = ""

            with patch("subprocess.run", mock_subprocess_run):
                tracker = StatusTracker(mock_project_root, ["python"])
                missing = tracker.get_missing_components()

                # Should identify Layer 2 as missing
                assert "plugins" in missing
                assert "python" in missing["plugins"]

                # Get next action
                next_action = tracker.get_next_action()
                assert "plugin" in next_action.lower()


class TestErrorHandlingIntegration:
    """Integration tests for error scenarios."""

    def test_handle_missing_npx(self, mock_project_root, sample_python_files):
        """Test handling when npx is not available."""
        from lsp_setup.plugin_manager import PluginManager
        from lsp_setup.status_tracker import StatusTracker

        with patch("shutil.which", return_value=None):
            manager = PluginManager()
            assert manager.is_npx_available() is False

            # Status tracker should warn about npx
            tracker = StatusTracker(mock_project_root, ["python"])
            guidance = tracker.generate_user_guidance()

            assert "npx" in guidance.lower() or "node" in guidance.lower()

    def test_handle_plugin_installation_failure(
        self, mock_project_root, sample_python_files, mock_npx_cclsp_failure
    ):
        """Test handling plugin installation failures."""
        from lsp_setup.plugin_manager import PluginManager

        with patch("subprocess.run", mock_npx_cclsp_failure):
            manager = PluginManager()
            result = manager.install_plugin("python")

            assert result is False

    def test_handle_env_file_permission_error(self, mock_project_root):
        """Test handling permission errors on .env file."""
        from lsp_setup.lsp_configurator import LSPConfigurator

        configurator = LSPConfigurator(mock_project_root)

        with patch("pathlib.Path.write_text", side_effect=PermissionError):
            result = configurator.enable_lsp()
            assert result is False


class TestMultiLanguageIntegration:
    """Integration tests for multi-language projects."""

    def test_setup_multiple_languages_sequentially(
        self,
        mock_project_root,
        sample_mixed_language_files,
        installed_lsp_binaries,
        mock_npx_cclsp_success,
    ):
        """Test setting up multiple languages one by one."""
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.plugin_manager import PluginManager

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            with patch("subprocess.run", mock_npx_cclsp_success):
                manager = PluginManager()

                # Install one by one
                for lang in languages:
                    result = manager.install_plugin(lang)
                    assert result is True

    def test_prioritize_primary_language(self, mock_project_root, sample_mixed_language_files):
        """Test prioritizing primary language (most files) in setup."""
        from lsp_setup.language_detector import LanguageDetector

        detector = LanguageDetector(mock_project_root)
        languages_with_scores = detector.detect_languages_with_confidence()

        # Should be able to identify primary language
        primary_lang = max(languages_with_scores.items(), key=lambda x: x[1])[0]
        assert primary_lang in ["python", "typescript", "javascript", "rust"]


class TestStatusReportingIntegration:
    """Integration tests for status reporting."""

    def test_generate_comprehensive_status_report(
        self,
        mock_project_root,
        sample_python_files,
        installed_lsp_binaries,
        mock_subprocess_run,
        mock_env_file,
    ):
        """Test generating comprehensive status report."""
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.status_tracker import StatusTracker

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            mock_subprocess_run.return_value.stdout = "python\n"
            mock_env_file.write_text("ENABLE_LSP_TOOL=1\n")

            with patch("subprocess.run", mock_subprocess_run):
                tracker = StatusTracker(mock_project_root, languages)
                report = tracker.export_status_report()

                assert report["overall_ready"] is True
                assert "python" in report["languages"]
                assert report["layer_1"]["python"]["installed"] is True
                assert report["layer_2"]["python"]["installed"] is True
                assert report["layer_3"]["enabled"] is True

    def test_track_setup_progress_over_time(
        self, mock_project_root, sample_python_files, installed_lsp_binaries
    ):
        """Test tracking setup progress as layers are completed."""
        from lsp_setup.status_tracker import StatusTracker

        tracker = StatusTracker(mock_project_root, ["python"])

        # Initial state (nothing configured)
        with patch("shutil.which", return_value=None):
            initial_percentage = tracker.get_completion_percentage()
            assert initial_percentage == 0

        # Layer 1 complete
        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            layer_1_percentage = tracker.get_completion_percentage()
            assert layer_1_percentage > initial_percentage
