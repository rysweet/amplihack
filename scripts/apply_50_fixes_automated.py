#!/usr/bin/env python3
"""
Automatically apply 50 specific fixes from identified_fixes.json.
Creates branches, applies fixes, commits, and pushes.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent


def run_git_command(cmd: list[str]) -> tuple[bool, str]:
    """Run a git command and return success status and output."""
    try:
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def filter_main_codebase_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter issues to only include main codebase (no worktrees, prioritize src/)."""
    filtered = []
    for issue in issues:
        location = issue["location"]
        # Skip worktrees
        if "worktrees/" in location:
            continue
        # Skip test files for now (focus on production code)
        if "/test_" in location or "/tests/" in location:
            continue
        filtered.append(issue)

    return filtered


def apply_bare_except_fix(file_path: Path, line_num: int, function_name: str) -> bool:
    """Fix bare except clause by replacing with Exception."""
    try:
        with open(file_path) as f:
            lines = f.readlines()

        # Find the bare except line
        for i in range(max(0, line_num - 5), min(len(lines), line_num + 5)):
            if "except:" in lines[i] and "except Exception" not in lines[i]:
                # Replace bare except with Exception
                lines[i] = lines[i].replace("except:", "except Exception:")

                with open(file_path, "w") as f:
                    f.writelines(lines)
                return True

        return False
    except Exception as e:
        print(f"Error applying bare except fix: {e}")
        return False


def apply_error_logging_fix(file_path: Path, line_num: int, function_name: str) -> bool:
    """Add logging to exception handler."""
    try:
        with open(file_path) as f:
            lines = f.readlines()

        # Check if file has logging import
        has_logging = any("import logging" in line for line in lines[:50])

        # Add logging import if not present
        if not has_logging:
            # Find first import statement
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    lines.insert(i + 1, "import logging\n\n")
                    line_num += 1  # Adjust line number
                    break

        # Find the except block around the line number
        for i in range(max(0, line_num - 2), min(len(lines), line_num + 10)):
            if "except" in lines[i]:
                # Find the body of except block
                indent = len(lines[i]) - len(lines[i].lstrip())
                body_indent = indent + 4

                # Look for the first line in except body
                for j in range(i + 1, min(len(lines), i + 15)):
                    if lines[j].strip() and not lines[j].strip().startswith("#"):
                        current_indent = len(lines[j]) - len(lines[j].lstrip())
                        if current_indent >= body_indent:
                            # Add logging statement before first line
                            log_line = (
                                " " * body_indent
                                + 'logger.exception(f"Error in {function_name}: {{e}}")\n'
                            )
                            lines.insert(j, log_line)

                            with open(file_path, "w") as f:
                                f.writelines(lines)
                            return True
                        break

        return False
    except Exception as e:
        print(f"Error applying error logging fix: {e}")
        return False


def apply_input_validation_fix(
    file_path: Path, line_num: int, function_name: str, parameter: str
) -> bool:
    """Add input validation for parameter."""
    try:
        with open(file_path) as f:
            lines = f.readlines()

        # Find function definition
        for i in range(max(0, line_num - 2), min(len(lines), line_num + 2)):
            if f"def {function_name}" in lines[i]:
                # Find function body start
                for j in range(i + 1, min(len(lines), i + 20)):
                    # Skip docstring
                    if '"""' in lines[j] or "'''" in lines[j]:
                        # Find end of docstring
                        for k in range(j + 1, min(len(lines), j + 50)):
                            if '"""' in lines[k] or "'''" in lines[k]:
                                j = k
                                break

                    # Find first real line of code
                    if lines[j].strip() and not lines[j].strip().startswith("#"):
                        indent = len(lines[j]) - len(lines[j].lstrip())

                        # Add validation based on parameter name
                        if parameter in ["path", "file_path", "directory"]:
                            validation = f"{' ' * indent}if not {parameter}:\n"
                            validation += f"{' ' * (indent + 4)}raise ValueError('Invalid {parameter}: cannot be empty')\n"
                        elif parameter == "url":
                            validation = f"{' ' * indent}if not {parameter} or not isinstance({parameter}, str):\n"
                            validation += (
                                f"{' ' * (indent + 4)}raise ValueError('Invalid URL provided')\n"
                            )
                        elif parameter == "data":
                            validation = f"{' ' * indent}if {parameter} is None:\n"
                            validation += (
                                f"{' ' * (indent + 4)}raise ValueError('Data cannot be None')\n"
                            )
                        else:
                            validation = f"{' ' * indent}if not {parameter}:\n"
                            validation += (
                                f"{' ' * (indent + 4)}raise ValueError('Invalid {parameter}')\n"
                            )

                        lines.insert(j, validation)

                        with open(file_path, "w") as f:
                            f.writelines(lines)
                        return True

        return False
    except Exception as e:
        print(f"Error applying input validation fix: {e}")
        return False


