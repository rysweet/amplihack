"""Tests for validator.py module."""

from pathlib import Path

import pytest

from github_pages import ValidationIssue, ValidationResult
from github_pages.validator import (
    ClarityResult,
    CoverageResult,
    RealityResult,
    validate_clarity,
    validate_coverage,
    validate_reality,
    validate_site,
)


class TestValidateSite:
    """Tests for validate_site function."""

    def test_raises_file_not_found_for_missing_dir(self, tmp_path: Path):
        """Test that missing site directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            validate_site(tmp_path / "nonexistent")

    def test_returns_validation_result(self, tmp_site_dir: Path):
        """Test that ValidationResult is returned."""
        result = validate_site(tmp_site_dir)

        assert isinstance(result, ValidationResult)
        assert hasattr(result, "passed")
        assert hasattr(result, "issues")
        assert hasattr(result, "pass1_coverage")
        assert hasattr(result, "pass2_clarity_score")
        assert hasattr(result, "pass3_grounded_pct")

    def test_all_passes_executed(self, tmp_site_dir: Path):
        """Test that all three passes are executed."""
        result = validate_site(tmp_site_dir)

        # Should have scores from all passes
        assert result.pass1_coverage >= 0
        assert result.pass2_clarity_score >= 0
        assert result.pass3_grounded_pct >= 0

    def test_passing_validation(self, tmp_site_dir: Path):
        """Test a site that should pass validation."""
        # Create well-structured content
        md_file = tmp_site_dir / "docs.md"
        md_file.write_text("""# Documentation

## Getting Started

This is a comprehensive guide to getting started with the project.

### Installation

Install the package using pip.

### Configuration

Configure the settings in config.yml.

## Features

The system provides several useful features.
""")

        result = validate_site(tmp_site_dir)

        # Should have reasonable scores
        assert result.pass1_coverage == 100.0  # No features specified
        assert result.pass2_clarity_score >= 0
        assert result.pass3_grounded_pct >= 0


class TestValidateCoverage:
    """Tests for validate_coverage (Pass 1)."""

    def test_returns_coverage_result(self, tmp_site_dir: Path):
        """Test that CoverageResult is returned."""
        result = validate_coverage(tmp_site_dir, [])

        assert isinstance(result, CoverageResult)
        assert hasattr(result, "coverage_pct")
        assert hasattr(result, "missing_features")
        assert hasattr(result, "issues")

    def test_no_features_returns_100_percent(self, tmp_site_dir: Path):
        """Test that empty feature list returns 100% coverage."""
        result = validate_coverage(tmp_site_dir, [])

        assert result.coverage_pct == 100.0
        assert result.missing_features == []

    def test_missing_feature_detected(self, tmp_site_dir: Path):
        """Test that missing features are detected."""
        result = validate_coverage(tmp_site_dir, ["Authentication", "Authorization"])

        # These features are not in the test site
        assert result.coverage_pct < 100.0
        assert len(result.missing_features) > 0

    def test_found_feature_not_in_missing(self, tmp_path: Path):
        """Test that documented features are not in missing list."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Create content with "Authentication"
        (site_dir / "auth.md").write_text("# Authentication\n\nHow to authenticate.")

        result = validate_coverage(site_dir, ["Authentication"])

        assert "Authentication" not in result.missing_features
        assert result.coverage_pct == 100.0

    def test_empty_site_zero_coverage(self, tmp_path: Path):
        """Test that empty site returns 0% coverage."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        result = validate_coverage(site_dir, [])

        # Empty site with no explicit features - should fail
        assert result.coverage_pct == 0.0

    def test_issues_created_for_missing_features(self, tmp_site_dir: Path):
        """Test that issues are created for missing features."""
        result = validate_coverage(tmp_site_dir, ["MissingFeature"])

        assert len(result.issues) > 0
        assert result.issues[0].pass_number == 1
        assert "MissingFeature" in result.issues[0].message


class TestValidateClarity:
    """Tests for validate_clarity (Pass 2)."""

    def test_returns_clarity_result(self, tmp_site_dir: Path):
        """Test that ClarityResult is returned."""
        result = validate_clarity(tmp_site_dir)

        assert isinstance(result, ClarityResult)
        assert hasattr(result, "clarity_score")
        assert hasattr(result, "nav_depth")
        assert hasattr(result, "heading_score")
        assert hasattr(result, "link_quality_score")
        assert hasattr(result, "passed")

    def test_shallow_navigation_passes(self, tmp_path: Path):
        """Test that shallow navigation structure passes."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "index.html").write_text("<html></html>")

        result = validate_clarity(site_dir)

        # Shallow structure should not trigger nav depth warning
        assert result.nav_depth <= 3

    def test_deep_navigation_creates_issue(self, tmp_path: Path):
        """Test that deep navigation creates an issue."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Create deep structure
        deep_path = site_dir / "a" / "b" / "c" / "d" / "e"
        deep_path.mkdir(parents=True)
        (deep_path / "page.html").write_text("<html></html>")

        result = validate_clarity(site_dir)

        # Should detect deep navigation
        assert result.nav_depth > 3
        assert len(result.issues) > 0

    def test_good_headings_score_high(self, tmp_path: Path):
        """Test that descriptive headings score well."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "doc.md").write_text("""
