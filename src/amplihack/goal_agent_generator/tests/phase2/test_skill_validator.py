"""Tests for SkillValidator."""

import pytest

from ...models import ValidationResult
from ...phase2.skill_validator import SkillValidator


class TestSkillValidator:
    """Tests for SkillValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return SkillValidator()

    @pytest.fixture
    def valid_skill_content(self):
        """Valid skill content."""
        return """---
name: test-skill
description: A test skill for validation
model: inherit
---

You are a test skill that performs testing operations.

## Core Capabilities

You have the following capabilities:

- Execute test suites
- Validate results
- Generate test reports
- Track test coverage

## Usage

To use this skill, follow these steps:

1. Prepare your test environment
2. Run the test suite
3. Analyze the results
4. Generate reports

## Examples

Here are some examples:

```python
def test_example():
    assert True
```

**Note**: This is a complete, production-ready skill.
"""

    @pytest.fixture
    def invalid_skill_with_placeholders(self):
        """Skill with placeholder text."""
        return """# Test Skill

TODO: Fill in the description

## Capabilities

- [INSERT CAPABILITY HERE]
- Replace this with actual content
- FIXME: Add more capabilities

## Usage

{{ user_instructions }}
"""

    @pytest.fixture
    def short_skill_content(self):
        """Too short skill content."""
        return """# Short Skill

Brief content."""

    @pytest.fixture
    def skill_missing_sections(self):
        """Skill missing required sections."""
        return """---
name: incomplete-skill
description: Missing sections
---

This skill has a description but is missing other required sections.

## Some Section

Content here.
"""

    def test_validate_valid_skill(self, validator, valid_skill_content):
        """Test validating a valid skill."""
        result = validator.validate_skill(valid_skill_content)

        assert result.passed is True
        assert len(result.issues) == 0
        assert result.quality_score > 0.7

    def test_validate_skill_with_placeholders(
        self, validator, invalid_skill_with_placeholders
    ):
        """Test validating skill with placeholders."""
        result = validator.validate_skill(invalid_skill_with_placeholders)

        assert result.passed is False
        assert len(result.issues) > 0
        assert any("placeholder" in issue.lower() for issue in result.issues)
        assert result.quality_score < 0.5

    def test_validate_short_skill(self, validator, short_skill_content):
        """Test validating too short skill."""
        result = validator.validate_skill(short_skill_content)

        assert result.passed is False
        assert any("too short" in issue.lower() for issue in result.issues)

    def test_validate_skill_missing_sections(self, validator, skill_missing_sections):
        """Test validating skill missing required sections."""
        result = validator.validate_skill(skill_missing_sections)

        assert result.passed is False
        assert any("missing" in issue.lower() for issue in result.issues)

    def test_check_placeholders_todo(self, validator):
        """Test detecting TODO placeholders."""
        content = "This has a TODO in it"
        issues = validator._check_placeholders(content)

        assert len(issues) > 0
        assert any("TODO" in issue for issue in issues)

    def test_check_placeholders_fixme(self, validator):
        """Test detecting FIXME placeholders."""
        content = "FIXME: This needs work"
        issues = validator._check_placeholders(content)

        assert len(issues) > 0
        assert any("FIXME" in issue for issue in issues)

    def test_check_placeholders_template_vars(self, validator):
        """Test detecting template variables."""
        content = "Replace {{variable}} with content"
        issues = validator._check_placeholders(content)

        assert len(issues) > 0

    def test_check_placeholders_clean_content(self, validator):
        """Test checking clean content."""
        content = "This is clean content without any placeholders"
        issues = validator._check_placeholders(content)

        assert len(issues) == 0

    def test_check_markdown_structure_valid(self, validator):
        """Test checking valid markdown structure."""
        content = """# Main Heading

Some content here.

## Subheading

More content.

```python
code_example()
```
"""
        issues, warnings = validator._check_markdown_structure(content)

        assert len(issues) == 0

    def test_check_markdown_structure_no_headings(self, validator):
        """Test checking markdown with no headings."""
        content = "Just plain text without headings"
        issues, warnings = validator._check_markdown_structure(content)

        assert len(issues) > 0
        assert any("heading" in issue.lower() for issue in issues)

    def test_check_markdown_structure_excessive_blanks(self, validator):
        """Test checking markdown with excessive blank lines."""
        content = "# Heading\n\n\n\n\n\nContent"
        issues, warnings = validator._check_markdown_structure(content)

        assert any("blank" in warning.lower() for warning in warnings)

    def test_check_required_sections_all_present(self, validator):
        """Test checking when all required sections present."""
        content = """---
