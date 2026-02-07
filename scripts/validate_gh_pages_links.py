#!/usr/bin/env python3
"""GitHub Pages Link Validator - Crawls deployed site and validates all links.

This validator supports two modes:
1. Web crawling mode: Crawls deployed GitHub Pages sites (original functionality)
2. Local file mode: Validates links in local markdown files (new functionality)

Validates:
- Internal links (same domain or relative file paths)
- External links (HTTP/HTTPS)
- Anchor references (#section-name)

Security Features:
- Path traversal attack prevention
- SSRF (Server-Side Request Forgery) prevention
- Markdown injection detection
- Strict internal vs pragmatic external validation modes

Features:
- Recursive crawling with cycle detection (web mode)
- Rate limiting to avoid abuse (web mode)
- Timeout handling for slow links
- JSON and human-readable output
- CI-ready exit codes

Usage:
    # Web crawling mode
    python validate_gh_pages_links.py --site-url https://example.github.io/project/

    # Local file validation mode
    python validate_gh_pages_links.py --local docs/README.md --strict
    python validate_gh_pages_links.py --local docs/ --pragmatic --skip-external
"""

import argparse
import ipaddress
import json
import logging
import re
import socket
import sys
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

__all__ = [
    "LinkValidator",
    "Crawler",
    "ValidationMode",
    "LinkValidationResult",
    "ValidationResults",
    "BrokenLink",
    "PathTraversalError",
    "SSRFError",
    "MarkdownInjectionError",
    "CircuitBreakerOpenError",
    "validate_site",
    "validate_local",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
DEFAULT_TIMEOUT = 10
DEFAULT_RATE_LIMIT = 0.5  # seconds between requests
DEFAULT_USER_AGENT = "Mozilla/5.0 (GitHub Pages Link Validator)"
MAX_RETRIES = 3  # Number of retry attempts
RETRY_BACKOFF_FACTOR = 2  # Exponential backoff multiplier
RETRY_INITIAL_DELAY = 1  # Initial retry delay in seconds
MAX_REDIRECTS = 3
CIRCUIT_BREAKER_THRESHOLD = 5  # Failed requests before circuit opens
CIRCUIT_BREAKER_TIMEOUT = 30  # Seconds before circuit half-opens

# Private network ranges for SSRF prevention
PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # Private
    ipaddress.ip_network("172.16.0.0/12"),  # Private
    ipaddress.ip_network("192.168.0.0/16"),  # Private
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local (AWS metadata)
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
]

# Markdown injection patterns (pre-compiled for performance)
INJECTION_PATTERNS = [
    re.compile(r"<script[>\s]", re.IGNORECASE),
    re.compile(r"<iframe[>\s]", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"data:text/html", re.IGNORECASE),
    re.compile(r"\bon\w+\s*=", re.IGNORECASE),  # Event handlers: onclick, onerror, etc.
]

# Additional compiled patterns for markdown parsing
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^\)]+)\)")


# ============================================================================
# Retry Logic with Exponential Backoff
# ============================================================================


