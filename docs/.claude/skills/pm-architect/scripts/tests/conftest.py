"""Shared test fixtures for PM Architect scripts."""

import subprocess
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock

import pytest


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
def sample_issue_data() -> Dict:
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
def sample_pr_data() -> Dict:
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
