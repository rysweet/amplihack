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


# ========================================
# NEW TESTS: Comprehensive Review Detection
# ========================================


def test_pr_1595_comprehensive_comment_review():
    """Test PR #1595 scenario - comprehensive review in comment (CRITICAL TEST).

    This test reproduces the exact bug from issue #1598 where a comprehensive
    code review posted as a comment was not recognized by the PM triage system.

    The comment contains 7 comprehensive review patterns:
    - Review Summary
    - Overall Assessment
    - Strengths
    - Issues Found
    - Breaking Changes
    - Philosophy Compliance
    - Final Verdict
    - Score (7/10)
    """
    pr_data = {
        "title": "Fix comprehensive review detection",
        "body": "Addresses issue #1598",
        "comments": [
            {
                "body": """
# Review Summary

Overall Assessment: This PR improves the PM triage system significantly.

## Strengths:
- Clean implementation
- Well-tested
- Follows philosophy

## Issues Found:
- Minor type hint issue in one function
- Documentation could be expanded

## Breaking Changes:
None identified

## Philosophy Compliance:
Excellent - follows ruthless simplicity and modular design

## Final Verdict:
Approved with minor suggestions for follow-up

Score: 7/10
                """
            },
        ],
        "reviews": [],  # No formal reviews - only comment
    }

    result = analyzers_mvp.validate_workflow_compliance(pr_data)

    # CRITICAL: Must pass Step 11 based on comprehensive comment review
    assert result["step11_completed"] is True, (
        f"Expected step11_completed=True for comprehensive review comment, "
        f"got {result['step11_completed']}"
    )

    # Evidence should mention comprehensive review detection
    assert "comprehensive review detected: true" in result["step11_evidence"].lower(), (
        f"Expected evidence to show 'comprehensive review detected: true', "
        f"got: {result['step11_evidence']}"
    )

    # Should be overall compliant if feedback responses are present
    assert result["overall_compliant"] is True or not result["step12_completed"], (
        "If step11 passes, only step12 could block overall compliance"
    )


def test_partial_patterns_no_trigger():
    """Test that comments with only 2-3 patterns don't trigger comprehensive detection.

    This ensures we don't have false positives - only truly comprehensive
    reviews should get the boost.
    """
    pr_data = {
        "title": "Test PR",
        "body": "Test body",
        "comments": [
            {
                "body": """
Review summary: Looks decent.

Some issues found here and there.
                """
            },  # Only 2 patterns: "review summary" and "issues found"
        ],
        "reviews": [],
    }

    result = analyzers_mvp.validate_workflow_compliance(pr_data)

    # Should NOT trigger comprehensive detection (< 4 patterns)
    assert "comprehensive review detected: true" not in result["step11_evidence"].lower(), (
        "Expected no comprehensive review detection with < 4 patterns"
    )

    # Should fall back to keyword scoring
    assert "score" in result["step11_evidence"].lower(), "Expected fallback to keyword scoring"

    # Likely won't pass Step 11 with just 2 patterns
    assert result["step11_completed"] is False, (
        "Expected step11_completed=False with only 2 patterns"
    )


def test_evidence_message_accuracy():
    """Test that evidence messages accurately report reviews and comments.

    The evidence should clearly show:
    - Number of formal reviews
    - Number of comprehensive comment reviews
    - Final review score
    - Comprehensive detection status
    """
    pr_data = {
        "title": "Test PR",
        "body": "Test body",
        "comments": [
            {
                "body": """
# Review Summary
Overall Assessment: Good work
Strengths: Clean code
Issues Found: None
Breaking Changes: None
Philosophy Compliance: Excellent
Final Verdict: Approved
Score: 8/10
                """
            },
        ],
        "reviews": [
            {"state": "APPROVED", "body": "LGTM!"},
        ],
    }

    result = analyzers_mvp.validate_workflow_compliance(pr_data)

    # Evidence should mention BOTH formal reviews and comments
    evidence = result["step11_evidence"].lower()

    # Should report formal reviews
    assert "1" in evidence and "review" in evidence, (
        f"Expected evidence to report 1 formal review, got: {result['step11_evidence']}"
    )

    # Should report comprehensive detection
    assert "comprehensive" in evidence, (
        f"Expected evidence to mention comprehensive detection, got: {result['step11_evidence']}"
    )

    # Should report score
    assert "score" in evidence, (
        f"Expected evidence to show review score, got: {result['step11_evidence']}"
    )

    # Should show comprehensive review detected
    assert "comprehensive review detected: true" in evidence, (
        f"Expected 'comprehensive review detected: true', got: {result['step11_evidence']}"
    )