def retry_with_backoff(
    max_retries: int = MAX_RETRIES,
    initial_delay: float = RETRY_INITIAL_DELAY,
    backoff_factor: float = RETRY_BACKOFF_FACTOR,
    retryable_exceptions: tuple = (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    ),
) -> Callable:
    """Decorator to retry function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for exponential backoff
        retryable_exceptions: Tuple of exceptions to retry on

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed. Last error: {e}")
                except Exception as e:
                    # Non-retryable exception - fail immediately
                    logger.error(f"Non-retryable error: {e}")
                    raise

            # All retries exhausted
            if last_exception:
                raise last_exception
            return None

        return wrapper

    return decorator


# ============================================================================
# Circuit Breaker Pattern
# ============================================================================


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """

    def __init__(
        self,
        failure_threshold: int = CIRCUIT_BREAKER_THRESHOLD,
        timeout: int = CIRCUIT_BREAKER_TIMEOUT,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds before attempting to half-open circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Too many failures. Will retry after {self.timeout}s."
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        elapsed = datetime.now() - self.last_failure_time
        return elapsed > timedelta(seconds=self.timeout)

    def _on_success(self) -> None:
        """Handle successful request."""
        if self.state == "HALF_OPEN":
            logger.info("Circuit breaker recovered, returning to CLOSED state")
            self.state = "CLOSED"
            self.failure_count = 0
            self.last_failure_time = None

    def _on_failure(self) -> None:
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            if self.state != "OPEN":
                logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
                self.state = "OPEN"


# Global circuit breaker instance for external link validation
external_link_circuit_breaker = CircuitBreaker()


# ============================================================================
# Custom Exceptions
# ============================================================================


class PathTraversalError(Exception):
    """Raised when path traversal attack is detected."""


class SSRFError(Exception):
    """Raised when SSRF attack is detected."""


class MarkdownInjectionError(Exception):
    """Raised when markdown injection is detected."""


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is in open state."""


# ============================================================================
# Enums
# ============================================================================


class ValidationMode(str, Enum):
    """Validation mode for link checking."""

    STRICT = "strict"  # Internal links must exist, errors block workflow
    PRAGMATIC = "pragmatic"  # External 404/410 block, 5xx/timeout warn only


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
    broken_links: list[BrokenLink] = field(default_factory=list)
    warnings: list[BrokenLink] = field(default_factory=list)
    scan_date: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class LinkValidationResult:
    """Result of validating a single file."""

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# ============================================================================
# Security Utilities
# ============================================================================


def is_private_ip(ip_str: str) -> bool:
    """Check if IP address is in private range.

    Args:
        ip_str: IP address as string

    Returns:
        True if IP is in private range
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in PRIVATE_NETWORKS)
    except ValueError:
        return False


def check_ssrf(url: str) -> None:
    """Check URL for SSRF vulnerabilities.

    Args:
        url: URL to check

    Raises:
        SSRFError: If URL points to private network
    """
    parsed = urlparse(url)

    # Only check http/https URLs
    if parsed.scheme not in ("http", "https"):
        return

    hostname = parsed.hostname
    if not hostname:
        return

    # Check if hostname is localhost
    if hostname.lower() in ("localhost", "0.0.0.0"):
        raise SSRFError(f"Access to localhost not allowed: {hostname}")

    # Resolve DNS to check for private IPs (DNS rebinding protection)
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip = sockaddr[0]
            if is_private_ip(ip):
                raise SSRFError(f"URL resolves to private network address: {hostname} -> {ip}")
    except socket.gaierror:
        # DNS resolution failed - let the request fail naturally
        pass
    except SSRFError:
        raise
    except Exception:
        # Other DNS errors - let the request fail naturally
        pass


def check_path_traversal(base_path: Path, target_path: Path) -> None:
    """Check for path traversal attacks.

    Args:
        base_path: Base repository path
        target_path: Target path to validate

    Raises:
        PathTraversalError: If path traversal detected
    """
    # Resolve to canonical absolute paths
    try:
        base_resolved = base_path.resolve()
        target_resolved = target_path.resolve()
    except Exception as e:
        raise PathTraversalError(f"Failed to resolve path: {e}")

    # Check if target is within base (is_relative_to in Python 3.9+)
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError:
        raise PathTraversalError(
            f"Path escapes repository: {target_path} resolves outside {base_path}"
        )

    # Check for symlinks that point outside repository
    if target_path.is_symlink():
        link_target = target_path.readlink()
        if link_target.is_absolute():
            raise PathTraversalError(f"Symlink points to absolute path: {link_target}")

        # Resolve symlink and check again
        symlink_resolved = (target_path.parent / link_target).resolve()
        try:
            symlink_resolved.relative_to(base_resolved)
        except ValueError:
            raise PathTraversalError(f"Symlink escapes repository: {target_path} -> {link_target}")


def check_markdown_injection(content: str) -> list[str]:
    """Check markdown content for injection attacks.

    Args:
        content: Markdown content to check

    Returns:
        List of detected injection patterns (empty if safe)
    """
    detected = []

    for pattern in INJECTION_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            detected.append(f"Potential injection: {matches[0][:50]}")

    return detected


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
    normalized = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/"),
            parsed.params,
            parsed.query,
            "",  # Remove fragment
        )
    )
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