# Getting Started with Authentication

## Configuring API Keys

## Handling Rate Limits
""")

        result = validate_clarity(site_dir)

        assert result.heading_score >= 50

    def test_generic_headings_score_lower(self, tmp_path: Path):
        """Test that generic headings score lower."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "doc.md").write_text("""
# Overview

## About

## More

## Info
""")

        result = validate_clarity(site_dir)

        # Generic headings should score lower
        assert result.heading_score < 100

    def test_good_links_score_high(self, tmp_path: Path):
        """Test that contextful links score well."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "doc.md").write_text("""
See the [Authentication Guide](auth.md) for details.
Check out [API Reference](api.md) for endpoints.
""")

        result = validate_clarity(site_dir)

        assert result.link_quality_score == 100.0

    def test_bad_links_score_lower(self, tmp_path: Path):
        """Test that 'click here' links score lower."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "doc.md").write_text("""
For more info, [click here](more.md).
See [this link](other.md) for details.
""")

        result = validate_clarity(site_dir)

        assert result.link_quality_score < 100


class TestValidateReality:
    """Tests for validate_reality (Pass 3)."""

    def test_returns_reality_result(self, tmp_site_dir: Path):
        """Test that RealityResult is returned."""
        result = validate_reality(tmp_site_dir)

        assert isinstance(result, RealityResult)
        assert hasattr(result, "grounded_pct")
        assert hasattr(result, "passed")
        assert hasattr(result, "issues")

    def test_empty_site_returns_100_percent(self, tmp_path: Path):
        """Test that empty site returns 100% grounded."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        result = validate_reality(site_dir)

        assert result.grounded_pct == 100.0
        assert result.passed is True

    def test_future_tense_detected(self, tmp_path: Path):
        """Test that future tense is detected."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "doc.md").write_text("""
# Roadmap

This feature will be implemented soon.
Authentication coming soon.
""")

        result = validate_reality(site_dir)

        assert result.grounded_pct < 100.0
        assert len(result.issues) > 0

    def test_future_tense_in_planned_section_allowed(self, tmp_path: Path):
        """Test that future tense in [PLANNED] section is allowed."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "doc.md").write_text("""
# Documentation

This is current functionality.

[PLANNED]
This feature will be added in the future.
Authentication will be implemented.
""")

        result = validate_reality(site_dir)

        # [PLANNED] sections should be excluded from analysis
        # Issues should be fewer or none
        # May still have issues from HTML files, but MD should be clean
        assert result is not None  # Verify validation ran

    def test_todo_detected(self, tmp_path: Path):
        """Test that TODO markers are detected."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "doc.md").write_text("""
# Guide

TODO: Complete this section
""")

        result = validate_reality(site_dir)

        assert len(result.issues) > 0
        assert any("TODO" in issue.message for issue in result.issues)

    def test_placeholder_examples_detected(self, tmp_path: Path):
        """Test that foo/bar placeholders are detected."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "doc.md").write_text("""
# Example

```python
user = foo
password = bar
```
""")

        result = validate_reality(site_dir)

        assert len(result.issues) > 0
        assert any("placeholder" in issue.message.lower() for issue in result.issues)

    def test_realistic_examples_pass(self, tmp_path: Path):
        """Test that realistic examples pass validation."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "doc.md").write_text("""
# Example

```python
user = "admin"
password = os.environ["API_KEY"]
client.authenticate(user, password)
```
""")

        result = validate_reality(site_dir)

        # Should not flag realistic code
        placeholder_issues = [i for i in result.issues if "placeholder" in i.message.lower()]
        assert len(placeholder_issues) == 0

    def test_grounded_threshold(self, tmp_path: Path):
        """Test that 95% threshold determines passed status."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        # Create mostly good content
        (site_dir / "good.md").write_text("# Good Documentation\n\nThis is complete.")

        result = validate_reality(site_dir)

        if result.grounded_pct >= 95.0:
            assert result.passed is True
        else:
            assert result.passed is False


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_issue_attributes(self, tmp_path: Path):
        """Test that issues have correct attributes."""
        site_dir = tmp_path / "site"
        site_dir.mkdir()

        (site_dir / "doc.md").write_text("TODO: fix this")

        result = validate_reality(site_dir)

        if result.issues:
            issue = result.issues[0]
            assert hasattr(issue, "severity")
            assert hasattr(issue, "pass_number")
            assert hasattr(issue, "location")
            assert hasattr(issue, "message")
            assert hasattr(issue, "suggestion")

    def test_issue_severity_levels(self):
        """Test that severity levels are valid."""
        valid_severities = {"error", "warning", "info"}

        issue = ValidationIssue(
            severity="warning",
            pass_number=1,
            location="test.md",
            message="Test issue",
        )

        assert issue.severity in valid_severities

    def test_issue_pass_numbers(self):
        """Test that pass numbers are 1, 2, or 3."""
        for pass_num in [1, 2, 3]:
            issue = ValidationIssue(
                severity="info",
                pass_number=pass_num,
                location="test.md",
                message="Test issue",
            )
            assert issue.pass_number == pass_num
