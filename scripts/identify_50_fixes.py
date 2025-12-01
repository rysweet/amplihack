#!/usr/bin/env python3
"""
Identify 50 specific, verifiable fixes from the codebase.
Outputs a JSON file with concrete fix descriptions and file locations.
"""

import ast
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent


class FixIdentifier(ast.NodeVisitor):
    """AST visitor to identify code issues."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.issues: list[dict[str, Any]] = []
        self.current_class = None
        self.current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions."""
        old_function = self.current_function
        self.current_function = node.name

        # Check for missing type hints
        if not node.returns:
            self.issues.append(
                {
                    "type": "missing_return_type",
                    "severity": "low",
                    "location": f"{self.file_path}:{node.lineno}",
                    "function": node.name,
                    "class": self.current_class,
                    "fix": f"Add return type hint to {node.name}",
                }
            )

        # Check for missing docstrings
        if not ast.get_docstring(node):
            self.issues.append(
                {
                    "type": "missing_docstring",
                    "severity": "low",
                    "location": f"{self.file_path}:{node.lineno}",
                    "function": node.name,
                    "class": self.current_class,
                    "fix": f"Add docstring to {node.name}",
                }
            )

        # Check for missing parameter type hints
        for arg in node.args.args:
            if not arg.annotation and arg.arg != "self" and arg.arg != "cls":
                self.issues.append(
                    {
                        "type": "missing_param_type",
                        "severity": "low",
                        "location": f"{self.file_path}:{node.lineno}",
                        "function": node.name,
                        "parameter": arg.arg,
                        "fix": f"Add type hint to parameter '{arg.arg}' in {node.name}",
                    }
                )

        self.generic_visit(node)
        self.current_function = old_function

    def visit_Try(self, node: ast.Try):
        """Visit try-except blocks."""
        # Check for bare except clauses
        for handler in node.handlers:
            if handler.type is None:
                self.issues.append(
                    {
                        "type": "bare_except",
                        "severity": "medium",
                        "location": f"{self.file_path}:{handler.lineno}",
                        "function": self.current_function,
                        "fix": "Replace bare 'except:' with specific exception type",
                    }
                )

            # Check for pass in except
            if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                self.issues.append(
                    {
                        "type": "silent_exception",
                        "severity": "medium",
                        "location": f"{self.file_path}:{handler.lineno}",
                        "function": self.current_function,
                        "fix": "Add logging or proper error handling in except block",
                    }
                )

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definitions."""
        old_class = self.current_class
        self.current_class = node.name

        # Check for missing class docstrings
        if not ast.get_docstring(node):
            self.issues.append(
                {
                    "type": "missing_class_docstring",
                    "severity": "low",
                    "location": f"{self.file_path}:{node.lineno}",
                    "class": node.name,
                    "fix": f"Add docstring to class {node.name}",
                }
            )

        self.generic_visit(node)
        self.current_class = old_class


def analyze_file(file_path: Path) -> list[dict[str, Any]]:
    """Analyze a single Python file for issues."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        visitor = FixIdentifier(str(file_path.relative_to(REPO_ROOT)))
        visitor.visit(tree)
        return visitor.issues
    except Exception:
        return []


def find_missing_logging(file_path: Path) -> list[dict[str, Any]]:
    """Find functions that should have logging but don't."""
    issues = []
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Check if file imports logging
        has_logging_import = "import logging" in content

        if has_logging_import:
            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_body = ast.unparse(node) if hasattr(ast, "unparse") else ""
                    # Check for error handling without logging
                    if (
                        "except" in func_body
                        and "logger." not in func_body
                        and "logging." not in func_body
                    ):
                        issues.append(
                            {
                                "type": "missing_error_logging",
                                "severity": "medium",
                                "location": f"{file_path.relative_to(REPO_ROOT)}:{node.lineno}",
                                "function": node.name,
                                "fix": f"Add logging to exception handler in {node.name}",
                            }
                        )
    except Exception:
        pass

    return issues


def find_missing_validation(file_path: Path) -> list[dict[str, Any]]:
    """Find functions that accept parameters without validation."""
    issues = []
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Functions with parameters that might need validation
                for arg in node.args.args:
                    if arg.arg in ["path", "file_path", "directory", "url", "data"]:
                        # Check if function body has validation
                        func_source = ast.get_source_segment(content, node)
                        if (
                            func_source
                            and "if not" not in func_source
                            and "raise ValueError" not in func_source
                        ):
                            issues.append(
                                {
                                    "type": "missing_input_validation",
                                    "severity": "medium",
                                    "location": f"{file_path.relative_to(REPO_ROOT)}:{node.lineno}",
                                    "function": node.name,
                                    "parameter": arg.arg,
                                    "fix": f"Add validation for parameter '{arg.arg}' in {node.name}",
                                }
                            )
                            break  # One issue per function
    except Exception:
        pass

    return issues


def main():
    """Main function to identify all fixes."""
    all_issues = []

    # Scan Python files
    python_files = list(REPO_ROOT.rglob("*.py"))
    print(f"Scanning {len(python_files)} Python files...")

    for file_path in python_files:
        # Skip virtual environments and build directories
        if any(
            part in file_path.parts
            for part in [".venv", "venv", "__pycache__", ".git", "node_modules", "build", "dist"]
        ):
            continue

        # AST-based analysis
        issues = analyze_file(file_path)
        all_issues.extend(issues)

        # Pattern-based analysis
        logging_issues = find_missing_logging(file_path)
        all_issues.extend(logging_issues)

        validation_issues = find_missing_validation(file_path)
        all_issues.extend(validation_issues)

    print(f"Found {len(all_issues)} total issues")

    # Sort by severity and type
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_issues.sort(key=lambda x: (severity_order.get(x["severity"], 3), x["type"]))

    # Select top 50 issues across different types
    selected_issues = []
    issue_types = {}

    for issue in all_issues:
        issue_type = issue["type"]
        if issue_type not in issue_types:
            issue_types[issue_type] = 0

        # Limit each type to ensure diversity
        if issue_types[issue_type] < 15:
            selected_issues.append(issue)
            issue_types[issue_type] += 1

        if len(selected_issues) >= 50:
            break

    # Output results
    output_file = REPO_ROOT / "identified_fixes.json"
    with open(output_file, "w") as f:
        json.dump(
            {
                "total_issues_found": len(all_issues),
                "selected_for_fixing": len(selected_issues),
                "issue_types": issue_types,
                "issues": selected_issues,
            },
            f,
            indent=2,
        )

    print(f"\nSelected {len(selected_issues)} issues for fixing")
    print(f"Results saved to: {output_file}")
    print("\nIssue breakdown:")
    for issue_type, count in sorted(issue_types.items()):
        print(f"  {issue_type}: {count}")


if __name__ == "__main__":
    main()