def extract_links(html: str, base_url: str) -> list[dict[str, str]]:
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

        links.append(
            {
                "url": absolute_url,
                "text": text or "(no text)",
            }
        )

    return links


def extract_anchors_from_markdown(markdown_path: Path) -> set[str]:
    """Extract all heading anchors from markdown file.

    Args:
        markdown_path: Path to markdown file

    Returns:
        Set of anchor names (lowercase, with dashes)
    """
    anchors = set()

    try:
        content = markdown_path.read_text(encoding="utf-8")
    except Exception:
        return anchors

    # Use pre-compiled pattern from module level
    for match in HEADING_PATTERN.finditer(content):
        heading_text = match.group(1).strip()

        # Convert heading to anchor format (GitHub style)
        # Example: "My Heading" -> "my-heading"
        anchor = heading_text.lower()
        anchor = re.sub(r"[^\w\s-]", "", anchor)  # Remove special chars
        anchor = re.sub(r"[\s_]+", "-", anchor)  # Replace spaces/underscores with dash
        anchor = anchor.strip("-")  # Remove leading/trailing dashes

        anchors.add(anchor)

    return anchors


def extract_links_from_markdown(markdown_path: Path) -> list[dict[str, str]]:
    """Extract all links from markdown file.

    Args:
        markdown_path: Path to markdown file

    Returns:
        List of dicts with 'url', 'text', and 'line' keys
    """
    links = []

    try:
        content = markdown_path.read_text(encoding="utf-8")
    except Exception:
        return links

    # Use pre-compiled pattern from module level
    for line_num, line in enumerate(content.split("\n"), 1):
        for match in LINK_PATTERN.finditer(line):
            text = match.group(1)
            url = match.group(2).strip()

            # Skip empty URLs
            if not url:
                continue

            links.append(
                {
                    "url": url,
                    "text": text or "(no text)",
                    "line": line_num,
                }
            )

    return links


# ============================================================================
# Local File Link Validator
# ============================================================================


