"""Success Criteria Evaluator Module.

This module evaluates task completion against success criteria using collected evidence
and execution logs. Provides scoring (0-100) and identifies gaps.

Evaluation Strategy:
- Parse success criteria into individual requirements
- Match requirements against evidence
- Award bonus points for tests, documentation
- Identify missing requirements
- Generate actionable feedback

Philosophy:
- Evidence-based evaluation (not subjective)
- Clear scoring rationale
- Actionable feedback on gaps
- Bonus for quality indicators (tests, docs)
"""

import re
from dataclasses import dataclass
from typing import Any

from .evidence_collector import EvidenceItem


@dataclass
class EvaluationResult:
    """Result of success criteria evaluation.

    Attributes:
        score: Success score from 0-100
        notes: Detailed evaluation notes explaining score
        requirements_met: List of requirements that were satisfied
        requirements_missing: List of requirements not satisfied
        bonus_points: Points awarded for quality indicators
    """

    score: int
    notes: str
    requirements_met: list[str] = None
    requirements_missing: list[str] = None
    bonus_points: int = 0

    def __post_init__(self):
        """Initialize default lists."""
        if self.requirements_met is None:
            self.requirements_met = []
        if self.requirements_missing is None:
            self.requirements_missing = []

        # Clamp score to valid range
        self.score = max(0, min(100, self.score))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "score": self.score,
            "notes": self.notes,
            "requirements_met": self.requirements_met,
            "requirements_missing": self.requirements_missing,
            "bonus_points": self.bonus_points,
        }


def parse_success_criteria(criteria: str) -> list[str | dict]:
    """Parse success criteria into individual requirements.

    Args:
        criteria: Success criteria string (may be bulleted list, numbered list, or prose)

    Returns:
        List of requirement strings or dictionaries
    """
    if not criteria or not criteria.strip():
        return []

    requirements = []
    lines = criteria.strip().split("\n")

    for line in lines:
        line = line.strip()

        # Skip empty lines and non-requirement lines
        if not line:
            continue

        # Match bullet points (-, *, •) or numbered lists (1., 2.)
        bullet_match = re.match(r"^[-*•]\s+(.+)$", line)
        numbered_match = re.match(r"^\d+\.\s+(.+)$", line)

        if bullet_match:
            requirement = bullet_match.group(1).strip()
            requirements.append(requirement)
        elif numbered_match:
            requirement = numbered_match.group(1).strip()
            requirements.append(requirement)
        elif line and not line.endswith(":") and len(line.split()) > 3:
            # Looks like a requirement (not a header)
            requirements.append(line)

    return requirements


