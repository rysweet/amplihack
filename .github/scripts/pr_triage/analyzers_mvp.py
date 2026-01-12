"""PR analysis functions using heuristic-based validation (MVP).

This MVP version uses simple heuristics instead of Claude AI for faster,
deterministic validation. Suitable for initial deployment and testing.

Comprehensive Review Detection:
    Recognizes structured code reviews posted as comments (not just formal GitHub reviews).
    Pattern examples that trigger comprehensive detection (need 4+):
    - "Review Summary:" / "Overall Assessment:"
    - "Strengths:" / "Issues Found:"
    - "Breaking Changes:" / "Philosophy Compliance"
    - "Final Verdict" / "Score: 8.5" / "8/10"
    - "Recommendations:"
"""

import re
from typing import Any

# Comprehensive review pattern detection
COMPREHENSIVE_REVIEW_PATTERNS = [
    r"review\s+summary",  # "Review Summary:"
    r"overall\s+assessment",  # "Overall Assessment:"
    r"strengths:",  # "Strengths:"
    r"issues?\s+found:",  # "Issues Found:" or "Issue Found:"
    r"breaking\s+changes?:",  # "Breaking Changes:" or "Breaking Change:"
    r"philosophy\s+compliance",  # "Philosophy Compliance"
    r"final\s+verdict",  # "Final Verdict"
    r"score:\s*[\d.]+",  # "Score: 8.5" or "score: 8/10"
    r"\b\d+(?:\.\d+)?/10\b",  # "8.5/10"
    r"recommendations?:",  # "Recommendations:" or "Recommendation:"
]

PATTERN_THRESHOLD = 4  # 4+ patterns = comprehensive review
# Chosen to avoid false positives from casual comments while catching
# structured reviews. Validated by PR #1595 which had 7 patterns.

COMPREHENSIVE_REVIEW_BOOST = 10  # Equivalent to 2 formal approvals
# (Formal approval = +5 score, so 2 x 5 = 10)
# Ensures comprehensive comment reviews have equal weight to formal reviews


def validate_workflow_compliance(pr_data: dict[str, Any]) -> dict[str, Any]:
    """Check if PR completed Steps 11-12 of workflow using heuristics.

    Args:
        pr_data: PR data dictionary

    Returns:
        Validation result with compliance status and details
    """
    comments = pr_data.get("comments", [])
    reviews = pr_data.get("reviews", [])

    # Step 11: Check for comprehensive code review
    step11_completed = False
    step11_evidence = ""

    # Look for review indicators in comments and reviews
    review_keywords = [
        "code review",
        "security review",
        "philosophy compliance",
        "test coverage",
        "code quality",
        "lgtm",
        "looks good",
        "approved",
    ]

    review_score = 0
    comprehensive_review_found = False

    for comment in comments:
        body = comment.get("body", "").lower()

        # Check for comprehensive review patterns
        pattern_matches = sum(
            1
            for pattern in COMPREHENSIVE_REVIEW_PATTERNS
            if re.search(pattern, body, re.IGNORECASE)
        )

        if pattern_matches >= PATTERN_THRESHOLD:
            comprehensive_review_found = True
            review_score += COMPREHENSIVE_REVIEW_BOOST
            # Continue to keyword matching to accumulate additional score

        # Original keyword matching (unchanged logic, just indented)
        for keyword in review_keywords:
            if keyword in body:
                review_score += 1

    for review in reviews:
        body = review.get("body", "").lower()
        state = review.get("state", "")

        # Approved reviews count heavily
        if state == "APPROVED":
            review_score += 5

        # Look for review keywords
        for keyword in review_keywords:
            if keyword in body:
                review_score += 1

    # Step 11 is complete if we have:
    # - At least one approval OR
    # - Multiple review-related comments OR
    # - Comprehensive review detected
    if review_score >= 5 or comprehensive_review_found:
        step11_completed = True
        step11_evidence = (
            f"Found {len(reviews)} formal reviews and {len(comments)} comments. "
            f"Review score: {review_score}. "
            f"Comprehensive review detected: {comprehensive_review_found}"
        )
    else:
        step11_evidence = (
            f"Insufficient review evidence. "
            f"Found {len(reviews)} formal reviews and {len(comments)} comments. "
            f"Review score: {review_score} (need >= 5). "
            f"Comprehensive review detected: {comprehensive_review_found}"
        )

    # Step 12: Check for feedback implementation
    step12_completed = False
    step12_evidence = ""

    # Look for response indicators
    response_keywords = [
        "addressed",
        "fixed",
        "updated",
        "implemented",
        "resolved",
        "done",
        "completed",
    ]

    response_score = 0
    for comment in comments:
        body = comment.get("body", "").lower()
        for keyword in response_keywords:
            if keyword in body:
                response_score += 1

    # Step 12 is complete if we have feedback responses
    if response_score >= 3 or len(comments) > 5:
        step12_completed = True
        step12_evidence = (
            f"Found {response_score} response indicators across {len(comments)} comments"
        )
    else:
        step12_evidence = (
            f"Insufficient feedback implementation. Response score: {response_score} (need >= 3)"
        )

    # Overall compliance
    overall_compliant = step11_completed and step12_completed

    blocking_issues = []
    if not step11_completed:
        blocking_issues.append(
            "Step 11 incomplete: Need comprehensive code review with security, "
            "quality, and philosophy checks"
        )
    if not step12_completed:
        blocking_issues.append("Step 12 incomplete: Need to address and respond to review feedback")

    recommendations = []
    if not overall_compliant:
        recommendations.append("Complete workflow steps 11-12 before marking PR as ready")
    if len(reviews) == 0:
        recommendations.append("Add at least one formal code review")

    return {
        "step11_completed": step11_completed,
        "step11_evidence": step11_evidence,
        "step12_completed": step12_completed,
        "step12_evidence": step12_evidence,
        "overall_compliant": overall_compliant,
        "blocking_issues": blocking_issues,
        "recommendations": recommendations,
    }