class LinkValidator:
    """Validates links in local markdown files."""

    def __init__(
        self,
        base_path: Path,
        mode: ValidationMode = ValidationMode.STRICT,
        timeout: int = DEFAULT_TIMEOUT,
        skip_external: bool = False,
    ):
        """Initialize validator.

        Args:
            base_path: Base repository path
            mode: Validation mode (STRICT or PRAGMATIC)
            timeout: Timeout for external requests
            skip_external: Skip external link validation
        """
        self.base_path = base_path.resolve()
        self.mode = mode
        self.timeout = timeout
        self.skip_external = skip_external

    def validate_file(self, markdown_path: Path) -> LinkValidationResult:
        """Validate all links in a markdown file.

        Args:
            markdown_path: Path to markdown file

        Returns:
            LinkValidationResult
        """
        result = LinkValidationResult(success=True)

        if not markdown_path.exists():
            result.success = False
            result.errors.append(f"File not found: {markdown_path}")
            return result

        # Check for markdown injection in file content
        try:
            content = markdown_path.read_text(encoding="utf-8")
            injection_warnings = check_markdown_injection(content)
            result.warnings.extend(injection_warnings)
        except Exception as e:
            result.errors.append(f"Failed to read file: {e}")
            result.success = False
            return result

        # Extract links
        links = extract_links_from_markdown(markdown_path)

        for link in links:
            url = link["url"]
            line = link.get("line", 0)

            # Validate link
            error, severity = self._validate_link(markdown_path, url)

            if error:
                error_msg = f"Line {line}: {error}"
                if severity == "error":
                    result.errors.append(error_msg)
                    result.success = False
                else:
                    result.warnings.append(error_msg)

        return result

    def _validate_link(self, source_file: Path, url: str) -> tuple[str | None, str]:
        """Validate a single link.

        Args:
            source_file: Source markdown file containing the link
            url: URL to validate

        Returns:
            (error_message, severity) tuple
            error_message is None if valid
            severity is "error" or "warning"
        """
        parsed = urlparse(url)

        # Check URL scheme
        if parsed.scheme in ("mailto", "tel"):
            return None, "ok"  # Skip these

        if parsed.scheme == "file":
            return (
                "file:// protocol not allowed (unsupported protocol)",
                "error",
            )

        if parsed.scheme in ("javascript", "data"):
            return f"Dangerous protocol: {parsed.scheme}:", "error"

        # External URL (http/https)
        if parsed.scheme in ("http", "https"):
            return self._validate_external_link(url)

        # Internal link (relative path or anchor)
        if parsed.scheme == "":
            return self._validate_internal_link(source_file, url)

        return f"Unsupported URL scheme: {parsed.scheme}", "error"

    def _validate_internal_link(self, source_file: Path, url: str) -> tuple[str | None, str]:
        """Validate internal (relative) link.

        Args:
            source_file: Source markdown file
            url: Relative URL

        Returns:
            (error_message, severity) tuple
        """
        # Split anchor from path
        if "#" in url:
            path_part, anchor = url.split("#", 1)
        else:
            path_part = url
            anchor = None

        # Anchor-only link (same file)
        if not path_part:
            if anchor and self.mode == ValidationMode.STRICT:
                # Validate anchor exists in current file
                anchors = extract_anchors_from_markdown(source_file)
                if anchor not in anchors:
                    return f"Anchor not found: #{anchor}", "error"
            return None, "ok"

        # Check for absolute paths
        if path_part.startswith("/"):
            return "Absolute path in internal link (absolute path not allowed)", "error"

        # Resolve relative path
        target_path = (source_file.parent / path_part).resolve()

        # Check for path traversal
        try:
            check_path_traversal(self.base_path, target_path)
        except PathTraversalError as e:
            return str(e), "error"

        # Check if file exists (STRICT mode)
        if self.mode == ValidationMode.STRICT:
            if not target_path.exists():
                return f"File not found: {path_part}", "error"

            # Validate anchor if present
            if anchor:
                anchors = extract_anchors_from_markdown(target_path)
                if anchor not in anchors:
                    return f"Anchor not found in {path_part}: #{anchor}", "error"

        return None, "ok"

    def _validate_external_link(self, url: str) -> tuple[str | None, str]:
        """Validate external (http/https) link with retry and circuit breaker.

        Args:
            url: External URL

        Returns:
            (error_message, severity) tuple
        """
        if self.skip_external:
            return None, "ok"

        # Check for SSRF vulnerabilities
        try:
            check_ssrf(url)
        except SSRFError as e:
            return str(e), "error"

        # Use circuit breaker to prevent cascading failures
        try:
            return external_link_circuit_breaker.call(self._make_external_request, url)
        except CircuitBreakerOpenError as e:
            # Circuit breaker is open - treat as warning in PRAGMATIC mode
            severity = "warning" if self.mode == ValidationMode.PRAGMATIC else "error"
            return str(e), severity

    def _make_external_request(self, url: str) -> tuple[str | None, str]:
        """Make HTTP request to external URL with retry logic.

        Args:
            url: External URL

        Returns:
            (error_message, severity) tuple
        """

        @retry_with_backoff(
            max_retries=MAX_RETRIES,
            initial_delay=RETRY_INITIAL_DELAY,
            backoff_factor=RETRY_BACKOFF_FACTOR,
        )
        def _do_request():
            return requests.head(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                max_redirects=MAX_REDIRECTS,
                headers={"User-Agent": DEFAULT_USER_AGENT},
                verify=True,  # SSL certificate validation
            )

        # Make HTTP request with retry logic
        try:
            response = _do_request()

            if response.status_code in (200, 201, 202, 203, 204, 205, 206):
                return None, "ok"

            # PRAGMATIC mode: 5xx errors are warnings only
            if self.mode == ValidationMode.PRAGMATIC:
                if response.status_code >= 500:
                    return f"Server error ({response.status_code})", "warning"

            # 404/410 are always errors
            if response.status_code in (404, 410):
                return f"Page not found ({response.status_code})", "error"

            # 3xx redirects (if not followed)
            if response.status_code in (301, 302, 303, 307, 308):
                return f"Redirect ({response.status_code})", "warning"

            # Other 4xx errors
            if response.status_code >= 400:
                return f"Client error ({response.status_code})", "error"

            return f"HTTP {response.status_code}", "warning"

        except requests.exceptions.SSLError as e:
            # PRAGMATIC mode: SSL errors are warnings
            severity = "warning" if self.mode == ValidationMode.PRAGMATIC else "error"
            return f"SSL error: {str(e)[:40]}", severity

        except requests.exceptions.Timeout:
            # PRAGMATIC mode: Timeouts are warnings
            severity = "warning" if self.mode == ValidationMode.PRAGMATIC else "error"
            return "Request timed out", severity

        except requests.exceptions.TooManyRedirects:
            return f"Too many redirects (max {MAX_REDIRECTS})", "error"

        except requests.exceptions.ConnectionError as e:
            # PRAGMATIC mode: Connection errors might be transient
            severity = "warning" if self.mode == ValidationMode.PRAGMATIC else "error"
            return f"Connection failed: {str(e)[:40]}", severity

        except requests.exceptions.RequestException as e:
            return f"Request error: {str(e)[:40]}", "error"


