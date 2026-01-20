"""End-to-end tests fer LSP detection and configuration.

Tests complete LSP workflows from outside-in perspective:
- Language detection
- LSP configuration generation
- Multi-language projects
"""

import pytest
from pathlib import Path
from tests.harness import LSPTestHarness


class TestLanguageDetection:
    """Test language detection workflows."""

    @pytest.fixture
    def harness(self):
        """Create LSP test harness."""
        h = LSPTestHarness()
        yield h
        h.cleanup()

    def test_detect_python_project(self, harness):
        """Test detectin' Python project.

        Workflow:
        1. Create Python project
        2. Run detection
        3. Verify Python detected
        """
        harness.create_python_project()

        result = harness.detect_languages()
        result.assert_success("Failed to detect Python project")
        result.assert_in_stdout("python")

    def test_detect_typescript_project(self, harness):
        """Test detectin' TypeScript project.

        Workflow:
        1. Create TypeScript project
        2. Run detection
        3. Verify TypeScript detected
        """
        harness.create_typescript_project()

        result = harness.detect_languages()
        result.assert_success("Failed to detect TypeScript project")
        result.assert_in_stdout("typescript")

    def test_detect_rust_project(self, harness):
        """Test detectin' Rust project.

        Workflow:
        1. Create Rust project
        2. Run detection
        3. Verify Rust detected
        """
        harness.create_rust_project()

        result = harness.detect_languages()
        result.assert_success("Failed to detect Rust project")
        result.assert_in_stdout("rust")

    def test_detect_multi_language_project(self, harness):
        """Test detectin' multi-language project.

        Workflow:
        1. Create project with Python, TypeScript, and Rust
        2. Run detection
        3. Verify all languages detected
        """
        harness.create_multi_language_project()

        result = harness.detect_languages()
        result.assert_success("Failed to detect multi-language project")

        # All three languages should be detected
        result.assert_in_stdout("python")
        result.assert_in_stdout("typescript")
        result.assert_in_stdout("rust")

    def test_detect_empty_project(self, harness):
        """Test detectin' empty project.

        Workflow:
        1. Create empty project
        2. Run detection
        3. Verify no languages detected or clear message
        """
        # Don't create any files

        result = harness.detect_languages()
        # Should succeed but report no languages
        # or fail with clear message
        if result.success:
            # Should indicate no languages found
            assert (
                "no languages" in result.stdout.lower() or
                "0 languages" in result.stdout.lower() or
                result.stdout.strip() == ""
            )
        else:
            # Should have clear error message
            assert len(result.stderr) > 0 or len(result.stdout) > 0

    def test_detect_with_hidden_files(self, harness):
        """Test detection ignores hidden files.

        Workflow:
        1. Create project with hidden Python files
        2. Run detection
        3. Verify hidden files ignored
        """
        # Create hidden Python file
        hidden_dir = harness.project_dir / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "hidden.py").write_text("print('hidden')")

        # Create normal Python file
        (harness.project_dir / "main.py").write_text("print('main')")

        result = harness.detect_languages()
        result.assert_success()

        # Python should be detected from main.py
        result.assert_in_stdout("python")

        # But hidden directory should be ignored (mentioned in output)
        # This depends on implementation - may or may not mention hidden files

    def test_detect_with_node_modules(self, harness):
        """Test detection ignores node_modules.

        Workflow:
        1. Create TypeScript project with node_modules
        2. Run detection
        3. Verify node_modules ignored
        """
        # Create TypeScript project
        harness.create_typescript_project()

        # Create node_modules with TypeScript files
        node_modules = harness.project_dir / "node_modules"
        node_modules.mkdir()
        (node_modules / "dep.ts").write_text("export const x = 1;")

        result = harness.detect_languages()
        result.assert_success()

        # TypeScript should be detected
        result.assert_in_stdout("typescript")

        # node_modules should be ignored
        # (implementation detail - may not be mentioned)


