#!/usr/bin/env python3
"""Script to convert all commands from .claude/commands/ to .github/commands/."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.adapters.copilot_command_converter import convert_commands


def main():
    """Convert all commands and print report."""
    print("Converting commands from .claude/commands/ to .github/commands/...")
    print()

    report = convert_commands(force=True)

    print(f"Total: {report.total}")
    print(f"Succeeded: {report.succeeded}")
    print(f"Failed: {report.failed}")
    print(f"Skipped: {report.skipped}")
    print()

    if report.errors:
        print("Errors:")
        for error in report.errors:
            print(f"  {error}")
        print()

    print("Converted commands:")
    for conversion in report.conversions:
        if conversion.status == "success":
            print(f"  ✓ {conversion.command_name}")
        elif conversion.status == "failed":
            print(f"  ✗ {conversion.command_name}: {conversion.reason}")
        elif conversion.status == "skipped":
            print(f"  ⊘ {conversion.command_name}: {conversion.reason}")

    print()
    print(f"Registry written to: .github/commands/COMMANDS_REGISTRY.json")

    sys.exit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()
