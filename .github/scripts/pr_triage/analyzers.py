"""PR analysis functions using Claude."""

import json
import re
from typing import Any

from .claude_runner import run_claude
from .formatters import format_comments, format_files, format_reviews


def validate_workflow_compliance(pr_data: dict[str, Any]) -> dict[str, Any]:
    """Check if PR completed Steps 11-12 of workflow.

    Args:
        pr_data: PR data dictionary

    Returns:
        Validation result with compliance status and details
    """
    prompt = f"""Analyze this PR for workflow compliance with DEFAULT_WORKFLOW.md.

**CRITICAL REQUIREMENTS:**

Step 11: Review the PR
- Must have comprehensive code review comment posted
- Security review must be performed
- Code quality and standards checked
- Philosophy compliance verified
- Test coverage verified
- No TODOs, stubs, or swallowed exceptions

Step 12: Implement Review Feedback
- All review comments must be addressed
- Each comment should have a response
- Changes pushed to address feedback
- Tests still passing

**PR Data:**
Title: {pr_data["title"]}
Author: {pr_data["author"]["login"]}
Branch: {pr_data["headRefName"]} -> {pr_data["baseRefName"]}

Body:
{pr_data["body"]}

Comments ({len(pr_data["comments"])}):
{format_comments(pr_data["comments"])}

Reviews ({len(pr_data["reviews"])}):
{format_reviews(pr_data["reviews"])}

**RESPOND IN JSON FORMAT:**
{{
    "step11_completed": true/false,
    "step11_evidence": "description of review evidence or missing items",
    "step12_completed": true/false,
    "step12_evidence": "description of feedback implementation or missing items",
    "overall_compliant": true/false,
    "blocking_issues": ["list", "of", "issues"],
    "recommendations": ["list", "of", "recommendations"]
}}
"""

    result = run_claude(prompt, timeout=300)

    if result["exit_code"] != 0:
        return {
            "overall_compliant": False,
            "error": f"Validation failed: {result['stderr']}",
        }

    return extract_json(result["output"])


def detect_priority_complexity(pr_data: dict[str, Any]) -> dict[str, str]:
    """Detect appropriate priority and complexity labels.

    Args:
        pr_data: PR data dictionary

    Returns:
        Dictionary with priority and complexity labels
    """
    prompt = f"""Analyze this PR to determine priority and complexity.

**PR Data:**
Title: {pr_data["title"]}
Body:
{pr_data["body"]}

Files Changed: {len(pr_data["files"])}
File List:
{format_files(pr_data["files"])}

Diff Preview (first 5000 chars):
{pr_data["diff"][:5000]}

**Priority Levels:**
- CRITICAL: Security issues, data loss, system down
- HIGH: Major bugs, important features, significant impact
- MEDIUM: Normal features, moderate bugs, improvements
- LOW: Minor fixes, documentation, cleanup

**Complexity Levels:**
- SIMPLE: Single file, < 50 lines, straightforward logic
- MODERATE: Few files, < 200 lines, some complexity
- COMPLEX: Multiple files, > 200 lines, intricate logic
- VERY_COMPLEX: System-wide changes, architectural shifts

**RESPOND IN JSON FORMAT:**
{{
    "priority": "CRITICAL/HIGH/MEDIUM/LOW",
    "priority_reasoning": "explanation",
    "complexity": "SIMPLE/MODERATE/COMPLEX/VERY_COMPLEX",
    "complexity_reasoning": "explanation"
}}
"""

    result = run_claude(prompt, timeout=300)

    if result["exit_code"] != 0:
        return {"priority": "MEDIUM", "complexity": "MODERATE", "error": result["stderr"]}

    return extract_json(result["output"])


def detect_unrelated_changes(pr_data: dict[str, Any]) -> dict[str, Any]:
    """Detect if PR contains unrelated changes.

    Args:
        pr_data: PR data dictionary

    Returns:
        Dictionary with unrelated changes detection results
    """
    prompt = f"""Analyze this PR to detect unrelated changes.

A PR should have a single, focused purpose. Unrelated changes are:
- Changes to files outside the scope of the PR's stated purpose
- Mixed refactoring with new features
- Unrelated bug fixes bundled together
- Documentation updates unrelated to the code changes

**PR Data:**
Title: {pr_data["title"]}
Body:
{pr_data["body"]}

Files Changed:
{format_files(pr_data["files"])}

Diff (first 10000 chars):
{pr_data["diff"][:10000]}

**RESPOND IN JSON FORMAT:**
{{
    "has_unrelated_changes": true/false,
    "unrelated_files": ["list", "of", "file", "paths"],
    "primary_purpose": "description of main PR purpose",
    "unrelated_purposes": ["list", "of", "unrelated", "changes"],
    "recommendation": "should these be split into separate PRs?"
}}
"""

    result = run_claude(prompt, timeout=300)

    if result["exit_code"] != 0:
        return {"has_unrelated_changes": False, "error": result["stderr"]}

    return extract_json(result["output"])


def extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from Claude output.

    Args:
        text: Full text output from Claude

    Returns:
        Parsed JSON dictionary
    """
    # Try to find JSON in code blocks
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))

    # Try to find raw JSON
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0))

    # Fallback: empty dict
    return {}
