#!/usr/bin/env python3
"""
Example usage of the GitHub issue creation tool.

This demonstrates practical usage patterns for the github_issue module.
"""

import sys

sys.path.insert(0, "/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding/.claude/tools")

from github_issue import create_issue


def create_bug_report():
    """Example: Create a bug report issue."""
    result = create_issue(
        title="Bug: Login fails with special characters in password",
        body="""## Description
Users cannot log in when their password contains certain special characters.

## Steps to Reproduce
1. Set password with characters like & or #
2. Try to log in
3. Login fails with "Invalid credentials"

## Expected Behavior
Login should work with all allowed password characters.

## Environment
- OS: macOS 13.0
- Browser: Chrome 120
- App Version: 2.1.0
""",
        labels=["bug", "authentication", "high-priority"],
    )

    if result["success"]:
        print(f"✓ Created bug report: {result['issue_url']}")
        return result["issue_number"]
    print(f"✗ Failed to create bug report: {result['error']}")
    return None


def create_feature_request():
    """Example: Create a feature request."""
    result = create_issue(
        title="Feature: Add dark mode support",
        body="""## Feature Request
Add a dark mode option to reduce eye strain during night usage.

## Requirements
- [ ] Settings toggle for dark/light mode
- [ ] Persist user preference
- [ ] Smooth transition animation
- [ ] Respect system preferences by default

## Mockups
(Mockups would go here)

## Priority
Medium - requested by 50+ users
""",
        labels=["enhancement", "ui/ux"],
    )

    if result["success"]:
        print(f"✓ Created feature request: {result['issue_url']}")
        return result["issue_number"]
    print(f"✗ Failed to create feature request: {result['error']}")
    return None


def create_task_list(tasks):
    """Example: Create multiple related issues."""
    created_issues = []

    for task in tasks:
        result = create_issue(
            title=f"Task: {task['title']}",
            body=task.get("description", ""),
            labels=task.get("labels", ["task"]),
            milestone=task.get("milestone"),
        )

        if result["success"]:
            created_issues.append(
                {
                    "title": task["title"],
                    "number": result["issue_number"],
                    "url": result["issue_url"],
                }
            )
            print(f"✓ Created task #{result['issue_number']}: {task['title']}")
        else:
            print(f"✗ Failed to create task '{task['title']}': {result['error']}")

    return created_issues


def main():
    """Demonstrate different usage patterns."""
    print("GitHub Issue Creation Examples\n")
    print("Note: These are examples only. Uncomment to actually create issues.\n")

    # Show the examples
    print("1. Bug Report Example:")
    print("-" * 40)
    print("# create_bug_report()")
    print()

    print("2. Feature Request Example:")
    print("-" * 40)
    print("# create_feature_request()")
    print()

    print("3. Task List Example:")
    print("-" * 40)
    print("""
# tasks = [
#     {'title': 'Set up CI/CD pipeline', 'labels': ['devops'], 'milestone': 'v1.0'},
#     {'title': 'Write unit tests', 'labels': ['testing'], 'milestone': 'v1.0'},
#     {'title': 'Update documentation', 'labels': ['docs'], 'milestone': 'v1.0'}
# ]
# created = create_task_list(tasks)
    """)

    print("\nTo run these examples, uncomment the function calls in main()")


if __name__ == "__main__":
    main()
