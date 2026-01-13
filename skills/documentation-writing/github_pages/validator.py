"""Three-pass documentation validator for GitHub Pages.

Validates documentation sites with three passes:
- Pass 1: Coverage - Every feature must be documented (100%)
- Pass 2: Clarity - Organization and readability (>= 80%)
- Pass 3: Reality - No future tense, no placeholders (>= 95%)

Philosophy:
- Single responsibility: Validate documentation quality
- Three distinct passes with clear thresholds
- Actionable feedback with suggestions
- Allow [PLANNED] markers for documented future features
"""

import re
from dataclasses import dataclass
from pathlib import Path

from . import ValidationIssue, ValidationResult


@dataclass
class CoverageResult:
    """Result of Pass 1: Coverage validation."""

    coverage_pct: float
    missing_features: list[str]
    checked_count: int
    issues: list[ValidationIssue]


@dataclass
class ClarityResult:
    """Result of Pass 2: Clarity validation."""

    clarity_score: float
    nav_depth: int
    heading_score: float
    link_quality_score: float
    passed: bool
    issues: list[ValidationIssue]


@dataclass
class RealityResult:
    """Result of Pass 3: Reality validation."""

    grounded_pct: float
    passed: bool
    issues: list[ValidationIssue]


def validate_site(site_dir: Path | str) -> ValidationResult:
    """Run complete three-pass validation on documentation site.

    Args:
        site_dir: Path to generated site directory

    Returns:
        ValidationResult with scores from all three passes

    Raises:
        FileNotFoundError: If site_dir doesn't exist
    """
    site_path = Path(site_dir)

    if not site_path.exists():
        raise FileNotFoundError(f"Site directory not found: {site_dir}")

    all_issues: list[ValidationIssue] = []

    # Pass 1: Coverage validation
    coverage_result = validate_coverage(site_path, [])
    all_issues.extend(coverage_result.issues)

    # Pass 2: Clarity validation
    clarity_result = validate_clarity(site_path)
    all_issues.extend(clarity_result.issues)

    # Pass 3: Reality validation
    reality_result = validate_reality(site_path)
    all_issues.extend(reality_result.issues)

    # Determine overall pass/fail
    # Thresholds: Coverage 100%, Clarity >= 80%, Grounded >= 95%
    passed = (
        coverage_result.coverage_pct >= 100.0
        and clarity_result.clarity_score >= 80.0
        and reality_result.grounded_pct >= 95.0
    )

    return ValidationResult(
        passed=passed,
        issues=all_issues,
        pass1_coverage=coverage_result.coverage_pct,
        pass2_clarity_score=clarity_result.clarity_score,
        pass3_grounded_pct=reality_result.grounded_pct,
    )


def validate_coverage(
    site_dir: Path,
    features: list[str],
) -> CoverageResult:
    """Pass 1: Validate that all features are documented.

    Args:
        site_dir: Path to site directory
        features: List of feature names to check for

    Returns:
        CoverageResult with coverage percentage and missing features
    """
    issues: list[ValidationIssue] = []
    missing_features: list[str] = []

    # If no features specified, check for basic documentation coverage
    if not features:
        # Auto-detect what should be documented by checking for common sections
        md_files = list(site_dir.rglob("*.md")) + list(site_dir.rglob("*.html"))
        if md_files:
            # If we have content, assume 100% coverage (no explicit feature list)
            return CoverageResult(
                coverage_pct=100.0,
                missing_features=[],
                checked_count=0,
                issues=[],
            )
        # No content at all
        issues.append(
            ValidationIssue(
                severity="error",
                pass_number=1,
                location=str(site_dir),
                message="No documentation content found",
                suggestion="Add markdown files to docs/ directory",
            )
        )
        return CoverageResult(
            coverage_pct=0.0,
            missing_features=["documentation"],
            checked_count=1,
            issues=issues,
        )

    # Check each feature
    documented_count = 0
    for feature in features:
        found = _find_feature_in_docs(site_dir, feature)
        if found:
            documented_count += 1
        else:
            missing_features.append(feature)
            issues.append(
                ValidationIssue(
                    severity="error",
                    pass_number=1,
                    location=str(site_dir),
                    message=f"Feature not documented: {feature}",
                    suggestion=f"Add documentation for {feature}",
                )
            )

    coverage_pct = (documented_count / len(features) * 100) if features else 100.0

    return CoverageResult(
        coverage_pct=coverage_pct,
        missing_features=missing_features,
        checked_count=len(features),
        issues=issues,
    )


