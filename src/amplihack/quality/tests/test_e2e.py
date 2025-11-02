"""End-to-end tests for quality module."""

import os
from pathlib import Path

import pytest

from amplihack.quality import QualityChecker, QualityConfig


@pytest.mark.e2e
class TestQualityE2E:
    """End-to-end tests for quality checking."""

    def test_real_world_python_file(self, tmp_path):
        """Test validation of real Python file."""
        py_file = tmp_path / "example.py"
        py_file.write_text("""
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
""")

        checker = QualityChecker()
        result = checker.check_file(py_file)

        # Should either validate successfully or skip if ruff not available
        if result and not result.skipped:
            assert isinstance(result.passed, bool)

    def test_real_world_json_config(self, tmp_path):
        """Test validation of JSON configuration file."""
        json_file = tmp_path / "config.json"
        json_file.write_text("""
{
    "name": "test-project",
    "version": "1.0.0",
    "dependencies": {
        "pytest": "^7.0.0"
    }
}
""")

        checker = QualityChecker()
        result = checker.check_file(json_file)

        assert result is not None
        assert result.passed is True

    def test_real_world_markdown_doc(self, tmp_path):
        """Test validation of Markdown documentation."""
        md_file = tmp_path / "README.md"
        md_file.write_text("""
# Project Title

This is a sample README file.

## Features

- Feature 1
- Feature 2
- Feature 3
""")

        checker = QualityChecker()
        result = checker.check_file(md_file)

        # Should either validate or skip if markdownlint not available
        if result:
            assert result.validator == "markdown"

    def test_environment_variable_configuration(self, tmp_path):
        """Test configuration via environment variables."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"env": "test"}')

        # Set environment variable
        os.environ["AMPLIHACK_QUALITY_FAST_MODE"] = "false"
        os.environ["AMPLIHACK_QUALITY_FULL_TIMEOUT"] = "60"

        try:
            config = QualityConfig.from_pyproject()
            assert config.fast_mode is False
            assert config.full_mode_timeout == 60

            checker = QualityChecker(config)
            result = checker.check_file(json_file)

            assert result is not None
        finally:
            del os.environ["AMPLIHACK_QUALITY_FAST_MODE"]
            del os.environ["AMPLIHACK_QUALITY_FULL_TIMEOUT"]

    def test_complete_workflow(self, tmp_path):
        """Test complete quality checking workflow."""
        # Create project structure
        src = tmp_path / "src"
        src.mkdir()

        # Create valid files
        (src / "main.py").write_text('print("Hello")')
        (src / "config.json").write_text('{"setting": true}')
        (src / "README.md").write_text("# Documentation")

        # Create invalid file
        (src / "broken.json").write_text('{"broken": }')

        # Run quality checks
        checker = QualityChecker()
        files = list(src.glob("*"))
        results = checker.check_files(files)

        # Generate summary
        summary = checker.get_summary(results)

        assert summary["total_files"] > 0
        assert summary["failed"] >= 1  # broken.json should fail
        assert summary["total_errors"] > 0

    @pytest.mark.performance
    def test_performance_large_batch(self, tmp_path):
        """Test performance with large batch of files."""
        import time

        # Create 50 JSON files
        files = []
        for i in range(50):
            json_file = tmp_path / f"file{i}.json"
            json_file.write_text(f'{{"index": {i}}}')
            files.append(json_file)

        config = QualityConfig(fast_mode=True)
        checker = QualityChecker(config)

        start = time.time()
        results = checker.check_files(files)
        duration = time.time() - start

        # Should complete in less than 10 seconds for 50 files in fast mode
        assert duration < 10.0
        assert len(results) == 50
