"""Shared fixtures for link fixer tests."""

import subprocess

import pytest


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary git repository for testing.

    Returns:
        Path: Path to temporary repository root
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo_path, capture_output=True, check=True
    )

    return repo_path


@pytest.fixture
def sample_markdown_files(temp_repo):
    """Create sample markdown files with various link types.

    Returns:
        Dict[str, Path]: Mapping of file identifiers to paths
    """
    files = {}

    # Create docs directory
    docs_dir = temp_repo / "docs"
    docs_dir.mkdir()

    # File 1: Documentation with valid links
    file1 = docs_dir / "README.md"
    file1.write_text("""# Documentation

[Valid link](./guide.md)
[Another valid](../other/file.md)
""")
    files["valid_links"] = file1

    # File 2: File with case-sensitivity issues
    file2 = docs_dir / "guide.md"
    file2.write_text("""# Guide

[Case issue](./README.MD)  <!-- Should be README.md -->
[Another case](./GUIDE.md)  <!-- Should be guide.md -->
""")
    files["case_issues"] = file2

    # File 3: Missing extensions
    file3 = docs_dir / "tutorial.md"
    file3.write_text("""# Tutorial

[Missing ext](./README)  <!-- Should be README.md -->
[Also missing](../docs/guide)  <!-- Should be guide.md -->
""")
    files["missing_ext"] = file3

    # File 4: Broken anchors
    file4 = docs_dir / "anchors.md"
    file4.write_text("""# Anchors

[Bad anchor](./guide.md#non-existent)
[Good anchor](./guide.md#guide)
""")
    files["anchors"] = file4

    # Commit initial files
    subprocess.run(["git", "add", "."], cwd=temp_repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=temp_repo, capture_output=True, check=True
    )

    return files


@pytest.fixture
def git_history_repo(temp_repo):
    """Create a repository with git history for moved files.

    Returns:
        tuple: (repo_path, old_path, new_path)
    """
    # Create initial file
    old_path = temp_repo / "old_location.md"
    old_path.write_text("# Original Content")

    subprocess.run(
        ["git", "add", "old_location.md"], cwd=temp_repo, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Add original file"], cwd=temp_repo, capture_output=True, check=True
    )

    # Move file
    _new_path = temp_repo / "new_location.md"
    subprocess.run(
        ["git", "mv", "old_location.md", "new_location.md"],
        cwd=temp_repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Move file"], cwd=temp_repo, capture_output=True, check=True
    )

    return temp_repo, "old_location.md", "new_location.md"


@pytest.fixture
def broken_link_data():
    """Fixture providing broken link test data.

    Returns:
        List[Dict]: List of broken link scenarios
    """
    return [
        {
            "source_file": "docs/README.md",
            "broken_path": "./GUIDE.MD",
            "line_number": 5,
            "expected_fix": "./guide.md",
            "fix_type": "case_sensitivity",
        },
        {
            "source_file": "docs/tutorial.md",
            "broken_path": "./README",
            "line_number": 3,
            "expected_fix": "./README.md",
            "fix_type": "missing_extension",
        },
        {
            "source_file": "docs/anchors.md",
            "broken_path": "./guide.md#non-existent",
            "line_number": 7,
            "expected_fix": "./guide.md#guide",
            "fix_type": "broken_anchor",
        },
    ]


@pytest.fixture
def confidence_test_cases():
    """Fixture providing confidence calculation test cases.

    Returns:
        List[Dict]: Test cases with expected confidence scores
    """
    return [
        {"strategy": "case_sensitivity", "matches": 1, "expected_confidence": 0.95},
        {
            "strategy": "case_sensitivity",
            "matches": 3,
            "expected_confidence": 0.50,  # Low confidence with multiple matches
        },
        {"strategy": "git_history", "moves": 1, "expected_confidence": 0.90},
        {"strategy": "missing_extension", "matches": 1, "expected_confidence": 0.85},
        {"strategy": "broken_anchor", "exact_match": True, "expected_confidence": 0.90},
        {
            "strategy": "broken_anchor",
            "fuzzy_match": True,
            "similarity": 0.85,
            "expected_confidence": 0.75,
        },
        {"strategy": "relative_path", "normalized": True, "expected_confidence": 0.75},
        {"strategy": "double_slash", "cleaned": True, "expected_confidence": 0.70},
    ]
