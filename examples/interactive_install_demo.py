#!/usr/bin/env python3
"""Demo script for interactive dependency installation.

This script demonstrates the new interactive installation feature that:
1. Checks for missing prerequisites
2. Prompts user for approval
3. Installs dependencies interactively (with sudo password prompts)
4. Logs all attempts to audit log
5. Handles edge cases (non-interactive, declined, failed)

Usage:
    python examples/interactive_install_demo.py
"""

import sys
from pathlib import Path

# Add src to path for demo purposes
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from amplihack.utils.prerequisites import PrerequisiteChecker


def main():
    """Demonstrate interactive installation workflow."""
    print("=" * 70)
    print("INTERACTIVE DEPENDENCY INSTALLATION DEMO")
    print("=" * 70)
    print()
    print("This demo will:")
    print("  1. Check for missing prerequisites")
    print("  2. Prompt you to install any missing tools")
    print("  3. Log all installation attempts")
    print()
    print("=" * 70)
    print()

    # Create checker
    checker = PrerequisiteChecker()
    print(f"Platform detected: {checker.platform.value}")
    print()

    # Run interactive installation
    result = checker.check_and_install(interactive=True)

    # Show results
    print()
    print("=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print()

    if result.all_available:
        print("[SUCCESS] All prerequisites are available!")
        print()
        print("Available tools:")
        for tool in result.available_tools:
            print(f"  ✓ {tool.tool} ({tool.version})")
    else:
        print(f"[WARNING] {len(result.missing_tools)} tool(s) still missing:")
        for tool in result.missing_tools:
            print(f"  ✗ {tool.tool}")
        print()
        print("Installation may have failed or been declined.")
        print("Check audit log at: ~/.claude/runtime/logs/installation_audit.jsonl")

    print()
    print("=" * 70)

    # Return exit code based on result
    return 0 if result.all_available else 1


if __name__ == "__main__":
    sys.exit(main())
