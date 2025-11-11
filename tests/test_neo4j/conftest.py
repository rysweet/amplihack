"""Pytest fixtures for Neo4j tests."""

import os
from pathlib import Path
from typing import Generator

import pytest
from neo4j import Driver, GraphDatabase

from amplihack.memory.neo4j.neo4j_schema import Neo4jSchema


@pytest.fixture(scope="session")
def neo4j_uri() -> str:
    """Get Neo4j connection URI from environment."""
    return os.environ.get("NEO4J_URI", "bolt://localhost:7687")


@pytest.fixture(scope="session")
def neo4j_user() -> str:
    """Get Neo4j username from environment."""
    return os.environ.get("NEO4J_USER", "neo4j")


@pytest.fixture(scope="session")
def neo4j_password() -> str:
    """Get Neo4j password from environment."""
    return os.environ.get("NEO4J_PASSWORD", "password")


@pytest.fixture(scope="function")
def neo4j_driver(
    neo4j_uri: str, neo4j_user: str, neo4j_password: str
) -> Generator[Driver, None, None]:
    """Create Neo4j driver for testing.

    Yields:
        Neo4j driver instance

    Note:
        This fixture clears the database before each test.
    """
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    try:
        # Verify connection
        driver.verify_connectivity()

        # Clear database before test
        schema = Neo4jSchema(driver)
        schema.clear_all_data()

        yield driver

    finally:
        # Clean up after test
        try:
            schema = Neo4jSchema(driver)
            schema.clear_all_data()
        except Exception:
            pass

        driver.close()


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary Git repository for testing.

    Args:
        tmp_path: pytest's temporary directory fixture

    Yields:
        Path to temporary Git repository
    """
    import subprocess

    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True
    )

    # Add remote
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/test/repo.git"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True, capture_output=True
    )

    yield repo_path


@pytest.fixture
def sample_codebase_identity():
    """Create sample CodebaseIdentity for testing."""
    from amplihack.memory.neo4j.identifier import CodebaseIdentifier

    return CodebaseIdentifier.create_manual_identity(
        remote_url="https://github.com/test/repo.git",
        branch="main",
        commit_sha="a" * 40,
    )
