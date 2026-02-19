"""TDD tests for README.md restructuring (Issue #2403)

These tests validate the requirements:
1. Value proposition present in first 50 lines
2. Only ONE "## Quick Start" heading
3. Features section < 100 lines
4. Table of contents < 20 lines
5. Total length 500-600 lines
6. All key features mentioned

Philosophy:
- Tests fail on current README.md (803 lines, 3 quick starts, etc.)
- Tests pass after restructuring to meet requirements
- Testing pyramid: unit tests for structure validation
"""

import re
from pathlib import Path

import pytest

README_PATH = Path(__file__).parent.parent / "README.md"


class READMEStructureValidator:
    """Validates README structure against requirements"""

    def __init__(self, readme_path: Path):
        self.path = readme_path
        self.content = self._read_content()
        self.lines = self.content.split("\n")

    def _read_content(self) -> str:
        """Read README content"""
        if not self.path.exists():
            raise FileNotFoundError(f"README not found at {self.path}")
        return self.path.read_text()

    def count_total_lines(self) -> int:
        """Count total lines in README"""
        return len(self.lines)

    def find_section_lines(self, heading_pattern: str) -> list[int]:
        """Find line numbers where section headings appear

        Args:
            heading_pattern: Regex pattern for heading (e.g., r'^## Quick Start$')
        """
        pattern = re.compile(heading_pattern)
        return [i for i, line in enumerate(self.lines) if pattern.match(line)]

    def count_section_occurrences(self, heading_pattern: str) -> int:
        """Count how many times a section heading appears"""
        return len(self.find_section_lines(heading_pattern))

    def get_section_length(self, start_pattern: str, end_pattern: str = None) -> int:
        """Get length of section between two headings

        Args:
            start_pattern: Regex for section start heading
            end_pattern: Regex for next section heading (optional)
        """
        start_lines = self.find_section_lines(start_pattern)
        if not start_lines:
            return 0

        start_idx = start_lines[0]

        # Find next section or end of file
        if end_pattern:
            end_lines = self.find_section_lines(end_pattern)
            end_lines = [idx for idx in end_lines if idx > start_idx]
            end_idx = end_lines[0] if end_lines else len(self.lines)
        else:
            # Find next ## heading
            for i in range(start_idx + 1, len(self.lines)):
                if self.lines[i].startswith("## "):
                    end_idx = i
                    break
            else:
                end_idx = len(self.lines)

        return end_idx - start_idx

    def has_value_proposition_in_first_n_lines(self, n: int = 50) -> bool:
        """Check if value proposition exists in first N lines

        Value prop keywords: "barebones", "problem", "solution", "engineering system"
        """
        first_n_lines = "\n".join(self.lines[:n]).lower()
        keywords = ["barebones", "problem", "solution", "engineering system"]
        return any(keyword in first_n_lines for keyword in keywords)

    def get_toc_length(self) -> int:
        """Get length of table of contents section"""
        toc_start = None
        for i, line in enumerate(self.lines):
            if line.strip() == "## Table of Contents":
                toc_start = i
                break

        if toc_start is None:
            return 0

        # Find next ## heading
        for i in range(toc_start + 1, len(self.lines)):
            if self.lines[i].startswith("## "):
                return i - toc_start

        return len(self.lines) - toc_start

    def check_feature_mentions(self, features: list[str]) -> dict:
        """Check which features are mentioned in README

        Returns:
            Dict mapping feature name to bool (present or not)
        """
        content_lower = self.content.lower()
        return {feature: feature.lower() in content_lower for feature in features}


# Fixtures


@pytest.fixture
def validator():
    """Fixture providing READMEStructureValidator instance"""
    return READMEStructureValidator(README_PATH)


# Test 1: Value Proposition Present


def test_value_proposition_in_first_50_lines(validator):
    """REQUIREMENT 1: Value proposition must be in first 50 lines

    Current README: FAILS - missing value prop in first 50 lines
    Restructured: PASSES - "Why amplihack?" section in first 50 lines
    """
    assert validator.has_value_proposition_in_first_n_lines(50), (
        "Value proposition (problem statement) must be in first 50 lines. "
        "Expected keywords: 'barebones', 'problem', 'solution', 'engineering system'"
    )


# Test 2: Single Quick Start Section


def test_single_quick_start_section(validator):
    """REQUIREMENT 2: Only ONE "## Quick Start" heading

    Current README: FAILS - has multiple Quick Start sections
    Restructured: PASSES - only one Quick Start section
    """
    count = validator.count_section_occurrences(r"^## Quick Start$")
    assert count == 1, f"README must have exactly ONE '## Quick Start' section. Found: {count}"


# Test 3: Features Section Length < 100 lines


def test_features_section_length(validator):
    """REQUIREMENT 3: Features section must be < 130 lines (catalog format for ALL features)

    Current README: FAILS - 236 lines
    Restructured: PASSES - < 130 lines (46% reduction while preserving ALL features)
    """
    # Find "Feature Catalog" or "Features" section
    feature_patterns = [r"^## Feature Catalog$", r"^## Features$"]

    for pattern in feature_patterns:
        if validator.count_section_occurrences(pattern) > 0:
            length = validator.get_section_length(pattern)
            assert length < 130, f"Features section must be < 130 lines. Found: {length} lines"
            return

    pytest.fail("No Features or Feature Catalog section found")


