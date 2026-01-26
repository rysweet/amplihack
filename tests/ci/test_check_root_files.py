"""
Test suite for check_root_files.py

Tests the RootFileValidator class that validates files against allowlist/blocklist.
"""

import sys
from pathlib import Path

import pytest
import yaml

# Add .claude/ci to path
ci_path = Path(__file__).resolve().parents[2] / ".claude" / "ci"
sys.path.insert(0, str(ci_path))

from check_root_files import RootFileValidator


class TestRootFileValidator:
    """Test RootFileValidator class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for tests."""
        return {
            "allowed_patterns": [
                "README.md",
                "LICENSE.md",
                ".gitignore",
                "requirements*.txt",
                "*.yml",
            ],
            "allowed_directories": [
                "src",
                "tests",
                "docs",
                ".github",
            ],
            "forbidden_patterns": [
                {
                    "pattern": "test_*.py",
                    "message": "Test files belong in tests/ directory",
                    "suggested_location": "tests/",
                },
                {
                    "pattern": "scratch.py",
                    "message": "Scratch files should never be committed",
                    "suggested_location": "DELETE",
                },
            ],
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
        validator = RootFileValidator(repo_root, config_path)

        assert validator.repo_root == repo_root
        assert validator.config_path == config_path
        assert validator.config is not None

    def test_load_config_missing_file(self, tmp_path):
        """Test loading config when file doesn't exist."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        config_path = repo_root / "missing.yml"

        with pytest.raises(SystemExit) as exc_info:
            RootFileValidator(repo_root, config_path)

        assert exc_info.value.code == 1

    def test_is_allowed_pattern_match(self, temp_repo):
        """Test allowed pattern matching."""
        repo_root, config_path = temp_repo
        validator = RootFileValidator(repo_root, config_path)

        assert validator._is_allowed("README.md") is True
        assert validator._is_allowed("LICENSE.md") is True
        assert validator._is_allowed(".gitignore") is True
        assert validator._is_allowed("requirements.txt") is True
        assert validator._is_allowed("requirements-dev.txt") is True

    def test_is_allowed_pattern_no_match(self, temp_repo):
        """Test files not matching allowed patterns."""
        repo_root, config_path = temp_repo
        validator = RootFileValidator(repo_root, config_path)

        assert validator._is_allowed("random.py") is False
        assert validator._is_allowed("script.py") is False
        assert validator._is_allowed("test_something.py") is False

    def test_check_forbidden_match(self, temp_repo):
        """Test forbidden pattern matching."""
        repo_root, config_path = temp_repo
        validator = RootFileValidator(repo_root, config_path)

        is_forbidden, message, location = validator._check_forbidden("test_example.py")
        assert is_forbidden is True
        assert "Test files belong in tests/" in message
        assert location == "tests/"

    def test_check_forbidden_scratch_file(self, temp_repo):
        """Test forbidden scratch file detection."""
        repo_root, config_path = temp_repo
        validator = RootFileValidator(repo_root, config_path)

        is_forbidden, message, location = validator._check_forbidden("scratch.py")
        assert is_forbidden is True
        assert "should never be committed" in message
        assert location == "DELETE"

    def test_check_forbidden_no_match(self, temp_repo):
        """Test files not matching forbidden patterns."""
        repo_root, config_path = temp_repo
        validator = RootFileValidator(repo_root, config_path)

        is_forbidden, message, location = validator._check_forbidden("README.md")
        assert is_forbidden is False
        assert message == ""
        assert location == ""

    def test_is_directory_allowed(self, temp_repo):
        """Test directory allowlist checking."""
        repo_root, config_path = temp_repo
        validator = RootFileValidator(repo_root, config_path)

        assert validator._is_directory_allowed("src") is True
        assert validator._is_directory_allowed("tests") is True
        assert validator._is_directory_allowed("docs") is True
        assert validator._is_directory_allowed(".github") is True

    def test_is_directory_not_allowed(self, temp_repo):
        """Test directories not in allowlist."""
        repo_root, config_path = temp_repo
        validator = RootFileValidator(repo_root, config_path)

        assert validator._is_directory_allowed("random") is False
        assert validator._is_directory_allowed("old_stuff") is False

    def test_get_root_entries_files_and_dirs(self, temp_repo):
        """Test getting root files and directories."""
        repo_root, config_path = temp_repo

        # Create test files and directories
        (repo_root / "README.md").touch()
        (repo_root / "LICENSE.md").touch()
        (repo_root / "src").mkdir()
        (repo_root / "tests").mkdir()
        (repo_root / ".git").mkdir()  # Should be ignored

        validator = RootFileValidator(repo_root, config_path)
        files, directories = validator._get_root_entries()

        assert "README.md" in files
        assert "LICENSE.md" in files
        assert "src" in directories
        assert "tests" in directories
        assert ".git" not in directories  # Should be excluded

    def test_get_root_entries_empty(self, temp_repo):
        """Test getting entries from empty root."""
        repo_root, config_path = temp_repo
        validator = RootFileValidator(repo_root, config_path)

        files, directories = validator._get_root_entries()

        # Only .github should exist (created by fixture)
        assert len(files) == 0
        assert ".github" in directories

    def test_validate_all_allowed(self, temp_repo):
        """Test validation when all files are allowed."""
        repo_root, config_path = temp_repo

        (repo_root / "README.md").touch()
        (repo_root / "LICENSE.md").touch()
        (repo_root / "src").mkdir()

        validator = RootFileValidator(repo_root, config_path)
        is_valid, warnings = validator.validate()

        assert is_valid is True
        assert len(warnings) == 0

    def test_validate_forbidden_file(self, temp_repo):
        """Test validation with forbidden file."""
        repo_root, config_path = temp_repo

        (repo_root / "test_something.py").touch()

        validator = RootFileValidator(repo_root, config_path)
        is_valid, warnings = validator.validate()

        assert is_valid is False
        assert len(warnings) == 1
        assert "test_something.py" in warnings[0]
        assert "Test files belong in tests/" in warnings[0]

    def test_validate_not_allowed_file(self, temp_repo):
        """Test validation with file not in allowlist."""
        repo_root, config_path = temp_repo

        (repo_root / "random_script.py").touch()

        validator = RootFileValidator(repo_root, config_path)
        is_valid, warnings = validator.validate()

        assert is_valid is False
        assert len(warnings) == 1
        assert "random_script.py" in warnings[0]
        assert "Not in allowlist" in warnings[0]

    def test_validate_forbidden_directory(self, temp_repo):
        """Test validation with directory not in allowlist."""
        repo_root, config_path = temp_repo

        (repo_root / "old_stuff").mkdir()

        validator = RootFileValidator(repo_root, config_path)
        is_valid, warnings = validator.validate()

        assert is_valid is False
        assert len(warnings) == 1
        assert "old_stuff/" in warnings[0]
        assert "not in allowlist" in warnings[0]

    def test_validate_mixed_issues(self, temp_repo):
        """Test validation with multiple issues."""
        repo_root, config_path = temp_repo

        (repo_root / "test_foo.py").touch()  # Forbidden
        (repo_root / "random.py").touch()  # Not allowed
        (repo_root / "old_stuff").mkdir()  # Dir not allowed
        (repo_root / "README.md").touch()  # OK

        validator = RootFileValidator(repo_root, config_path)
        is_valid, warnings = validator.validate()

        assert is_valid is False
        assert len(warnings) == 3

    def test_generate_report_pass(self, temp_repo):
        """Test report generation for passing validation."""
        repo_root, config_path = temp_repo

        (repo_root / "README.md").touch()

        validator = RootFileValidator(repo_root, config_path)
        report = validator.generate_report()

        assert "PASSED" in report
        assert "All root files and directories are approved" in report

    def test_generate_report_warnings(self, temp_repo):
        """Test report generation with warnings."""
        repo_root, config_path = temp_repo

        (repo_root / "test_foo.py").touch()
        (repo_root / "random.py").touch()

        validator = RootFileValidator(repo_root, config_path)
        report = validator.generate_report()

        assert "WARNINGS" in report
        assert "test_foo.py" in report
        assert "random.py" in report
        assert "2 issue(s)" in report

    def test_validate_sorts_output(self, temp_repo):
        """Test that validation output is sorted."""
        repo_root, config_path = temp_repo

        # Create files out of order
        (repo_root / "z_file.py").touch()
        (repo_root / "a_file.py").touch()
        (repo_root / "m_file.py").touch()

        validator = RootFileValidator(repo_root, config_path)
        _, warnings = validator.validate()

        # Extract filenames from warnings
        filenames = [w.split("\n")[0].split()[1] for w in warnings]
        assert filenames == sorted(filenames)

    def test_empty_config_sections(self, tmp_path):
        """Test handling of empty config sections."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        config_dir = repo_root / ".github"
        config_dir.mkdir()
        config_path = config_dir / "root-hygiene-config.yml"

        # Write config with empty sections
        with open(config_path, "w") as f:
            yaml.dump(
                {
                    "allowed_patterns": [],
                    "allowed_directories": [],
                    "forbidden_patterns": [],
                },
                f,
            )

        (repo_root / "README.md").touch()

        validator = RootFileValidator(repo_root, config_path)
        is_valid, warnings = validator.validate()

        # Should have warnings since nothing is allowed
        # Both README.md and .github directory trigger warnings
        assert is_valid is False
        assert len(warnings) == 2