# ============================================================================
# Web Crawler (Original Functionality)
# ============================================================================


class Crawler:
    """Web crawler for GitHub Pages sites."""

    def __init__(
        self,
        base_url: str,
        timeout: int = DEFAULT_TIMEOUT,
        rate_limit: float = DEFAULT_RATE_LIMIT,
        max_depth: int | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.rate_limit = rate_limit
        self.max_depth = max_depth

        # State
        self.visited: set[str] = set()
        self.queue: deque = deque([(self.base_url, 0)])  # (url, depth)
        self.all_links: dict[str, list[dict]] = {}  # page_url -> list of links
        self.link_cache: dict[str, tuple[str | None, str]] = {}  # url -> (error, severity)

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

    def get_next_url(self) -> tuple[str, int] | None:
        """Get next URL from queue."""
        if self.queue:
            return self.queue.popleft()
        return None

    def fetch_page(self, url: str) -> str | None:
        """Fetch HTML content of page with retry logic.

        Returns:
            HTML content as string, or None if error
        """

        @retry_with_backoff(
            max_retries=MAX_RETRIES,
            initial_delay=RETRY_INITIAL_DELAY,
            backoff_factor=RETRY_BACKOFF_FACTOR,
        )
        def _do_request():
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": DEFAULT_USER_AGENT},
            )
            response.raise_for_status()
            return response

        try:
            response = _do_request()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {str(e)[:60]}")
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

    def validate_link_cached(self, url: str) -> tuple[str | None, str]:
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
# Link Validation (Web Crawler)
# ============================================================================