description: Test skill
---

# Test Skill

## Capabilities

- Capability 1
- Capability 2

## Usage

Instructions here.
"""
        issues = validator._check_required_sections(content)

        assert len(issues) == 0

    def test_check_required_sections_missing(self, validator):
        """Test checking when sections missing."""
        content = """# Test Skill

Just a heading, no other sections.
"""
        issues = validator._check_required_sections(content)

        assert len(issues) > 0

    def test_check_content_quality_good(self, validator):
        """Test checking good quality content."""
        content = """# Test Skill

This is a well-structured skill with proper paragraphs.
It uses **bold** and *italic* formatting for emphasis.

## Features

- Feature 1
- Feature 2
- Feature 3

### Procedures

1. Step one
2. Step two
3. Step three

This ensures good readability and structure.
"""
        warnings = validator._check_content_quality(content)

        # Should have few or no warnings
        assert len(warnings) <= 2

    def test_check_content_quality_poor(self, validator):
        """Test checking poor quality content."""
        content = """# Skill

Short.

## Section

Brief.
"""
        warnings = validator._check_content_quality(content)

        assert len(warnings) > 0

    def test_validate_batch(self, validator, valid_skill_content, short_skill_content):
        """Test validating multiple skills."""
        skills = [
            ("valid-skill", valid_skill_content),
            ("short-skill", short_skill_content),
        ]

        results = validator.validate_batch(skills)

        assert len(results) == 2
        assert results[0].passed is True
        assert results[1].passed is False

    def test_get_validation_summary_empty(self, validator):
        """Test getting summary for empty results."""
        summary = validator.get_validation_summary([])

        assert summary["total"] == 0
        assert summary["passed"] == 0
        assert summary["failed"] == 0
        assert summary["pass_rate"] == 0.0

    def test_get_validation_summary_mixed(
        self, validator, valid_skill_content, short_skill_content
    ):
        """Test getting summary for mixed results."""
        results = [
            validator.validate_skill(valid_skill_content),
            validator.validate_skill(short_skill_content),
        ]

        summary = validator.get_validation_summary(results)

        assert summary["total"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert summary["pass_rate"] == 0.5
        assert 0 <= summary["average_quality"] <= 1

    def test_validation_result_model(self):
        """Test ValidationResult model."""
        result = ValidationResult(
            passed=True,
            issues=[],
            warnings=["Warning 1"],
            quality_score=0.85,
        )

        assert result.passed is True
        assert len(result.issues) == 0
        assert len(result.warnings) == 1
        assert result.quality_score == 0.85

    def test_validation_result_invalid_score(self):
        """Test ValidationResult with invalid score."""
        with pytest.raises(ValueError):
            ValidationResult(
                passed=True,
                issues=[],
                warnings=[],
                quality_score=1.5,  # Invalid
            )

    def test_quality_score_calculation(self, validator):
        """Test that quality score is properly calculated."""
        # Perfect skill
        perfect_content = """---
name: perfect-skill
description: Perfect skill
model: inherit
---

You are a perfect skill with comprehensive documentation.

## Core Capabilities

- **Primary capability**: Execute complex operations
- **Secondary capability**: Validate results
- **Tertiary capability**: Generate reports

## Usage

To use this skill effectively:

1. Initialize the environment
2. Configure parameters
3. Execute operations
4. Validate results

## Examples

```python
def example():
    return "perfect"
```

## Best Practices

- Follow guidelines
- Maintain quality
- Document thoroughly
"""

        result = validator.validate_skill(perfect_content)

        assert result.passed is True
        assert result.quality_score > 0.8

    def test_case_insensitive_placeholder_detection(self, validator):
        """Test that placeholder detection is case insensitive."""
        content = "todo: Fix this later"
        issues = validator._check_placeholders(content)

        assert len(issues) > 0
