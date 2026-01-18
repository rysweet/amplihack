"""Tests for report generation."""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir.parent))

from pr_triage.report_generator import generate_triage_report


def test_generate_report_compliant():
    """Test report generation for compliant PR."""
    pr_data = {
        "title": "Test PR",
        "author": {"login": "testuser"},
        "headRefName": "feature-branch",
        "baseRefName": "main",
        "files": [{"path": "test.py"}],
        "comments": [],
        "reviews": [],
    }

    compliance = {
        "overall_compliant": True,
        "step11_completed": True,
        "step11_evidence": "Review completed",
        "step12_completed": True,
        "step12_evidence": "Feedback addressed",
        "recommendations": [],
    }

    labels = {
        "priority": "MEDIUM",
        "priority_reasoning": "Standard feature",
        "complexity": "SIMPLE",
        "complexity_reasoning": "Single file change",
    }

    unrelated = {
        "has_unrelated_changes": False,
        "primary_purpose": "Add new feature",
    }

    report = generate_triage_report(123, pr_data, compliance, labels, unrelated)

    assert "PM Architect PR Triage Analysis" in report
    assert "#123" in report
    assert "Test PR" in report
    assert "@testuser" in report
    assert "COMPLIANT" in report
    assert "MEDIUM" in report
    assert "SIMPLE" in report


def test_generate_report_non_compliant():
    """Test report generation for non-compliant PR."""
    pr_data = {
        "title": "Incomplete PR",
        "author": {"login": "testuser"},
        "headRefName": "wip-branch",
        "baseRefName": "main",
        "files": [],
        "comments": [],
        "reviews": [],
    }

    compliance = {
        "overall_compliant": False,
        "step11_completed": False,
        "step11_evidence": "No review posted",
        "step12_completed": False,
        "step12_evidence": "No feedback",
        "blocking_issues": ["Missing code review", "No tests"],
        "recommendations": ["Post review", "Add tests"],
    }

    labels = {"priority": "LOW", "complexity": "SIMPLE"}

    unrelated = {"has_unrelated_changes": False}

    report = generate_triage_report(456, pr_data, compliance, labels, unrelated)

    assert "NON-COMPLIANT" in report
    assert "Missing code review" in report
    assert "No tests" in report
    assert "Post review" in report


def test_generate_report_unrelated_changes():
    """Test report generation with unrelated changes."""
    pr_data = {
        "title": "Mixed PR",
        "author": {"login": "testuser"},
        "headRefName": "mixed",
        "baseRefName": "main",
        "files": [],
        "comments": [],
        "reviews": [],
    }

    compliance = {"overall_compliant": True}

    labels = {"priority": "MEDIUM", "complexity": "MODERATE"}

    unrelated = {
        "has_unrelated_changes": True,
        "primary_purpose": "Fix bug",
        "unrelated_purposes": ["Refactor code", "Update docs"],
        "unrelated_files": ["unrelated.py", "docs.md"],
        "recommendation": "Split into separate PRs",
    }

    report = generate_triage_report(789, pr_data, compliance, labels, unrelated)

    assert "UNRELATED CHANGES DETECTED" in report
    assert "Fix bug" in report
    assert "Refactor code" in report
    assert "unrelated.py" in report
    assert "Split into separate PRs" in report


def test_generate_report_includes_statistics():
    """Test that report includes statistics section."""
    pr_data = {
        "title": "Test",
        "author": {"login": "user"},
        "headRefName": "branch",
        "baseRefName": "main",
        "files": [{"path": "a.py"}, {"path": "b.py"}],
        "comments": [{"body": "comment"}],
        "reviews": [{"state": "APPROVED"}],
    }

    compliance = {"overall_compliant": True}
    labels = {"priority": "LOW", "complexity": "SIMPLE"}
    unrelated = {"has_unrelated_changes": False}

    report = generate_triage_report(999, pr_data, compliance, labels, unrelated)

    assert "Statistics" in report
    assert "Files Changed**: 2" in report
    assert "Comments**: 1" in report
    assert "Reviews**: 1" in report


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
