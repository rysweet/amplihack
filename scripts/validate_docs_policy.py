#!/usr/bin/env python3
"""Documentation Policy Validator - Validates amplihack-specific documentation policies.

This validator checks amplihack-specific documentation requirements that are not
covered by standard markdown linting tools like markdownlint.

Policies enforced:
1. All documentation must be in docs/ directory (except root README.md)
2. Documentation must be linked from discoverable locations
3. No stub documentation (empty sections, TODO markers)
4. Code examples must be marked as runnable or partial
5. No unnecessary abstraction in documentation hierarchy

Usage:
    python validate_docs_policy.py docs/
    python validate_docs_policy.py docs/README.md --verbose
"""

import argparse
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "DocsPolicyValidator",
    "PolicyResult",
    "PolicyViolation",
]

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

# Stub markers that indicate incomplete documentation
STUB_MARKERS = [
    "TODO",
    "FIXME",
    "TBD",
    "XXX",
    "STUB",
    "PLACEHOLDER",
    "Coming soon",
    "To be written",
    "To be documented",
]

# Compiled regex patterns (module-level for performance)
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^\)]+)\)")
CODE_FENCE_START = re.compile(r"^(`{3,}|~{3,})(\w+)?")
CODE_FENCE_END = re.compile(r"^(`{3,}|~{3,})")
RUNNABLE_MARKER = re.compile(r"<!--\s*runnable\s*-->", re.IGNORECASE)

# Root-level files that are allowed outside docs/
ALLOWED_ROOT_DOCS = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
]

# Files that serve as documentation entry points (must link to other docs)
ENTRY_POINT_FILES = [
    "README.md",
    "docs/README.md",
    "docs/index.md",
]


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class PolicyViolation:
    """Represents a policy violation."""

    file: Path
    line: int
    rule: str
    message: str
    severity: str  # "error" or "warning"


@dataclass
class PolicyResult:
    """Result of policy validation."""

    success: bool
    violations: list[PolicyViolation] = field(default_factory=list)
    warnings: list[PolicyViolation] = field(default_factory=list)
    info: list[str] = field(default_factory=list)


# ============================================================================
# Policy Validators
# ============================================================================


def check_docs_directory_placement(
    repo_root: Path, markdown_files: list[Path]
) -> list[PolicyViolation]:
    """Check that all documentation is in docs/ directory.

    Args:
        repo_root: Repository root path
        markdown_files: List of markdown files to check

    Returns:
        List of PolicyViolation objects
    """
    violations = []

    for md_file in markdown_files:
        relative_path = md_file.relative_to(repo_root)

        # Check if file is in docs/ or is an allowed root-level file
        if not str(relative_path).startswith("docs/"):
            if relative_path.name not in ALLOWED_ROOT_DOCS:
                violations.append(
                    PolicyViolation(
                        file=md_file,
                        line=0,
                        rule="docs-directory",
                        message=f"Documentation file should be in docs/ directory: {relative_path}",
                        severity="error",
                    )
                )

    return violations


def check_discoverability(repo_root: Path, markdown_files: list[Path]) -> list[PolicyViolation]:
    """Check that documentation is linked from discoverable locations.

    Args:
        repo_root: Repository root path
        markdown_files: List of markdown files to check

    Returns:
        List of PolicyViolation objects
    """
    violations = []

    # Find entry point files
    entry_points = []
    for entry_point in ENTRY_POINT_FILES:
        entry_file = repo_root / entry_point
        if entry_file.exists():
            entry_points.append(entry_file)

    if not entry_points:
        violations.append(
            PolicyViolation(
                file=repo_root,
                line=0,
                rule="discoverability",
                message="No documentation entry points found (README.md, docs/README.md, or docs/index.md)",
                severity="error",
            )
        )
        return violations

    # Extract all links from entry points
    linked_files = set()
    for entry_point in entry_points:
        links = extract_internal_links(entry_point)
        linked_files.update(links)

    # Check if docs/ files are linked
    docs_dir = repo_root / "docs"
    if docs_dir.exists():
        for md_file in markdown_files:
            if not str(md_file.relative_to(repo_root)).startswith("docs/"):
                continue

            # Skip entry point files themselves
            if md_file in entry_points:
                continue

            # Check if file is linked
            relative_path = md_file.relative_to(repo_root)
            if relative_path not in linked_files:
                violations.append(
                    PolicyViolation(
                        file=md_file,
                        line=0,
                        rule="discoverability",
                        message=f"Documentation file not linked from any entry point: {relative_path}",
                        severity="warning",
                    )
                )

    return violations


