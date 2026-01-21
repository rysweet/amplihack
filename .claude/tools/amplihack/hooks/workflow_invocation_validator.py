#!/usr/bin/env python3
"""
Workflow Invocation Validator

Validates that ultrathink-orchestrator skill properly invokes workflows using
the Skill tool or Read tool as required. Detects violations where workflows are
triggered but not properly invoked.

Philosophy:
- Ruthlessly Simple: Single-purpose validation module
- Zero-BS: No stubs, every function works
- Fail-Open: Returns valid result on errors, never blocks falsely
- Clear Contract: ValidationResult with boolean + reason

Issue: #2040 - Enforce workflow invocation via Skill/Read tools
"""

import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class ValidationResult:
    """Result of workflow invocation validation."""

    valid: bool
    reason: str
    violation_type: Literal[
        "none", "missing_skill_invocation", "missing_read_fallback", "no_workflow_loaded"
    ] = "none"
    evidence: str = ""


def validate_workflow_invocation(
    transcript: str, session_type: str = "DEVELOPMENT"
) -> ValidationResult:
    """Validate that workflow was properly invoked when ultrathink triggered.

    Checks for:
    1. Ultrathink trigger detected (skill auto-activation or explicit command)
    2. Proper workflow invocation via Skill tool
    3. Fallback to Read tool for workflow markdown if skill fails
    4. Workflow content loaded and followed

    Args:
        transcript: Full session transcript
        session_type: Session type (DEVELOPMENT, INVESTIGATION, etc.)

    Returns:
        ValidationResult with validation status and detailed reason

    Examples:
        >>> result = validate_workflow_invocation(transcript, "DEVELOPMENT")
        >>> if not result.valid:
        ...     print(f"Violation: {result.reason}")
    """
    # Only validate DEVELOPMENT and INVESTIGATION sessions
    if session_type not in ("DEVELOPMENT", "INVESTIGATION"):
        return ValidationResult(
            valid=True, reason=f"Validation not required for {session_type} sessions"
        )

    # Step 1: Check if ultrathink was triggered
    ultrathink_triggered = _detect_ultrathink_trigger(transcript)

    if not ultrathink_triggered:
        return ValidationResult(
            valid=True, reason="Ultrathink not triggered - validation not applicable"
        )

    # Step 2: Check for Skill tool invocation
    skill_invoked = _detect_skill_invocation(transcript)

    if skill_invoked:
        return ValidationResult(
            valid=True,
            reason="Workflow properly invoked via Skill tool",
            evidence=skill_invoked,
        )

    # Step 3: Check for Read tool fallback (acceptable alternative)
    read_fallback = _detect_read_workflow_fallback(transcript)

    if read_fallback:
        return ValidationResult(
            valid=True,
            reason="Workflow loaded via Read tool fallback (acceptable)",
            evidence=read_fallback,
        )

    # Step 4: Violation detected - ultrathink triggered but no workflow invocation
    return ValidationResult(
        valid=False,
        reason="Ultrathink triggered but workflow not invoked via Skill or Read tool",
        violation_type="no_workflow_loaded",
        evidence="Ultrathink skill auto-activated but no workflow loading detected",
    )


def _detect_ultrathink_trigger(transcript: str) -> bool:
    """Detect if ultrathink-orchestrator skill was triggered.

    Patterns:
    - Explicit: /ultrathink command
    - Auto-activation: Skill auto-activation based on keywords
    - Skill invocation: Skill(skill="ultrathink-orchestrator")

    Args:
        transcript: Session transcript

    Returns:
        True if ultrathink was triggered
    """
    patterns = [
        r"/ultrathink\b",  # Explicit command
        r"Skill\(.*ultrathink-orchestrator.*\)",  # Skill invocation
        r"ultrathink-orchestrator.*auto.*activat",  # Auto-activation message
        r"auto.*activat.*ultrathink-orchestrator",  # Auto-activation (reversed)
        r"<command-name>/ultrathink</command-name>",  # Command tag
    ]

    for pattern in patterns:
        if re.search(pattern, transcript, re.IGNORECASE):
            return True

    return False


def _detect_skill_invocation(transcript: str) -> str:
    """Detect Skill tool invocation for workflow skills.

    Looks for:
    - Skill(skill="default-workflow")
    - Skill(skill="investigation-workflow")
    - Skill tool calls with workflow skills

    Args:
        transcript: Session transcript

    Returns:
        Evidence string if found, empty string otherwise
    """
    patterns = [
        (r'Skill\(skill="default-workflow"\)', "default-workflow skill invoked"),
        (
            r'Skill\(skill="investigation-workflow"\)',
            "investigation-workflow skill invoked",
        ),
        (
            r"<invoke name=\"Skill\">.*default-workflow",
            "Skill tool invoked for default-workflow",
        ),
        (
            r"<invoke name=\"Skill\">.*investigation-workflow",
            "Skill tool invoked for investigation-workflow",
        ),
    ]

    for pattern, evidence in patterns:
        if re.search(pattern, transcript, re.IGNORECASE | re.DOTALL):
            return evidence

    return ""


def _detect_read_workflow_fallback(transcript: str) -> str:
    """Detect Read tool used to load workflow markdown files.

    Acceptable fallback when skill invocation fails. Looks for:
    - Read(.claude/workflow/DEFAULT_WORKFLOW.md)
    - Read(.claude/workflow/INVESTIGATION_WORKFLOW.md)

    Args:
        transcript: Session transcript

    Returns:
        Evidence string if found, empty string otherwise
    """
    patterns = [
        (
            r"Read.*\.claude/workflow/DEFAULT_WORKFLOW\.md",
            "DEFAULT_WORKFLOW.md loaded via Read tool",
        ),
        (
            r"Read.*\.claude/workflow/INVESTIGATION_WORKFLOW\.md",
            "INVESTIGATION_WORKFLOW.md loaded via Read tool",
        ),
        (
            r"<invoke name=\"Read\">.*DEFAULT_WORKFLOW",
            "Read tool invoked for DEFAULT_WORKFLOW",
        ),
        (
            r"<invoke name=\"Read\">.*INVESTIGATION_WORKFLOW",
            "Read tool invoked for INVESTIGATION_WORKFLOW",
        ),
    ]

    for pattern, evidence in patterns:
        if re.search(pattern, transcript, re.IGNORECASE | re.DOTALL):
            return evidence

    return ""


# Public API
__all__ = ["ValidationResult", "validate_workflow_invocation"]
