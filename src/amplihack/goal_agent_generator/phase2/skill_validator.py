"""
Skill Validator - Validates generated skills meet quality standards.

Checks markdown structure, verifies no placeholder text, and assigns quality scores.
"""

import re
from typing import List

from ..models import ValidationResult


class SkillValidator:
    """Validates that skills meet quality standards."""

    # Placeholder patterns that should not appear in production skills
    PLACEHOLDER_PATTERNS = [
        r"\bTODO\b",
        r"\bXXX\b",
        r"\bFIXME\b",
        r"\bHACK\b",
        r"\[INSERT\s+\w+\]",
        r"\[YOUR\s+\w+\]",
        r"\[PLACEHOLDER\]",
        r"\{\{.*?\}\}",  # Template variables
        r"<replace.*?>",
        r"fill\s+in",
        r"replace\s+this",
    ]

    # Required markdown sections for amplihack skills
    REQUIRED_SECTIONS = [
        "description",  # Front matter or description section
        "capabilities",  # Core capabilities section
        "usage",  # Usage instructions
    ]

    # Minimum content lengths
    MIN_SKILL_LENGTH = 200  # Minimum total characters
    MIN_SECTION_LENGTH = 50  # Minimum characters per section

    def validate_skill(self, skill_content: str, skill_name: str = "") -> ValidationResult:
        """
        Validate a skill definition.

        Args:
            skill_content: The full markdown content of the skill
            skill_name: Optional skill name for error messages

        Returns:
            ValidationResult with validation status and details
        """
        issues = []
        warnings = []
        quality_score = 100.0  # Start at 100, deduct points for issues

        # Check minimum length
        if len(skill_content) < self.MIN_SKILL_LENGTH:
            issues.append(
                f"Skill content too short: {len(skill_content)} chars "
                f"(minimum {self.MIN_SKILL_LENGTH})"
            )
            quality_score -= 20

        # Check for placeholder text
        placeholder_issues = self._check_placeholders(skill_content)
        if placeholder_issues:
            issues.extend(placeholder_issues)
            quality_score -= len(placeholder_issues) * 15

        # Check markdown structure
        structure_issues, structure_warnings = self._check_markdown_structure(skill_content)
        issues.extend(structure_issues)
        warnings.extend(structure_warnings)
        quality_score -= len(structure_issues) * 10
        quality_score -= len(structure_warnings) * 5

        # Check for required sections
        section_issues = self._check_required_sections(skill_content)
        if section_issues:
            issues.extend(section_issues)
            quality_score -= len(section_issues) * 15

        # Check content quality
        content_warnings = self._check_content_quality(skill_content)
        warnings.extend(content_warnings)
        quality_score -= len(content_warnings) * 3

        # Normalize quality score to 0-1 range
        quality_score = max(0.0, min(100.0, quality_score)) / 100.0

        # Validation passes if no critical issues
        passed = len(issues) == 0

        return ValidationResult(
            passed=passed,
            issues=issues,
            warnings=warnings,
            quality_score=quality_score,
        )

    def _check_placeholders(self, content: str) -> List[str]:
        """
        Check for placeholder text that shouldn't be in production.

        Args:
            content: Skill content to check

        Returns:
            List of issues found
        """
        issues = []

        for pattern in self.PLACEHOLDER_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                issues.append(
                    f"Found placeholder text: '{match.group()}' at position {match.start()}"
                )

        return issues

    def _check_markdown_structure(self, content: str) -> tuple[List[str], List[str]]:
        """
        Check markdown structure and formatting.

        Args:
            content: Skill content to check

        Returns:
            Tuple of (issues, warnings)
        """
        issues = []
        warnings = []

        # Check for at least one heading
        if not re.search(r"^#+\s+\w+", content, re.MULTILINE):
            issues.append("No markdown headings found")

        # Check for front matter (YAML between ---)
        has_frontmatter = content.strip().startswith("---")
        if not has_frontmatter:
            warnings.append("No YAML front matter found (recommended for amplihack skills)")

        # Check for excessive blank lines
        if re.search(r"\n{5,}", content):
            warnings.append("Excessive blank lines found (4+ consecutive)")

        # Check for proper heading hierarchy
        headings = re.findall(r"^(#+)\s+", content, re.MULTILINE)
        if headings:
            levels = [len(h) for h in headings]
            # First heading should be h1 (#)
            if levels[0] != 1 and not has_frontmatter:
                warnings.append("First heading should be level 1 (#)")

        # Check for code blocks (should have some examples)
        if "```" not in content and "`" not in content:
            warnings.append("No code blocks or inline code found (consider adding examples)")

        return issues, warnings

    def _check_required_sections(self, content: str) -> List[str]:
        """
        Check for required sections.

        Args:
            content: Skill content to check

        Returns:
            List of issues for missing sections
        """
        issues = []
        content_lower = content.lower()

        for section in self.REQUIRED_SECTIONS:
            # Look for section as heading or in front matter
            section_pattern = rf"(?:^#+\s+.*{section}|{section}:)"
            if not re.search(section_pattern, content_lower, re.MULTILINE):
                issues.append(f"Missing required section: '{section}'")

        return issues

    def _check_content_quality(self, content: str) -> List[str]:
        """
        Check content quality indicators.

        Args:
            content: Skill content to check

        Returns:
            List of quality warnings
        """
        warnings = []

        # Check for minimum word count in paragraphs
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        short_paragraphs = [p for p in paragraphs if len(p) < self.MIN_SECTION_LENGTH]

        if len(short_paragraphs) > len(paragraphs) / 2:
            warnings.append("Many short paragraphs found (consider adding more detail)")

        # Check for lists (good for clarity)
        if not re.search(r"^[\-\*]\s+", content, re.MULTILINE):
            warnings.append("No bullet lists found (consider using lists for clarity)")

        # Check for numbered lists (good for procedures)
        if not re.search(r"^\d+\.\s+", content, re.MULTILINE):
            warnings.append("No numbered lists found (consider for step-by-step procedures)")

        # Check for emphasis (bold/italic)
        if not re.search(r"[\*_]{1,2}\w+[\*_]{1,2}", content):
            warnings.append("No text emphasis found (consider highlighting key concepts)")

        # Check for very long lines (readability)
        lines = content.split("\n")
        long_lines = [l for l in lines if len(l) > 120 and not l.strip().startswith("#")]
        if len(long_lines) > 5:
            warnings.append(f"Found {len(long_lines)} very long lines (>120 chars)")

        return warnings

    def validate_batch(self, skills: List[tuple[str, str]]) -> List[ValidationResult]:
        """
        Validate multiple skills at once.

        Args:
            skills: List of (skill_name, skill_content) tuples

        Returns:
            List of ValidationResult objects
        """
        results = []

        for skill_name, skill_content in skills:
            result = self.validate_skill(skill_content, skill_name)
            results.append(result)

        return results

    def get_validation_summary(self, results: List[ValidationResult]) -> dict:
        """
        Get summary statistics for validation results.

        Args:
            results: List of validation results

        Returns:
            Dictionary with summary statistics
        """
        if not results:
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "average_quality": 0.0,
                "total_issues": 0,
                "total_warnings": 0,
            }

        passed = sum(1 for r in results if r.passed)
        total_issues = sum(len(r.issues) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)
        avg_quality = sum(r.quality_score for r in results) / len(results)

        return {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": passed / len(results),
            "average_quality": avg_quality,
            "total_issues": total_issues,
            "total_warnings": total_warnings,
        }
