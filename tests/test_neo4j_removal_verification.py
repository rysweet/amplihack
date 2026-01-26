"""Verification tests for complete Neo4j removal.

These tests ensure that ALL Neo4j code has been removed from the codebase.
They should PASS after the removal is complete.
"""

import subprocess
from pathlib import Path


def test_no_neo4j_source_directories():
    """Verify no Neo4j directories exist in source code."""
    project_root = Path(__file__).parent.parent

    # Check for neo4j directories in src/
    neo4j_dirs = list((project_root / "src").rglob("*neo4j*"))

    assert len(neo4j_dirs) == 0, (
        f"Found Neo4j directories in source: {[str(d) for d in neo4j_dirs]}"
    )


def test_no_neo4j_imports_in_source():
    """Verify no Neo4j imports remain in source code (Python files only)."""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"

    # Search for Neo4j imports in Python files only (not markdown)
    result = subprocess.run(
        [
            "grep",
            "-r",
            "-i",
            "from.*neo4j\\|import.*neo4j",
            str(src_dir),
            "--include=*.py",
            "--exclude=*neo4j_removal*",
        ],
        capture_output=True,
        text=True,
    )

    # grep returns 1 when no matches found (success for us)
    assert result.returncode == 1, f"Found Neo4j imports in Python source code:\n{result.stdout}"


def test_no_active_neo4j_code():
    """Verify no active Neo4j code (imports/classes) in Python files.

    Historical comments and documentation references are allowed.
    """
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"

    # Search for actual Neo4j code (imports, classes, function calls)
    # Exclude comments that say "Neo4j removed" or "Neo4j cleanup"
    result = subprocess.run(
        [
            "grep",
            "-r",
            "from.*neo4j\\|import.*neo4j\\|Neo4jConnector\\|Neo4jManager",
            str(src_dir),
            "--include=*.py",
            "--exclude=*neo4j_removal*",
        ],
        capture_output=True,
        text=True,
    )

    # grep returns 1 when no matches found
    assert result.returncode == 1, (
        f"Found active Neo4j code (imports/classes) in Python files:\n{result.stdout}"
    )


def test_no_neo4j_in_dependencies():
    """Verify no Neo4j dependencies in pyproject.toml."""
    project_root = Path(__file__).parent.parent
    pyproject = project_root / "pyproject.toml"

    content = pyproject.read_text()

    # Check for neo4j mentions (case-insensitive)
    assert "neo4j" not in content.lower(), (
        "Found 'neo4j' in pyproject.toml - should be completely removed"
    )


def test_launcher_imports_successfully():
    """Verify launcher can be imported without Neo4j errors."""
    try:
        from amplihack.launcher.core import ClaudeLauncher  # noqa: F401

        # If we get here, import succeeded (no Neo4j import errors)
        assert True
    except ImportError as e:
        if "neo4j" in str(e).lower():
            raise AssertionError(f"Launcher import failed due to Neo4j reference: {e}")
        # Other import errors are acceptable (might be env-specific)


def test_memory_system_imports_successfully():
    """Verify memory system imports without Neo4j dependencies."""
    try:
        from amplihack.memory import (
            auto_backend,
            coordinator,  # noqa: F401
        )

        # Check that auto_backend doesn't have neo4j option
        backend_code = Path(auto_backend.__file__).read_text()
        assert 'env_backend == "neo4j"' not in backend_code, (
            "auto_backend.py still has Neo4j backend option"
        )

    except ImportError as e:
        if "neo4j" in str(e).lower():
            raise AssertionError(f"Memory system import failed due to Neo4j reference: {e}")


def test_no_neo4j_test_markers():
    """Verify Neo4j test markers removed from pytest.ini."""
    project_root = Path(__file__).parent.parent
    pytest_ini = project_root / "pytest.ini"

    if pytest_ini.exists():
        content = pytest_ini.read_text()
        assert "neo4j" not in content.lower(), "Found 'neo4j' test marker in pytest.ini"


def test_no_neo4j_in_hooks():
    """Verify no Neo4j references in hook files."""
    project_root = Path(__file__).parent.parent

    # Check .claude/tools/amplihack/hooks/
    hooks_dir = project_root / "src" / "amplihack" / ".claude" / "tools" / "amplihack" / "hooks"

    if hooks_dir.exists():
        result = subprocess.run(
            ["grep", "-r", "-i", "neo4j", str(hooks_dir)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1, f"Found Neo4j references in hooks:\n{result.stdout}"