def validate_link(url: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[str | None, str]:
    """Validate a single link with retry logic.

    Args:
        url: URL to validate
        timeout: Request timeout in seconds

    Returns:
        (error_message, severity) tuple
        error_message is None if valid
        severity is "error", "warning", or "ok"
    """

    @retry_with_backoff(
        max_retries=MAX_RETRIES,
        initial_delay=RETRY_INITIAL_DELAY,
        backoff_factor=RETRY_BACKOFF_FACTOR,
    )
    def _do_request():
        return requests.head(
            url,
            timeout=timeout,
            allow_redirects=False,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )

    try:
        response = _do_request()

        if response.status_code == 200:
            return None, "ok"
        if response.status_code in (301, 302, 307, 308):
            location = response.headers.get("Location", "unknown")
            return f"Redirects to: {location}", "warning"
        if response.status_code == 403:
            return "Access forbidden (may require authentication)", "warning"
        if response.status_code == 404:
            return "Page not found (404)", "error"
        if response.status_code == 429:
            return "Rate limited", "warning"
        if response.status_code >= 500:
            return f"Server error ({response.status_code})", "error"
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
            lines.extend(
                [
                    f"{i}. Page: {link.page_url}",
                    f"   Link: {link.link_url} ({link.link_text})",
                    f"   Error: {link.error}",
                    "",
                ]
            )

    if results.warnings:
        lines.append("Warnings:")
        lines.append("-" * 60)
        # Limit warnings to 20
        displayed_warnings = results.warnings[:20]
        for i, link in enumerate(displayed_warnings, 1):
            lines.extend(
                [
                    f"{i}. Page: {link.page_url}",
                    f"   Link: {link.link_url} ({link.link_text})",
                    f"   Warning: {link.error}",
                    "",
                ]
            )
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
    max_depth: int | None = None,
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


def validate_local(
    path: Path,
    mode: ValidationMode = ValidationMode.STRICT,
    timeout: int = DEFAULT_TIMEOUT,
    skip_external: bool = False,
) -> tuple[bool, int, int]:
    """Validate links in local markdown file(s).

    Args:
        path: Path to markdown file or directory
        mode: Validation mode
        timeout: Timeout for external requests
        skip_external: Skip external link validation

    Returns:
        (success, error_count, warning_count) tuple
    """
    validator = LinkValidator(
        base_path=Path.cwd(),
        mode=mode,
        timeout=timeout,
        skip_external=skip_external,
    )

    if path.is_file():
        print(f"Validating: {path}")
        result = validator.validate_file(path)

        for error in result.errors:
            print(f"  ✗ {error}")
        for warning in result.warnings:
            print(f"  ⚠ {warning}")

        if result.success:
            print("  ✓ All links valid")

        return result.success, len(result.errors), len(result.warnings)

    if path.is_dir():
        markdown_files = sorted(path.rglob("*.md"))
        if not markdown_files:
            print(f"No markdown files found in {path}")
            return True, 0, 0

        print(f"Found {len(markdown_files)} markdown file(s)")
        total_errors = 0
        total_warnings = 0
        failed_files = []

        for md_file in markdown_files:
            result = validator.validate_file(md_file)
            total_errors += len(result.errors)
            total_warnings += len(result.warnings)

            if not result.success:
                failed_files.append(md_file)
                print(f"\n✗ {md_file}")
                for error in result.errors:
                    print(f"    {error}")
            else:
                print(f"✓ {md_file}")

        print(f"\nSummary: {len(markdown_files) - len(failed_files)}/{len(markdown_files)} passed")
        print(f"Errors: {total_errors}, Warnings: {total_warnings}")

        return len(failed_files) == 0, total_errors, total_warnings

    print(f"Error: Path does not exist: {path}")
    return False, 1, 0


def parse_args(args=None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate links on GitHub Pages site or in local markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Web crawling mode
  %(prog)s --site-url https://example.github.io/project/
  %(prog)s --site-url https://example.com --timeout 30 --max-depth 5

  # Local file validation mode
  %(prog)s --local docs/README.md --strict
  %(prog)s --local docs/ --pragmatic --skip-external
        """,
    )

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--site-url",
        help="Base URL of the site to validate (web crawling mode)",
    )
    mode_group.add_argument(
        "--local",
        type=Path,
        help="Local markdown file or directory to validate",
    )

    # Local validation options
    parser.add_argument(
        "--strict",
        action="store_const",
        const=ValidationMode.STRICT,
        dest="mode",
        help="Strict validation: internal links must exist, all errors block",
    )
    parser.add_argument(
        "--pragmatic",
        action="store_const",
        const=ValidationMode.PRAGMATIC,
        dest="mode",
        help="Pragmatic validation: external 5xx/timeout are warnings only",
    )
    parser.add_argument(
        "--skip-external",
        action="store_true",
        help="Skip external link validation (local mode only)",
    )

    # Common options
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

    # Web crawling options
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Maximum crawl depth (web mode only, default: unlimited)",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=DEFAULT_RATE_LIMIT,
        help=f"Delay between requests in seconds (web mode only, default: {DEFAULT_RATE_LIMIT})",
    )

    # Set default mode
    parser.set_defaults(mode=ValidationMode.STRICT)

    return parser.parse_args(args)


def main() -> int:
    """Main entry point."""
    args = parse_args()

    print("GitHub Pages Link Validator")
    print("=" * 60)

    if args.site_url:
        # Web crawling mode
        print("Mode: Web Crawling")
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

    # Local validation mode
    print("Mode: Local File Validation")
    print(f"Path: {args.local}")
    print(f"Validation Mode: {args.mode.value}")
    print(f"Skip External: {args.skip_external}")
    print(f"Timeout: {args.timeout}s")
    print()

    success, errors, warnings = validate_local(
        args.local,
        mode=args.mode,
        timeout=args.timeout,
        skip_external=args.skip_external,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
