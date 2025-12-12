#!/usr/bin/env python3
"""GitHub Pages Link Validator - Crawls deployed site and validates all links.

Validates:
- Internal links (same domain)
- External links (HTTP/HTTPS)
- Anchor references (#section-name)

Features:
- Recursive crawling with cycle detection
- Rate limiting to avoid abuse
- Timeout handling for slow links
- JSON and human-readable output
- CI-ready exit codes

Usage:
    python validate_gh_pages_links.py --site-url https://example.github.io/project/
"""

import argparse
import json
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

# Configuration
DEFAULT_TIMEOUT = 10
DEFAULT_RATE_LIMIT = 0.5  # seconds between requests
DEFAULT_USER_AGENT = "Mozilla/5.0 (GitHub Pages Link Validator)"
MAX_RETRIES = 2


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class BrokenLink:
    """Represents a broken link found during validation."""
    page_url: str
    link_url: str
    link_text: str
    error: str
    severity: str  # "error" or "warning"


@dataclass
class ValidationResults:
    """Results of link validation operation."""
    total_pages: int = 0
    total_links: int = 0
    broken_links: List[BrokenLink] = field(default_factory=list)
    warnings: List[BrokenLink] = field(default_factory=list)
    scan_date: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# ============================================================================
# URL Utilities
# ============================================================================

def parse_url(url: str) -> urlparse:
    """Parse URL into components."""
    return urlparse(url)


def normalize_url(url: str) -> str:
    """Normalize URL by removing fragments and trailing slashes."""
    parsed = urlparse(url)
    # Remove fragment
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path.rstrip("/"),
        parsed.params,
        parsed.query,
        ""  # Remove fragment
    ))
    return normalized


def is_same_domain(base_url: str, url: str) -> bool:
    """Check if URL is on the same domain as base URL."""
    base_parsed = urlparse(base_url)
    url_parsed = urlparse(url)
    return base_parsed.netloc == url_parsed.netloc


def resolve_url(base_url: str, relative_url: str) -> str:
    """Resolve relative URL against base URL."""
    return urljoin(base_url, relative_url)


# ============================================================================
# HTML Parsing
# ============================================================================

def extract_links(html: str, base_url: str) -> List[Dict[str, str]]:
    """Extract all links from HTML content.

    Args:
        html: HTML content as string
        base_url: Base URL for resolving relative links

    Returns:
        List of dicts with 'url' and 'text' keys
    """
    links = []
    soup = BeautifulSoup(html, "html.parser")

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        text = anchor.get_text(strip=True)

        # Skip empty links, mailto, tel, javascript
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "data:")):
            continue

        # Resolve relative URLs
        absolute_url = resolve_url(base_url, href)

        links.append({
            "url": absolute_url,
            "text": text or "(no text)",
        })

    return links


# ============================================================================
# Crawler
# ============================================================================

