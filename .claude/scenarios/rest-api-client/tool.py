#!/usr/bin/env python3
"""REST API Client CLI tool.

A command-line interface for making HTTP requests using the REST API Client.
Supports all common HTTP methods, authentication, and advanced features.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from rest_api_client import APIClient
from rest_api_client.exceptions import APIClientError


def parse_json_input(json_str: str) -> dict[str, Any]:
    """Parse JSON input string.

    Args:
        json_str: JSON string to parse

    Returns:
        Parsed dictionary

    Raises:
        ValueError: If JSON is invalid
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def parse_headers(headers_str: str) -> dict[str, str]:
    """Parse headers from JSON string or key:value format.

    Args:
        headers_str: Headers string

    Returns:
        Headers dictionary
    """
    if headers_str.startswith("{"):
        # JSON format
        return parse_json_input(headers_str)
    # key:value,key:value format
    headers = {}
    for pair in headers_str.split(","):
        if ":" in pair:
            key, value = pair.split(":", 1)
            headers[key.strip()] = value.strip()
    return headers


def format_response(response, format_type: str = "plain") -> str:
    """Format response for output.

    Args:
        response: Response object
        format_type: Output format (plain, json, headers)

    Returns:
        Formatted response string
    """
    if format_type == "json":
        output = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text if response.text else None,
            "elapsed_time": response.elapsed_time,
        }
        return json.dumps(output, indent=2)

    if format_type == "headers":
        lines = [f"Status: {response.status_code}"]
        lines.append(f"Time: {response.elapsed_time:.2f}s")
        lines.append("\nHeaders:")
        for name, value in response.headers.items():
            lines.append(f"  {name}: {value}")
        return "\n".join(lines)

    # plain
    lines = []
    lines.append(f"Status: {response.status_code}")
    lines.append(f"Time: {response.elapsed_time:.2f}s")
    if response.text:
        lines.append("\nBody:")
        lines.append(response.text)
    return "\n".join(lines)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="REST API Client - Make HTTP requests from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple GET request
  %(prog)s --url https://api.github.com/users/octocat

  # POST with JSON data
  %(prog)s --url https://api.example.com/data --method POST --json '{"key": "value"}'

  # With custom headers
  %(prog)s --url https://api.example.com --headers '{"Authorization": "Bearer token"}'

  # Save response to file
  %(prog)s --url https://api.example.com --output response.json

  # Disable SSRF protection for internal APIs
  %(prog)s --url http://internal-api:8080/data --no-ssrf-protection
        """,
    )

    # Required arguments
    parser.add_argument("--url", required=True, help="Full URL to request")

    # HTTP method
    parser.add_argument(
        "--method",
        default="GET",
        choices=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
        help="HTTP method (default: GET)",
    )

    # Request data
    parser.add_argument("--json", help="JSON data to send with request")
    parser.add_argument("--data", help="Raw data to send with request")

    # Headers and auth
    parser.add_argument("--headers", help="Request headers as JSON or key:value,key:value")
    parser.add_argument("--auth", help="Basic auth as username:password")

    # Request options
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, help="Maximum retry attempts (default: 3)"
    )

    # Security options
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification (not recommended)",
    )
    parser.add_argument(
        "--no-ssrf-protection",
        action="store_true",
        help="Disable SSRF protection (use only for trusted internal APIs)",
    )
    parser.add_argument(
        "--max-response-size",
        type=int,
        default=100 * 1024 * 1024,
        help="Maximum response size in bytes (default: 100MB)",
    )

    # Output options
    parser.add_argument(
        "--format",
        choices=["plain", "json", "headers"],
        default="plain",
        help="Output format (default: plain)",
    )
    parser.add_argument("--output", help="Save response to file")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Parse URL to extract base and path
    parsed = urlparse(args.url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path
    if parsed.query:
        path += f"?{parsed.query}"
    if parsed.fragment:
        path += f"#{parsed.fragment}"

    # Prepare headers
    headers = {}
    if args.headers:
        try:
            headers = parse_headers(args.headers)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Add basic auth if provided
    if args.auth:
        import base64

        auth_bytes = args.auth.encode("ascii")
        auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
        headers["Authorization"] = f"Basic {auth_b64}"

    # Prepare JSON data
    json_data = None
    if args.json:
        try:
            json_data = parse_json_input(args.json)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        # Create client
        client = APIClient(
            base_url=base_url,
            headers=headers,
            timeout=args.timeout,
            verify_ssl=not args.no_verify_ssl,
            max_retries=args.max_retries,
            max_response_size=args.max_response_size,
            enable_ssrf_protection=not args.no_ssrf_protection,
        )

        # Make request
        if args.verbose:
            print(f"Making {args.method} request to {args.url}", file=sys.stderr)

        response = client.request(method=args.method, url=path, json=json_data, data=args.data)

        # Format output
        output = format_response(response, args.format)

        # Save or print
        if args.output:
            Path(args.output).write_text(output)
            if args.verbose:
                print(f"Response saved to {args.output}", file=sys.stderr)
        else:
            print(output)

        # Exit with appropriate code
        if response.status_code >= 400:
            sys.exit(1)

    except APIClientError as e:
        print(f"API Error: {e}", file=sys.stderr)
        if args.verbose and hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
