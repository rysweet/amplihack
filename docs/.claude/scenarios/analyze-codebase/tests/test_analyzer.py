#!/usr/bin/env python3
"""
Test suite for simplified CodebaseAnalyzer.
"""

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from tool import CodebaseAnalyzer


class TestCodebaseAnalyzer:
    """Test suite for CodebaseAnalyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.analyzer = CodebaseAnalyzer()

        # Create sample files for testing
        (self.temp_dir / "sample.py").write_text("""
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
        """)

        (self.temp_dir / "config.yaml").write_text("app:\n  name: test\n  version: 1.0")
        (self.temp_dir / "README.md").write_text("# Test Project")

        # Create subdirectory with more files
        (self.temp_dir / "src").mkdir()
        (self.temp_dir / "src" / "main.py").write_text("""
class DataProcessor:
    def __init__(self):
        self.data = []

    def process(self, item):
        self.data.append(item)
        return item * 2
        """)

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        analyzer = CodebaseAnalyzer()
        assert analyzer.skip_patterns
        assert analyzer.max_file_size > 0

    def test_analyze_valid_directory(self):
        """Test analysis of valid directory."""
        result = self.analyzer.analyze(str(self.temp_dir), {"format": "json"})
        assert "summary" in result
        assert result["summary"]["files_analyzed"] > 0
        assert result["summary"]["total_lines"] > 0

    def test_analyze_nonexistent_path(self):
        """Test analysis of nonexistent path raises error."""
        with pytest.raises(ValueError, match="Target path does not exist"):
            self.analyzer.analyze("/nonexistent/path")

    def test_discover_content_python_files(self):
        """Test content discovery finds Python files correctly."""
        content_map = self.analyzer._discover_content(self.temp_dir)
        assert "python" in content_map
        assert len(content_map["python"]) == 2  # sample.py and src/main.py

    def test_discover_content_yaml_files(self):
        """Test content discovery finds YAML files correctly."""
        content_map = self.analyzer._discover_content(self.temp_dir)
        assert "yaml" in content_map
        assert len(content_map["yaml"]) == 1  # config.yaml

    def test_discover_content_markdown_files(self):
        """Test content discovery finds Markdown files correctly."""
        content_map = self.analyzer._discover_content(self.temp_dir)
        assert "markdown" in content_map
        assert len(content_map["markdown"]) == 1  # README.md

    def test_discover_content_single_file(self):
        """Test content discovery with single file input."""
        test_file = self.temp_dir / "sample.py"
        content_map = self.analyzer._discover_content(test_file)
        assert "python" in content_map
        assert len(content_map["python"]) == 1
        assert content_map["python"][0] == test_file

    def test_should_skip_git_directory(self):
        """Test file skipping for git directories."""
        git_file = self.temp_dir / ".git" / "config"
        git_file.parent.mkdir()
        git_file.write_text("test")
        assert self.analyzer._should_skip(git_file) is True

    def test_should_skip_pycache(self):
        """Test file skipping for Python cache directories."""
        cache_file = self.temp_dir / "__pycache__" / "test.pyc"
        cache_file.parent.mkdir()
        cache_file.write_text("test")
        assert self.analyzer._should_skip(cache_file) is True

    def test_should_skip_normal_file(self):
        """Test file skipping allows normal files."""
        normal_file = self.temp_dir / "normal.py"
        normal_file.write_text("print('hello')")
        assert self.analyzer._should_skip(normal_file) is False

    def test_count_lines_calculation(self):
        """Test line counting calculation."""
        content_map = {"python": [self.temp_dir / "sample.py"]}
        lines = self.analyzer._count_lines(content_map)
        assert lines > 0
        assert isinstance(lines, int)

    def test_analyze_json_format(self):
        """Test analysis with JSON output format."""
        result = self.analyzer.analyze(str(self.temp_dir), {"format": "json"})
        assert isinstance(result, dict)
        assert "summary" in result
        assert "findings" in result
        assert "recommendations" in result

    def test_analyze_text_format(self):
        """Test analysis with text output format."""
        result = self.analyzer.analyze(str(self.temp_dir), {"format": "text"})
        assert isinstance(result, str)
        assert "Codebase Analysis Results" in result

    def test_security_scan_functionality(self):
        """Test basic security scanning functionality."""
        # Create file with potential security issue
        (self.temp_dir / "insecure.py").write_text("""
password = "hardcoded_password"  # pragma: allowlist secret
api_key = "secret_api_key"  # pragma: allowlist secret
        """)

        result = self.analyzer.analyze(str(self.temp_dir), {"format": "json"})
        assert result["summary"]["security_issues"] > 0

    def test_large_codebase_handling(self):
        """Test handling of larger codebase."""
        # Create multiple files
        for i in range(10):
            (self.temp_dir / f"module_{i}.py").write_text(f"""
def function_{i}():
    return {i} * 2

class Class{i}:
    def __init__(self):
        self.value = {i}
            """)

        result = self.analyzer.analyze(str(self.temp_dir), {"format": "json"})
        assert result["summary"]["files_analyzed"] >= 10
        assert len(result["findings"]) > 0

    def test_empty_directory_handling(self):
        """Test handling of empty directories."""
        empty_dir = self.temp_dir / "empty"
        empty_dir.mkdir()

        result = self.analyzer.analyze(str(empty_dir))
        assert "message" in result
        assert result["files"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