class SuccessCriteriaEvaluator:
    """Evaluates task success against criteria using evidence."""

    def evaluate(
        self,
        criteria: str,
        evidence: list[EvidenceItem],
        execution_log: str,
    ) -> EvaluationResult:
        """Evaluate success based on criteria and evidence.

        Args:
            criteria: Success criteria string
            evidence: List of collected evidence items
            execution_log: Execution log content

        Returns:
            EvaluationResult with score and notes
        """
        # Parse criteria into requirements
        requirements = parse_success_criteria(criteria)

        if not requirements:
            # No specific criteria - do basic evaluation
            return self._evaluate_basic(evidence, execution_log)

        # Evaluate each requirement
        requirements_met = []
        requirements_missing = []

        for requirement in requirements:
            if self._is_requirement_met(requirement, evidence, execution_log):
                requirements_met.append(requirement)
            else:
                requirements_missing.append(requirement)

        # Calculate base score
        if len(requirements) > 0:
            base_score = int((len(requirements_met) / len(requirements)) * 100)
        else:
            base_score = 50

        # Award bonus points
        bonus_points = 0

        # Bonus for passing tests
        if self._has_passing_tests(evidence, execution_log):
            bonus_points += 10

        # Bonus for documentation
        if self._has_documentation(evidence):
            bonus_points += 5

        # Calculate final score
        final_score = min(100, base_score + bonus_points)

        # Generate notes
        notes = self._generate_notes(
            requirements_met,
            requirements_missing,
            evidence,
            execution_log,
            bonus_points,
        )

        return EvaluationResult(
            score=final_score,
            notes=notes,
            requirements_met=requirements_met,
            requirements_missing=requirements_missing,
            bonus_points=bonus_points,
        )

    def _evaluate_basic(
        self,
        evidence: list[EvidenceItem],
        execution_log: str,
    ) -> EvaluationResult:
        """Perform basic evaluation when no specific criteria provided.

        Args:
            evidence: Evidence items
            execution_log: Execution log

        Returns:
            EvaluationResult
        """
        score = 50  # Base score

        # Check for code files
        code_files = [e for e in evidence if e.type == "code_file"]
        if code_files:
            score += 20

        # Check for tests
        test_files = [e for e in evidence if e.type == "test_file"]
        if test_files:
            score += 15

        # Check for documentation
        docs = [e for e in evidence if e.type == "documentation"]
        if docs:
            score += 10

        # Check execution log for success
        if self._has_passing_tests(evidence, execution_log):
            score += 5

        notes = f"Basic evaluation: Found {len(code_files)} code files, {len(test_files)} test files, {len(docs)} documentation files."

        return EvaluationResult(
            score=min(100, score),
            notes=notes,
        )

    def _is_requirement_met(
        self,
        requirement: str,
        evidence: list[EvidenceItem],
        execution_log: str,
    ) -> bool:
        """Check if a requirement is met by evidence.

        Args:
            requirement: Requirement string
            evidence: Evidence items
            execution_log: Execution log

        Returns:
            True if requirement appears to be met
        """
        requirement_lower = requirement.lower()

        # Extract key terms from requirement
        key_terms = self._extract_key_terms(requirement_lower)

        # Search evidence for key terms
        evidence_text = " ".join([f"{e.path} {e.excerpt}" for e in evidence]).lower()

        log_text = execution_log.lower()

        # Check if key terms appear in evidence or log
        matches = 0
        for term in key_terms:
            if term in evidence_text or term in log_text:
                matches += 1

        # Requirement is met if most key terms are found
        if len(key_terms) == 0:
            return False

        return matches / len(key_terms) >= 0.5

    def _extract_key_terms(self, text: str) -> list[str]:
        """Extract key terms from requirement text.

        Args:
            text: Requirement text

        Returns:
            List of key terms
        """
        # Remove common words
        common_words = {
            "has",
            "have",
            "with",
            "the",
            "a",
            "an",
            "and",
            "or",
            "for",
            "to",
            "of",
            "in",
            "on",
            "at",
            "by",
            "is",
            "are",
            "should",
            "must",
            "will",
            "can",
            "be",
            "been",
            "being",
        }

        words = re.findall(r"\b\w+\b", text)
        key_terms = [word for word in words if word not in common_words and len(word) > 2]

        return key_terms

    def _has_passing_tests(
        self,
        evidence: list[EvidenceItem],
        execution_log: str,
    ) -> bool:
        """Check if tests are passing.

        Args:
            evidence: Evidence items
            execution_log: Execution log

        Returns:
            True if tests appear to pass
        """
        log_lower = execution_log.lower()

        # Check for test pass patterns
        pass_patterns = [
            "all tests passed",
            "pass",
            "ok",
            "100% passed",
            "tests successful",
            "✓",
            "test passed",
        ]

        for pattern in pass_patterns:
            if pattern in log_lower:
                # Make sure it's not a failure message
                if "fail" not in log_lower[: log_lower.find(pattern) + 50]:
                    return True

        # Check test result files
        test_results = [e for e in evidence if e.type == "test_results"]
        for result in test_results:
            if "passed" in result.content.lower() and "failed: 0" in result.content.lower():
                return True

        return False

    def _has_documentation(self, evidence: list[EvidenceItem]) -> bool:
        """Check if documentation exists.

        Args:
            evidence: Evidence items

        Returns:
            True if documentation found
        """
        docs = [e for e in evidence if e.type in ["documentation", "architecture_doc", "api_spec"]]

        # Should have at least one substantial doc (> 100 chars)
        return any(e.size_bytes > 100 for e in docs)

    def _generate_notes(
        self,
        requirements_met: list[str],
        requirements_missing: list[str],
        evidence: list[EvidenceItem],
        execution_log: str,
        bonus_points: int,
    ) -> str:
        """Generate detailed evaluation notes.

        Args:
            requirements_met: List of satisfied requirements
            requirements_missing: List of missing requirements
            evidence: Evidence items
            execution_log: Execution log
            bonus_points: Bonus points awarded

        Returns:
            Formatted notes string
        """
        notes_parts = []

        # Summary
        total_requirements = len(requirements_met) + len(requirements_missing)
        if total_requirements > 0:
            notes_parts.append(
                f"Requirements satisfied: {len(requirements_met)}/{total_requirements}"
            )

        # Met requirements
        if requirements_met:
            notes_parts.append("\n✓ Requirements met:")
            for req in requirements_met[:5]:  # Show first 5
                notes_parts.append(f"  - {req}")
            if len(requirements_met) > 5:
                notes_parts.append(f"  ... and {len(requirements_met) - 5} more")

        # Missing requirements
        if requirements_missing:
            notes_parts.append("\n✗ Requirements not found or incomplete:")
            for req in requirements_missing[:5]:
                notes_parts.append(f"  - {req}")
            if len(requirements_missing) > 5:
                notes_parts.append(f"  ... and {len(requirements_missing) - 5} more")

        # Bonus points
        if bonus_points > 0:
            notes_parts.append(f"\n✓ Bonus points: +{bonus_points}")
            if self._has_passing_tests(evidence, execution_log):
                notes_parts.append("  - Passing tests detected")
            if self._has_documentation(evidence):
                notes_parts.append("  - Documentation provided")

        # Evidence summary
        evidence_by_type = {}
        for item in evidence:
            evidence_by_type[item.type] = evidence_by_type.get(item.type, 0) + 1

        if evidence_by_type:
            notes_parts.append("\nEvidence collected:")
            for etype, count in sorted(evidence_by_type.items()):
                notes_parts.append(f"  - {etype}: {count}")

        return "\n".join(notes_parts)
