#!/usr/bin/env python3
"""
Link checker tool for documentation sites and markdown files.

Philosophy:
- Simple, self-contained module with clear public API
- Uses linkinator (npm package) as backend
- Zero-BS: Every function works or doesn't exist
- Follows amplihack brick philosophy

Public API ("studs"):
    check_site(url: str, timeout: int) -> LinkCheckReport
    check_local(path: Path, timeout: int) -> LinkCheckReport
    format_report(report: LinkCheckReport) -> str
    get_exit_code(report: LinkCheckReport) -> int
"""

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class BrokenLink:
    """Represents a broken link found during checking."""

    url: str
    status_code: int | None = None
    parent_url: str | None = None
    error_message: str | None = None


@dataclass
class LinkCheckReport:
    """Report from link checking operation."""

    passed: bool
    checked_count: int
    broken_count: int
    broken_links: list[BrokenLink] = field(default_factory=list)
    error: bool = False
    error_message: str | None = None


@dataclass
class PrerequisiteCheckResult:
    """Result from prerequisite checking."""

    linkinator_available: bool
    linkinator_path: str | None = None
    error_message: str | None = None


# =============================================================================
# PREREQUISITE CHECKING
# =============================================================================


def check_prerequisites() -> PrerequisiteCheckResult:
    """Check if linkinator is installed.

    Returns:
        PrerequisiteCheckResult with availability status
    """
    linkinator_path = shutil.which("linkinator")

    if linkinator_path:
        return PrerequisiteCheckResult(linkinator_available=True, linkinator_path=linkinator_path)
    return PrerequisiteCheckResult(
        linkinator_available=False, error_message=get_install_instructions("linkinator")
    )


def get_install_instructions(tool: str) -> str:
    """Get installation instructions for a tool.

    Args:
        tool: Name of the tool (e.g., "linkinator")

    Returns:
        Installation instructions string
    """
    if tool == "linkinator":
        return (
            "linkinator is not installed.\n"
            "Install it with: npm install -g linkinator\n"
            "Or use npx: npx linkinator <url>"
        )
    return f"Tool '{tool}' is not installed."


# =============================================================================
# SUBPROCESS WRAPPER
# =============================================================================