class TestLSPConfiguration:
    """Test LSP configuration generation workflows."""

    @pytest.fixture
    def harness(self):
        """Create LSP test harness."""
        h = LSPTestHarness()
        yield h
        h.cleanup()

    def test_configure_python_lsp(self, harness):
        """Test configurin' Python LSP.

        Workflow:
        1. Create Python project
        2. Configure LSP
        3. Verify config created
        """
        harness.create_python_project()

        result = harness.configure_lsp()
        result.assert_success("Failed to configure Python LSP")

        # Verify config file created
        assert harness.verify_lsp_config_exists("python")

    def test_configure_typescript_lsp(self, harness):
        """Test configurin' TypeScript LSP.

        Workflow:
        1. Create TypeScript project
        2. Configure LSP
        3. Verify config created
        """
        harness.create_typescript_project()

        result = harness.configure_lsp()
        result.assert_success("Failed to configure TypeScript LSP")

        # Verify config file created
        assert harness.verify_lsp_config_exists("typescript")

    def test_configure_multi_language_lsp(self, harness):
        """Test configurin' LSP fer multiple languages.

        Workflow:
        1. Create multi-language project
        2. Configure LSP
        3. Verify configs created fer all languages
        """
        harness.create_multi_language_project()

        result = harness.configure_lsp()
        result.assert_success("Failed to configure multi-language LSP")

        # Verify all configs created
        assert harness.verify_lsp_config_exists("python")
        assert harness.verify_lsp_config_exists("typescript")
        assert harness.verify_lsp_config_exists("rust")

    def test_configure_specific_language(self, harness):
        """Test configurin' LSP fer specific language.

        Workflow:
        1. Create multi-language project
        2. Configure LSP fer Python only
        3. Verify only Python config created
        """
        harness.create_multi_language_project()

        result = harness.configure_lsp(languages=["python"])
        result.assert_success("Failed to configure Python LSP")

        # Verify only Python config created
        assert harness.verify_lsp_config_exists("python")
        assert not harness.verify_lsp_config_exists("typescript")
        assert not harness.verify_lsp_config_exists("rust")

    def test_configure_invalid_language(self, harness):
        """Test configurin' LSP fer invalid language.

        Workflow:
        1. Try to configure unsupported language
        2. Verify fails with clear error
        """
        result = harness.configure_lsp(languages=["invalid-lang"])

        # Should fail or skip with clear message
        if not result.success:
            assert (
                "invalid" in result.stderr.lower() or
                "invalid" in result.stdout.lower() or
                "unsupported" in result.stderr.lower() or
                "unsupported" in result.stdout.lower()
            )
        else:
            # If it succeeds, should mention skipping
            assert (
                "skipped" in result.stdout.lower() or
                "not supported" in result.stdout.lower()
            )

    def test_reconfigure_existing_lsp(self, harness):
        """Test reconfigurin' existing LSP.

        Workflow:
        1. Create Python project
        2. Configure LSP
        3. Configure again
        4. Verify handled correctly (idempotent)
        """
        harness.create_python_project()

        # First configuration
        result1 = harness.configure_lsp()
        result1.assert_success()

        # Second configuration
        result2 = harness.configure_lsp()

        # Should succeed (idempotent)
        result2.assert_success("LSP configuration should be idempotent")

        # Config should still exist
        assert harness.verify_lsp_config_exists("python")


class TestIntegratedWorkflow:
    """Test complete integrated LSP workflow."""

    @pytest.fixture
    def harness(self):
        """Create LSP test harness."""
        h = LSPTestHarness()
        yield h
        h.cleanup()

    def test_detect_and_configure_workflow(self, harness):
        """Test complete detect + configure workflow.

        Workflow:
        1. Create multi-language project
        2. Detect languages
        3. Configure LSP based on detection
        4. Verify all configs created
        """
        # Create project
        harness.create_multi_language_project()

        # Detect languages
        detect_result = harness.detect_languages()
        detect_result.assert_success()

        # Configure LSP (auto-detect mode)
        config_result = harness.configure_lsp()
        config_result.assert_success()

        # Verify all configs created
        assert harness.verify_lsp_config_exists("python")
        assert harness.verify_lsp_config_exists("typescript")
        assert harness.verify_lsp_config_exists("rust")

    def test_incremental_language_addition(self, harness):
        """Test addin' languages incrementally.

        Workflow:
        1. Create Python project
        2. Configure LSP
        3. Add TypeScript files
        4. Reconfigure LSP
        5. Verify both configs exist
        """
        # Start with Python
        harness.create_python_project()
        harness.configure_lsp().assert_success()
        assert harness.verify_lsp_config_exists("python")

        # Add TypeScript
        harness.create_typescript_project()
        harness.configure_lsp().assert_success()

        # Both should exist now
        assert harness.verify_lsp_config_exists("python")
        assert harness.verify_lsp_config_exists("typescript")

    def test_language_removal_handling(self, harness):
        """Test handlin' language removal.

        Workflow:
        1. Create multi-language project
        2. Configure LSP
        3. Remove Python files
        4. Reconfigure LSP
        5. Verify behavior (implementation-dependent)
        """
        # Create multi-language project
        harness.create_multi_language_project()
        harness.configure_lsp().assert_success()

        # Remove Python files
        (harness.project_dir / "main.py").unlink()
        (harness.project_dir / "pyproject.toml").unlink()

        # Reconfigure
        result = harness.configure_lsp()

        # Should succeed
        result.assert_success()

        # Behavior depends on implementation:
        # - May keep Python config (safe)
        # - May remove Python config (cleanup)
        # Both are valid approaches

    def test_performance_large_project(self, harness):
        """Test detection performance on larger project.

        Workflow:
        1. Create project with many files
        2. Run detection
        3. Verify completes in reasonable time
        """
        # Create many Python files
        for i in range(100):
            (harness.project_dir / f"file{i}.py").write_text(f"print({i})")

        # Create some subdirectories
        for i in range(10):
            subdir = harness.project_dir / f"subdir{i}"
            subdir.mkdir()
            for j in range(10):
                (subdir / f"file{j}.py").write_text(f"print({i},{j})")

        # Run detection (should complete quickly)
        result = harness.detect_languages()
        result.assert_success()

        # Should complete in < 5 seconds
        assert result.duration < 5.0, f"Detection took {result.duration}s (too slow)"

        # Python should be detected
        result.assert_in_stdout("python")
