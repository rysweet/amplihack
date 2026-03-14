#!/usr/bin/env python3
"""Comprehensive link checker for documentation and GitHub Pages.

Validates:
- Internal markdown links (relative paths)
- Anchor references (#section-name)
- External HTTP/HTTPS links
- GitHub Pages URLs
- Image and asset references

Security notes:
- Uses environment variables for configuration
- Rate limits external requests to avoid abuse
- No user input is processed (reads only from repository files)
- SSRF protection: blocks requests to internal/private IPs
"""

import ipaddress
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import requests

# Configuration
DOCS_DIRS = ["docs", ".claude", "Specs"]
MARKDOWN_EXTENSIONS = [".md", ".mdx"]
REQUEST_TIMEOUT = 10
RATE_LIMIT_DELAY = 0.5  # seconds between external requests

# Security: Hosts that should never be accessed (SSRF protection)
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

# Patterns
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
ANCHOR_PATTERN = re.compile(r"^#+\s+(.+)$", re.MULTILINE)
IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def is_safe_url(url: str) -> tuple[bool, str]:
    """Validate URL is safe to request (SSRF protection).

    Returns (is_safe, error_message).
    """
    try:
        parsed = urlparse(url)

        # Check for blocked hostnames
        hostname = parsed.hostname
        if hostname is None:
            return False, "Invalid URL: no hostname"

        if hostname.lower() in BLOCKED_HOSTS:
            return False, f"Blocked host: {hostname}"

        # Check for private/internal IP addresses
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved:
                return False, f"Private/internal IP not allowed: {hostname}"
        except ValueError:
            # Not an IP address, that's fine (it's a hostname)
            pass

        # Check for valid schemes
        if parsed.scheme not in ("http", "https"):
            return False, f"Invalid scheme: {parsed.scheme}"

        return True, ""

    except (ValueError, AttributeError) as e:
        return False, f"URL validation error: {e}"


@dataclass
class BrokenLink:
    """Represents a broken link found during validation."""

    file: str
    line: int
    link_text: str
    link_url: str
    error: str
    severity: str = "error"  # error, warning, info


@dataclass
class LinkCheckResult:
    """Results of link checking operation."""

    total_links: int = 0
    valid_links: int = 0
    broken_links: list[BrokenLink] = field(default_factory=list)
    warnings: list[BrokenLink] = field(default_factory=list)
    skipped: int = 0


def slugify(text: str) -> str:
    """Convert heading text to anchor slug (GitHub style)."""
    # Remove special characters, lowercase, replace spaces with hyphens
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    return slug


def extract_anchors(content: str) -> set[str]:
    """Extract all anchor targets from markdown content."""
    anchors = set()
    for match in ANCHOR_PATTERN.finditer(content):
        heading = match.group(1).strip()
        anchors.add(slugify(heading))
    return anchors


def extract_links(content: str, file_path: Path) -> list[tuple[int, str, str]]:
    """Extract all links from markdown content with line numbers."""
    links = []
    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        # Regular links
        for match in MARKDOWN_LINK_PATTERN.finditer(line):
            link_text = match.group(1)
            link_url = match.group(2)
            links.append((line_num, link_text, link_url))

        # Image links
        for match in IMAGE_PATTERN.finditer(line):
            alt_text = match.group(1)
            image_url = match.group(2)
            links.append((line_num, f"[image: {alt_text}]", image_url))

    return links