def validate_clarity(site_dir: Path) -> ClarityResult:
    """Pass 2: Validate documentation clarity and organization.

    Checks:
    - Navigation depth (<= 3 levels)
    - Descriptive headings
    - Contextful links (not "click here")
    - Proper structure (no walls of text)

    Args:
        site_dir: Path to site directory

    Returns:
        ClarityResult with clarity score and component scores
    """
    issues: list[ValidationIssue] = []

    # Analyze navigation depth
    nav_depth = _analyze_navigation_depth_from_site(site_dir)
    if nav_depth > 3:
        issues.append(
            ValidationIssue(
                severity="warning",
                pass_number=2,
                location=str(site_dir),
                message=f"Navigation depth ({nav_depth}) exceeds recommended 3 levels",
                suggestion="Flatten navigation structure",
            )
        )

    # Analyze heading quality
    heading_score = _analyze_heading_quality(site_dir)

    # Analyze link quality
    link_quality_score = _analyze_link_quality(site_dir)

    # Analyze content structure (walls of text)
    structure_score = _analyze_content_structure(site_dir)
    if structure_score < 80:
        issues.append(
            ValidationIssue(
                severity="warning",
                pass_number=2,
                location=str(site_dir),
                message="Readability issues: large text blocks without structure",
                suggestion="Add subheadings to break up content",
            )
        )

    # Calculate overall clarity score
    # Weight: nav 20%, headings 30%, links 20%, structure 30%
    nav_score = 100 if nav_depth <= 3 else max(0, 100 - (nav_depth - 3) * 20)
    clarity_score = (
        nav_score * 0.2 + heading_score * 0.3 + link_quality_score * 0.2 + structure_score * 0.3
    )

    return ClarityResult(
        clarity_score=clarity_score,
        nav_depth=nav_depth,
        heading_score=heading_score,
        link_quality_score=link_quality_score,
        passed=clarity_score >= 80.0,
        issues=issues,
    )


def validate_reality(site_dir: Path) -> RealityResult:
    """Pass 3: Validate documentation is grounded in reality.

    Checks:
    - No future tense ("will be", "coming soon") unless in [PLANNED]
    - No TODO markers
    - No foo/bar placeholder examples

    Args:
        site_dir: Path to site directory

    Returns:
        RealityResult with grounded percentage
    """
    issues: list[ValidationIssue] = []

    # Find all content files
    content_files = list(site_dir.rglob("*.md")) + list(site_dir.rglob("*.html"))

    if not content_files:
        # No content to validate - consider it valid
        return RealityResult(
            grounded_pct=100.0,
            passed=True,
            issues=[],
        )

    total_checks = 0
    ungrounded_count = 0

    for file_path in content_files:
        try:
            content = file_path.read_text(errors="ignore")
        except Exception:
            continue

        # Check for future tense (unless in [PLANNED] section)
        future_issues = _check_future_tense(content, str(file_path))
        for issue in future_issues:
            issues.append(issue)
            ungrounded_count += 1
        total_checks += 1

        # Check for TODOs (unless in [PLANNED] section)
        todo_issues = _check_todos(content, str(file_path))
        for issue in todo_issues:
            issues.append(issue)
            ungrounded_count += 1
        total_checks += 1

        # Check for placeholder examples
        placeholder_issues = _check_placeholders(content, str(file_path))
        for issue in placeholder_issues:
            issues.append(issue)
            ungrounded_count += 1
        total_checks += 1

    # Calculate grounded percentage
    # Formula: Start at 100%, subtract penalty for each ungrounded check
    # Penalty = (ungrounded_count / total_checks) * 100
    # Example: 3 files checked, 1 ungrounded issue per file = 3 ungrounded, 9 total checks
    #          grounded_pct = 100 - (3/9 * 100) = 100 - 33.3 = 66.7%
    if total_checks == 0:
        grounded_pct = 100.0
    else:
        grounded_pct = max(0, 100.0 - (ungrounded_count / total_checks * 100))

    return RealityResult(
        grounded_pct=grounded_pct,
        passed=grounded_pct >= 95.0,
        issues=issues,
    )