def test_backward_compatibility_formal_reviews():
    """Test that existing formal APPROVED reviews still work (no regression).

    This ensures our changes don't break the existing functionality for
    formal GitHub review approvals.
    """
    pr_data = {
        "title": "Test PR",
        "body": "Test body",
        "comments": [
            {"body": "Fixed the issue"},
            {"body": "Addressed feedback"},
            {"body": "Updated per comments"},
        ],
        "reviews": [
            {"state": "APPROVED", "body": "Looks good to me!"},
        ],
    }

    result = analyzers_mvp.validate_workflow_compliance(pr_data)

    # Should still pass as before (formal approval = +5 score)
    assert result["step11_completed"] is True, "Formal APPROVED review should still pass Step 11"

    # Evidence should report the formal review
    assert "1" in result["step11_evidence"] and "review" in result["step11_evidence"].lower(), (
        "Evidence should mention the formal review"
    )

    # Should be overall compliant
    assert result["overall_compliant"] is True, (
        "Should be overall compliant with approval and feedback responses"
    )


def test_comprehensive_and_formal_both():
    """Test that both formal review AND comprehensive comment count together.

    When a PR has both a formal approval and a comprehensive comment review,
    both should contribute to the review score, resulting in a higher score.
    """
    pr_data = {
        "title": "Test PR",
        "body": "Test body",
        "comments": [
            {
                "body": """
# Review Summary
Overall Assessment: Excellent
Strengths: Great design
Issues Found: None
Breaking Changes: None
Philosophy Compliance: Perfect
Final Verdict: Ship it
Score: 9/10
                """
            },
        ],
        "reviews": [
            {"state": "APPROVED", "body": "Approved!"},
        ],
    }

    result = analyzers_mvp.validate_workflow_compliance(pr_data)

    # Both should contribute to passing
    assert result["step11_completed"] is True, (
        "Should pass with both formal and comprehensive reviews"
    )

    # Evidence should show both
    evidence = result["step11_evidence"].lower()
    assert "review" in evidence, "Should mention reviews"
    assert "comprehensive" in evidence, "Should mention comprehensive detection"

    # Score should be high (formal approval + comprehensive boost)
    assert "score" in evidence, "Should show review score"


def test_case_insensitivity():
    """Test that pattern matching is case-insensitive.

    Patterns should match regardless of case:
    - "REVIEW SUMMARY" = "Review Summary" = "review summary"
    """
    test_cases = [
        "REVIEW SUMMARY\nOVERALL ASSESSMENT\nSTRENGTHS:\nISSUES FOUND:\nBREAKING CHANGES\nFINAL VERDICT\nSCORE: 8/10",
        "Review Summary\nOverall Assessment\nStrengths:\nIssues Found:\nBreaking Changes\nFinal Verdict\nScore: 8/10",
        "review summary\noverall assessment\nstrengths:\nissues found:\nbreaking changes\nfinal verdict\nscore: 8/10",
    ]

    for body in test_cases:
        pr_data = {
            "title": "Test PR",
            "body": "Test body",
            "comments": [{"body": body}],
            "reviews": [],
        }

        result = analyzers_mvp.validate_workflow_compliance(pr_data)

        # All variations should trigger comprehensive detection
        assert "comprehensive review detected: true" in result["step11_evidence"].lower(), (
            f"Pattern matching should be case-insensitive, failed for: {body[:50]}"
        )

        # All should pass Step 11
        assert result["step11_completed"] is True, (
            "Should pass Step 11 with comprehensive review (case variation)"
        )


def test_edge_case_threshold_boundary():
    """Test exactly at threshold (4 patterns) and just below (3 patterns).

    - Exactly 4 patterns = comprehensive detection triggered
    - Only 3 patterns = comprehensive detection NOT triggered
    """
    # Test with exactly 4 patterns (at threshold)
    pr_data_at_threshold = {
        "title": "Test PR",
        "body": "Test body",
        "comments": [
            {
                "body": """
Review Summary: Good work
Overall Assessment: Solid implementation
Strengths: Clean code
Issues Found: None
                """
            },  # 4 patterns
        ],
        "reviews": [],
    }

    result_at = analyzers_mvp.validate_workflow_compliance(pr_data_at_threshold)

    # Should trigger comprehensive detection (>= 4 patterns)
    assert "comprehensive review detected: true" in result_at["step11_evidence"].lower(), (
        "Expected comprehensive detection with exactly 4 patterns"
    )

    # Test with 3 patterns (below threshold)
    pr_data_below_threshold = {
        "title": "Test PR",
        "body": "Test body",
        "comments": [
            {
                "body": """
Review Summary: Good work
Overall Assessment: Solid implementation
Strengths: Clean code
                """
            },  # Only 3 patterns
        ],
        "reviews": [],
    }

    result_below = analyzers_mvp.validate_workflow_compliance(pr_data_below_threshold)

    # Should NOT trigger comprehensive detection (< 4 patterns)
    assert "comprehensive review detected: true" not in result_below["step11_evidence"].lower(), (
        "Should NOT trigger comprehensive detection with only 3 patterns"
    )
