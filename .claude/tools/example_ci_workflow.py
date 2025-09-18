#!/usr/bin/env python3
"""
Example usage of the CI Workflow Tool

This demonstrates how to use the CI workflow functions programmatically.
"""

from ci_workflow import diagnose_ci, poll_status


def example_diagnose():
    """Example of running CI diagnostics."""
    print("Running CI Diagnostics")
    print("-" * 40)

    # Run diagnostics for current branch
    result = diagnose_ci()

    print(f"Overall Status: {result['overall_status']}")

    # Check individual components
    if result.get("ci_status"):
        print(f"CI Status: {result['ci_status'].get('status', 'UNKNOWN')}")

    for check in ["lint_check", "test_check", "build_check"]:
        if result.get(check):
            status = "✓ Passed" if result[check].get("success") else "✗ Failed"
            print(f"{check.replace('_', ' ').title()}: {status}")


def example_poll():
    """Example of polling CI status."""
    print("\nPolling CI Status")
    print("-" * 40)

    # Poll status for current branch with short timeout for demo
    result = poll_status(
        timeout=30,  # 30 seconds for demo
        interval=5,  # Start with 5 second intervals
        exponential_backoff=True,
    )

    print(f"Final Status: {result['final_status']}")
    print(f"Success: {result['success']}")
    print(f"Polls Made: {len(result['polls'])}")

    if result["timed_out"]:
        print("Note: Polling timed out")


def example_iterate_fixes():
    """Example of iterating CI fixes (mock only for safety)."""
    print("\nIterating CI Fixes (Mock Example)")
    print("-" * 40)

    # This is a mock example - in real usage, you'd specify a PR
    print("In real usage, you would run:")
    print("  result = iterate_fixes(max_attempts=3, pr_number=123)")
    print()
    print("This would:")
    print("  1. Run diagnostics")
    print("  2. Apply automatic fixes (lint, formatting)")
    print("  3. Commit and push fixes")
    print("  4. Re-run diagnostics")
    print("  5. Repeat until passing or max attempts reached")


def example_bash_usage():
    """Show examples of using the tool from bash."""
    print("\nBash Command Examples")
    print("-" * 40)

    examples = [
        ("Run diagnostics for PR #123:", "python .claude/tools/ci_workflow.py diagnose --pr 123"),
        (
            "Run diagnostics for current branch with JSON output:",
            "python .claude/tools/ci_workflow.py diagnose --json",
        ),
        (
            "Iterate fixes with max 3 attempts:",
            "python .claude/tools/ci_workflow.py iterate-fixes --max-attempts 3 --pr 123",
        ),
        (
            "Poll CI status with 5 minute timeout:",
            "python .claude/tools/ci_workflow.py poll-status --timeout 300",
        ),
        (
            "Poll specific PR with no backoff:",
            "python .claude/tools/ci_workflow.py poll-status 123 --no-backoff --interval 15",
        ),
    ]

    for description, command in examples:
        print(f"\n{description}")
        print(f"  $ {command}")


if __name__ == "__main__":
    print("=" * 50)
    print("CI Workflow Tool Examples")
    print("=" * 50)

    example_diagnose()
    example_poll()
    example_iterate_fixes()
    example_bash_usage()

    print("\n" + "=" * 50)
    print("Examples Complete")
    print("=" * 50)
