"""Tests for MVP heuristic-based analyzers."""

from pr_triage import analyzers_mvp


def test_validate_workflow_compliance_with_approval():
    """Test workflow compliance with approved review."""
    pr_data = {
        "title": "Test PR",
        "body": "Test body",
        "comments": [
            {"body": "Code review completed. LGTM!"},
            {"body": "Security review passed."},
            {"body": "Addressed feedback"},
            {"body": "Fixed the issue"},
            {"body": "Updated per comments"},
            {"body": "Done"},
        ],
        "reviews": [
            {"state": "APPROVED", "body": "Looks good to me!"},
        ],
    }

    result = analyzers_mvp.validate_workflow_compliance(pr_data)

    assert result["step11_completed"] is True
    assert result["overall_compliant"] is True
    assert len(result["blocking_issues"]) == 0


def test_validate_workflow_compliance_no_review():
    """Test workflow compliance with no review."""
    pr_data = {
        "title": "Test PR",
        "body": "Test body",
        "comments": [],
        "reviews": [],
    }

    result = analyzers_mvp.validate_workflow_compliance(pr_data)

    assert result["step11_completed"] is False
    assert result["overall_compliant"] is False
    assert len(result["blocking_issues"]) > 0


def test_validate_workflow_compliance_partial():
    """Test workflow compliance with partial evidence."""
    pr_data = {
        "title": "Test PR",
        "body": "Test body",
        "comments": [
            {"body": "Code quality looks good"},
            {"body": "Test coverage verified"},
        ],
        "reviews": [],
    }

    result = analyzers_mvp.validate_workflow_compliance(pr_data)

    # Should have some review score but not enough for compliance
    assert result["overall_compliant"] is False
    assert "score" in result["step11_evidence"].lower()


def test_detect_priority_complexity_critical():
    """Test priority detection for critical issues."""
    pr_data = {
        "title": "CRITICAL: Security vulnerability in auth",
        "body": "Fixes critical security issue",
        "files": [{"path": "auth.py", "additions": 10, "deletions": 5}],
        "diff": "test diff",
    }

    result = analyzers_mvp.detect_priority_complexity(pr_data)

    assert result["priority"] == "CRITICAL"
    assert "security" in result["priority_reasoning"].lower()


def test_detect_priority_complexity_simple():
    """Test complexity detection for simple changes."""
    pr_data = {
        "title": "Update typo in documentation",
        "body": "Simple typo correction in docs",
        "files": [{"path": "docs/README.md", "additions": 1, "deletions": 1}],
        "diff": "test diff",
    }

    result = analyzers_mvp.detect_priority_complexity(pr_data)

    assert result["priority"] == "LOW"
    assert result["complexity"] == "SIMPLE"


def test_detect_priority_complexity_very_complex():
    """Test complexity detection for large changes."""
    pr_data = {
        "title": "Major refactoring of core system",
        "body": "Large architectural changes",
        "files": [{"path": f"file{i}.py", "additions": 50, "deletions": 30} for i in range(15)],
        "diff": "test diff",
    }

    result = analyzers_mvp.detect_priority_complexity(pr_data)

    assert result["complexity"] == "VERY_COMPLEX"
    assert "15 files" in result["complexity_reasoning"]


def test_detect_unrelated_changes_focused():
    """Test detection with focused changes."""
    pr_data = {
        "title": "Add user authentication",
        "body": "Implements JWT auth",
        "files": [
            {"path": "auth.py"},
            {"path": "models/user.py"},
            {"path": "tests/test_auth.py"},
        ],
        "diff": "test diff",
    }

    result = analyzers_mvp.detect_unrelated_changes(pr_data)

    assert result["has_unrelated_changes"] is False


def test_detect_unrelated_changes_mixed():
    """Test detection with mixed unrelated changes."""
    pr_data = {
        "title": "Add feature X",
        "body": "New feature implementation",
        "files": [
            {"path": "feature_x.py"},
            {"path": "tests/test_feature_x.py"},
            {"path": "README.md"},
            {"path": ".github/workflows/ci.yml"},
            {"path": "config.json"},
        ],
        "diff": "test diff",
    }

    result = analyzers_mvp.detect_unrelated_changes(pr_data)

    assert result["has_unrelated_changes"] is True
    assert len(result["unrelated_purposes"]) > 0


def test_detect_unrelated_changes_refactor_and_feature():
    """Test detection with mixed refactor and feature."""
    pr_data = {
        "title": "Refactor and add feature Y",
        "body": "Refactoring + new feature",
        "files": [{"path": f"file{i}.py"} for i in range(10)],
        "diff": "test diff",
    }

    result = analyzers_mvp.detect_unrelated_changes(pr_data)

    assert result["has_unrelated_changes"] is True
    assert "refactoring" in result["recommendation"].lower()


def test_detect_priority_high_for_bugs():
    """Test priority is HIGH for bug fixes."""
    pr_data = {
        "title": "Fix critical bug in payment processing",
        "body": "Fixes issue #123",
        "files": [{"path": "payment.py", "additions": 20, "deletions": 10}],
        "diff": "test diff",
    }

    result = analyzers_mvp.detect_priority_complexity(pr_data)

    assert result["priority"] in ["HIGH", "CRITICAL"]


def test_detect_complexity_moderate():
    """Test complexity is MODERATE for typical changes."""
    pr_data = {
        "title": "Add validation function",
        "body": "New validation logic",
        "files": [
            {"path": "validators.py", "additions": 80, "deletions": 20},
            {"path": "tests/test_validators.py", "additions": 50, "deletions": 0},
        ],
        "diff": "test diff",
    }

    result = analyzers_mvp.detect_priority_complexity(pr_data)

    assert result["complexity"] == "MODERATE"


def test_architectural_changes_increase_complexity():
    """Test architectural files increase complexity."""
    pr_data = {
        "title": "Update workflow",
        "body": "Workflow changes",
        "files": [
            {"path": "workflow/DEFAULT_WORKFLOW.md", "additions": 30, "deletions": 10},
        ],
        "diff": "test diff",
    }

    result = analyzers_mvp.detect_priority_complexity(pr_data)

    assert result["complexity"] == "VERY_COMPLEX"
    assert "architectural" in result["complexity_reasoning"].lower()
