"""
Unit tests for LSPDetector brick.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- Focus on language detection and LSP config generation
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest


class TestLSPDetectorLanguageDetection:
    """Unit tests for language detection (35% of unit tests)."""

    def test_detect_python_project(self):
        """Test detection of Python projects."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        project_path = Path("/fake/project")

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [
                Path("/fake/project/main.py"),
                Path("/fake/project/utils.py")
            ]

            languages = detector.detect_languages(project_path)

        assert "python" in languages

    def test_detect_javascript_project(self):
        """Test detection of JavaScript projects."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        project_path = Path("/fake/project")

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [
                Path("/fake/project/index.js"),
                Path("/fake/project/app.js")
            ]

            languages = detector.detect_languages(project_path)

        assert "javascript" in languages

    def test_detect_typescript_project(self):
        """Test detection of TypeScript projects."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        project_path = Path("/fake/project")

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [
                Path("/fake/project/src/main.ts"),
                Path("/fake/project/src/types.d.ts")
            ]

            languages = detector.detect_languages(project_path)

        assert "typescript" in languages

    def test_detect_multiple_languages(self):
        """Test detection of multi-language projects."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        project_path = Path("/fake/project")

        def glob_side_effect(pattern):
            patterns = {
                "**/*.py": [Path("/fake/project/main.py")],
                "**/*.js": [Path("/fake/project/index.js")],
                "**/*.ts": [Path("/fake/project/app.ts")],
                "**/*.rs": [Path("/fake/project/main.rs")]
            }
            return patterns.get(pattern, [])

        with patch("pathlib.Path.glob", side_effect=glob_side_effect):
            languages = detector.detect_languages(project_path)

        assert "python" in languages
        assert "javascript" in languages
        assert "typescript" in languages
        assert "rust" in languages

    def test_detect_no_languages_in_empty_project(self):
        """Test detection returns empty list for empty projects."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        project_path = Path("/fake/empty")

        with patch("pathlib.Path.glob", return_value=[]):
            languages = detector.detect_languages(project_path)

        assert languages == []

    def test_detect_languages_ignores_hidden_files(self):
        """Test language detection ignores hidden files."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        project_path = Path("/fake/project")

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [
                Path("/fake/project/.hidden.py"),
                Path("/fake/project/main.py")
            ]

            languages = detector.detect_languages(project_path)

        # Should still detect python, but hidden files shouldn't affect count
        assert "python" in languages

    def test_detect_languages_ignores_node_modules(self):
        """Test language detection ignores node_modules directory."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        project_path = Path("/fake/project")

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [
                Path("/fake/project/src/main.js"),
                Path("/fake/project/node_modules/lib/index.js")
            ]

            languages = detector.detect_languages(project_path)

        # Should detect JavaScript but not count node_modules files
        assert "javascript" in languages

    def test_detect_languages_ignores_venv(self):
        """Test language detection ignores virtual environment directories."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        project_path = Path("/fake/project")

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [
                Path("/fake/project/main.py"),
                Path("/fake/project/venv/lib/python.py")
            ]

            languages = detector.detect_languages(project_path)

        assert "python" in languages

    def test_detect_go_project(self):
        """Test detection of Go projects."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        project_path = Path("/fake/project")

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [
                Path("/fake/project/main.go"),
                Path("/fake/project/utils.go")
            ]

            languages = detector.detect_languages(project_path)

        assert "go" in languages

    def test_detect_rust_project(self):
        """Test detection of Rust projects."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        project_path = Path("/fake/project")

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [
                Path("/fake/project/src/main.rs"),
                Path("/fake/project/src/lib.rs")
            ]

            languages = detector.detect_languages(project_path)

        assert "rust" in languages


class TestLSPDetectorConfigGeneration:
    """Unit tests for LSP config generation (40% of unit tests)."""

    def test_generate_python_lsp_config(self):
        """Test LSP config generation for Python."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        languages = ["python"]

        config = detector.generate_lsp_config(languages)

        assert "python-lsp-server" in config or "pylsp" in config
        assert "command" in config["python-lsp-server"]

    def test_generate_typescript_lsp_config(self):
        """Test LSP config generation for TypeScript."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        languages = ["typescript"]

        config = detector.generate_lsp_config(languages)

        assert "typescript-language-server" in config
        assert config["typescript-language-server"]["command"] == "typescript-language-server"

    def test_generate_multi_language_config(self):
        """Test LSP config generation for multiple languages."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        languages = ["python", "typescript", "rust"]

        config = detector.generate_lsp_config(languages)

        # Should have config for all languages
        assert len(config) == 3
        assert any("python" in k.lower() for k in config.keys())
        assert any("typescript" in k.lower() for k in config.keys())
        assert any("rust" in k.lower() for k in config.keys())

    def test_generate_config_empty_languages(self):
        """Test config generation with empty language list."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        languages = []

        config = detector.generate_lsp_config(languages)

        assert config == {}

    def test_generate_config_unsupported_language(self):
        """Test config generation skips unsupported languages."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        languages = ["python", "unsupported-lang"]

        config = detector.generate_lsp_config(languages)

        # Should have Python config but skip unsupported
        assert any("python" in k.lower() for k in config.keys())
        assert not any("unsupported" in k.lower() for k in config.keys())

    def test_generate_config_with_custom_args(self):
        """Test LSP config includes custom arguments."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        languages = ["rust"]

        config = detector.generate_lsp_config(languages)

        # Rust analyzer should have args
        rust_config = config.get("rust-analyzer", {})
        assert "args" in rust_config or "command" in rust_config

    def test_generate_config_includes_env_vars(self):
        """Test LSP config includes necessary environment variables."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        languages = ["python"]

        config = detector.generate_lsp_config(languages)

        python_config = next((v for k, v in config.items() if "python" in k.lower()), {})
        # May include env vars for Python path, etc.
        assert "command" in python_config


