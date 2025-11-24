#!/usr/bin/env python3
"""Manual verification test for stop hook duplicate execution fix.

This test verifies that stop hooks are NOT called from the launcher's signal
handlers or atexit handlers, preventing duplicate execution when Claude Code
already executes stop hooks via settings.json.

Tests verify:
1. _setup_signal_handlers() no longer imports or calls execute_stop_hook()
2. _cleanup_on_exit() no longer imports or calls execute_stop_hook()
3. Signal handler docstrings reflect that Claude Code handles stop hooks
4. Cleanup handler docstrings reflect that Claude Code handles stop hooks

Run this test manually:
    python tests/manual_test_stop_hook_duplicate_fix.py
"""

import ast
import sys
from pathlib import Path


def test_signal_handler_no_stop_hook_call():
    """Verify _setup_signal_handlers does not call execute_stop_hook()."""
    # Read the launcher core.py file
    launcher_path = Path(__file__).parent.parent / "src" / "amplihack" / "launcher" / "core.py"
    source_code = launcher_path.read_text()

    # Parse the AST
    tree = ast.parse(source_code)

    # Find _setup_signal_handlers method
    setup_signal_handlers = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_setup_signal_handlers":
            setup_signal_handlers = node
            break

    assert setup_signal_handlers is not None, "_setup_signal_handlers method not found"

    # Check for execute_stop_hook calls
    has_stop_hook_call = False
    has_stop_hook_import = False

    for node in ast.walk(setup_signal_handlers):
        # Check for function calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "execute_stop_hook":
                has_stop_hook_call = True

        # Check for imports
        if isinstance(node, ast.ImportFrom):
            if node.module == "amplihack.hooks.manager":
                if any(alias.name == "execute_stop_hook" for alias in node.names):
                    has_stop_hook_import = True

    assert not has_stop_hook_call, "FAIL: _setup_signal_handlers still calls execute_stop_hook()"
    assert not has_stop_hook_import, "FAIL: _setup_signal_handlers still imports execute_stop_hook"

    # Verify docstring mentions Claude Code handling stop hooks
    docstring = ast.get_docstring(setup_signal_handlers)
    assert docstring is not None, "FAIL: _setup_signal_handlers missing docstring"
    assert "Claude Code" in docstring, "FAIL: Docstring does not mention Claude Code"
    assert "settings.json" in docstring, "FAIL: Docstring does not mention settings.json"

    print("✓ PASS: _setup_signal_handlers does not call execute_stop_hook()")
    print("✓ PASS: _setup_signal_handlers does not import execute_stop_hook")
    print("✓ PASS: Docstring correctly documents Claude Code handling stop hooks")


def test_cleanup_on_exit_no_stop_hook_call():
    """Verify _cleanup_on_exit does not call execute_stop_hook()."""
    # Read the launcher core.py file
    launcher_path = Path(__file__).parent.parent / "src" / "amplihack" / "launcher" / "core.py"
    source_code = launcher_path.read_text()

    # Parse the AST
    tree = ast.parse(source_code)

    # Find _cleanup_on_exit method
    cleanup_on_exit = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_cleanup_on_exit":
            cleanup_on_exit = node
            break

    assert cleanup_on_exit is not None, "_cleanup_on_exit method not found"

    # Check for execute_stop_hook calls
    has_stop_hook_call = False
    has_stop_hook_import = False

    for node in ast.walk(cleanup_on_exit):
        # Check for function calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "execute_stop_hook":
                has_stop_hook_call = True

        # Check for imports
        if isinstance(node, ast.ImportFrom):
            if node.module == "amplihack.hooks.manager":
                if any(alias.name == "execute_stop_hook" for alias in node.names):
                    has_stop_hook_import = True

    assert not has_stop_hook_call, "FAIL: _cleanup_on_exit still calls execute_stop_hook()"
    assert not has_stop_hook_import, "FAIL: _cleanup_on_exit still imports execute_stop_hook"

    # Verify docstring mentions Claude Code handling stop hooks
    docstring = ast.get_docstring(cleanup_on_exit)
    assert docstring is not None, "FAIL: _cleanup_on_exit missing docstring"
    assert "Claude Code" in docstring, "FAIL: Docstring does not mention Claude Code"
    assert "settings.json" in docstring, "FAIL: Docstring does not mention settings.json"

    print("✓ PASS: _cleanup_on_exit does not call execute_stop_hook()")
    print("✓ PASS: _cleanup_on_exit does not import execute_stop_hook")
    print("✓ PASS: Docstring correctly documents Claude Code handling stop hooks")


def test_signal_handler_nested_function():
    """Verify the nested signal_handler function does not call execute_stop_hook()."""
    # Read the launcher core.py file
    launcher_path = Path(__file__).parent.parent / "src" / "amplihack" / "launcher" / "core.py"
    source_code = launcher_path.read_text()

    # Parse the AST
    tree = ast.parse(source_code)

    # Find _setup_signal_handlers method
    setup_signal_handlers = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_setup_signal_handlers":
            setup_signal_handlers = node
            break

    assert setup_signal_handlers is not None, "_setup_signal_handlers method not found"

    # Find nested signal_handler function
    signal_handler = None
    for node in setup_signal_handlers.body:
        if isinstance(node, ast.FunctionDef) and node.name == "signal_handler":
            signal_handler = node
            break

    assert signal_handler is not None, "Nested signal_handler function not found"

    # Check for execute_stop_hook calls in nested function
    has_stop_hook_call = False

    for node in ast.walk(signal_handler):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "execute_stop_hook":
                has_stop_hook_call = True

    assert not has_stop_hook_call, "FAIL: Nested signal_handler() still calls execute_stop_hook()"

    # Check for comment about Claude Code handling stop hooks
    source_lines = source_code.split("\n")

    # Find the line range for signal_handler function
    start_line = signal_handler.lineno
    end_line = (
        signal_handler.end_lineno if hasattr(signal_handler, "end_lineno") else start_line + 20
    )

    handler_source = "\n".join(source_lines[start_line - 1 : end_line])

    assert "Claude Code" in handler_source or "settings.json" in handler_source, (
        "FAIL: signal_handler does not mention Claude Code or settings.json in comments"
    )

    print("✓ PASS: Nested signal_handler() does not call execute_stop_hook()")
    print("✓ PASS: Comments correctly document Claude Code handling stop hooks")


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("Stop Hook Duplicate Execution Fix - Verification Tests")
    print("=" * 70)
    print()

    try:
        test_signal_handler_no_stop_hook_call()
        print()
        test_cleanup_on_exit_no_stop_hook_call()
        print()
        test_signal_handler_nested_function()
        print()
        print("=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70)
        print()
        print("Fix verified: Stop hooks are no longer called from launcher,")
        print("preventing duplicate execution with Claude Code's settings.json.")
        return 0
    except AssertionError as e:
        print()
        print("=" * 70)
        print("TEST FAILED ✗")
        print("=" * 70)
        print(f"\nError: {e}")
        return 1
    except Exception as e:
        print()
        print("=" * 70)
        print("UNEXPECTED ERROR ✗")
        print("=" * 70)
        print(f"\nError: {type(e).__name__}: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