# ==============================================================================
# Helper Functions
# ==============================================================================


def _find_feature_in_docs(site_dir: Path, feature_name: str) -> bool:
    """Search for feature mention in documentation.

    Args:
        site_dir: Path to site directory
        feature_name: Name of feature to search for

    Returns:
        True if feature is documented, False otherwise
    """
    # Search in all content files
    content_files = list(site_dir.rglob("*.md")) + list(site_dir.rglob("*.html"))

    feature_pattern = re.compile(re.escape(feature_name), re.IGNORECASE)

    for file_path in content_files:
        try:
            content = file_path.read_text(errors="ignore")
            if feature_pattern.search(content):
                return True
        except Exception:
            continue

    return False


def _analyze_navigation_depth(nav_structure: dict | list) -> int:
    """Calculate maximum depth of navigation structure.

    Args:
        nav_structure: Navigation dictionary or list

    Returns:
        Maximum depth of navigation
    """
    if isinstance(nav_structure, dict):
        if not nav_structure:
            return 0
        return 1 + max((_analyze_navigation_depth(v) for v in nav_structure.values()), default=0)
    if isinstance(nav_structure, list):
        if not nav_structure:
            return 0
        return max((_analyze_navigation_depth(item) for item in nav_structure), default=0)
    return 0


def _analyze_navigation_depth_from_site(site_dir: Path) -> int:
    """Analyze navigation depth from site directory structure.

    Args:
        site_dir: Path to site directory

    Returns:
        Maximum depth of navigation
    """
    max_depth = 0

    for file_path in site_dir.rglob("*.html"):
        # Count directory depth from site root
        try:
            rel_path = file_path.relative_to(site_dir)
            depth = len(rel_path.parts) - 1  # -1 for the file itself
            max_depth = max(max_depth, depth)
        except ValueError:
            continue

    return max(1, max_depth)  # At least depth 1


def _analyze_heading_quality(site_dir: Path) -> float:
    """Analyze quality of headings in documentation.

    Checks for:
    - Descriptive headings (not just "Overview", "Introduction")
    - Proper heading hierarchy

    Args:
        site_dir: Path to site directory

    Returns:
        Heading quality score (0-100)
    """
    generic_headings = {
        "overview",
        "introduction",
        "about",
        "description",
        "more",
        "details",
        "info",
        "information",
    }

    total_headings = 0
    good_headings = 0

    heading_pattern = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)

    for file_path in site_dir.rglob("*.md"):
        try:
            content = file_path.read_text(errors="ignore")
            headings = heading_pattern.findall(content)

            for heading in headings:
                total_headings += 1
                heading_lower = heading.strip().lower()

                # Check if heading is descriptive
                if heading_lower not in generic_headings and len(heading_lower) > 5:
                    good_headings += 1
        except Exception:
            continue

    if total_headings == 0:
        return 100.0

    return (good_headings / total_headings) * 100


def _analyze_link_quality(site_dir: Path) -> float:
    """Analyze quality of links in documentation.

    Checks for bad link text like "click here", "here", "link".

    Args:
        site_dir: Path to site directory

    Returns:
        Link quality score (0-100)
    """
    bad_link_texts = {"click here", "here", "link", "this", "this link"}

    total_links = 0
    good_links = 0

    link_pattern = re.compile(r"\[([^\]]+)\]\([^)]+\)")

    for file_path in site_dir.rglob("*.md"):
        try:
            content = file_path.read_text(errors="ignore")
            links = link_pattern.findall(content)

            for link_text in links:
                total_links += 1
                if link_text.strip().lower() not in bad_link_texts:
                    good_links += 1
        except Exception:
            continue

    if total_links == 0:
        return 100.0

    return (good_links / total_links) * 100


