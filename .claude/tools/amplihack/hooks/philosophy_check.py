#!/usr/bin/env python3
"""
Philosophy compliance checker for pre-commit.
Ensures code follows the project's ruthless simplicity principles.
"""

import ast
import sys
from typing import List, Tuple


class PhilosophyChecker(ast.NodeVisitor):
    """Check Python code for philosophy compliance."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[Tuple[int, str]] = []
        self.complexity_score = 0
        self.max_function_lines = 50
        self.max_complexity = 10

    def _check_function_length(self, node: ast.FunctionDef) -> None:
        """Check if function exceeds maximum line limit."""
        # Handle case where end_lineno might be None
        if node.end_lineno is None:
            return

        func_lines = node.end_lineno - node.lineno
        if func_lines > self.max_function_lines:
            self.violations.append(
                (
                    node.lineno,
                    f"Function '{node.name}' is too long ({func_lines} lines). "
                    f"Consider breaking it down (max: {self.max_function_lines})",
                )
            )

    def _check_placeholder_comments(self, node: ast.FunctionDef) -> None:
        """Check for forbidden placeholder comments in code."""
        forbidden_markers = ["TODO", "FIXME", "XXX", "HACK"]

        for child in ast.walk(node):
            if not isinstance(child, ast.Expr):
                continue
            if not isinstance(child.value, ast.Constant):
                continue
            if not isinstance(child.value.value, str):
                continue

            comment = child.value.value.upper()
            if any(marker in comment for marker in forbidden_markers):
                self.violations.append(
                    (
                        child.lineno,
                        f"Found placeholder comment in '{node.name}'. "
                        "No stubs or placeholders allowed.",
                    )
                )

    def _check_not_implemented(self, node: ast.FunctionDef) -> None:
        """Check for NotImplementedError usage."""
        for child in ast.walk(node):
            if not isinstance(child, ast.Raise):
                continue
            if not isinstance(child.exc, ast.Call):
                continue
            # Properly check if func is a Name node with an id attribute
            if not isinstance(child.exc.func, ast.Name):
                continue
            if child.exc.func.id == "NotImplementedError":
                self.violations.append(
                    (
                        child.lineno,
                        f"Function '{node.name}' contains NotImplementedError. No stubs allowed.",
                    )
                )

    def _check_pass_statements(self, node: ast.FunctionDef) -> None:
        """Check for pass statements indicating incomplete code."""
        for child in node.body:
            if isinstance(child, ast.Pass):
                self.violations.append(
                    (
                        child.lineno,
                        f"Function '{node.name}' contains 'pass' statement. "
                        "Implement real functionality or remove.",
                    )
                )

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _check_function_complexity(self, node: ast.FunctionDef) -> None:
        """Check if function complexity exceeds maximum."""
        complexity = self._calculate_complexity(node)

        if complexity > self.max_complexity:
            self.violations.append(
                (
                    node.lineno,
                    f"Function '{node.name}' is too complex (score: {complexity}). "
                    f"Consider simplifying (max: {self.max_complexity})",
                )
            )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function for all philosophy compliance rules."""
        self._check_function_length(node)
        self._check_placeholder_comments(node)
        self._check_not_implemented(node)
        self._check_pass_statements(node)
        self._check_function_complexity(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class complexity."""
        # Count public methods (single responsibility check)
        public_methods = [
            n for n in node.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
        ]

        if len(public_methods) > 7:  # Arbitrary but reasonable limit
            self.violations.append(
                (
                    node.lineno,
                    f"Class '{node.name}' has {len(public_methods)} public methods. "
                    "Consider splitting responsibilities.",
                )
            )

        self.generic_visit(node)


def check_file(filepath: str) -> List[str]:
    """Check a Python file for philosophy compliance."""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        checker = PhilosophyChecker(filepath)
        checker.visit(tree)

        return [f"{filepath}:{lineno}: {msg}" for lineno, msg in checker.violations]

    except SyntaxError as e:
        return [f"{filepath}:{e.lineno}: Syntax error: {e.msg}"]
    except Exception as e:
        return [f"{filepath}: Error checking file: {e}"]


def main() -> int:
    """Main entry point for pre-commit hook."""
    if len(sys.argv) < 2:
        print("No files to check")
        return 0

    all_violations = []
    for filepath in sys.argv[1:]:
        if filepath.endswith(".py"):
            violations = check_file(filepath)
            all_violations.extend(violations)

    if all_violations:
        print("Philosophy compliance violations found:")
        for violation in all_violations:
            print(f"  {violation}")
        print(f"\nTotal violations: {len(all_violations)}")
        print("\nRemember: Ruthless simplicity. Every line must earn its place.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
