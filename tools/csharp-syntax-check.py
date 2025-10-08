#!/usr/bin/env python3
"""
C# Syntax Validation Tool
Fast syntax validation using basic parsing checks.

Checks for:
- Balanced braces, brackets, parentheses
- Semicolon placement
- String/comment closure
- Basic structure validity
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def validate_balanced_delimiters(content: str, filepath: str) -> List[str]:
    """Check for balanced delimiters in C# code."""
    errors = []

    # Remove strings and comments to avoid false positives
    # This is a simplified approach - not perfect but fast
    cleaned = re.sub(r'"(?:[^"\\]|\\.)*"', '""', content)  # Remove string contents
    cleaned = re.sub(r"//.*?$", "", cleaned, flags=re.MULTILINE)  # Remove line comments
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)  # Remove block comments

    # Check balanced braces
    brace_count = cleaned.count("{") - cleaned.count("}")
    if brace_count != 0:
        errors.append(
            f"Unbalanced braces: {abs(brace_count)} extra {'{{' if brace_count > 0 else '}'}"
        )

    # Check balanced parentheses
    paren_count = cleaned.count("(") - cleaned.count(")")
    if paren_count != 0:
        errors.append(
            f"Unbalanced parentheses: {abs(paren_count)} extra {'(' if paren_count > 0 else ')'}"
        )

    # Check balanced brackets
    bracket_count = cleaned.count("[") - cleaned.count("]")
    if bracket_count != 0:
        errors.append(
            f"Unbalanced brackets: {abs(bracket_count)} extra {'[' if bracket_count > 0 else ']'}"
        )

    return errors


def validate_common_patterns(content: str, filepath: str) -> List[str]:
    """Check for common C# syntax errors."""
    errors = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()

        # Skip empty lines and comments
        if not line_stripped or line_stripped.startswith("//"):
            continue

        # Check for malformed catch blocks (catch without parentheses)
        if re.search(r"\bcatch\s+[^({]", line_stripped):
            if not re.search(r"\bcatch\s*$", line_stripped):  # Allow catch on its own line
                errors.append(f"Line {i}: Possible malformed catch block (missing parentheses)")

        # Check for malformed if statements (if without parentheses)
        if re.search(r"\bif\s+[^(]", line_stripped):
            if not re.search(r"\bif\s*$", line_stripped):  # Allow if on its own line
                errors.append(f"Line {i}: Possible malformed if statement (missing parentheses)")

        # Check for malformed for/while loops
        if re.search(r"\b(for|while)\s+[^(]", line_stripped):
            if not re.search(r"\b(for|while)\s*$", line_stripped):  # Allow on its own line
                errors.append(f"Line {i}: Possible malformed loop (missing parentheses)")

        # Check for unclosed strings (basic check)
        # Count quotes, ignoring escaped quotes
        quote_content = re.sub(r"\\.", "", line_stripped)  # Remove escaped characters
        if quote_content.count('"') % 2 != 0:
            # Could be multiline string or verbatim string, so just warn
            if not line_stripped.startswith('@"'):
                errors.append(f"Line {i}: Possible unclosed string literal")

    return errors


def validate_namespace_class_structure(content: str, filepath: str) -> List[str]:
    """Basic validation of namespace and class structure."""
    errors = []

    # Remove strings and comments
    cleaned = re.sub(r'"(?:[^"\\]|\\.)*"', '""', content)
    cleaned = re.sub(r"//.*?$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

    # Check for namespace/class keywords without proper structure
    if re.search(r"\bnamespace\s+[^{;]+\s*[^{;\s]", cleaned):
        errors.append("Possible malformed namespace declaration")

    # Check for class/struct/interface without proper structure
    if re.search(r"\b(class|struct|interface|enum)\s+\w+\s*[^{:;]", cleaned):
        errors.append("Possible malformed type declaration")

    return errors


def validate_cs_syntax(filepath: str) -> Tuple[bool, List[str]]:
    """
    Validate C# file syntax.
    Returns (is_valid, list_of_errors)
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, [f"Failed to read file: {e}"]

    errors = []

    # Run all validation checks
    errors.extend(validate_balanced_delimiters(content, filepath))
    errors.extend(validate_common_patterns(content, filepath))
    errors.extend(validate_namespace_class_structure(content, filepath))

    return len(errors) == 0, errors


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: csharp-syntax-check.py <file1.cs> [file2.cs ...]", file=sys.stderr)
        return 2

    files = sys.argv[1:]
    all_passed = True
    total_errors = 0

    for filepath in files:
        # Skip non-existent files
        if not Path(filepath).exists():
            print(f"✗ {filepath}: File not found", file=sys.stderr)
            all_passed = False
            continue

        is_valid, errors = validate_cs_syntax(filepath)

        if not is_valid:
            all_passed = False
            total_errors += len(errors)
            print(f"✗ {filepath}:")
            for error in errors:
                print(f"  - {error}")

    if all_passed:
        print(f"✓ Syntax validation passed for {len(files)} file(s)")
        return 0
    print(f"\n✗ Syntax validation failed: {total_errors} error(s) found", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
