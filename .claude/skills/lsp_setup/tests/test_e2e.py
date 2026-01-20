"""
End-to-end tests for LSP Auto-Configuration (10% - E2E Tests)

Tests complete user workflows from start to finish.
All tests should FAIL initially (TDD red phase).
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json


class TestCompleteSetupWorkflows:
    """E2E tests for complete setup workflows."""

    def test_first_time_user_full_auto_setup(
        self,
        mock_project_root,
        sample_python_files,
        installed_lsp_binaries,
        mock_npx_cclsp_success,
        mock_env_file,
    ):
        """
        E2E: First-time user with Python project, LSP binaries installed.
        Expected: Full auto-setup completes all 3 layers.
        """
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.plugin_manager import PluginManager
        from lsp_setup.lsp_configurator import LSPConfigurator
        from lsp_setup.status_tracker import StatusTracker

        # User starts with Python project, pyright installed
        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            with patch("subprocess.run", mock_npx_cclsp_success):
                # Simulate user running the skill
                detector = LanguageDetector(mock_project_root)
                languages = detector.detect_languages()

                # Auto-setup flow
                manager = PluginManager()
                manager.install_plugins(languages)

                configurator = LSPConfigurator(mock_project_root)
                configurator.enable_lsp()

                # Verify final state
                tracker = StatusTracker(mock_project_root, languages)
                status = tracker.get_full_status()

                assert status["overall_ready"] is True
                assert configurator.is_lsp_enabled() is True

    def test_first_time_user_no_binaries_manual_setup(
        self, mock_project_root, sample_python_files
    ):
        """
        E2E: First-time user with Python project, no LSP binaries installed.
        Expected: Generate user guidance for manual installation.
        """
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.status_tracker import StatusTracker

        # User starts with Python project, no binaries
        with patch("shutil.which", return_value=None):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = ""

                # Simulate user running the skill
                detector = LanguageDetector(mock_project_root)
                languages = detector.detect_languages()

                tracker = StatusTracker(mock_project_root, languages)
                guidance = tracker.generate_user_guidance()

                # Verify guidance includes all necessary steps
                assert "Layer 1" in guidance
                assert "pyright" in guidance.lower()
                assert "npm install" in guidance.lower() or "pip install" in guidance.lower()
                assert "npx cclsp install" in guidance
                assert "ENABLE_LSP_TOOL=1" in guidance

    def test_multi_language_project_full_setup(
        self,
        mock_project_root,
        sample_mixed_language_files,
        language_to_lsp_mapping,
        mock_npx_cclsp_success,
        mock_env_file,
    ):
        """
        E2E: Multi-language project (Python, TypeScript, Rust, JavaScript).
        Expected: Setup all detected languages.
        """
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.plugin_manager import PluginManager
        from lsp_setup.lsp_configurator import LSPConfigurator
        from lsp_setup.status_tracker import StatusTracker

        # Mock all binaries installed
        def mock_which(binary):
            binary_map = {
                "pyright": "/usr/local/bin/pyright",
                "typescript-language-server": "/usr/local/bin/typescript-language-server",
                "rust-analyzer": "/usr/local/bin/rust-analyzer",
            }
            return binary_map.get(binary)

        with patch("shutil.which", side_effect=mock_which):
            with patch("subprocess.run", mock_npx_cclsp_success):
                # Detect all languages
                detector = LanguageDetector(mock_project_root)
                languages = detector.detect_languages()

                assert len(languages) == 4  # Python, TS, JS, Rust

                # Install plugins for all
                manager = PluginManager()
                results = manager.install_plugins(languages)

                for lang in languages:
                    assert results[lang] is True

                # Configure .env
                configurator = LSPConfigurator(mock_project_root)
                configurator.enable_lsp()

                # Verify all languages ready
                tracker = StatusTracker(mock_project_root, languages)
                status = tracker.get_full_status()

                assert status["overall_ready"] is True

    def test_existing_user_adding_new_language(
        self,
        mock_project_root,
        sample_python_files,
        installed_lsp_binaries,
        mock_npx_cclsp_success,
        mock_env_file,
    ):
        """
        E2E: Existing user with Python setup, adds TypeScript files.
        Expected: Detect new language and extend setup.
        """
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.plugin_manager import PluginManager
        from lsp_setup.status_tracker import StatusTracker

        # Initial setup: Python already configured
        mock_env_file.write_text("ENABLE_LSP_TOOL=1\n")

        # User adds TypeScript files
        (mock_project_root / "index.ts").write_text("// TypeScript")
        (mock_project_root / "utils.ts").write_text("// TypeScript")

        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            with patch("subprocess.run") as mock_run:
                # Mock: Python plugin already installed, TS not installed
                def mock_run_fn(cmd, *args, **kwargs):
                    result = MagicMock()
                    if "list" in cmd:
                        result.stdout = "python\n"  # Only Python installed
                    elif "install" in cmd and "typescript" in cmd:
                        result.returncode = 0
                        result.stdout = "Installed typescript"
                    else:
                        result.returncode = 0
                        result.stdout = ""
                    return result

                mock_run.side_effect = mock_run_fn

                # Detect languages (should find Python + TypeScript)
                detector = LanguageDetector(mock_project_root)
                languages = detector.detect_languages()

                assert "python" in languages
                assert "typescript" in languages

                # Check status
                tracker = StatusTracker(mock_project_root, languages)
                missing = tracker.get_missing_components()

                # TypeScript plugin should be missing
                assert "typescript" in missing["plugins"]

                # Install TypeScript plugin
                manager = PluginManager()
                result = manager.install_plugin("typescript")
                assert result is True

    def test_user_disables_then_re_enables_lsp(
        self, mock_project_root, sample_python_files, mock_env_file
    ):
        """
        E2E: User disables LSP, then re-enables it later.
        Expected: .env updates correctly both times.
        """
        from lsp_setup.lsp_configurator import LSPConfigurator

        configurator = LSPConfigurator(mock_project_root)

        # Enable LSP
        configurator.enable_lsp()
        assert configurator.is_lsp_enabled() is True

        # Disable LSP
        configurator.disable_lsp()
        assert configurator.is_lsp_enabled() is False

        # Re-enable LSP
        configurator.enable_lsp()
        assert configurator.is_lsp_enabled() is True

    def test_troubleshooting_workflow(
        self, mock_project_root, sample_python_files, mock_subprocess_run
    ):
        """
        E2E: User reports LSP not working, troubleshooting flow.
        Expected: Identify specific layer that's broken.
        """
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.status_tracker import StatusTracker

        # Scenario: Layer 1 OK, Layer 2 broken, Layer 3 OK
        with patch("shutil.which", return_value="/usr/local/bin/pyright"):
            mock_subprocess_run.return_value.stdout = ""  # No plugins installed
            (mock_project_root / ".env").write_text("ENABLE_LSP_TOOL=1\n")

            with patch("subprocess.run", mock_subprocess_run):
                detector = LanguageDetector(mock_project_root)
                languages = detector.detect_languages()

                tracker = StatusTracker(mock_project_root, languages)
                issues = tracker.validate_layer_dependencies()

                # Should identify Layer 2 as the problem
                assert len(issues) > 0

                next_action = tracker.get_next_action()
                assert "plugin" in next_action.lower()


class TestEdgeCases:
    """E2E tests for edge cases and unusual scenarios."""

    def test_empty_project_no_languages(self, mock_project_root):
        """
        E2E: Empty project with no source files.
        Expected: Graceful handling with appropriate message.
        """
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.status_tracker import StatusTracker

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert len(languages) == 0

        # Status tracker should handle empty language list
        tracker = StatusTracker(mock_project_root, languages)
        guidance = tracker.generate_user_guidance()

        assert "no languages detected" in guidance.lower() or "empty project" in guidance.lower()

    def test_unsupported_language_project(self, mock_project_root):
        """
        E2E: Project with unsupported language files only.
        Expected: Report no supported languages found.
        """
        from lsp_setup.language_detector import LanguageDetector

        # Create files for unsupported language (e.g., .txt, .md only)
        (mock_project_root / "README.md").write_text("# Project")
        (mock_project_root / "data.txt").write_text("Some data")

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        assert len(languages) == 0

    def test_large_project_with_many_files(self, mock_project_root):
        """
        E2E: Large project with 100+ files across multiple languages.
        Expected: Efficient detection and setup.
        """
        from lsp_setup.language_detector import LanguageDetector

        # Create 50 Python files
        for i in range(50):
            (mock_project_root / f"file{i}.py").write_text("# Python")

        # Create 30 TypeScript files
        for i in range(30):
            (mock_project_root / f"file{i}.ts").write_text("// TypeScript")

        # Create 20 JavaScript files
        for i in range(20):
            (mock_project_root / f"file{i}.js").write_text("// JavaScript")

        detector = LanguageDetector(mock_project_root)
        languages_with_scores = detector.detect_languages_with_confidence()

        assert languages_with_scores["python"] == 50
        assert languages_with_scores["typescript"] == 30
        assert languages_with_scores["javascript"] == 20

    def test_project_with_gitignore_exclusions(self, mock_project_root):
        """
        E2E: Project with .gitignore excluding certain directories.
        Expected: Respect .gitignore when detecting languages.
        """
        from lsp_setup.language_detector import LanguageDetector

        # Create .gitignore
        (mock_project_root / ".gitignore").write_text("build/\n*.tmp\n")

        # Create files (some should be ignored)
        (mock_project_root / "main.py").write_text("# Python")
        (mock_project_root / "build").mkdir()
        (mock_project_root / "build" / "generated.py").write_text("# Should ignore")
        (mock_project_root / "temp.tmp").write_text("# Should ignore")

        detector = LanguageDetector(mock_project_root)
        languages_with_scores = detector.detect_languages_with_confidence()

        # Should only count main.py
        assert languages_with_scores.get("python", 0) == 1


class TestPlatformSpecific:
    """E2E tests for platform-specific scenarios."""

    def test_macos_setup_workflow(
        self,
        mock_project_root,
        sample_python_files,
        mock_platform_system,
        installed_lsp_binaries,
    ):
        """
        E2E: Setup workflow on macOS.
        Expected: macOS-specific installation guidance.
        """
        from lsp_setup.status_tracker import StatusTracker

        mock_platform_system.return_value = "Darwin"

        with patch("platform.system", mock_platform_system):
            with patch("shutil.which", return_value=None):
                tracker = StatusTracker(mock_project_root, ["python"])
                guidance = tracker.generate_user_guidance()

                # Should include macOS-specific commands (Homebrew)
                assert "brew" in guidance.lower() or "macos" in guidance.lower()

    def test_linux_setup_workflow(
        self, mock_project_root, sample_python_files, mock_platform_system
    ):
        """
        E2E: Setup workflow on Linux.
        Expected: Linux-specific installation guidance.
        """
        from lsp_setup.status_tracker import StatusTracker

        mock_platform_system.return_value = "Linux"

        with patch("platform.system", mock_platform_system):
            with patch("shutil.which", return_value=None):
                tracker = StatusTracker(mock_project_root, ["python"])
                guidance = tracker.generate_user_guidance()

                # Should include Linux-specific commands (apt/dnf)
                assert "apt" in guidance.lower() or "dnf" in guidance.lower() or "linux" in guidance.lower()


class TestUserExperience:
    """E2E tests for user experience scenarios."""

    def test_clear_progress_reporting(
        self,
        mock_project_root,
        sample_python_files,
        installed_lsp_binaries,
        mock_npx_cclsp_success,
    ):
        """
        E2E: User sees clear progress through setup.
        Expected: Percentage completion updates correctly.
        """
        from lsp_setup.language_detector import LanguageDetector
        from lsp_setup.status_tracker import StatusTracker
        from lsp_setup.plugin_manager import PluginManager
        from lsp_setup.lsp_configurator import LSPConfigurator

        detector = LanguageDetector(mock_project_root)
        languages = detector.detect_languages()

        with patch("shutil.which", side_effect=lambda x: installed_lsp_binaries.get(x)):
            with patch("subprocess.run", mock_npx_cclsp_success):
                tracker = StatusTracker(mock_project_root, languages)

                # Initial progress
                progress_0 = tracker.get_completion_percentage()

                # After plugin install
                manager = PluginManager()
                manager.install_plugins(languages)
                progress_1 = tracker.get_completion_percentage()

                # After .env config
                configurator = LSPConfigurator(mock_project_root)
                configurator.enable_lsp()
                progress_2 = tracker.get_completion_percentage()

                # Progress should increase
                assert progress_1 > progress_0
                assert progress_2 > progress_1
                assert progress_2 == 100

    def test_helpful_error_messages(self, mock_project_root, sample_python_files):
        """
        E2E: User encounters errors, gets helpful error messages.
        Expected: Clear, actionable error messages.
        """
        from lsp_setup.plugin_manager import PluginManager

        with patch("shutil.which", return_value=None):
            manager = PluginManager()

            # npx not available
            is_available = manager.is_npx_available()
            assert is_available is False

            # Should provide helpful guidance
            # (In real implementation, this would be in error messages)
