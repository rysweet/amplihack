#!/usr/bin/env python3
"""
Drift detection script for Claude Agent SDK skill.

Checks if source documentation has changed since last sync.
Generates SHA-256 content hashes to detect changes.

Usage:
    python check_drift.py                    # Check for drift
    python check_drift.py --update           # Update hashes after check
    python check_drift.py --json             # Output JSON format
    python check_drift.py --metadata PATH    # Custom metadata location
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Check for requests library
try:
    import requests
except ImportError:
    print("Error: requests library not installed", file=sys.stderr)
    print("Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


def load_metadata(metadata_path: Path) -> dict:
    """Load version metadata from JSON file."""
    if not metadata_path.exists():
        return {
            "skill_version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "sources": [],
            "token_counts": {},
            "notes": [],
        }

    try:
        return json.loads(metadata_path.read_text())
    except json.JSONDecodeError as e:
        print(f"Error parsing metadata JSON: {e}", file=sys.stderr)
        sys.exit(1)


def save_metadata(metadata_path: Path, metadata: dict):
    """Save version metadata to JSON file."""
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2))


def fetch_content(url: str, timeout: int = 30) -> Optional[str]:
    """
    Fetch content from URL.

    Returns:
        Content as string if successful, None if error
    """
    try:
        headers = {"User-Agent": "Claude-Agent-SDK-Skill-Drift-Checker/1.0"}
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.Timeout:
        print(f"Timeout fetching {url}", file=sys.stderr)
        return None
    except requests.HTTPError as e:
        print(f"HTTP error fetching {url}: {e}", file=sys.stderr)
        return None
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def generate_hash(content: str) -> str:
    """Generate SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def check_source_drift(source: dict) -> dict:
    """
    Check if a single source has drifted.

    Args:
        source: Source dictionary with url and content_hash

    Returns:
        Result dictionary with drift status
    """
    url = source["url"]
    stored_hash = source.get("content_hash", "")

    print(f"Checking: {url}")
    content = fetch_content(url)

    if content is None:
        return {
            "url": url,
            "status": "error",
            "message": "Failed to fetch content",
            "drift_detected": False,
            "error": True,
        }

    current_hash = generate_hash(content)
    has_drifted = current_hash != stored_hash and not stored_hash.startswith("placeholder")

    # Handle placeholder hashes (first run)
    if stored_hash.startswith("placeholder"):
        message = "First hash generation (placeholder detected)"
    elif has_drifted:
        message = "Content hash changed - drift detected"
    else:
        message = "No drift detected"

    return {
        "url": url,
        "status": "ok",
        "message": message,
        "stored_hash": stored_hash,
        "current_hash": current_hash,
        "drift_detected": has_drifted,
        "last_checked": datetime.now().isoformat(),
        "error": False,
    }


def check_all_drift(metadata_path: Path) -> Dict[str, any]:
    """
    Check drift for all sources in metadata.

    Returns:
        Report dictionary with overall status and per-source results
    """
    metadata = load_metadata(metadata_path)
    sources = metadata.get("sources", [])

    if not sources:
        return {
            "status": "warning",
            "message": "No sources configured in metadata",
            "drift_count": 0,
            "error_count": 0,
            "total_sources": 0,
            "results": [],
            "checked_at": datetime.now().isoformat(),
        }

    results = []
    drift_count = 0
    error_count = 0

    for source in sources:
        result = check_source_drift(source)
        results.append(result)

        if result.get("error"):
            error_count += 1
        elif result["drift_detected"]:
            drift_count += 1

    # Determine overall status
    if error_count == len(sources):
        status = "error"
        message = "All sources failed to fetch"
    elif drift_count > 0:
        status = "drift_detected"
        message = f"{drift_count} of {len(sources)} sources have drifted"
    elif error_count > 0:
        status = "warning"
        message = f"{error_count} sources had errors, {len(sources) - error_count} ok"
    else:
        status = "ok"
        message = f"All {len(sources)} sources up to date"

    return {
        "status": status,
        "message": message,
        "drift_count": drift_count,
        "error_count": error_count,
        "total_sources": len(sources),
        "results": results,
        "checked_at": datetime.now().isoformat(),
    }