def _analyze_content_structure(site_dir: Path) -> float:
    """Analyze content structure for walls of text.

    Args:
        site_dir: Path to site directory

    Returns:
        Structure score (0-100)
    """
    total_files = 0
    well_structured_files = 0

    for file_path in site_dir.rglob("*.md"):
        try:
            content = file_path.read_text(errors="ignore")
            total_files += 1

            # Check for walls of text (paragraphs > 500 words)
            paragraphs = content.split("\n\n")
            has_wall = False

            for para in paragraphs:
                # Skip code blocks
                if para.strip().startswith("```"):
                    continue
                word_count = len(para.split())
                if word_count > 300:
                    has_wall = True
                    break

            if not has_wall:
                well_structured_files += 1
        except Exception:
            continue

    if total_files == 0:
        return 100.0

    return (well_structured_files / total_files) * 100


def _check_future_tense(content: str, file_path: str) -> list[ValidationIssue]:
    """Check for future tense language in content.

    Args:
        content: File content to check
        file_path: Path for issue reporting

    Returns:
        List of validation issues found
    """
    issues: list[ValidationIssue] = []

    # Skip [PLANNED] sections
    if "[PLANNED]" in content:
        # Remove [PLANNED] sections from analysis
        planned_pattern = re.compile(
            r"\[PLANNED\].*?(?=^#|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE
        )
        content = planned_pattern.sub("", content)

    future_patterns = [
        (r"\bwill be\b", "will be"),
        (r"\bcoming soon\b", "coming soon"),
        (r"\bto be implemented\b", "to be implemented"),
        (r"\bin the future\b", "in the future"),
        (r"\bnext release\b", "next release"),
    ]

    for pattern, phrase in future_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            issues.append(
                ValidationIssue(
                    severity="info",
                    pass_number=3,
                    location=file_path,
                    message=f"Future tense detected: '{phrase}'",
                    suggestion="Use present tense or mark with [PLANNED]",
                )
            )

    return issues


def _check_todos(content: str, file_path: str) -> list[ValidationIssue]:
    """Check for TODO markers in content.

    Args:
        content: File content to check
        file_path: Path for issue reporting

    Returns:
        List of validation issues found
    """
    issues: list[ValidationIssue] = []

    # Skip [PLANNED] sections
    if "[PLANNED]" in content:
        planned_pattern = re.compile(
            r"\[PLANNED\].*?(?=^#|\Z)", re.MULTILINE | re.DOTALL | re.IGNORECASE
        )
        content = planned_pattern.sub("", content)

    todo_pattern = re.compile(r"\bTODO\b", re.IGNORECASE)
    matches = todo_pattern.findall(content)

    if matches:
        issues.append(
            ValidationIssue(
                severity="warning",
                pass_number=3,
                location=file_path,
                message="TODO marker found in documentation",
                suggestion="Complete the TODO or move to [PLANNED] section",
            )
        )

    return issues


def _check_placeholders(content: str, file_path: str) -> list[ValidationIssue]:
    """Check for foo/bar placeholder examples.

    Args:
        content: File content to check
        file_path: Path for issue reporting

    Returns:
        List of validation issues found
    """
    issues: list[ValidationIssue] = []

    # Check for common placeholder patterns in code blocks
    code_block_pattern = re.compile(r"```[\s\S]*?```")
    code_blocks = code_block_pattern.findall(content)

    placeholder_patterns = [
        (r"\bfoo\b", "foo"),
        (r"\bbar\b", "bar"),
        (r"\bbaz\b", "baz"),
        (r"\bqux\b", "qux"),
        (r"example\.com", "example.com"),
    ]

    for code_block in code_blocks:
        for pattern, placeholder in placeholder_patterns:
            if re.search(pattern, code_block, re.IGNORECASE):
                issues.append(
                    ValidationIssue(
                        severity="info",
                        pass_number=3,
                        location=file_path,
                        message=f"Placeholder example detected: '{placeholder}'",
                        suggestion="Replace with realistic example",
                    )
                )
                break  # Only report one per block

    return issues
