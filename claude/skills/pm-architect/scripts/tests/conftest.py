"""Shared test fixtures for PM Architect scripts."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project root directory."""
    return tmp_path


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Mock subprocess.run to avoid actual subprocess calls."""
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.returncode = 0
    mock.stdout = ""
    mock.stderr = ""

    def _mock_run(*args, **kwargs):
        return mock

    monkeypatch.setattr(subprocess, "run", _mock_run)
    return mock


@pytest.fixture
def sample_issue_data() -> dict:
    """Sample issue data from GitHub API."""
    return {
        "number": 123,
        "title": "Sample Issue Title",
        "author": {"login": "testuser"},
        "body": "This is a sample issue description.",
        "comments": [
            {
                "author": {"login": "commenter1"},
                "body": "This is a comment.",
                "createdAt": "2025-01-01T00:00:00Z",
            }
        ],
    }


@pytest.fixture
def sample_pr_data() -> dict:
    """Sample PR data from GitHub API."""
    return {
        "number": 456,
        "title": "Sample PR Title",
        "author": {"login": "testuser"},
        "body": "This is a sample PR description.",
        "createdAt": "2025-01-01T00:00:00Z",
        "additions": 100,
        "deletions": 50,
        "files": [
            {"path": "file1.py", "additions": 50, "deletions": 25},
            {"path": "file2.py", "additions": 50, "deletions": 25},
        ],
        "labels": [{"name": "bug"}, {"name": "priority:high"}],
        "reviews": [],
    }


@pytest.fixture
def sample_auto_mode_output() -> str:
    """Sample amplihack auto mode output."""
    return """Initializing amplihack...
AUTONOMOUS MODE ACTIVATED
Processing request...

## Analysis

This is a sample analysis of the request.

### Key Points

1. Point one
2. Point two
3. Point three

## Recommendations

Based on the analysis, here are the recommendations:

- Recommendation 1
- Recommendation 2

## Next Steps

1. Step one
2. Step two

Auto mode completed successfully.
"""


@pytest.fixture
def sample_daily_status_output() -> str:
    """Sample daily status report output."""
    return """# Daily Status Report - 2025-01-01

## Summary

Project is progressing well with 5 active workstreams.

## Active Workstreams

### Authentication System
- Status: In Progress
- Progress: 75%
- Blockers: None

### API Refactoring
- Status: In Progress
- Progress: 50%
- Blockers: Awaiting design review

## Metrics

- Open Issues: 23
- Open PRs: 8
- Velocity: 45 story points/week

## Recommendations

1. Prioritize design review for API refactoring
2. Address technical debt in authentication system
"""


# --- Top 5 Priority Aggregation Fixtures ---


@pytest.fixture
def pm_dir(tmp_path: Path) -> Path:
    """Create .pm/ directory structure with sample data."""
    pm = tmp_path / ".pm"
    (pm / "backlog").mkdir(parents=True)
    (pm / "workstreams").mkdir(parents=True)
    (pm / "delegations").mkdir(parents=True)
    return pm


@pytest.fixture
def sample_backlog_items() -> dict:
    """Sample backlog items YAML data."""
    return {
        "items": [
            {
                "id": "BL-001",
                "title": "Fix authentication bug",
                "description": "Auth tokens expire prematurely",
                "priority": "HIGH",
                "estimated_hours": 2,
                "status": "READY",
                "tags": ["auth", "bug"],
                "dependencies": [],
            },
            {
                "id": "BL-002",
                "title": "Implement config parser",
                "description": "Parse YAML and JSON config files",
                "priority": "MEDIUM",
                "estimated_hours": 4,
                "status": "READY",
                "tags": ["config", "core"],
                "dependencies": [],
            },
            {
                "id": "BL-003",
                "title": "Add logging framework",
                "description": "Structured logging with JSON output",
                "priority": "LOW",
                "estimated_hours": 8,
                "status": "READY",
                "tags": ["infrastructure"],
                "dependencies": ["BL-002"],
            },
            {
                "id": "BL-004",
                "title": "Write API documentation",
                "description": "Document all REST endpoints",
                "priority": "MEDIUM",
                "estimated_hours": 3,
                "status": "READY",
                "tags": ["docs"],
                "dependencies": [],
            },
            {
                "id": "BL-005",
                "title": "Database migration tool",
                "description": "Automated schema migrations",
                "priority": "HIGH",
                "estimated_hours": 6,
                "status": "READY",
                "tags": ["database", "core"],
                "dependencies": ["BL-002"],
            },
            {
                "id": "BL-006",
                "title": "Refactor test suite",
                "description": "Improve test performance and coverage",
                "priority": "MEDIUM",
                "estimated_hours": 1,
                "status": "IN_PROGRESS",
                "tags": ["test"],
                "dependencies": [],
            },
        ]
    }


@pytest.fixture
def populated_pm(pm_dir, sample_backlog_items):
    """Create fully populated .pm/ directory."""
    with open(pm_dir / "backlog" / "items.yaml", "w") as f:
        yaml.dump(sample_backlog_items, f)

    ws_data = {
        "id": "ws-1",
        "backlog_id": "BL-006",
        "title": "Test Suite Refactor",
        "agent": "builder",
        "status": "RUNNING",
        "last_activity": "2020-01-01T00:00:00Z",
    }
    with open(pm_dir / "workstreams" / "ws-1.yaml", "w") as f:
        yaml.dump(ws_data, f)

    deleg_data = {
        "id": "DEL-001",
        "title": "Implement caching layer",
        "status": "READY",
        "backlog_id": "BL-002",
    }
    with open(pm_dir / "delegations" / "del-001.yaml", "w") as f:
        yaml.dump(deleg_data, f)

    roadmap = """# Project Roadmap

## Q1 Goals

### Core Infrastructure
- Implement config parser
- Database migration tool
- Logging framework

### Quality
- Test coverage above 80%
- API documentation complete
"""
    (pm_dir / "roadmap.md").write_text(roadmap)

    return pm_dir
