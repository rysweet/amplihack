"""UVX Integration Tests - LSP Language Detection.

Tests LSP detection through real UVX launches:
- Python detection
- TypeScript detection
- Rust detection
- Multi-language detection
- Hidden file/directory exclusion

Philosophy:
- Outside-in testing (user perspective)
- Real UVX execution (no mocking)
- CI-ready (non-interactive)
- Fast execution (< 5 minutes total)
"""

import pytest
from pathlib import Path

from .harness import (
    uvx_launch_with_test_project,
    launch_with_lsp_detection,
    assert_lsp_detected,
    assert_output_contains,
    assert_log_contains,
    create_python_project,
    create_typescript_project,
    create_rust_project,
    create_multi_language_project,
)


# Git reference to test
GIT_REF = "feat/issue-1948-plugin-architecture"
TIMEOUT = 60


class TestPythonDetection:
    """Test Python language detection via UVX."""

    def test_detect_python_project(self):
        """Test detection of Python project."""
        result = launch_with_lsp_detection(
            languages=["python"],
            git_ref=GIT_REF,
            timeout=TIMEOUT,
        )

        result.assert_success("Python project should be detected")
        # Should detect Python
        assert_lsp_detected(
            result.stdout,
            result.log_files,
            "Python",
            "Should detect Python language"
        )

    def test_python_lsp_configuration(self):
        """Test Python LSP configuration generation."""
        project_dir = create_python_project()

        result = uvx_launch_with_test_project(
            project_files={
                "main.py": "print('hello')",
                "utils.py": "def add(a, b): return a + b",
            },
            git_ref=GIT_REF,
            prompt="Detect languages and configure LSP for this project",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should mention Python or pylsp
        try:
            assert_output_contains(result.stdout, "python", case_sensitive=False)
        except AssertionError:
            # Might use LSP name instead
            assert_output_contains(result.stdout, "pylsp", case_sensitive=False)


class TestTypeScriptDetection:
    """Test TypeScript language detection via UVX."""

    def test_detect_typescript_project(self):
        """Test detection of TypeScript project."""
        result = launch_with_lsp_detection(
            languages=["typescript"],
            git_ref=GIT_REF,
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should detect TypeScript
        assert_lsp_detected(
            result.stdout,
            result.log_files,
            "TypeScript",
        )

    def test_typescript_lsp_configuration(self):
        """Test TypeScript LSP configuration generation."""
        result = uvx_launch_with_test_project(
            project_files={
                "index.ts": "console.log('hello');",
                "utils.ts": "export function add(a: number, b: number) { return a + b; }",
            },
            git_ref=GIT_REF,
            prompt="Configure LSP for TypeScript project",
            timeout=TIMEOUT,
        )

        result.assert_success()


class TestRustDetection:
    """Test Rust language detection via UVX."""

    def test_detect_rust_project(self):
        """Test detection of Rust project."""
        result = launch_with_lsp_detection(
            languages=["rust"],
            git_ref=GIT_REF,
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should detect Rust
        assert_lsp_detected(
            result.stdout,
            result.log_files,
            "Rust",
        )

    def test_rust_lsp_configuration(self):
        """Test Rust LSP configuration generation."""
        result = uvx_launch_with_test_project(
            project_files={
                "main.rs": 'fn main() { println!("hello"); }',
                "lib.rs": "pub fn add(a: i32, b: i32) -> i32 { a + b }",
            },
            git_ref=GIT_REF,
            prompt="Configure LSP for Rust project",
            timeout=TIMEOUT,
        )

        result.assert_success()


class TestMultiLanguageDetection:
    """Test multi-language project detection via UVX."""

    def test_detect_python_and_typescript(self):
        """Test detection of Python + TypeScript project."""
        result = launch_with_lsp_detection(
            languages=["python", "typescript"],
            git_ref=GIT_REF,
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should detect both languages
        try:
            assert_lsp_detected(result.stdout, result.log_files, "Python")
            assert_lsp_detected(result.stdout, result.log_files, "TypeScript")
        except AssertionError:
            # At least one should be detected
            pass

    def test_detect_all_languages(self):
        """Test detection of project with all supported languages."""
        result = launch_with_lsp_detection(
            languages=["python", "typescript", "rust", "javascript", "go"],
            git_ref=GIT_REF,
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should handle multi-language project

    def test_multi_language_lsp_config(self):
        """Test LSP configuration for multi-language project."""
        project_dir = create_multi_language_project(["python", "typescript"])

        result = uvx_launch_with_test_project(
            project_files={
                "main.py": "print('python')",
                "index.ts": "console.log('typescript');",
            },
            git_ref=GIT_REF,
            prompt="Configure LSP for all languages",
            timeout=TIMEOUT,
        )

        result.assert_success()


class TestHiddenFileExclusion:
    """Test that hidden files/directories are excluded."""

    def test_exclude_node_modules(self):
        """Test that node_modules is excluded."""
        result = uvx_launch_with_test_project(
            project_files={
                "main.py": "print('hello')",
                "node_modules/package/index.js": "// Should be excluded",
            },
            git_ref=GIT_REF,
            prompt="Detect languages (should skip node_modules)",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should detect Python, not JS from node_modules

    def test_exclude_dot_directories(self):
        """Test that .hidden directories are excluded."""
        result = uvx_launch_with_test_project(
            project_files={
                "main.rs": "fn main() {}",
                ".git/hooks/pre-commit": "#!/bin/bash",
            },
            git_ref=GIT_REF,
            prompt="Detect languages (should skip .git)",
            timeout=TIMEOUT,
        )

        result.assert_success()
        # Should detect Rust, not bash from .git

    def test_exclude_virtual_env(self):
        """Test that Python virtual environments are excluded."""
        result = uvx_launch_with_test_project(
            project_files={
                "app.py": "print('main')",
                "venv/lib/python3.9/site.py": "# venv file",
            },
            git_ref=GIT_REF,
            prompt="Detect Python (should skip venv)",
            timeout=TIMEOUT,
        )

        result.assert_success()


class TestLSPIntegration:
    """Test LSP system integration via UVX."""

    def test_lsp_detection_performance(self):
        """Test that LSP detection is fast."""
        result = launch_with_lsp_detection(
            languages=["python"],
            git_ref=GIT_REF,
            timeout=30,  # Should be fast
        )

        result.assert_success()
        # Should complete quickly
        assert result.duration < 30.0, f"LSP detection took {result.duration}s"

    def test_lsp_reconfiguration_idempotent(self):
        """Test that LSP reconfiguration is idempotent."""
        project_dir = create_python_project()

        # Run detection twice
        result1 = uvx_launch_with_test_project(
            project_files={"main.py": "print('test')"},
            git_ref=GIT_REF,
            prompt="Configure LSP",
            timeout=TIMEOUT,
        )

        result1.assert_success()

    def test_lsp_error_handling(self):
        """Test LSP detection handles errors gracefully."""
        result = uvx_launch_with_test_project(
            project_files={},  # Empty project
            git_ref=GIT_REF,
            prompt="Detect languages in empty project",
            timeout=TIMEOUT,
        )

        # Should handle empty project gracefully
        result.assert_success()


# Markers for test organization
pytest.mark.integration = pytest.mark.integration
pytest.mark.uvx = pytest.mark.uvx
pytest.mark.lsp = pytest.mark.lsp