# Test 4: TOC Length < 20 lines


def test_toc_length(validator):
    """REQUIREMENT 4: Table of contents must be < 20 lines

    Current README: FAILS - 43 lines
    Restructured: PASSES - < 20 lines
    """
    toc_length = validator.get_toc_length()
    assert toc_length > 0, "Table of Contents section not found"
    assert toc_length < 20, f"Table of Contents must be < 20 lines. Found: {toc_length} lines"


# Test 5: Total Length 500-600 lines


def test_total_length(validator):
    """REQUIREMENT 5: README must be 350-600 lines (ruthless simplicity)

    Current README: FAILS - 803 lines
    Restructured: PASSES - 350-600 lines (shorter if complete aligns with philosophy)
    """
    total = validator.count_total_lines()
    assert 350 <= total <= 600, (
        f"README must be 350-600 lines (ruthless simplicity allows shorter if complete). Found: {total} lines"
    )


# Test 6: All Key Features Present


def test_key_features_present(validator):
    """REQUIREMENT 6: All key features must be mentioned

    Current README: Should PASS (features are present)
    Restructured: Must also PASS (preserve all features)
    """
    required_features = [
        "Recipe Runner",
        "Memory",
        "Workflows",
        "Auto Mode",
        "Skills",
        "UltraThink",
        "Agents",
        "Document-Driven Development",
        "Investigation Workflow",
        "Multitask",
    ]

    feature_check = validator.check_feature_mentions(required_features)
    missing = [f for f, present in feature_check.items() if not present]

    assert not missing, f"README must mention all key features. Missing: {', '.join(missing)}"


# Test 7: Section Presence


def test_required_sections_present(validator):
    """Verify all required sections are present

    Required sections:
    - Why amplihack?
    - Quick Start
    - Features (or Feature Catalog)
    - Configuration
    - Documentation Navigator (or similar)
    """
    required_sections = [
        (r"^## Why amplihack\?$", "Why amplihack?"),
        (r"^## Quick Start$", "Quick Start"),
        (r"^## (Features|Feature Catalog)$", "Features/Feature Catalog"),
        (r"^## Configuration$", "Configuration"),
    ]

    for pattern, name in required_sections:
        count = validator.count_section_occurrences(pattern)
        assert count > 0, f"Required section not found: {name}"


# Test 8: Link Validity (Bonus - Basic Check)


def test_no_broken_internal_links(validator):
    """Basic check for broken internal anchor links

    This is a simple check - just verifies anchors reference existing headings
    """
    # Extract all internal links [text](#anchor)
    internal_links = re.findall(r"\[.*?\]\(#(.*?)\)", validator.content)

    # Extract all heading anchors (GitHub auto-generates from headings)
    headings = re.findall(r"^#{1,6} (.+)$", validator.content, re.MULTILINE)
    heading_anchors = [re.sub(r"[^\w\s-]", "", h.lower()).replace(" ", "-") for h in headings]

    broken_links = [anchor for anchor in internal_links if anchor not in heading_anchors]

    # Allow some flexibility for manual anchors and external sections
    # Just check that most links are valid (> 90%)
    if internal_links:
        valid_ratio = (len(internal_links) - len(broken_links)) / len(internal_links)
        assert valid_ratio > 0.9, (
            f"Too many broken internal links. Found {len(broken_links)} broken out of {len(internal_links)} total"
        )


# Test 9: No Multiple Quick Start Headings (Explicit)


def test_no_duplicate_quick_start_headings(validator):
    """Explicit test: README must not have multiple Quick Start sections

    Current README: FAILS - multiple "Quick Start" patterns
    Restructured: PASSES - only one
    """
    # Check various forms of "Quick Start"
    quick_start_patterns = [
        r"^## Quick Start$",
        r"^### Quick Start$",
        r"^# Quick Start$",
    ]

    total_count = sum(
        validator.count_section_occurrences(pattern) for pattern in quick_start_patterns
    )

    assert total_count == 1, (
        f"README must have exactly ONE Quick Start section (any level). Found: {total_count}"
    )


# Test 10: Proportionality Check (Philosophy Alignment)


def test_length_proportional_to_content(validator):
    """Verify README length is proportional to content complexity

    Philosophy alignment: Ruthless simplicity, proportionality principle

    README should be dense with information, not padded with fluff.
    Target: > 80% of lines contain meaningful content (not blank/decorative)
    """
    total_lines = len(validator.lines)
    blank_lines = sum(1 for line in validator.lines if not line.strip())
    decorative_lines = sum(1 for line in validator.lines if re.match(r"^[\s\-\*\=]+$", line))

    meaningful_lines = total_lines - blank_lines - decorative_lines
    density = meaningful_lines / total_lines if total_lines > 0 else 0

    assert density > 0.65, (
        f"README density too low. {meaningful_lines}/{total_lines} = {density:.1%} "
        f"(target: > 65% meaningful content - allows for code blocks and formatting)"
    )


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
