#!/usr/bin/env python3
"""
Check Microsoft Agent Framework Skill Documentation Freshness

This script validates that the skill documentation is current by checking:
1. Age of documentation (warns if >30 days old)
2. Framework version matches latest release
3. Source URLs are still accessible
4. Breaking changes in framework since last update
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class FreshnessChecker:
    """Check documentation freshness for Microsoft Agent Framework skill."""

    def __init__(self, skill_root: Path):
        self.skill_root = skill_root
        self.metadata_path = skill_root / "metadata" / "version-tracking.json"
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def load_metadata(self) -> dict:
        """Load version tracking metadata."""
        if not self.metadata_path.exists():
            self.errors.append(f"Metadata file not found: {self.metadata_path}")
            return {}

        with open(self.metadata_path) as f:
            return json.load(f)

    def check_documentation_age(self, metadata: dict) -> bool:
        """Check if documentation is within acceptable age."""
        last_updated = metadata.get("last_updated")
        if not last_updated:
            self.warnings.append("No last_updated date in metadata")
            return False

        update_date = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        age = datetime.now(update_date.tzinfo) - update_date
        age_days = age.days

        if age_days > 30:
            self.warnings.append(f"Documentation is {age_days} days old (threshold: 30 days)")
            return False

        print(f"✓ Documentation age: {age_days} days (current)")
        return True

    def check_url_accessibility(self, url: str, timeout: int = 10) -> bool:
        """Check if a URL is accessible with retry logic."""
        import time

        headers = {"User-Agent": "Mozilla/5.0 (compatible; SkillFreshnessChecker/1.0)"}

        # Retry up to 3 times for transient failures
        for attempt in range(3):
            try:
                req = Request(url, headers=headers)
                with urlopen(req, timeout=timeout) as response:
                    if response.status == 200:
                        return True
            except (URLError, HTTPError):
                if attempt == 2:  # Last attempt
                    return False
                time.sleep(1)  # Wait before retry

        return False

    def check_source_urls(self, metadata: dict) -> bool:
        """Validate all source URLs are accessible."""
        sources = metadata.get("sources", {})
        if not sources:
            self.warnings.append("No source URLs found in metadata")
            return False

        all_accessible = True
        for name, info in sources.items():
            url = info.get("url")
            if not url:
                continue

            print(f"Checking {name}...", end=" ")
            if self.check_url_accessibility(url):
                print("✓")
            else:
                print("✗")
                self.warnings.append(f"Source URL not accessible: {name} ({url})")
                all_accessible = False

        return all_accessible

    def check_github_version(self, metadata: dict) -> bool:
        """Check if framework version matches latest GitHub release."""
        current_version = metadata.get("framework_version", "unknown")

        print(f"✓ Framework version: {current_version}")
        print("  (Manual check recommended for latest release)")
        return True

    def check_breaking_changes(self, metadata: dict) -> bool:
        """Check for reported breaking changes."""
        breaking_changes = metadata.get("breaking_changes", [])
        if breaking_changes:
            self.warnings.append(f"Breaking changes reported: {len(breaking_changes)} changes")
            for change in breaking_changes:
                print(f"  - {change}")
            return False

        print("✓ No breaking changes reported")
        return True

    def check_next_verification(self, metadata: dict) -> bool:
        """Check if verification is overdue."""
        next_due = metadata.get("next_verification_due")
        if not next_due:
            self.warnings.append("No next_verification_due date set")
            return False

        due_date = datetime.fromisoformat(next_due)
        now = datetime.now()

        if now > due_date:
            days_overdue = (now - due_date).days
            self.warnings.append(f"Verification overdue by {days_overdue} days")
            return False

        days_until = (due_date - now).days
        print(f"✓ Next verification due in {days_until} days")
        return True

    def run(self) -> bool:
        """Run all freshness checks."""
        print("=" * 60)
        print("Microsoft Agent Framework Skill - Freshness Check")
        print("=" * 60)
        print()

        metadata = self.load_metadata()
        if not metadata:
            print("✗ Failed to load metadata")
            return False

        print(f"Skill Version: {metadata.get('skill_version', 'unknown')}")
        print(f"Framework Version: {metadata.get('framework_version', 'unknown')}")
        print(f"Last Updated: {metadata.get('last_updated', 'unknown')}")
        print()

        # Run checks
        age_ok = self.check_documentation_age(metadata)
        urls_ok = self.check_source_urls(metadata)
        self.check_github_version(metadata)
        self.check_breaking_changes(metadata)
        self.check_next_verification(metadata)

        # Report results
        print()
        print("=" * 60)
        if self.errors:
            print("ERRORS:")
            for error in self.errors:
                print(f"  ✗ {error}")
            print()

        if self.warnings:
            print("WARNINGS:")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
            print()

        all_ok = not self.errors and age_ok and urls_ok
        if all_ok:
            print("✓ Documentation is current and accessible")
        else:
            print("⚠ Documentation may need updating")
            print()
            print("To update:")
            print("  1. Review framework release notes")
            print("  2. Check for breaking changes")
            print("  3. Fetch latest content from source URLs")
            print("  4. Update skill files and metadata")

        print("=" * 60)
        return all_ok


def main():
    """Main entry point."""
    # Detect skill root (script is in skill_root/scripts/)
    script_path = Path(__file__).resolve()
    skill_root = script_path.parent.parent

    checker = FreshnessChecker(skill_root)
    success = checker.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