def safe_subprocess_call(
    cmd: list[str],
    context: str,
    timeout: int | None = 30,
) -> tuple[int, str, str]:
    """Safely execute subprocess with comprehensive error handling.

    Args:
        cmd: Command and arguments to execute
        context: Context description for error messages
        timeout: Timeout in seconds (default: 30)

    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr

    except FileNotFoundError:
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Command not found: {cmd_name}\n"
        if context:
            error_msg += f"Context: {context}\n"
        error_msg += "Please ensure the tool is installed and in your PATH."
        return 127, "", error_msg

    except subprocess.TimeoutExpired:
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Command timed out after {timeout}s: {cmd_name}\n"
        if context:
            error_msg += f"Context: {context}\n"
        return 124, "", error_msg

    except PermissionError:
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Permission denied: {cmd_name}\n"
        if context:
            error_msg += f"Context: {context}\n"
        error_msg += "Check file and directory permissions."
        return 1, "", error_msg

    except Exception as e:
        cmd_name = cmd[0] if cmd else "command"
        error_msg = f"Unexpected error running {cmd_name}: {e!s}\n"
        if context:
            error_msg += f"Context: {context}\n"
        return 1, "", error_msg


# =============================================================================
# REPORT PARSING
# =============================================================================


def parse_linkinator_output(json_output: str) -> LinkCheckReport:
    """Parse linkinator JSON output into LinkCheckReport.

    Args:
        json_output: JSON string from linkinator

    Returns:
        LinkCheckReport with parsed data

    Raises:
        ValueError: If JSON is invalid or empty
    """
    if not json_output:
        raise ValueError("Empty output from linkinator")

    try:
        data = json.loads(json_output)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from linkinator: {e}")

    # Extract links
    links = data.get("links", [])
    checked_count = len(links)

    # Find broken links
    broken_links = []
    for link in links:
        if link.get("state") == "BROKEN":
            broken_link = BrokenLink(
                url=link.get("url", "unknown"),
                status_code=link.get("status"),
                parent_url=link.get("parent"),
                error_message=link.get("failureDetails", {}).get("error"),
            )
            broken_links.append(broken_link)

    passed = data.get("passed", len(broken_links) == 0)

    return LinkCheckReport(
        passed=passed,
        checked_count=checked_count,
        broken_count=len(broken_links),
        broken_links=broken_links,
    )


# =============================================================================
# REPORT FORMATTING
# =============================================================================


def format_report(report: LinkCheckReport) -> str:
    """Format LinkCheckReport into human-readable text.

    Args:
        report: LinkCheckReport to format

    Returns:
        Formatted report string
    """
    lines = []
    lines.append("=" * 70)
    lines.append("Link Check Report")
    lines.append("=" * 70)
    lines.append("")

    # Summary statistics
    lines.append(f"Total links checked: {report.checked_count}")
    lines.append(f"Broken links found: {report.broken_count}")

    if report.checked_count > 0:
        success_rate = ((report.checked_count - report.broken_count) / report.checked_count) * 100
        lines.append(f"Success rate: {success_rate:.1f}%")

    lines.append("")

    # Status
    if report.error:
        lines.append("STATUS: ERROR")
        if report.error_message:
            lines.append(f"Error: {report.error_message}")
    elif report.passed:
        lines.append("STATUS: PASSED ✓")
        lines.append("All links are valid!")
    else:
        lines.append("STATUS: FAILED ✗")
        lines.append(f"Found {report.broken_count} broken link(s)")

    # Broken links details
    if report.broken_links:
        lines.append("")
        lines.append("Broken Links:")
        lines.append("-" * 70)
        for i, broken in enumerate(report.broken_links, 1):
            lines.append(f"\n{i}. {broken.url}")
            if broken.status_code:
                lines.append(f"   Status: {broken.status_code}")
            if broken.parent_url:
                lines.append(f"   Found in: {broken.parent_url}")
            if broken.error_message:
                lines.append(f"   Error: {broken.error_message}")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


# =============================================================================
# EXIT CODES
# =============================================================================


def get_exit_code(report: LinkCheckReport) -> int:
    """Get exit code from LinkCheckReport.

    Args:
        report: LinkCheckReport

    Returns:
        Exit code (0=success, 1=broken links, 2=error)
    """
    if report.error:
        return 2
    if not report.passed:
        return 1
    return 0


# =============================================================================
# PUBLIC API
# =============================================================================


def check_site(url: str, timeout: int = 120) -> LinkCheckReport:
    """Check a website for broken links.

    Args:
        url: URL to check (e.g., "https://example.com")
        timeout: Timeout in seconds (default: 120)

    Returns:
        LinkCheckReport with results
    """
    # Validate URL (basic check)
    if not url.startswith(("http://", "https://")):
        return LinkCheckReport(
            passed=False,
            checked_count=0,
            broken_count=0,
            error=True,
            error_message=f"Invalid URL: {url}. Must start with http:// or https://",
        )

    # Check prerequisites
    prereq = check_prerequisites()
    if not prereq.linkinator_available:
        return LinkCheckReport(
            passed=False,
            checked_count=0,
            broken_count=0,
            error=True,
            error_message=prereq.error_message,
        )

    # Run linkinator
    cmd = ["linkinator", url, "--format", "json"]
    returncode, stdout, stderr = safe_subprocess_call(
        cmd, context=f"checking {url}", timeout=timeout
    )

    # Handle errors
    if returncode == 127:
        return LinkCheckReport(
            passed=False, checked_count=0, broken_count=0, error=True, error_message=stderr
        )
    if returncode == 124:
        return LinkCheckReport(
            passed=False,
            checked_count=0,
            broken_count=0,
            error=True,
            error_message=f"Timeout after {timeout}s",
        )
    if returncode != 0 and not stdout:
        return LinkCheckReport(
            passed=False,
            checked_count=0,
            broken_count=0,
            error=True,
            error_message=stderr or f"Linkinator failed with exit code {returncode}",
        )

    # Parse output
    try:
        report = parse_linkinator_output(stdout)
        return report
    except ValueError as e:
        return LinkCheckReport(
            passed=False, checked_count=0, broken_count=0, error=True, error_message=str(e)
        )


def check_local(path: Path, timeout: int = 120) -> LinkCheckReport:
    """Check local documentation for broken links.

    Args:
        path: Path to check (file or directory)
        timeout: Timeout in seconds (default: 120)

    Returns:
        LinkCheckReport with results
    """
    # Validate path exists
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    # Convert to absolute path
    abs_path = path.resolve()

    # Check prerequisites
    prereq = check_prerequisites()
    if not prereq.linkinator_available:
        return LinkCheckReport(
            passed=False,
            checked_count=0,
            broken_count=0,
            error=True,
            error_message=prereq.error_message,
        )

    # Run linkinator with file:// URL
    file_url = f"file://{abs_path}"
    cmd = ["linkinator", file_url, "--format", "json"]
    returncode, stdout, stderr = safe_subprocess_call(
        cmd, context=f"checking {abs_path}", timeout=timeout
    )

    # Handle errors
    if returncode == 127:
        return LinkCheckReport(
            passed=False, checked_count=0, broken_count=0, error=True, error_message=stderr
        )
    if returncode == 124:
        return LinkCheckReport(
            passed=False,
            checked_count=0,
            broken_count=0,
            error=True,
            error_message=f"Timeout after {timeout}s",
        )
    if returncode != 0 and not stdout:
        return LinkCheckReport(
            passed=False,
            checked_count=0,
            broken_count=0,
            error=True,
            error_message=stderr or f"Linkinator failed with exit code {returncode}",
        )

    # Parse output
    try:
        report = parse_linkinator_output(stdout)
        return report
    except ValueError as e:
        return LinkCheckReport(
            passed=False, checked_count=0, broken_count=0, error=True, error_message=str(e)
        )


# =============================================================================
# CLI INTERFACE
# =============================================================================


def main():
    """CLI entry point for link checker."""
    if len(sys.argv) < 2:
        print("Usage: python link_checker.py <url-or-path>")
        print("")
        print("Examples:")
        print("  python link_checker.py https://example.com")
        print("  python link_checker.py /path/to/docs")
        sys.exit(2)

    target = sys.argv[1]

    # Determine if target is URL or path
    if target.startswith(("http://", "https://")):
        print(f"Checking website: {target}")
        report = check_site(target)
    else:
        path = Path(target)
        print(f"Checking local path: {path}")
        report = check_local(path)

    # Print report
    print(format_report(report))

    # Exit with appropriate code
    sys.exit(get_exit_code(report))


if __name__ == "__main__":
    main()


__all__ = [
    "BrokenLink",
    "LinkCheckReport",
    "check_site",
    "check_local",
    "format_report",
    "get_exit_code",
]
