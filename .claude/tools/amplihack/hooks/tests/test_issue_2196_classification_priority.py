#!/usr/bin/env python3
"""
Tests for Issue #2196 Phase 1.1: Classification Priority Reordering.

Verifies that tool usage patterns (concrete evidence) take priority over
investigation keywords when classifying sessions.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


def test_analyze_with_code_changes_is_development():
    """Sessions with 'analyze' keyword BUT code changes should be DEVELOPMENT."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "user",
            "message": {"content": "analyze the checker and fix bugs"},
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll analyze and fix the issues."},
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {
                            "file_path": "checker.py",
                            "old_string": "old",
                            "new_string": "new",
                        },
                    },
                    {
                        "type": "tool_use",
                        "name": "Write",
                        "input": {
                            "file_path": "test_checker.py",
                            "content": "test code",
                        },
                    },
                ]
            },
        },
    ]

    session_type = checker.detect_session_type(transcript)
    assert session_type == "DEVELOPMENT", (
        f"Expected DEVELOPMENT for sessions with code changes, got {session_type}. "
        f"Tool usage should override investigation keywords."
    )


def test_investigate_keyword_without_tools_is_investigation():
    """Pure investigation keywords WITHOUT tools should still be INVESTIGATION."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "user",
            "message": {"content": "investigate why the tests are failing"},
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll investigate the test failures."},
                ]
            },
        },
    ]

    session_type = checker.detect_session_type(transcript)
    assert session_type in ["INVESTIGATION", "INFORMATIONAL"], (
        f"Expected INVESTIGATION or INFORMATIONAL without tools, got {session_type}"
    )


def test_troubleshoot_with_write_tools_is_development():
    """'Troubleshoot' keyword with Write tools should be DEVELOPMENT."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "user",
            "message": {"content": "troubleshoot the import errors"},
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll fix the import errors."},
                    {
                        "type": "tool_use",
                        "name": "Write",
                        "input": {
                            "file_path": "module.py",
                            "content": "fixed code",
                        },
                    },
                ]
            },
        },
    ]

    session_type = checker.detect_session_type(transcript)
    assert session_type == "DEVELOPMENT", (
        f"Expected DEVELOPMENT with Write tools, got {session_type}"
    )


def test_diagnose_with_tests_is_development():
    """'Diagnose' keyword with test execution should be DEVELOPMENT."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "user",
            "message": {"content": "diagnose the test failures"},
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll run the tests."},
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "pytest tests/"},
                    },
                ]
            },
        },
    ]

    session_type = checker.detect_session_type(transcript)
    assert session_type == "DEVELOPMENT", (
        f"Expected DEVELOPMENT with test execution, got {session_type}"
    )


def test_explore_with_only_read_is_investigation():
    """'Explore' keyword with only Read tools should be INVESTIGATION."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "user",
            "message": {"content": "explore the codebase structure"},
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll explore the structure."},
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "module.py"},
                    },
                    {
                        "type": "tool_use",
                        "name": "Grep",
                        "input": {"pattern": "class", "path": "."},
                    },
                ]
            },
        },
    ]

    session_type = checker.detect_session_type(transcript)
    assert session_type == "INVESTIGATION", (
        f"Expected INVESTIGATION with Read/Grep only, got {session_type}"
    )


def test_research_with_pr_operations_is_development():
    """'Research' keyword with PR operations should be DEVELOPMENT."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "user",
            "message": {"content": "research the bug and create PR"},
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll create a PR."},
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "gh pr create --title 'Fix bug'"},
                    },
                ]
            },
        },
    ]

    session_type = checker.detect_session_type(transcript)
    assert session_type == "DEVELOPMENT", (
        f"Expected DEVELOPMENT with PR operations, got {session_type}"
    )


def test_tool_usage_overrides_multiple_investigation_keywords():
    """Multiple investigation keywords should NOT override tool evidence."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "user",
            "message": {
                "content": "investigate, analyze, and troubleshoot this module, then fix it"
            },
        },
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "I'll investigate and fix the module."},
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "module.py"},
                    },
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {
                            "file_path": "module.py",
                            "old_string": "bug",
                            "new_string": "fix",
                        },
                    },
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "pytest module_test.py"},
                    },
                ]
            },
        },
    ]

    session_type = checker.detect_session_type(transcript)
    assert session_type == "DEVELOPMENT", (
        f"Expected DEVELOPMENT - tool evidence should override keywords, got {session_type}"
    )


if __name__ == "__main__":
    print("Running Issue #2196 Phase 1.1 tests (Classification Priority)...")

    test_analyze_with_code_changes_is_development()
    print("✓ test_analyze_with_code_changes_is_development")

    test_investigate_keyword_without_tools_is_investigation()
    print("✓ test_investigate_keyword_without_tools_is_investigation")

    test_troubleshoot_with_write_tools_is_development()
    print("✓ test_troubleshoot_with_write_tools_is_development")

    test_diagnose_with_tests_is_development()
    print("✓ test_diagnose_with_tests_is_development")

    test_explore_with_only_read_is_investigation()
    print("✓ test_explore_with_only_read_is_investigation")

    test_research_with_pr_operations_is_development()
    print("✓ test_research_with_pr_operations_is_development")

    test_tool_usage_overrides_multiple_investigation_keywords()
    print("✓ test_tool_usage_overrides_multiple_investigation_keywords")

    print("\n✅ All Phase 1.1 tests passed!")