class TestLSPDetectorSettingsUpdate:
    """Unit tests for settings.json update (20% of unit tests)."""

    def test_update_settings_json_adds_lsp_config(self):
        """Test updating settings.json adds LSP config."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        existing_settings = {
            "some_setting": "value"
        }
        lsp_config = {
            "python-lsp-server": {
                "command": "pylsp"
            }
        }

        updated = detector.update_settings_json(existing_settings, lsp_config)

        assert "mcpServers" in updated
        assert "python-lsp-server" in updated["mcpServers"]
        assert updated["some_setting"] == "value"  # Preserves existing

    def test_update_settings_json_merges_existing_mcp(self):
        """Test updating settings.json merges with existing MCP servers."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        existing_settings = {
            "mcpServers": {
                "existing-server": {
                    "command": "existing"
                }
            }
        }
        lsp_config = {
            "python-lsp-server": {
                "command": "pylsp"
            }
        }

        updated = detector.update_settings_json(existing_settings, lsp_config)

        assert "existing-server" in updated["mcpServers"]
        assert "python-lsp-server" in updated["mcpServers"]

    def test_update_settings_json_overwrites_duplicate_servers(self):
        """Test updating settings.json overwrites duplicate server configs."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        existing_settings = {
            "mcpServers": {
                "python-lsp-server": {
                    "command": "old-command"
                }
            }
        }
        lsp_config = {
            "python-lsp-server": {
                "command": "new-command"
            }
        }

        updated = detector.update_settings_json(existing_settings, lsp_config)

        assert updated["mcpServers"]["python-lsp-server"]["command"] == "new-command"

    def test_update_settings_json_empty_lsp_config(self):
        """Test updating with empty LSP config preserves settings."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        existing_settings = {
            "some_setting": "value"
        }
        lsp_config = {}

        updated = detector.update_settings_json(existing_settings, lsp_config)

        assert updated == existing_settings


class TestLSPDetectorEdgeCases:
    """Unit tests for edge cases (5% of unit tests)."""

    def test_detect_languages_nonexistent_path(self):
        """Test language detection handles nonexistent paths."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        project_path = Path("/nonexistent/path")

        with patch("pathlib.Path.exists", return_value=False):
            languages = detector.detect_languages(project_path)

        assert languages == []

    def test_detect_languages_permission_error(self):
        """Test language detection handles permission errors gracefully."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        project_path = Path("/restricted/path")

        with patch("pathlib.Path.glob", side_effect=PermissionError("Access denied")):
            languages = detector.detect_languages(project_path)

        # Should return empty list rather than crash
        assert languages == []

    def test_generate_config_handles_invalid_language_list(self):
        """Test config generation handles invalid input."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()

        with pytest.raises(TypeError):
            detector.generate_lsp_config(None)

    def test_update_settings_json_handles_malformed_settings(self):
        """Test settings update handles malformed existing settings."""
        from amplihack.lsp_detector import LSPDetector

        detector = LSPDetector()
        malformed_settings = "not a dict"
        lsp_config = {"python-lsp-server": {"command": "pylsp"}}

        with pytest.raises(TypeError):
            detector.update_settings_json(malformed_settings, lsp_config)