def detect_priority_complexity(pr_data: dict[str, Any]) -> dict[str, str]:
    """Detect appropriate priority and complexity labels using heuristics.

    Args:
        pr_data: PR data dictionary

    Returns:
        Dictionary with priority and complexity labels
    """
    title = pr_data.get("title", "").lower()
    body = pr_data.get("body", "").lower()
    files = pr_data.get("files", [])

    # Calculate metrics
    num_files = len(files)
    total_additions = sum(f.get("additions", 0) for f in files)
    total_deletions = sum(f.get("deletions", 0) for f in files)
    total_changes = total_additions + total_deletions

    # Priority detection
    priority = "MEDIUM"
    priority_reasoning = "Default priority for normal changes"

    critical_keywords = ["security", "critical", "urgent", "hotfix", "vulnerability", "data loss"]
    high_keywords = ["bug", "fix", "error", "crash", "broken", "important"]
    low_keywords = ["docs", "documentation", "readme", "typo", "comment", "cleanup"]

    if any(kw in title or kw in body for kw in critical_keywords):
        priority = "CRITICAL"
        priority_reasoning = "Contains critical/security keywords"
    elif any(kw in title or kw in body for kw in high_keywords):
        priority = "HIGH"
        priority_reasoning = "Bug fix or important change"
    elif any(kw in title or kw in body for kw in low_keywords):
        priority = "LOW"
        priority_reasoning = "Documentation or minor cleanup"

    # Complexity detection
    complexity = "MODERATE"
    complexity_reasoning = "Default complexity for normal changes"

    if num_files == 1 and total_changes < 50:
        complexity = "SIMPLE"
        complexity_reasoning = f"Single file with {total_changes} lines changed"
    elif num_files <= 3 and total_changes < 200:
        complexity = "MODERATE"
        complexity_reasoning = f"{num_files} files with {total_changes} lines changed"
    elif num_files <= 10 and total_changes < 500:
        complexity = "COMPLEX"
        complexity_reasoning = f"{num_files} files with {total_changes} lines changed"
    else:
        complexity = "VERY_COMPLEX"
        complexity_reasoning = (
            f"{num_files} files with {total_changes} lines changed - system-wide changes"
        )

    # Check for architectural changes
    architectural_files = [
        f
        for f in files
        if any(
            pattern in f.get("path", "").lower()
            for pattern in ["architecture", "design", "workflow", "config", "settings"]
        )
    ]
    if architectural_files:
        complexity = "VERY_COMPLEX"
        complexity_reasoning += " (architectural changes detected)"

    return {
        "priority": priority,
        "priority_reasoning": priority_reasoning,
        "complexity": complexity,
        "complexity_reasoning": complexity_reasoning,
    }