def check_internal_link(link_url: str, source_file: Path, repo_root: Path) -> str | None:
    """Check if internal link target exists."""
    # Handle anchor-only links
    if link_url.startswith("#"):
        return check_anchor_in_file(link_url[1:], source_file)

    # Split URL and anchor
    if "#" in link_url:
        path_part, anchor = link_url.split("#", 1)
    else:
        path_part, anchor = link_url, None

    # Skip external links
    if path_part.startswith(("http://", "https://", "mailto:", "tel:")):
        return None

    # Resolve relative path
    if path_part.startswith("/"):
        target_path = repo_root / path_part.lstrip("/")
    else:
        target_path = source_file.parent / path_part

    # Normalize path
    try:
        target_path = target_path.resolve()
    except (ValueError, OSError):
        return f"Invalid path: {link_url}"

    # Check if file exists
    if not target_path.exists():
        # Try with .md extension
        if not target_path.suffix and (target_path.with_suffix(".md")).exists():
            target_path = target_path.with_suffix(".md")
        else:
            return f"File not found: {path_part}"

    # Case-sensitive check: verify the resolved path matches exactly
    # On case-insensitive filesystems (macOS), we need to check the actual directory listing
    if target_path.exists():
        parent_dir = target_path.parent
        expected_name = Path(path_part).name

        # Get actual files in directory
        try:
            actual_files = {f.name for f in parent_dir.iterdir() if f.is_file()}

            # Check if the exact case matches
            if expected_name not in actual_files:
                # Find case-insensitive match
                for actual_name in actual_files:
                    if actual_name.lower() == expected_name.lower():
                        return f"Case mismatch: found {actual_name}, link says {expected_name}"
        except (OSError, PermissionError):
            # If we can't read the directory, just continue
            pass

    # Check anchor if present
    if anchor and target_path.suffix in MARKDOWN_EXTENSIONS:
        return check_anchor_in_file(anchor, target_path)

    return None


