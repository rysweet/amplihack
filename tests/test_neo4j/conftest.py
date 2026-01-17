"""Pytest fixtures for Neo4j tests."""

import os
import subprocess
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

# Conditional imports - these tests require amplihack and neo4j to be installed
NEO4J_AVAILABLE = False
GraphDatabase: Any = None
Neo4jSchema: Any = None
CodebaseIdentifier: Any = None

try:
    from neo4j import GraphDatabase as _GraphDatabase

    from amplihack.memory.neo4j.identifier import CodebaseIdentifier as _CodebaseIdentifier
    from amplihack.memory.neo4j.neo4j_schema import Neo4jSchema as _Neo4jSchema

    GraphDatabase = _GraphDatabase
    Neo4jSchema = _Neo4jSchema
    CodebaseIdentifier = _CodebaseIdentifier
    NEO4J_AVAILABLE = True
except ImportError:
    pass


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
) -> Generator[Any, None, None]:
    """Create Neo4j driver for testing.

    Yields:
        Neo4j driver instance

    Note:
        This fixture clears the database before each test.
    """
    if not NEO4J_AVAILABLE:
        pytest.skip("Neo4j dependencies not available")

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
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
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
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    yield repo_path


@pytest.fixture
def sample_codebase_identity() -> Any:
    """Create sample CodebaseIdentity for testing."""
    if not NEO4J_AVAILABLE:
        pytest.skip("Neo4j dependencies not available")

    from amplihack.memory.neo4j.identifier import CodebaseIdentifier

    return CodebaseIdentifier.create_manual_identity(
        remote_url="https://github.com/test/repo.git",
        branch="main",
        commit_sha="a" * 40,
    )