def detect_unrelated_changes(pr_data: dict[str, Any]) -> dict[str, Any]:
    """Detect if PR contains unrelated changes using heuristics.

    Args:
        pr_data: PR data dictionary

    Returns:
        Dictionary with unrelated changes detection results
    """
    title = pr_data.get("title", "").lower()
    files = pr_data.get("files", [])

    # Categorize files by type
    file_categories = {
        "docs": [],
        "tests": [],
        "config": [],
        "core": [],
        "workflows": [],
        "other": [],
    }

    for file_data in files:
        path = file_data.get("path", "").lower()

        if "readme" in path or "doc" in path or path.endswith(".md"):
            file_categories["docs"].append(path)
        elif "test" in path or path.startswith("tests/"):
            file_categories["tests"].append(path)
        elif (
            "config" in path
            or path.endswith(".json")
            or path.endswith(".yaml")
            or path.endswith(".yml")
            or path.endswith(".toml")
        ):
            file_categories["config"].append(path)
        elif ".github/workflows" in path:
            file_categories["workflows"].append(path)
        elif path.endswith((".py", ".js", ".ts", ".go", ".java", ".cpp", ".c")):
            file_categories["core"].append(path)
        else:
            file_categories["other"].append(path)

    # Count non-empty categories
    non_empty_categories = [cat for cat, paths in file_categories.items() if paths]

    # Determine primary purpose from title
    primary_purpose = "General code changes"
    if "fix" in title or "bug" in title:
        primary_purpose = "Bug fix"
    elif "feat" in title or "add" in title:
        primary_purpose = "New feature"
    elif "refactor" in title:
        primary_purpose = "Code refactoring"
    elif "doc" in title:
        primary_purpose = "Documentation update"
    elif "test" in title:
        primary_purpose = "Test updates"

    # Detect unrelated changes
    has_unrelated_changes = False
    unrelated_files = []
    unrelated_purposes = []
    recommendation = "Changes appear focused"

    # If we have more than 2 categories, likely unrelated
    if len(non_empty_categories) >= 3:
        has_unrelated_changes = True

        # Identify what seems unrelated
        if file_categories["docs"] and primary_purpose != "Documentation update":
            unrelated_purposes.append("Documentation changes")
            unrelated_files.extend(file_categories["docs"])

        if file_categories["workflows"] and "workflow" not in title and "ci" not in title:
            unrelated_purposes.append("Workflow/CI changes")
            unrelated_files.extend(file_categories["workflows"])

        if file_categories["config"] and "config" not in title:
            unrelated_purposes.append("Configuration changes")
            unrelated_files.extend(file_categories["config"])

        recommendation = "Consider splitting this PR into separate focused PRs for each concern"

    # Special case: Large refactoring with feature work
    if "refactor" in title and ("feat" in title or "add" in title) and len(files) > 5:
        has_unrelated_changes = True
        unrelated_purposes.append("Mixed refactoring and feature work")
        recommendation = "Separate refactoring from new features into different PRs"

    return {
        "has_unrelated_changes": has_unrelated_changes,
        "unrelated_files": unrelated_files[:10],  # Limit to 10 files
        "primary_purpose": primary_purpose,
        "unrelated_purposes": unrelated_purposes,
        "recommendation": recommendation,
        "file_categories": {k: len(v) for k, v in file_categories.items() if v},  # Statistics
    }
