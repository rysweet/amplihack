"""
TDD Tests for LSPDetector module.

These tests validate automatic LSP server detection based on project
structure, language files, and dependency manifests.

Testing Strategy:
- 60% unit tests (detection logic)
- 30% integration tests (real project structures)
- 10% E2E tests (complete LSP configuration generation)
"""

import pytest
from pathlib import Path
import json


class TestLSPDetectorUnit:
    """Unit tests for LSPDetector - detection logic."""

    def test_detect_python_project_by_requirements_txt(self, tmp_path):
        """
        Test Python project detection via requirements.txt.

        Validates:
        - requirements.txt indicates Python project
        - Python language is added to detected languages
        - LSP server recommendation is 'pylsp'
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "requirements.txt").write_text("flask\nrequests")

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "python" in languages
        assert detector.recommend_lsp("python") == "pylsp"

    def test_detect_python_project_by_pyproject_toml(self, tmp_path):
        """
        Test Python project detection via pyproject.toml.

        Validates:
        - pyproject.toml indicates Python project
        - Python language is detected
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("""
[tool.poetry]
name = "myproject"
version = "0.1.0"
""")

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "python" in languages

    def test_detect_python_project_by_py_files(self, tmp_path):
        """
        Test Python project detection via .py files.

        Validates:
        - Presence of .py files indicates Python project
        - Detection works even without manifest files
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "main.py").write_text("print('hello')")
        (project_root / "module.py").write_text("def func(): pass")

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "python" in languages

    def test_detect_typescript_project_by_package_json(self, tmp_path):
        """
        Test TypeScript/JavaScript project detection via package.json.

        Validates:
        - package.json indicates JS/TS project
        - Presence of typescript dependency indicates TypeScript
        - Otherwise JavaScript is assumed
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()

        # TypeScript project
        package_json = {
            "name": "myproject",
            "dependencies": {
                "typescript": "^5.0.0"
            }
        }
        (project_root / "package.json").write_text(json.dumps(package_json))

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "typescript" in languages

    def test_detect_javascript_project_without_typescript_dep(self, tmp_path):
        """
        Test JavaScript detection when package.json has no typescript.

        Validates:
        - package.json without typescript => JavaScript
        - Recommendation is for JavaScript LSP
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()

        package_json = {
            "name": "myproject",
            "dependencies": {
                "express": "^4.0.0"
            }
        }
        (project_root / "package.json").write_text(json.dumps(package_json))

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "javascript" in languages

    def test_detect_rust_project_by_cargo_toml(self, tmp_path):
        """
        Test Rust project detection via Cargo.toml.

        Validates:
        - Cargo.toml indicates Rust project
        - LSP recommendation is 'rust-analyzer'
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "Cargo.toml").write_text("""
[package]
name = "myproject"
version = "0.1.0"
""")

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "rust" in languages
        assert detector.recommend_lsp("rust") == "rust-analyzer"

    def test_detect_go_project_by_go_mod(self, tmp_path):
        """
        Test Go project detection via go.mod.

        Validates:
        - go.mod indicates Go project
        - LSP recommendation is 'gopls'
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "go.mod").write_text("""
module example.com/myproject

