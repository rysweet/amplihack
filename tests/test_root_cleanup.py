"""
Test-Driven Development tests for root directory cleanup feature.

These tests are written BEFORE implementation and should FAIL initially.
They define the expected behavior of the cleanup process.

Testing Pyramid:
- 60% Unit tests (file move logic)
- 30% Integration tests (multiple operations)
- 10% E2E tests (complete workflow)
"""

import subprocess
from pathlib import Path

import pytest

# =============================================================================
# UNIT TESTS (60%) - Test individual file operations
# =============================================================================


class TestFileMoves:
    """Unit tests for individual file move operations"""

    def test_evaluation_summary_moved_to_docs_memory(self):
        """Test EVALUATION_SUMMARY.md moved to docs/memory/"""
        old_path = Path("EVALUATION_SUMMARY.md")
        new_path = Path("docs/memory/evaluation-summary.md")

        # Should not exist in root
        assert not old_path.exists(), f"{old_path} should not exist in root"

        # Should exist in new location
        assert new_path.exists(), f"{new_path} should exist"
        assert new_path.is_file(), f"{new_path} should be a file"

    def test_gh_pages_link_validation_moved_to_docs_testing(self):
        """Test gh_pages_link_validation.txt moved to docs/testing/"""
        old_path = Path("gh_pages_link_validation.txt")
        new_path = Path("docs/testing/gh-pages-link-validation.txt")

        assert not old_path.exists(), f"{old_path} should not exist in root"
        assert new_path.exists(), f"{new_path} should exist"
        assert new_path.is_file(), f"{new_path} should be a file"

    def test_setup_py_moved_to_archive_legacy(self):
        """Test setup.py moved to archive/legacy/"""
        old_path = Path("setup.py")
        new_path = Path("archive/legacy/setup.py")

        assert not old_path.exists(), f"{old_path} should not exist in root"
        assert new_path.exists(), f"{new_path} should exist"
        assert new_path.is_file(), f"{new_path} should be a file"


class TestFileContent:
    """Unit tests verifying file content preserved during move"""

    def test_evaluation_summary_content_preserved(self):
        """Test EVALUATION_SUMMARY.md content unchanged after move"""
        new_path = Path("docs/memory/evaluation-summary.md")
        assert new_path.exists()

        content = new_path.read_text()
        # Should contain key markers from original file
        assert "Memory System Evaluation" in content or "EVALUATION" in content
        assert len(content) > 100, "File should not be empty or truncated"

    def test_setup_py_content_preserved(self):
        """Test setup.py content unchanged after move"""
        new_path = Path("archive/legacy/setup.py")
        assert new_path.exists()

        content = new_path.read_text()
        # Should contain Python setup markers
        assert "setup(" in content or "setuptools" in content
        assert len(content) > 50, "File should not be empty or truncated"