def update_metadata_hashes(metadata_path: Path, drift_results: dict):
    """
    Update metadata file with new content hashes.

    Args:
        metadata_path: Path to versions.json
        drift_results: Results from check_all_drift
    """
    metadata = load_metadata(metadata_path)

    for result in drift_results["results"]:
        if result["status"] == "ok" and not result.get("error"):
            # Find and update source
            for source in metadata["sources"]:
                if source["url"] == result["url"]:
                    source["content_hash"] = result["current_hash"]
                    source["last_checked"] = result["last_checked"]

                    # Update last_changed only if drift detected
                    if result["drift_detected"]:
                        source["last_changed"] = result["last_checked"]
                        print(f"  Updated hash for {source['url']}")

    # Update metadata timestamp
    metadata["last_updated"] = datetime.now().isoformat()

    # Save updated metadata
    save_metadata(metadata_path, metadata)


def format_output_text(results: dict):
    """Format results as human-readable text."""
    print(f"\n{'=' * 70}")
    print(f"Drift Detection Report - {results['checked_at']}")
    print(f"{'=' * 70}\n")

    for result in results["results"]:
        if result.get("error"):
            status_symbol = "✗"
            status_color = "ERROR"
        elif result["drift_detected"]:
            status_symbol = "⚠"
            status_color = "DRIFT"
        else:
            status_symbol = "✓"
            status_color = "OK"

        print(f"{status_symbol} [{status_color}] {result['url']}")

        if result.get("error"):
            print(f"  Error: {result.get('message', 'Unknown error')}")
        elif result["drift_detected"]:
            print(f"  {result['message']}")
            stored = result.get("stored_hash", "N/A")
            current = result.get("current_hash", "N/A")
            if not stored.startswith("placeholder"):
                print(f"  Old hash: {stored[:16]}...")
            print(f"  New hash: {current[:16]}...")

        print()

    print(f"{'=' * 70}")
    print(f"Summary: {results['message']}")
    if results["drift_count"] > 0:
        print("Action Required: Update skill content to reflect source changes")
        print("Run with --update to save new hashes after updating skill files")
    if results["error_count"] > 0:
        print(f"Warning: {results['error_count']} sources could not be fetched")
    print(f"{'=' * 70}\n")


def main():
    """Main CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check for drift in Claude Agent SDK skill sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python check_drift.py                    Check for drift
  python check_drift.py --update           Update hashes after fixing skill
  python check_drift.py --json             Output as JSON
  python check_drift.py --metadata custom.json  Use custom metadata file
        """,
    )

    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path(__file__).parent.parent / ".metadata" / "versions.json",
        help="Path to versions.json metadata file (default: ../.metadata/versions.json)",
    )

    parser.add_argument(
        "--update", action="store_true", help="Update metadata with new hashes after checking"
    )

    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON (for automation)"
    )

    args = parser.parse_args()

    # Check that metadata file exists
    if not args.metadata.exists():
        print(f"Error: Metadata file not found: {args.metadata}", file=sys.stderr)
        print(f"Expected location: {args.metadata.absolute()}", file=sys.stderr)
        sys.exit(1)

    # Check drift
    results = check_all_drift(args.metadata)

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        format_output_text(results)

    # Update metadata if requested
    if args.update:
        if results["error_count"] == results["total_sources"]:
            print("Error: Cannot update hashes - all sources failed to fetch", file=sys.stderr)
            sys.exit(1)

        update_metadata_hashes(args.metadata, results)
        print(f"✓ Metadata updated: {args.metadata}")
        print(f"  Updated {results['total_sources'] - results['error_count']} source hashes")

    # Exit code:
    # 0 = no drift, all ok
    # 1 = drift detected or errors
    # 2 = all sources failed
    if results["error_count"] == results["total_sources"]:
        sys.exit(2)
    elif results["drift_count"] > 0 or results["error_count"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