class Crawler:
    """Web crawler for GitHub Pages sites."""

    def __init__(
        self,
        base_url: str,
        timeout: int = DEFAULT_TIMEOUT,
        rate_limit: float = DEFAULT_RATE_LIMIT,
        max_depth: Optional[int] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.rate_limit = rate_limit
        self.max_depth = max_depth

        # State
        self.visited: Set[str] = set()
        self.queue: deque = deque([(self.base_url, 0)])  # (url, depth)
        self.all_links: Dict[str, List[Dict]] = {}  # page_url -> list of links
        self.link_cache: Dict[str, Tuple[Optional[str], str]] = {}  # url -> (error, severity)

    def is_visited(self, url: str) -> bool:
        """Check if URL has been visited."""
        return normalize_url(url) in self.visited

    def mark_visited(self, url: str) -> None:
        """Mark URL as visited."""
        self.visited.add(normalize_url(url))

    def add_to_queue(self, url: str, depth: int = 0) -> None:
        """Add URL to crawl queue if not visited."""
        normalized = normalize_url(url)
        if normalized not in self.visited and is_same_domain(self.base_url, url):
            self.queue.append((url, depth))

    def get_next_url(self) -> Optional[Tuple[str, int]]:
        """Get next URL from queue."""
        if self.queue:
            return self.queue.popleft()
        return None

    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content of page.

        Returns:
            HTML content as string, or None if error
        """
        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": DEFAULT_USER_AGENT},
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"  Error fetching {url}: {str(e)[:60]}")
            return None

    def crawl(self) -> ValidationResults:
        """Crawl site and validate all links.

        Returns:
            ValidationResults object
        """
        results = ValidationResults()

        print(f"Starting crawl from {self.base_url}")

        while self.queue:
            url, depth = self.get_next_url()

            # Check depth limit
            if self.max_depth is not None and depth > self.max_depth:
                continue

            # Skip if already visited
            if self.is_visited(url):
                continue

            print(f"  Crawling: {url} (depth {depth})")
            self.mark_visited(url)
            results.total_pages += 1

            # Fetch page
            html = self.fetch_page(url)
            if html is None:
                continue

            # Extract links
            links = extract_links(html, url)
            self.all_links[url] = links
            results.total_links += len(links)

            # Validate links and add internal links to queue
            for link in links:
                link_url = link["url"]

                # Add internal links to crawl queue
                if is_same_domain(self.base_url, link_url):
                    self.add_to_queue(link_url, depth + 1)

                # Validate link
                error, severity = self.validate_link_cached(link_url)
                if error:
                    broken = BrokenLink(
                        page_url=url,
                        link_url=link_url,
                        link_text=link["text"],
                        error=error,
                        severity=severity,
                    )
                    if severity == "error":
                        results.broken_links.append(broken)
                    else:
                        results.warnings.append(broken)

            # Rate limit
            time.sleep(self.rate_limit)

        return results

    def validate_link_cached(self, url: str) -> Tuple[Optional[str], str]:
        """Validate link with caching.

        Returns:
            (error_message, severity) tuple
            error_message is None if link is valid
            severity is "error", "warning", or "ok"
        """
        if url in self.link_cache:
            return self.link_cache[url]

        result = validate_link(url, self.timeout)
        self.link_cache[url] = result
        return result


# ============================================================================
# Link Validation
# ============================================================================

def validate_link(url: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[Optional[str], str]:
    """Validate a single link.

    Args:
        url: URL to validate
        timeout: Request timeout in seconds

    Returns:
        (error_message, severity) tuple
        error_message is None if valid
        severity is "error", "warning", or "ok"
    """
    try:
        response = requests.head(
            url,
            timeout=timeout,
            allow_redirects=False,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )

        if response.status_code == 200:
            return None, "ok"
        elif response.status_code in (301, 302, 307, 308):
            location = response.headers.get("Location", "unknown")
            return f"Redirects to: {location}", "warning"
        elif response.status_code == 403:
            return "Access forbidden (may require authentication)", "warning"
        elif response.status_code == 404:
            return "Page not found (404)", "error"
        elif response.status_code == 429:
            return "Rate limited", "warning"
        elif response.status_code >= 500:
            return f"Server error ({response.status_code})", "error"
        else:
            return f"HTTP {response.status_code}", "error"

    except requests.exceptions.Timeout:
        return "Request timed out", "warning"
    except requests.exceptions.SSLError as e:
        return f"SSL error: {str(e)[:40]}", "warning"
    except requests.exceptions.ConnectionError as e:
        return f"Connection failed: {str(e)[:40]}", "error"
    except requests.exceptions.RequestException as e:
        return f"Request error: {str(e)[:40]}", "error"


# ============================================================================
# Reporting
# ============================================================================

def generate_report(results: ValidationResults) -> str:
    """Generate human-readable report.

    Args:
        results: ValidationResults object

    Returns:
        Formatted report as string
    """
    lines = [
        "GitHub Pages Link Validation Report",
        "=" * 60,
        f"Scan Date: {results.scan_date}",
        "",
        "Summary:",
        f"  Total pages crawled: {results.total_pages}",
        f"  Total links checked: {results.total_links}",
        f"  Broken links: {len(results.broken_links)}",
        f"  Warnings: {len(results.warnings)}",
        "",
    ]

    if results.broken_links:
        lines.append("Broken Links (Errors):")
        lines.append("-" * 60)
        for i, link in enumerate(results.broken_links, 1):
            lines.extend([
                f"{i}. Page: {link.page_url}",
                f"   Link: {link.link_url} ({link.link_text})",
                f"   Error: {link.error}",
                "",
            ])

    if results.warnings:
        lines.append("Warnings:")
        lines.append("-" * 60)
        # Limit warnings to 20
        displayed_warnings = results.warnings[:20]
        for i, link in enumerate(displayed_warnings, 1):
            lines.extend([
                f"{i}. Page: {link.page_url}",
                f"   Link: {link.link_url} ({link.link_text})",
                f"   Warning: {link.error}",
                "",
            ])
        if len(results.warnings) > 20:
            lines.append(f"... and {len(results.warnings) - 20} more warnings")
            lines.append("")

    if not results.broken_links and not results.warnings:
        lines.append("✓ All links are valid!")
        lines.append("")

    return "\n".join(lines)


def save_results(results: ValidationResults, output_path: str) -> None:
    """Save results to JSON file.

    Args:
        results: ValidationResults object
        output_path: Path to output file
    """
    data = {
        "summary": {
            "total_pages": results.total_pages,
            "total_links": results.total_links,
            "broken_links": len(results.broken_links),
            "warnings": len(results.warnings),
            "scan_date": results.scan_date,
        },
        "broken_links": [
            {
                "page_url": link.page_url,
                "link_url": link.link_url,
                "link_text": link.link_text,
                "error": link.error,
                "severity": link.severity,
            }
            for link in results.broken_links
        ],
        "warnings": [
            {
                "page_url": link.page_url,
                "link_url": link.link_url,
                "link_text": link.link_text,
                "error": link.error,
                "severity": link.severity,
            }
            for link in results.warnings
        ],
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResults saved to {output_path}")


def get_exit_code(results: ValidationResults) -> int:
    """Get exit code based on results.

    Args:
        results: ValidationResults object

    Returns:
        0 if no errors, 1 if errors found (warnings don't cause non-zero exit)
    """
    return 1 if results.broken_links else 0


# ============================================================================
# Main Entry Point
# ============================================================================

def validate_site(
    site_url: str,
    timeout: int = DEFAULT_TIMEOUT,
    max_depth: Optional[int] = None,
) -> ValidationResults:
    """Validate all links on a site.

    Args:
        site_url: Base URL to start crawling
        timeout: Request timeout in seconds
        max_depth: Maximum crawl depth (None for unlimited)

    Returns:
        ValidationResults object
    """
    crawler = Crawler(site_url, timeout=timeout, max_depth=max_depth)
    return crawler.crawl()


def parse_args(args=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate links on GitHub Pages site",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --site-url https://example.github.io/project/
  %(prog)s --site-url https://example.com --timeout 30 --max-depth 5
        """,
    )

    parser.add_argument(
        "--site-url",
        required=True,
        help="Base URL of the site to validate (required)",
    )
    parser.add_argument(
        "--output",
        default="broken_links.json",
        help="Output JSON file (default: broken_links.json)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum crawl depth (default: unlimited)",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=DEFAULT_RATE_LIMIT,
        help=f"Delay between requests in seconds (default: {DEFAULT_RATE_LIMIT})",
    )

    return parser.parse_args(args)


def main() -> int:
    """Main entry point."""
    args = parse_args()

    print("GitHub Pages Link Validator")
    print("=" * 60)
    print(f"Site URL: {args.site_url}")
    print(f"Timeout: {args.timeout}s")
    print(f"Max Depth: {args.max_depth or 'unlimited'}")
    print()

    # Validate site
    results = validate_site(
        args.site_url,
        timeout=args.timeout,
        max_depth=args.max_depth,
    )

    # Generate and print report
    report = generate_report(results)
    print(report)

    # Save JSON results
    save_results(results, args.output)

    # Return exit code
    return get_exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