class TestGitHistory:
    """Unit tests for git history preservation"""

    def test_git_log_follow_works_for_evaluation_summary(self):
        """Test git log --follow tracks EVALUATION_SUMMARY.md through rename"""
        new_path = "docs/memory/evaluation-summary.md"

        result = subprocess.run(
            ["git", "log", "--follow", "--oneline", new_path],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        assert result.returncode == 0, "git log --follow should succeed"
        assert len(result.stdout.strip()) > 0, "Should have commit history"

    def test_git_log_follow_works_for_setup_py(self):
        """Test git log --follow tracks setup.py through rename"""
        new_path = "archive/legacy/setup.py"

        result = subprocess.run(
            ["git", "log", "--follow", "--oneline", new_path],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        assert result.returncode == 0, "git log --follow should succeed"
        assert len(result.stdout.strip()) > 0, "Should have commit history"


# =============================================================================
# INTEGRATION TESTS (30%) - Test multiple operations together
# =============================================================================


class TestDocumentationCreation:
    """Integration tests for documentation files created during cleanup"""

    def test_file_organization_guide_created(self):
        """Test docs/contributing/file-organization.md exists and has content"""
        doc_path = Path("docs/contributing/file-organization.md")

        assert doc_path.exists(), "File organization guide should exist"
        content = doc_path.read_text()

        # Should document the cleanup
        assert "root directory" in content.lower()
        assert "organization" in content.lower()

        # Should have structure
        assert "#" in content, "Should have markdown headers"
        assert len(content) > 200, "Should have meaningful content"

    def test_archive_legacy_readme_created(self):
        """Test archive/legacy/README.md exists and documents purpose"""
        readme_path = Path("archive/legacy/README.md")

        assert readme_path.exists(), "Archive README should exist"
        content = readme_path.read_text()

        # Should explain archive purpose
        assert "legacy" in content.lower() or "archive" in content.lower()
        assert "setup.py" in content.lower(), "Should mention setup.py"

    def test_discoveries_updated(self):
        """Test docs/DISCOVERIES.md updated with cleanup learnings"""
        discoveries_path = Path("docs/DISCOVERIES.md")

        assert discoveries_path.exists(), "DISCOVERIES.md should exist"
        content = discoveries_path.read_text()

        # Should document the cleanup
        assert "cleanup" in content.lower() or "organization" in content.lower()

    def test_docs_index_updated_with_organization_link(self):
        """Test docs/index.md links to file organization guide"""
        index_path = Path("docs/index.md")

        assert index_path.exists(), "docs/index.md should exist"
        content = index_path.read_text()

        # Should link to file organization guide
        assert "file-organization" in content.lower() or "contributing" in content.lower()


class TestRootDirectoryState:
    """Integration tests verifying root directory is clean"""

    def test_moved_files_not_in_root(self):
        """Test all moved files removed from root"""
        root_files_to_remove = ["EVALUATION_SUMMARY.md", "gh_pages_link_validation.txt", "setup.py"]

        for filename in root_files_to_remove:
            path = Path(filename)
            assert not path.exists(), f"{filename} should be removed from root"

    def test_root_contains_only_essential_files(self):
        """Test root directory contains only essential files"""
        root = Path(".")

        # List all files in root (not directories)
        root_files = [f.name for f in root.iterdir() if f.is_file()]

        # Define essential files that should remain
        essential_files = {
            "README.md",
            "CLAUDE.md",
            "pyproject.toml",
            "Makefile",
            "LICENSE",
            ".gitignore",
            # Add other essential files as needed
        }

        # Check for unexpected files
        unexpected_files = set(root_files) - essential_files

        # Filter out dotfiles and common acceptable files
        unexpected_files = {
            f for f in unexpected_files if not f.startswith(".") and f not in ["setup.cfg"]
        }

        assert len(unexpected_files) == 0, (
            f"Root should only have essential files, found: {unexpected_files}"
        )


class TestReferenceIntegrity:
    """Integration tests verifying no broken references to old paths"""

    def test_no_code_references_old_paths(self):
        """Test no Python code references old file paths"""
        old_paths = ["EVALUATION_SUMMARY.md", "gh_pages_link_validation.txt", "setup.py"]

        # Search Python files for references
        python_files = Path(".").rglob("*.py")

        for py_file in python_files:
            # Skip test files and venv
            if "test" in str(py_file) or "venv" in str(py_file):
                continue

            try:
                content = py_file.read_text()
                for old_path in old_paths:
                    assert old_path not in content, f"{py_file} references old path: {old_path}"
            except Exception:
                # Skip files that can't be read
                pass

    def test_no_markdown_references_old_paths(self):
        """Test no markdown docs reference old file paths"""
        old_paths = [
            "EVALUATION_SUMMARY.md",
            "gh_pages_link_validation.txt",
        ]

        # Search markdown files for references
        md_files = Path("docs").rglob("*.md")

        for md_file in md_files:
            try:
                content = md_file.read_text()
                for old_path in old_paths:
                    # Allow references if they're in archive context
                    if old_path in content and "archive" not in content.lower():
                        pytest.fail(
                            f"{md_file} references old path without archive context: {old_path}"
                        )
            except Exception:
                # Skip files that can't be read
                pass


# =============================================================================
# E2E TESTS (10%) - Test complete workflow
# =============================================================================


class TestCompleteCleanup:
    """End-to-end tests for complete cleanup workflow"""

    def test_cleanup_workflow_complete(self):
        """Test complete cleanup workflow executed successfully"""
        # Check all files moved
        assert not Path("EVALUATION_SUMMARY.md").exists()
        assert not Path("gh_pages_link_validation.txt").exists()
        assert not Path("setup.py").exists()

        # Check all files in new locations
        assert Path("docs/memory/evaluation-summary.md").exists()
        assert Path("docs/testing/gh-pages-link-validation.txt").exists()
        assert Path("archive/legacy/setup.py").exists()

        # Check documentation created
        assert Path("docs/contributing/file-organization.md").exists()
        assert Path("archive/legacy/README.md").exists()

        # Check git history preserved
        result = subprocess.run(
            ["git", "log", "--follow", "--oneline", "docs/memory/evaluation-summary.md"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_project_still_functional_after_cleanup(self):
        """Test project remains functional after cleanup"""
        # Try to import main package
        try:
            import amplihack

            assert amplihack is not None
        except ImportError as e:
            pytest.fail(f"Package import failed after cleanup: {e}")

        # Check critical files still exist
        assert Path("pyproject.toml").exists()
        assert Path("README.md").exists()
        assert Path("CLAUDE.md").exists()


# =============================================================================
# TEST FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture
def git_repo():
    """Fixture ensuring we're in a git repository"""
    result = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True, text=True)
    assert result.returncode == 0, "Must be run in a git repository"
    return Path.cwd()


# =============================================================================
# TEST CONFIGURATION
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests (60% of test suite)")
    config.addinivalue_line("markers", "integration: Integration tests (30% of test suite)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (10% of test suite)")