def check_stub_documentation(markdown_file: Path) -> list[PolicyViolation]:
    """Check for stub documentation markers.

    Args:
        markdown_file: Path to markdown file

    Returns:
        List of PolicyViolation objects
    """
    violations = []

    try:
        content = markdown_file.read_text(encoding="utf-8")
    except Exception:
        return violations

    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        # Check for stub markers
        for marker in STUB_MARKERS:
            if marker.lower() in line.lower():
                violations.append(
                    PolicyViolation(
                        file=markdown_file,
                        line=line_num,
                        rule="no-stubs",
                        message=f"Stub marker found: {marker}",
                        severity="error",
                    )
                )
                break

        # Check for empty sections (heading followed by another heading)
        if line.strip().startswith("#"):
            # Look ahead to see if next non-empty line is also a heading
            next_non_empty = None
            for i in range(line_num, len(lines)):
                if lines[i].strip():
                    next_non_empty = lines[i].strip()
                    break

            if next_non_empty and next_non_empty.startswith("#"):
                violations.append(
                    PolicyViolation(
                        file=markdown_file,
                        line=line_num,
                        rule="no-stubs",
                        message=f"Empty section: '{line.strip()}' has no content",
                        severity="error",
                    )
                )

    return violations


def check_code_block_markers(markdown_file: Path) -> list[PolicyViolation]:
    """Check that code blocks are marked as runnable or clearly partial.

    Args:
        markdown_file: Path to markdown file

    Returns:
        List of PolicyViolation objects
    """
    violations = []

    try:
        content = markdown_file.read_text(encoding="utf-8")
    except Exception:
        return violations

    lines = content.split("\n")
    in_code_block = False
    code_block_start = 0
    code_block_lang = None
    has_runnable_marker = False

    for line_num, line in enumerate(lines, 1):
        # Check for runnable marker
        if RUNNABLE_MARKER.search(line):
            has_runnable_marker = True

        # Check for code fence start
        match = CODE_FENCE_START.match(line)
        if match and not in_code_block:
            in_code_block = True
            code_block_start = line_num
            code_block_lang = match.group(2) or ""
            has_runnable_marker = False  # Reset for next block
            continue

        # Check for code fence end
        if in_code_block and CODE_FENCE_END.match(line):
            in_code_block = False

            # Check if this was an executable language without marker
            if code_block_lang in ("python", "py", "javascript", "js", "bash", "sh"):
                # Look for partial example indicators
                prev_lines = lines[max(0, code_block_start - 3) : code_block_start]
                context = "\n".join(prev_lines).lower()

                is_partial = any(
                    indicator in context
                    for indicator in [
                        "example",
                        "snippet",
                        "partial",
                        "excerpt",
                        "fragment",
                        "illustration",
                    ]
                )

                # Check if code block has obvious placeholders
                code_lines = lines[code_block_start : line_num - 1]
                code_content = "\n".join(code_lines)
                has_placeholders = any(
                    marker in code_content for marker in ["...", "# ...", "// ...", "TODO", "FIXME"]
                )

                if not has_runnable_marker and not is_partial and not has_placeholders:
                    violations.append(
                        PolicyViolation(
                            file=markdown_file,
                            line=code_block_start,
                            rule="code-block-markers",
                            message="Code block should be marked with <!-- runnable --> or clearly indicated as partial example",
                            severity="warning",
                        )
                    )

    return violations


def check_unnecessary_abstraction(markdown_file: Path) -> list[PolicyViolation]:
    """Check for unnecessary abstraction in documentation hierarchy.

    Args:
        markdown_file: Path to markdown file

    Returns:
        List of PolicyViolation objects
    """
    violations = []

    try:
        content = markdown_file.read_text(encoding="utf-8")
    except Exception:
        return violations

    # Check file length - very short files might indicate over-fragmentation
    lines = [line for line in content.split("\n") if line.strip()]
    if len(lines) < 10:
        violations.append(
            PolicyViolation(
                file=markdown_file,
                line=0,
                rule="unnecessary-abstraction",
                message=f"Very short documentation file ({len(lines)} lines) - consider consolidating",
                severity="warning",
            )
        )

    # Check for excessive heading depth
    for line_num, line in enumerate(content.split("\n"), 1):
        if line.strip().startswith("######"):  # Level 6 heading
            violations.append(
                PolicyViolation(
                    file=markdown_file,
                    line=line_num,
                    rule="unnecessary-abstraction",
                    message="Excessive heading depth (6 levels) - consider flattening structure",
                    severity="warning",
                )
            )

    return violations


# ============================================================================
# Utilities
# ============================================================================


def extract_internal_links(markdown_file: Path) -> set[Path]:
    """Extract internal file links from markdown.

    Args:
        markdown_file: Path to markdown file

    Returns:
        Set of linked file paths (relative to repo root)
    """
    links = set()

    try:
        content = markdown_file.read_text(encoding="utf-8")
    except Exception:
        return links

    # Use compiled regex pattern from module level
    for match in LINK_PATTERN.finditer(content):
        url = match.group(2).strip()

        # Skip external links
        if url.startswith(("http://", "https://", "mailto:", "tel:")):
            continue

        # Skip anchors
        if url.startswith("#"):
            continue

        # Remove anchor from URL
        if "#" in url:
            url = url.split("#")[0]

        # Skip empty URLs
        if not url:
            continue

        # Resolve relative path
        try:
            target_path = (markdown_file.parent / url).resolve()
            repo_root = find_repo_root(markdown_file.parent)

            relative_path = target_path.relative_to(repo_root)
            links.add(relative_path)
        except Exception:
            # Skip links that can't be resolved
            pass

    return links