def apply_silent_exception_fix(file_path: Path, line_num: int, function_name: str) -> bool:
    """Fix silent exception (pass in except block)."""
    try:
        with open(file_path) as f:
            lines = f.readlines()

        # Find the except block with pass
        for i in range(max(0, line_num - 3), min(len(lines), line_num + 5)):
            if "pass" in lines[i] and i > 0:
                # Check if previous line is except
                for j in range(max(0, i - 3), i):
                    if "except" in lines[j]:
                        # Replace pass with logging
                        indent = len(lines[i]) - len(lines[i].lstrip())
                        lines[i] = (
                            f"{' ' * indent}logger.warning(f'Exception handled in {function_name}')\n"
                        )

                        # Ensure logging import exists
                        has_logging = any("import logging" in line for line in lines[:50])
                        if not has_logging:
                            for k, line in enumerate(lines):
                                if line.startswith("import ") or line.startswith("from "):
                                    lines.insert(k + 1, "import logging\n\n")
                                    break

                        with open(file_path, "w") as f:
                            f.writelines(lines)
                        return True

        return False
    except Exception as e:
        print(f"Error applying silent exception fix: {e}")
        return False


def apply_fix(issue: dict[str, Any], fix_number: int) -> bool:
    """Apply a single fix and create branch/commit."""
    location = issue["location"]
    parts = location.split(":")
    file_path = REPO_ROOT / parts[0]
    line_num = int(parts[1]) if len(parts) > 1 else 1

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return False

    # Create branch
    branch_name = f"fix/specific-{fix_number}"
    print(f"\n[{fix_number}/50] Creating branch: {branch_name}")

    success, output = run_git_command(["git", "checkout", "main"])
    if not success:
        print(f"Failed to checkout main: {output}")
        return False

    success, output = run_git_command(["git", "checkout", "-b", branch_name])
    if not success:
        print(f"Failed to create branch: {output}")
        return False

    # Apply the fix based on type
    fix_applied = False
    fix_type = issue["type"]
    function_name = issue.get("function", "unknown")

    print(f"Applying {fix_type} fix to {file_path}:{line_num} in {function_name}")

    if fix_type == "bare_except":
        fix_applied = apply_bare_except_fix(file_path, line_num, function_name)
    elif fix_type == "missing_error_logging":
        fix_applied = apply_error_logging_fix(file_path, line_num, function_name)
    elif fix_type == "missing_input_validation":
        parameter = issue.get("parameter", "param")
        fix_applied = apply_input_validation_fix(file_path, line_num, function_name, parameter)
    elif fix_type == "silent_exception":
        fix_applied = apply_silent_exception_fix(file_path, line_num, function_name)

    if not fix_applied:
        print("Failed to apply fix")
        run_git_command(["git", "checkout", "main"])
        run_git_command(["git", "branch", "-D", branch_name])
        return False

    # Commit the change
    success, _ = run_git_command(["git", "add", str(file_path)])
    if not success:
        print("Failed to stage changes")
        return False

    commit_message = (
        f"{issue['fix']}\n\nType: {fix_type}\nLocation: {location}\nFunction: {function_name}"
    )
    success, _ = run_git_command(["git", "commit", "-m", commit_message])
    if not success:
        print("Failed to commit")
        return False

    # Push to remote
    success, output = run_git_command(["git", "push", "-u", "origin", branch_name])
    if not success:
        print(f"Failed to push: {output}")
        return False

    print(f"Successfully applied fix {fix_number}/50")

    # Return to main
    run_git_command(["git", "checkout", "main"])

    return True


def main():
    """Main function."""
    # Load identified fixes
    fixes_file = REPO_ROOT / "identified_fixes.json"
    if not fixes_file.exists():
        print("identified_fixes.json not found. Run identify_50_fixes.py first.")
        sys.exit(1)

    with open(fixes_file) as f:
        data = json.load(f)

    issues = data["issues"]

    # Filter to main codebase
    main_issues = filter_main_codebase_issues(issues)

    if len(main_issues) < 50:
        print(f"Warning: Only found {len(main_issues)} issues in main codebase")
        print("Including some test files to reach 50...")
        # Add back test files if needed
        test_issues = [i for i in issues if "/test_" in i["location"] or "/tests/" in i["location"]]
        main_issues.extend(test_issues[: 50 - len(main_issues)])

    # Take first 50
    selected_issues = main_issues[:50]

    print(f"Applying 50 fixes from {len(issues)} total issues")
    print(f"Main codebase issues: {len(main_issues)}")

    # Apply each fix
    successes = 0
    failures = 0

    for i, issue in enumerate(selected_issues, 1):
        try:
            if apply_fix(issue, i):
                successes += 1
            else:
                failures += 1
        except Exception as e:
            print(f"Error applying fix {i}: {e}")
            failures += 1

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print("Total fixes: 50")
    print(f"Successful: {successes}")
    print(f"Failed: {failures}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
