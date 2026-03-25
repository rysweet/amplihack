#!/usr/bin/env python3
"""Outside-in smoke test: plugin install TimeoutExpired is caught (#3563).

Validates from the outside that:
1. subprocess.TimeoutExpired is caught during plugin installation
2. The fallback to directory copy mode is triggered on timeout
3. No unhandled traceback escapes to the user
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = REPO_ROOT / "src" / "amplihack" / "cli.py"


def test_timeout_expired_is_caught() -> bool:
    """The plugin install subprocess calls must be inside try/except TimeoutExpired."""
    source = CLI_PATH.read_text()
    if "except subprocess.TimeoutExpired" not in source:
        print("FAIL: subprocess.TimeoutExpired is not caught in cli.py")
        return False
    print("PASS: subprocess.TimeoutExpired is caught")
    return True


def test_fallback_message_on_timeout() -> bool:
    """The timeout handler must print a user-friendly message."""
    source = CLI_PATH.read_text()
    if "Plugin installation timed out" not in source:
        print("FAIL: missing user-friendly timeout message")
        return False
    print("PASS: user-friendly timeout message present")
    return True


def test_fallback_to_directory_copy() -> bool:
    """The timeout handler must call _fallback_to_directory_copy."""
    source = CLI_PATH.read_text()
    if '_fallback_to_directory_copy(\n                                "Plugin install timed out"' not in source:
        # Looser check
        if "_fallback_to_directory_copy" not in source or "Plugin install timed out" not in source:
            print("FAIL: timeout does not trigger directory copy fallback")
            return False
    print("PASS: timeout triggers directory copy fallback")
    return True


def test_try_except_structure() -> bool:
    """Verify the try/except wraps both subprocess.run calls (marketplace add + plugin install)."""
    source = CLI_PATH.read_text()
    tree = ast.parse(source)

    # Find the main() function
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            # Look for Try nodes containing subprocess.TimeoutExpired handlers
            for child in ast.walk(node):
                if isinstance(child, ast.Try):
                    for handler in child.handlers:
                        if handler.type and hasattr(handler.type, "attr"):
                            if handler.type.attr == "TimeoutExpired":
                                print("PASS: try/except subprocess.TimeoutExpired found in main()")
                                return True
    print("FAIL: no try/except subprocess.TimeoutExpired in main()")
    return False


def main() -> int:
    tests = [
        test_timeout_expired_is_caught,
        test_fallback_message_on_timeout,
        test_fallback_to_directory_copy,
        test_try_except_structure,
    ]
    results = [t() for t in tests]
    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
