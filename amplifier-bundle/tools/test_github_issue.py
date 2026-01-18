#!/usr/bin/env python3
"""
Test script for GitHub issue creation tool.

This demonstrates how to use the github_issue module.
"""

from github_issue import GitHubIssueCreator, create_issue


def test_validation():
    """Test that validation works correctly."""
    print("Testing validation...")

    # Test empty title
    result = create_issue(title="")
    assert not result["success"]
    assert "Title is required" in result["error"]
    print("✓ Empty title validation works")

    # Test whitespace-only title
    result = create_issue(title="   ")
    assert not result["success"]
    assert "Title is required" in result["error"]
    print("✓ Whitespace title validation works")

    print()


def test_gh_cli_check():
    """Test that gh CLI validation works."""
    print("Testing GitHub CLI check...")

    try:
        GitHubIssueCreator()
        print("✓ GitHub CLI is installed and authenticated")
    except RuntimeError as e:
        print(f"✗ GitHub CLI check failed: {e}")
        print("  Please install gh CLI and authenticate with: gh auth login")
        return False

    print()
    return True


def demo_create_issue():
    """Demo creating an issue (dry run - won't actually create)."""
    print("Demo: How to create an issue")
    print("-" * 40)

    # Example 1: Simple issue
    print("\nExample 1: Simple issue")
    print("""
    result = create_issue(
        title="Fix login timeout issue"
    )
    """)

    # Example 2: Full-featured issue
    print("\nExample 2: Issue with all options")
    print("""
    result = create_issue(
        title="Add dark mode support",
        body="Users have requested dark mode. This should include:\\n- Settings toggle\\n- Theme persistence\\n- Smooth transitions",
        labels=["enhancement", "ui/ux"],
        assignees=["username1", "username2"],
        milestone="v2.0",
        project="Q1 Roadmap"
    )
    """)

    # Example 3: Check result
    print("\nExample 3: Handling the result")
    print("""
    if result['success']:
        print(f"Created issue #{result['issue_number']}")
        print(f"View at: {result['issue_url']}")
    else:
        print(f"Error: {result['error']}")
    """)

    print("\n" + "-" * 40)


def main():
    """Run tests and demo."""
    print("GitHub Issue Creation Tool Test\n")

    # Test validation
    test_validation()

    # Test gh CLI
    if not test_gh_cli_check():
        return 1

    # Show demo
    demo_create_issue()

    print("\nTo create a real issue, use:")
    print("  python github_issue.py 'Issue title' --body 'Description'")
    print("\nOr in Python:")
    print("  from github_issue import create_issue")
    print("  result = create_issue(title='Bug report')")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
