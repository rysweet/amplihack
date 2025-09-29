#!/usr/bin/env python3
"""Test the reflection system with specific error messages."""

import sys
from pathlib import Path

# Add the module path
sys.path.insert(0, str(Path(__file__).parent / ".claude" / "tools" / "amplihack" / "reflection"))


def test_reflection_specific_errors():
    """Test reflection system with specific error patterns."""
    print("🔍 Testing Reflection System with Specific Errors")
    print("=" * 50)

    from reflection import analyze_session_patterns  # type: ignore

    test_cases = [
        {
            "name": "File Not Found Error",
            "messages": [
                {"content": "Starting process"},
                {"content": "FileNotFoundError: No such file or directory: 'config.json'"},
                {"content": "Operation failed"},
            ],
            "expected_type": "file_missing",
        },
        {
            "name": "Permission Error",
            "messages": [
                {"content": "Processing files"},
                {"content": "PermissionError: [Errno 13] Permission denied: '/etc/secret'"},
                {"content": "Access denied"},
            ],
            "expected_type": "file_permissions",
        },
        {
            "name": "Module Not Found",
            "messages": [
                {"content": "Importing libraries"},
                {"content": "ModuleNotFoundError: No module named 'requests'"},
                {"content": "Import failed"},
            ],
            "expected_type": "missing_dependency",
        },
        {
            "name": "API Error",
            "messages": [
                {"content": "Making API call"},
                {"content": "HTTP 500 Internal Server Error from API endpoint"},
                {"content": "Request failed"},
            ],
            "expected_type": "api_failure",
        },
        {
            "name": "Timeout Error",
            "messages": [
                {"content": "Connecting to server"},
                {"content": "Connection timeout after 30 seconds"},
                {"content": "Connection failed"},
            ],
            "expected_type": "timeout_error",
        },
    ]

    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print("-" * 30)

        patterns = analyze_session_patterns(test_case["messages"])

        print(f"Patterns found: {len(patterns)}")

        if patterns:
            top_pattern = patterns[0]
            pattern_type = top_pattern.get("type", "unknown")
            suggestion = top_pattern.get("suggestion", "No suggestion")
            priority = top_pattern.get("priority", "unknown")

            print(f"Type: {pattern_type}")
            print(f"Priority: {priority}")
            print(f"Suggestion: {suggestion}")

            # Check if it's the expected specific type
            if test_case["expected_type"] in pattern_type:
                print("✅ Specific error detection: PASS")
            else:
                print(f"⚠️  Expected {test_case['expected_type']}, got {pattern_type}")

            # Check if suggestion is specific (not generic)
            generic_phrases = ["improve error handling based on session failures"]
            is_generic = any(phrase.lower() in suggestion.lower() for phrase in generic_phrases)

            if not is_generic:
                print("✅ Specific suggestion: PASS")
            else:
                print(f"⚠️  Generic suggestion detected: {suggestion}")

        else:
            print("❌ No patterns detected")


def main():
    """Run reflection system tests."""
    print("🚀 Reflection System Error Analysis Test")
    print("=" * 40)

    test_reflection_specific_errors()

    print("\n✅ Reflection testing complete!")


if __name__ == "__main__":
    main()