def find_repo_root(start_path: Path) -> Path:
    """Find repository root by looking for .git directory.

    Args:
        start_path: Starting path for search

    Returns:
        Repository root path
    """
    current = start_path.resolve()

    while current.parent != current:
        if (current / ".git").exists():
            return current
        current = current.parent

    # Fallback to start path
    return start_path.resolve()


# ============================================================================
# Main Validator
# ============================================================================


class DocsPolicyValidator:
    """Validates amplihack-specific documentation policies."""

    def __init__(self, repo_root: Path | None = None):
        """Initialize validator.

        Args:
            repo_root: Repository root path (auto-detected if None)
        """
        self.repo_root = repo_root or find_repo_root(Path.cwd())

    def validate_file(self, markdown_file: Path) -> PolicyResult:
        """Validate a single markdown file.

        Args:
            markdown_file: Path to markdown file

        Returns:
            PolicyResult
        """
        result = PolicyResult(success=True)

        if not markdown_file.exists():
            result.success = False
            result.violations.append(
                PolicyViolation(
                    file=markdown_file,
                    line=0,
                    rule="file-not-found",
                    message=f"File not found: {markdown_file}",
                    severity="error",
                )
            )
            return result

        # Run individual policy checks
        violations = []
        violations.extend(check_stub_documentation(markdown_file))
        violations.extend(check_code_block_markers(markdown_file))
        violations.extend(check_unnecessary_abstraction(markdown_file))

        # Separate errors and warnings
        for violation in violations:
            if violation.severity == "error":
                result.violations.append(violation)
                result.success = False
            else:
                result.warnings.append(violation)

        return result

    def validate_directory(self, directory: Path) -> PolicyResult:
        """Validate all markdown files in directory.

        Args:
            directory: Path to directory

        Returns:
            PolicyResult
        """
        result = PolicyResult(success=True)

        if not directory.exists():
            result.success = False
            result.violations.append(
                PolicyViolation(
                    file=directory,
                    line=0,
                    rule="directory-not-found",
                    message=f"Directory not found: {directory}",
                    severity="error",
                )
            )
            return result

        # Find all markdown files
        markdown_files = sorted(directory.rglob("*.md"))

        if not markdown_files:
            result.info.append(f"No markdown files found in {directory}")
            return result

        result.info.append(f"Found {len(markdown_files)} markdown file(s)")

        # Run project-wide checks
        violations = []
        violations.extend(check_docs_directory_placement(self.repo_root, markdown_files))
        violations.extend(check_discoverability(self.repo_root, markdown_files))

        # Run per-file checks
        for md_file in markdown_files:
            file_result = self.validate_file(md_file)
            violations.extend(file_result.violations)
            violations.extend(file_result.warnings)

        # Separate errors and warnings
        for violation in violations:
            if violation.severity == "error":
                result.violations.append(violation)
                result.success = False
            else:
                result.warnings.append(violation)

        return result


# ============================================================================
# CLI Interface
# ============================================================================


def format_violation(violation: PolicyViolation) -> str:
    """Format a policy violation for display.

    Args:
        violation: PolicyViolation object

    Returns:
        Formatted string
    """
    symbol = "✗" if violation.severity == "error" else "⚠"
    location = f"{violation.file}"
    if violation.line > 0:
        location += f":{violation.line}"

    return f"  {symbol} [{violation.rule}] {location}\n      {violation.message}"


def parse_args(args=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate amplihack-specific documentation policies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s docs/
  %(prog)s docs/README.md --verbose
  %(prog)s . --repo-root /path/to/repo
        """,
    )

    parser.add_argument(
        "path",
        type=Path,
        help="Markdown file or directory to validate",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Repository root path (auto-detected if not provided)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args(args)


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Configure logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
    )

    print("Documentation Policy Validator")
    print("=" * 60)

    # Create validator
    validator = DocsPolicyValidator(repo_root=args.repo_root)
    print(f"Repository root: {validator.repo_root}")
    print()

    # Validate file or directory
    if args.path.is_file():
        result = validator.validate_file(args.path)
    elif args.path.is_dir():
        result = validator.validate_directory(args.path)
    else:
        print(f"Error: Path does not exist: {args.path}")
        return 1

    # Display info
    for info in result.info:
        print(f"ℹ {info}")

    # Display violations
    if result.violations:
        print(f"\nErrors ({len(result.violations)}):")
        print("-" * 60)
        for violation in result.violations:
            print(format_violation(violation))

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        print("-" * 60)
        for violation in result.warnings:
            print(format_violation(violation))

    # Summary
    print("\n" + "=" * 60)
    if result.success:
        print("✓ All policy checks passed")
        if result.warnings:
            print(f"  ({len(result.warnings)} warning(s))")
    else:
        print(f"✗ Policy validation failed: {len(result.violations)} error(s)")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
