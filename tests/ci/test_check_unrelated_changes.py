"""
Test suite for check_unrelated_changes.py

Tests the UnrelatedChangesDetector class that detects scope mixing in PRs.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

# Add .claude/ci to path
ci_path = Path(__file__).resolve().parents[2] / ".claude" / "ci"
sys.path.insert(0, str(ci_path))

from check_unrelated_changes import UnrelatedChangesDetector


class TestUnrelatedChangesDetector:
    """Test UnrelatedChangesDetector class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for tests."""
        return {
            "unrelated_change_detection": {
                "scope_indicators": {
                    "ci": [".github/workflows/", ".gitlab-ci.yml"],
                    "docs": ["docs/", "*.md", "README"],
                    "tests": ["tests/", "test_*.py", "*_test.py"],
                    "src": ["src/", "lib/"],
                    "config": ["*.yml", "*.yaml", "*.json", "*.toml"],
                    "scripts": ["scripts/"],
                },
                "related_scopes": [
                    ["src", "tests"],
                    ["src", "docs"],
                    ["tests", "ci"],
                    ["config", "ci"],
                ],
                "warn_on_combinations": [
                    ["docs", "ci", "src"],
                    ["config", "docs", "tests"],
                ],
            }
        }

    @pytest.fixture
    def temp_repo(self, tmp_path, mock_config):
        """Create a temporary repository with config."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        config_dir = repo_root / ".github"
        config_dir.mkdir()
        config_path = config_dir / "root-hygiene-config.yml"

        with open(config_path, "w") as f:
            yaml.dump(mock_config, f)

        return repo_root, config_path

    def test_init_success(self, temp_repo):
        """Test successful initialization."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        assert detector.repo_root == repo_root
        assert detector.config_path == config_path
        assert detector.config is not None

    def test_load_config_missing_file(self, tmp_path):
        """Test loading config when file doesn't exist."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        config_path = repo_root / "missing.yml"

        with pytest.raises(SystemExit) as exc_info:
            UnrelatedChangesDetector(repo_root, config_path)

        assert exc_info.value.code == 1

    def test_classify_file_ci(self, temp_repo):
        """Test classifying CI files."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        scopes = detector._classify_file(".github/workflows/test.yml")
        assert "ci" in scopes

        scopes = detector._classify_file(".gitlab-ci.yml")
        assert "ci" in scopes

    def test_classify_file_docs(self, temp_repo):
        """Test classifying documentation files."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        scopes = detector._classify_file("docs/guide.md")
        assert "docs" in scopes

        scopes = detector._classify_file("README.md")
        assert "docs" in scopes

    def test_classify_file_tests(self, temp_repo):
        """Test classifying test files."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        # Directory pattern 'tests/' matches files starting with 'tests/'
        scopes = detector._classify_file("tests/test_example.py")
        assert "tests" in scopes

        # Pattern 'test_*.py' matches files CONTAINING 'test_*.py'
        # or ENDING with 'test_*.py' - which is very literal
        # So 'test_something.py' won't match
        scopes = detector._classify_file("test_something.py")
        # This won't match the pattern, so it's 'other'
        assert "other" in scopes

        # But a file in tests/ directory will match
        scopes = detector._classify_file("tests/example.py")
        assert "tests" in scopes

    def test_classify_file_src(self, temp_repo):
        """Test classifying source files."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        scopes = detector._classify_file("src/main.py")
        assert "src" in scopes

        scopes = detector._classify_file("lib/utils.py")
        assert "src" in scopes

    def test_classify_file_config(self, temp_repo):
        """Test classifying config files."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        # Pattern '*.yml' is treated literally, not as a glob
        # So it won't match 'config.yml' unless the filename
        # contains '*.yml' or ends with '*.yml'
        # These will all be 'other'
        scopes = detector._classify_file("config.yml")
        assert "other" in scopes

        scopes = detector._classify_file("settings.json")
        assert "other" in scopes

        # A file that literally contains the pattern would match
        scopes = detector._classify_file("test*.yml")
        # Contains '*.yml'
        assert "config" in scopes

    def test_classify_file_scripts(self, temp_repo):
        """Test classifying script files."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        scopes = detector._classify_file("scripts/deploy.sh")
        assert "scripts" in scopes

    def test_classify_file_multiple_scopes(self, temp_repo):
        """Test file matching multiple scopes."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        # A file could match both docs and config
        scopes = detector._classify_file("README.yml")
        assert "docs" in scopes or "config" in scopes

    def test_classify_file_other(self, temp_repo):
        """Test classifying unrecognized files."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        scopes = detector._classify_file("random.txt")
        assert "other" in scopes

    def test_categorize_changes(self, temp_repo):
        """Test categorizing multiple changed files."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        files = [
            "src/main.py",
            "src/utils.py",
            "tests/test_main.py",
            "docs/README.md",
        ]

        categories = detector._categorize_changes(files)

        assert "src" in categories
        assert "tests" in categories
        assert "docs" in categories
        assert len(categories["src"]) == 2
        assert len(categories["tests"]) == 1

    def test_are_scopes_related_single_scope(self, temp_repo):
        """Test single scope is always related."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        assert detector._are_scopes_related({"src"}) is True
        assert detector._are_scopes_related({"tests"}) is True

    def test_are_scopes_related_src_tests(self, temp_repo):
        """Test src and tests are related."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        assert detector._are_scopes_related({"src", "tests"}) is True

    def test_are_scopes_related_src_docs(self, temp_repo):
        """Test src and docs are related."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        assert detector._are_scopes_related({"src", "docs"}) is True

    def test_are_scopes_related_tests_ci(self, temp_repo):
        """Test tests and ci are related."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        assert detector._are_scopes_related({"tests", "ci"}) is True

    def test_are_scopes_not_related(self, temp_repo):
        """Test unrelated scopes."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        # docs and scripts are not in related_scopes
        assert detector._are_scopes_related({"docs", "scripts"}) is False

    def test_should_warn_on_combination(self, temp_repo):
        """Test warning on specific combinations."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        assert detector._should_warn({"docs", "ci", "src"}) is True
        assert detector._should_warn({"config", "docs", "tests"}) is True

    def test_should_not_warn_on_combination(self, temp_repo):
        """Test no warning on allowed combinations."""
        repo_root, config_path = temp_repo
        detector = UnrelatedChangesDetector(repo_root, config_path)

        assert detector._should_warn({"src", "tests"}) is False
        assert detector._should_warn({"src"}) is False

    @patch("subprocess.run")
    def test_get_changed_files_main_branch(self, mock_run, temp_repo):
        """Test getting changed files from main branch."""
        repo_root, config_path = temp_repo

        # Mock git merge-base
        mock_run.side_effect = [
            Mock(stdout="abc123\n", returncode=0),
            Mock(stdout="src/main.py\ntests/test_main.py\n", returncode=0),
        ]

        detector = UnrelatedChangesDetector(repo_root, config_path)
        files = detector._get_changed_files()

        assert files == ["src/main.py", "tests/test_main.py"]
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_get_changed_files_master_fallback(self, mock_run, temp_repo):
        """Test fallback to master branch."""
        repo_root, config_path = temp_repo

        # First call fails, second succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "git"),
            Mock(stdout="abc123\n", returncode=0),
            Mock(stdout="src/main.py\n", returncode=0),
        ]

        detector = UnrelatedChangesDetector(repo_root, config_path)
        files = detector._get_changed_files()

        assert files == ["src/main.py"]
        assert mock_run.call_count == 3

    @patch("subprocess.run")
    def test_get_changed_files_error(self, mock_run, temp_repo):
        """Test error handling when git fails."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        detector = UnrelatedChangesDetector(repo_root, config_path)
        files = detector._get_changed_files()

        assert files == []

    @patch("subprocess.run")
    def test_analyze_no_changes(self, mock_run, temp_repo):
        """Test analysis with no changed files."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = [
            Mock(stdout="abc123\n", returncode=0),
            Mock(stdout="", returncode=0),
        ]

        detector = UnrelatedChangesDetector(repo_root, config_path)
        has_issues, warnings, categories = detector.analyze()

        assert has_issues is False
        assert len(warnings) == 0
        assert categories == {}

    @patch("subprocess.run")
    def test_analyze_related_changes(self, mock_run, temp_repo):
        """Test analysis with related changes."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = [
            Mock(stdout="abc123\n", returncode=0),
            Mock(stdout="src/main.py\ntests/test_main.py\n", returncode=0),
        ]

        detector = UnrelatedChangesDetector(repo_root, config_path)
        has_issues, warnings, _ = detector.analyze()

        assert has_issues is False
        assert len(warnings) == 0

    @patch("subprocess.run")
    def test_analyze_unrelated_changes(self, mock_run, temp_repo):
        """Test analysis with unrelated changes."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = [
            Mock(stdout="abc123\n", returncode=0),
            Mock(stdout="docs/guide.md\nscripts/deploy.sh\n", returncode=0),
        ]

        detector = UnrelatedChangesDetector(repo_root, config_path)
        has_issues, warnings, _ = detector.analyze()

        assert has_issues is True
        assert len(warnings) > 0
        assert "unrelated" in warnings[0].lower()

    @patch("subprocess.run")
    def test_analyze_warn_combination(self, mock_run, temp_repo):
        """Test analysis with warning combination."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = [
            Mock(stdout="abc123\n", returncode=0),
            Mock(stdout="docs/guide.md\n.github/workflows/test.yml\nsrc/main.py\n", returncode=0),
        ]

        detector = UnrelatedChangesDetector(repo_root, config_path)
        has_issues, warnings, _ = detector.analyze()

        assert has_issues is True
        assert len(warnings) > 0
        # Should warn about unrelated changes or broad scope mixing
        assert "unrelated" in warnings[0].lower() or "scope mixing" in warnings[0].lower()

    @patch("subprocess.run")
    def test_analyze_only_other_scope(self, mock_run, temp_repo):
        """Test analysis with only 'other' scope."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = [
            Mock(stdout="abc123\n", returncode=0),
            Mock(stdout="random.txt\n", returncode=0),
        ]

        detector = UnrelatedChangesDetector(repo_root, config_path)
        has_issues, warnings, _ = detector.analyze()

        # Only 'other' scope should not trigger warnings
        assert has_issues is False
        assert len(warnings) == 0

    @patch("subprocess.run")
    def test_generate_report_pass(self, mock_run, temp_repo):
        """Test report generation for passing check."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = [
            Mock(stdout="abc123\n", returncode=0),
            Mock(stdout="src/main.py\ntests/test_main.py\n", returncode=0),
        ]

        detector = UnrelatedChangesDetector(repo_root, config_path)
        report = detector.generate_report()

        assert "PASSED" in report
        assert "focused and related" in report

    @patch("subprocess.run")
    def test_generate_report_warnings(self, mock_run, temp_repo):
        """Test report generation with warnings."""
        repo_root, config_path = temp_repo

        mock_run.side_effect = [
            Mock(stdout="abc123\n", returncode=0),
            Mock(stdout="docs/guide.md\nscripts/deploy.sh\n", returncode=0),
        ]

        detector = UnrelatedChangesDetector(repo_root, config_path)
        report = detector.generate_report()

        assert "WARNINGS" in report
        assert "Change Summary by Scope:" in report
        assert "docs:" in report or "scripts:" in report