def check_anchor_in_file(anchor: str, file_path: Path) -> str | None:
    """Check if anchor exists in markdown file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        anchors = extract_anchors(content)

        # Normalize anchor for comparison
        normalized_anchor = slugify(anchor)

        if normalized_anchor not in anchors:
            return f"Anchor not found: #{anchor}"
    except (OSError, UnicodeDecodeError) as e:
        return f"Could not read file for anchor check: {e}"

    return None


def check_external_link(url: str) -> tuple[str | None, str]:
    """Check if external URL is accessible. Returns (error, severity)."""
    # SSRF protection: validate URL before making request
    is_safe, error_msg = is_safe_url(url)
    if not is_safe:
        return f"Unsafe URL: {error_msg}", "error"

    try:
        response = requests.head(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,  # Don't follow redirects so we can detect them
            headers={"User-Agent": "Mozilla/5.0 (Link Checker Bot)"},
        )

        if response.status_code == 200:
            return None, "ok"
        if response.status_code in (301, 302, 307, 308):
            return f"Redirects to: {response.headers.get('Location', 'unknown')}", "warning"
        if response.status_code == 403:
            return "Access forbidden (may require authentication)", "warning"
        if response.status_code == 404:
            return "Page not found (404)", "error"
        if response.status_code == 429:
            return "Rate limited - skipped", "info"
        return f"HTTP {response.status_code}", "error"

    except requests.exceptions.Timeout:
        return "Request timed out", "warning"
    except requests.exceptions.SSLError as e:
        return f"SSL certificate error: {str(e)[:40]}", "warning"
    except requests.exceptions.ConnectionError as e:
        return f"Connection failed: {str(e)[:40]}", "error"
    except requests.exceptions.RequestException as e:
        return f"Request error: {str(e)[:40]}", "error"


def find_markdown_files(repo_root: Path) -> list[Path]:
    """Find all markdown files in documentation directories."""
    files = []

    for docs_dir in DOCS_DIRS:
        dir_path = repo_root / docs_dir
        if dir_path.exists():
            for ext in MARKDOWN_EXTENSIONS:
                files.extend(dir_path.rglob(f"*{ext}"))

    # Also check root-level markdown files
    for ext in MARKDOWN_EXTENSIONS:
        files.extend(repo_root.glob(f"*{ext}"))

    return sorted(set(files))


def check_all_links(repo_root: Path) -> LinkCheckResult:
    """Check all links in all markdown files."""
    result = LinkCheckResult()
    checked_external = {}  # Cache for external URL results

    markdown_files = find_markdown_files(repo_root)
    print(f"Found {len(markdown_files)} markdown files to check")

    for file_path in markdown_files:
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  Error reading {file_path}: {e}")
            continue

        links = extract_links(content, file_path)
        relative_path = str(file_path.relative_to(repo_root))

        for line_num, link_text, link_url in links:
            result.total_links += 1

            # Skip empty links
            if not link_url or link_url.isspace():
                result.skipped += 1
                continue

            # Skip special protocols
            if link_url.startswith(("mailto:", "tel:", "javascript:", "data:")):
                result.skipped += 1
                continue

            # Check internal vs external links
            if link_url.startswith(("http://", "https://")):
                # External link - use cache
                if link_url in checked_external:
                    error, severity = checked_external[link_url]
                else:
                    time.sleep(RATE_LIMIT_DELAY)  # Rate limit
                    error, severity = check_external_link(link_url)
                    checked_external[link_url] = (error, severity)

                if error:
                    broken = BrokenLink(
                        file=relative_path,
                        line=line_num,
                        link_text=link_text,
                        link_url=link_url,
                        error=error,
                        severity=severity,
                    )
                    if severity == "error":
                        result.broken_links.append(broken)
                    else:
                        result.warnings.append(broken)
                else:
                    result.valid_links += 1
            else:
                # Internal link
                error = check_internal_link(link_url, file_path, repo_root)
                if error:
                    result.broken_links.append(
                        BrokenLink(
                            file=relative_path,
                            line=line_num,
                            link_text=link_text,
                            link_url=link_url,
                            error=error,
                            severity="error",
                        )
                    )
                else:
                    result.valid_links += 1

    return result


def generate_report(result: LinkCheckResult) -> str:
    """Generate markdown report of broken links."""
    lines = [
        "## Broken Links Report",
        "",
        f"**Scan Date**: {time.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "### Summary",
        "",
        f"- Total links checked: {result.total_links}",
        f"- Valid links: {result.valid_links}",
        f"- Broken links: {len(result.broken_links)}",
        f"- Warnings: {len(result.warnings)}",
        f"- Skipped: {result.skipped}",
        "",
    ]

    if result.broken_links:
        lines.extend(
            [
                "### Broken Links (Errors)",
                "",
                "| File | Line | Link | Error |",
                "|------|------|------|-------|",
            ]
        )
        for link in result.broken_links:
            lines.append(f"| `{link.file}` | {link.line} | `{link.link_url[:50]}` | {link.error} |")
        lines.append("")

    if result.warnings:
        lines.extend(
            [
                "### Warnings",
                "",
                "| File | Line | Link | Warning |",
                "|------|------|------|---------|",
            ]
        )
        for link in result.warnings[:20]:  # Limit warnings
            lines.append(f"| `{link.file}` | {link.line} | `{link.link_url[:50]}` | {link.error} |")
        if len(result.warnings) > 20:
            lines.append(f"| ... | ... | *{len(result.warnings) - 20} more warnings* | ... |")
        lines.append("")

    lines.extend(
        [
            "---",
            "🤖 Generated by automated link checker",
        ]
    )

    return "\n".join(lines)


class LinkChecker:
    """Wrapper class for link checking functionality."""

    def __init__(self, repo_path: Path | None = None):
        """Initialize with repository path."""
        self.repo_path = repo_path or Path.cwd()

    def check_all(self) -> list[dict]:
        """Check all links and return broken links as list of dicts."""
        result = check_all_links(self.repo_path)

        # Convert BrokenLink dataclasses to dicts for test compatibility
        broken_links = []
        for link in result.broken_links:
            broken_links.append(
                {
                    "file": link.file,
                    "line": link.line,
                    "text": link.link_text,
                    "path": link.link_url,
                    "error": link.error,
                    "severity": link.severity,
                }
            )

        return broken_links


def main() -> int:
    """Main entry point."""
    repo_root = Path.cwd()

    print("Starting link check...")
    result = check_all_links(repo_root)

    print("\nResults:")
    print(f"  Total: {result.total_links}")
    print(f"  Valid: {result.valid_links}")
    print(f"  Broken: {len(result.broken_links)}")
    print(f"  Warnings: {len(result.warnings)}")

    if result.broken_links or result.warnings:
        report = generate_report(result)
        try:
            Path("broken_links_report.md").write_text(report)
            print("\nReport written to broken_links_report.md")
        except OSError as e:
            print(f"\nError writing report: {e}", file=sys.stderr)
            # Still print report to stdout so workflow can capture it
            print("\n--- Report follows ---")
            print(report)

    return 0  # Always succeed - let workflow handle issue creation


if __name__ == "__main__":
    sys.exit(main())
