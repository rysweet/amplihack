"""Shared fixtures for GitHub Pages tests."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    """Create a temporary project root with basic structure."""
    # Create docs directory with content
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    # Create index.md
    index_md = docs_dir / "index.md"
    index_md.write_text("""# Test Project Documentation

Welcome to the test project.

## Features

- Feature one description
- Feature two description

## Getting Started

Follow these steps to get started.
""")

    # Create a reference section
    reference_dir = docs_dir / "reference"
    reference_dir.mkdir()

    api_md = reference_dir / "api.md"
    api_md.write_text("""# API Reference

## Authentication

Use the `authenticate()` function.

## Endpoints

### GET /users

Returns list of users.

### POST /users

Creates a new user.
""")

    # Create README.md
    readme = tmp_path / "README.md"
    readme.write_text("""# Test Project

This is the test project README.
""")

    # Initialize as git repo
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    return tmp_path


@pytest.fixture
def tmp_docs_dir(tmp_project_root: Path) -> Path:
    """Return the docs directory from the project root."""
    return tmp_project_root / "docs"


@pytest.fixture
def tmp_site_dir(tmp_path: Path) -> Path:
    """Create a temporary generated site directory."""
    site_dir = tmp_path / "site"
    site_dir.mkdir()

    # Create basic HTML structure
    (site_dir / "index.html").write_text("""<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Test Project</h1></body>
</html>
""")

    # Create a subdirectory with content
    reference_dir = site_dir / "reference"
    reference_dir.mkdir()

    (reference_dir / "api.html").write_text("""<!DOCTYPE html>
<html>
<head><title>API Reference</title></head>
<body><h1>API Reference</h1></body>
</html>
""")

    return site_dir


@pytest.fixture
def sample_markdown_files(tmp_path: Path) -> list[Path]:
    """Create sample markdown files for testing navigation generation."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(exist_ok=True)

    files = []

    # Root level files
    index = docs_dir / "index.md"
    index.write_text("# Home\n\nWelcome page.")
    files.append(index)

    getting_started = docs_dir / "getting-started.md"
    getting_started.write_text("# Getting Started\n\nHow to begin.")
    files.append(getting_started)

    # Tutorial section
    tutorials_dir = docs_dir / "tutorials"
    tutorials_dir.mkdir()

    tutorial1 = tutorials_dir / "basic.md"
    tutorial1.write_text("# Basic Tutorial\n\nBasic tutorial content.")
    files.append(tutorial1)

    # Reference section
    reference_dir = docs_dir / "reference"
    reference_dir.mkdir()

    cli_ref = reference_dir / "cli.md"
    cli_ref.write_text("# CLI Reference\n\nCommand line reference.")
    files.append(cli_ref)

    return files


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary directory that simulates a git repo."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    # Create .git directory (basic structure)
    git_dir = repo_dir / ".git"
    git_dir.mkdir()

    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")

    refs_dir = git_dir / "refs" / "heads"
    refs_dir.mkdir(parents=True)

    # Create site directory
    site_dir = repo_dir / "site"
    site_dir.mkdir()
    (site_dir / "index.html").write_text("<html><body>Test</body></html>")

    return repo_dir