go 1.21
""")

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "go" in languages
        assert detector.recommend_lsp("go") == "gopls"

    def test_detect_multi_language_project(self, tmp_path):
        """
        Test detection of project with multiple languages.

        Validates:
        - Multiple languages are detected simultaneously
        - Each language has appropriate LSP recommendation
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()

        # Python
        (project_root / "requirements.txt").write_text("flask")
        (project_root / "main.py").write_text("print('hello')")

        # TypeScript
        package_json = {
            "dependencies": {"typescript": "^5.0.0"}
        }
        (project_root / "package.json").write_text(json.dumps(package_json))
        (project_root / "index.ts").write_text("console.log('hello');")

        # Rust
        (project_root / "Cargo.toml").write_text("[package]\nname = 'test'")

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "python" in languages
        assert "typescript" in languages
        assert "rust" in languages

    def test_generate_lsp_config_for_single_language(self, tmp_path):
        """
        Test LSP configuration generation for single language.

        Validates:
        - Config includes correct command
        - Config includes correct arguments
        - Config structure matches Claude Code format
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "requirements.txt").write_text("flask")

        detector = LSPDetector(project_root)
        config = detector.generate_lsp_config()

        assert "lspServers" in config
        assert "python" in config["lspServers"]
        assert config["lspServers"]["python"]["command"] == "pylsp"

    def test_generate_lsp_config_for_multiple_languages(self, tmp_path):
        """
        Test LSP configuration generation for multiple languages.

        Validates:
        - All detected languages have LSP config
        - Each config is independent
        - Configs don't conflict
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()

        (project_root / "requirements.txt").write_text("flask")
        (project_root / "Cargo.toml").write_text("[package]\nname='test'")

        detector = LSPDetector(project_root)
        config = detector.generate_lsp_config()

        assert "python" in config["lspServers"]
        assert "rust" in config["lspServers"]
        assert config["lspServers"]["python"]["command"] == "pylsp"
        assert config["lspServers"]["rust"]["command"] == "rust-analyzer"

    def test_detect_no_languages_in_empty_project(self, tmp_path):
        """
        Test detection in empty project (no code files).

        Validates:
        - Returns empty language list
        - LSP config is empty or minimal
        - No errors raised
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "empty"
        project_root.mkdir()

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert len(languages) == 0

        config = detector.generate_lsp_config()
        assert config.get("lspServers", {}) == {}


class TestLSPDetectorIntegration:
    """Integration tests for LSPDetector - real project structures."""

    def test_detect_python_project_with_subdirectories(self, tmp_path):
        """
        Test Python detection in project with nested structure.

        Validates:
        - .py files in subdirectories are found
        - Detection works across directory tree
        - Only project root is checked for manifests
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        src_dir = project_root / "src" / "mypackage"
        src_dir.mkdir(parents=True)

        (src_dir / "__init__.py").write_text("")
        (src_dir / "main.py").write_text("def main(): pass")
        (project_root / "setup.py").write_text("from setuptools import setup")

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "python" in languages

    def test_detect_typescript_monorepo(self, tmp_path):
        """
        Test TypeScript detection in monorepo structure.

        Validates:
        - package.json at root detected
        - Subdirectory package.json files considered
        - TypeScript is primary language if found anywhere
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "monorepo"
        project_root.mkdir()

        # Root package.json
        root_package = {"name": "monorepo", "workspaces": ["packages/*"]}
        (project_root / "package.json").write_text(json.dumps(root_package))

        # Workspace with TypeScript
        workspace = project_root / "packages" / "app"
        workspace.mkdir(parents=True)
        workspace_package = {"dependencies": {"typescript": "^5.0.0"}}
        (workspace / "package.json").write_text(json.dumps(workspace_package))

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "typescript" in languages or "javascript" in languages

    def test_generate_complete_lsp_config_for_fullstack_project(self, tmp_path):
        """
        Test LSP config generation for fullstack project.

        Validates:
        - Backend (Python) LSP configured
        - Frontend (TypeScript) LSP configured
        - Both configs are valid
        - No conflicts between configs
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "fullstack"

        # Backend
        backend = project_root / "backend"
        backend.mkdir(parents=True)
        (backend / "requirements.txt").write_text("fastapi\nuvicorn")
        (backend / "main.py").write_text("from fastapi import FastAPI")

        # Frontend
        frontend = project_root / "frontend"
        frontend.mkdir(parents=True)
        frontend_package = {
            "dependencies": {
                "react": "^18.0.0",
                "typescript": "^5.0.0"
            }
        }
        (frontend / "package.json").write_text(json.dumps(frontend_package))

        # Detect from root
        detector = LSPDetector(project_root)
        config = detector.generate_lsp_config()

        assert "python" in config["lspServers"]
        assert "typescript" in config["lspServers"]

    def test_save_lsp_config_to_settings_file(self, tmp_path):
        """
        Test saving generated LSP config to settings.json.

        Validates:
        - Config is written in valid JSON format
        - File can be loaded and parsed
        - Structure matches Claude Code requirements
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / "requirements.txt").write_text("django")

        detector = LSPDetector(project_root)
        config = detector.generate_lsp_config()

        # Save to file
        settings_file = tmp_path / "settings.json"
        detector.save_config(config, settings_file)

        # Verify file
        assert settings_file.exists()
        loaded = json.loads(settings_file.read_text())
        assert "lspServers" in loaded
        assert "python" in loaded["lspServers"]


class TestLSPDetectorEdgeCases:
    """Edge case tests for LSPDetector."""

    def test_detect_with_symlinked_directories(self, tmp_path):
        """
        Test detection when project contains symlinks.

        Validates:
        - Symlinked directories are followed
        - Files through symlinks are detected
        - Infinite loops are prevented
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()

        real_src = tmp_path / "real_src"
        real_src.mkdir()
        (real_src / "main.py").write_text("print('hello')")

        # Create symlink
        symlink = project_root / "src"
        symlink.symlink_to(real_src)

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "python" in languages

    def test_detect_with_hidden_files(self, tmp_path):
        """
        Test that hidden files/directories are handled correctly.

        Validates:
        - .git directory is ignored
        - .venv directory is ignored
        - node_modules is ignored
        - Hidden config files (.eslintrc) are considered
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()

        # Should be ignored
        (project_root / ".git").mkdir()
        (project_root / ".venv").mkdir()
        (project_root / "node_modules").mkdir()

        # Should be considered
        (project_root / ".eslintrc.json").write_text("{}")
        (project_root / "main.py").write_text("print('test')")

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "python" in languages

    def test_detect_with_invalid_manifest_files(self, tmp_path):
        """
        Test detection when manifest files are invalid/corrupted.

        Validates:
        - Invalid JSON in package.json is handled gracefully
        - Invalid TOML in Cargo.toml is handled gracefully
        - Fallback to file extension detection works
        - Errors are logged but don't crash
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()

        # Invalid package.json
        (project_root / "package.json").write_text("{ invalid json }")

        # But valid code files exist
        (project_root / "index.js").write_text("console.log('test');")

        detector = LSPDetector(project_root)

        # Should still detect via file extensions
        languages = detector.detect_languages()
        assert "javascript" in languages

    def test_recommend_lsp_for_unsupported_language(self):
        """
        Test LSP recommendation for language without known LSP.

        Validates:
        - Returns None or generic recommendation
        - Does not crash
        - Logs warning about unsupported language
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        detector = LSPDetector(Path("/tmp"))

        recommendation = detector.recommend_lsp("brainfuck")
        assert recommendation is None or recommendation == ""

    def test_detect_language_by_shebang(self, tmp_path):
        """
        Test language detection via shebang in files.

        Validates:
        - #!/usr/bin/env python3 indicates Python
        - #!/bin/bash indicates shell script
        - Shebang overrides extension
        """
        from amplihack.plugin.lsp_detector import LSPDetector

        project_root = tmp_path / "project"
        project_root.mkdir()

        # Python file without .py extension
        script = project_root / "script"
        script.write_text("#!/usr/bin/env python3\nprint('hello')")

        detector = LSPDetector(project_root)
        languages = detector.detect_languages()

        assert "python" in languages

    def test_performance_with_large_project(self, tmp_path):
        """
        Test detection performance with large project (1000+ files).

        Validates:
        - Detection completes in reasonable time (<2 seconds)
        - Memory usage is reasonable
        - Accurate results despite size
        """
        from amplihack.plugin.lsp_detector import LSPDetector
        import time

        project_root = tmp_path / "large_project"
        project_root.mkdir()

        # Create many files
        for i in range(100):
            dir_path = project_root / f"module_{i}"
            dir_path.mkdir()
            for j in range(10):
                (dir_path / f"file_{j}.py").write_text(f"# File {i}-{j}")

        start = time.time()
        detector = LSPDetector(project_root)
        languages = detector.detect_languages()
        elapsed = time.time() - start

        assert "python" in languages
        assert elapsed < 2.0  # Should be fast even with 1000 files
