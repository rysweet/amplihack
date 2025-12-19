#!/usr/bin/env python3
"""Quick validation script to verify documentation navigation and discoverability.

Checks:
1. All landing pages exist (memory/, features/, troubleshooting/, security/)
2. Index.md has links to major sections
3. Goal-seeking agents are prominently featured
4. DDD phases have breadcrumbs
"""

import sys
from pathlib import Path


def check_file_exists(path: Path, description: str) -> bool:
    """Check if a file exists and report."""
    if path.exists():
        print(f"✅ {description}: {path.name}")
        return True
    print(f"❌ MISSING {description}: {path}")
    return False


def check_content_contains(path: Path, search_term: str, description: str) -> bool:
    """Check if file contains specific content."""
    if not path.exists():
        print(f"❌ File not found: {path}")
        return False

    content = path.read_text()
    if search_term.lower() in content.lower():
        print(f"✅ {description}")
        return True
    print(f"❌ MISSING: {description}")
    return False


def main():
    docs_dir = Path(__file__).parent.parent / "docs"

    if not docs_dir.exists():
        print(f"❌ docs/ directory not found at {docs_dir}")
        return 1

    print("=" * 60)
    print("Documentation Navigation Validation")
    print("=" * 60)
    print()

    all_checks_passed = True

    # Check 1: Landing pages exist
    print("📋 Checking Landing Pages...")
    landing_pages = [
        (docs_dir / "memory" / "README.md", "Memory landing page"),
        (docs_dir / "features" / "README.md", "Features landing page"),
        (docs_dir / "troubleshooting" / "README.md", "Troubleshooting landing page"),
        (docs_dir / "security" / "README.md", "Security landing page"),
        (docs_dir / "document_driven_development" / "README.md", "DDD landing page"),
    ]

    for path, desc in landing_pages:
        if not check_file_exists(path, desc):
            all_checks_passed = False
    print()

    # Check 2: Index.md has key sections
    print("📋 Checking index.md Structure...")
    index_path = docs_dir / "index.md"
    index_checks = [
        ("Goal-Seeking Agents", "Goal-seeking agents section present"),
        ("Memory & Knowledge", "Memory section present"),
        ("Features & Integrations", "Features section present"),
        ("Troubleshooting", "Troubleshooting section present"),
        ("Security", "Security section present"),
        ("Document-Driven Development", "DDD section present"),
    ]

    for term, desc in index_checks:
        if not check_content_contains(index_path, term, desc):
            all_checks_passed = False
    print()

    # Check 3: DDD phases have breadcrumbs
    print("📋 Checking DDD Phase Breadcrumbs...")
    phases_dir = docs_dir / "document_driven_development" / "phases"
    phase_files = [
        "00_planning_and_alignment.md",
        "01_documentation_retcon.md",
        "02_approval_gate.md",
        "03_implementation_planning.md",
        "04_code_implementation.md",
        "05_testing_and_verification.md",
        "06_cleanup_and_push.md",
    ]

    for phase_file in phase_files:
        phase_path = phases_dir / phase_file
        if not check_content_contains(phase_path, "[Home]", f"Breadcrumbs in {phase_file}"):
            all_checks_passed = False
    print()

    # Check 4: Breadcrumbs in landing pages
    print("📋 Checking Landing Page Breadcrumbs...")
    breadcrumb_checks = [
        (docs_dir / "memory" / "README.md", "Memory README breadcrumbs"),
        (docs_dir / "features" / "README.md", "Features README breadcrumbs"),
        (docs_dir / "troubleshooting" / "README.md", "Troubleshooting README breadcrumbs"),
        (docs_dir / "security" / "README.md", "Security README breadcrumbs"),
    ]

    for path, desc in breadcrumb_checks:
        if not check_content_contains(path, "[Home]", desc):
            all_checks_passed = False
    print()

    # Summary
    print("=" * 60)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED!")
        print()
        print("Documentation is properly organized and discoverable.")
        return 0
    print("❌ SOME CHECKS FAILED")
    print()
    print("Please review the failures above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
