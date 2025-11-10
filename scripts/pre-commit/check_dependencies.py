#!/usr/bin/env python3
"""Dependency validation for pre-commit hook.

Validates that optional dependencies are properly handled with try/except.
Catches issues like importing Rich without graceful fallback.

Usage:
    python scripts/pre-commit/check_dependencies.py file1.py file2.py

Exit Codes:
    0: All dependencies properly handled
    1: Missing try/except for optional imports
"""

import ast
import sys
from pathlib import Path
from typing import List, Set, Tuple

# Known optional dependencies that require try/except handling
OPTIONAL_DEPENDENCIES = {
    "rich": [
        "rich.console",
        "rich.layout",
        "rich.live",
        "rich.panel",
        "rich.table",
        "rich.text",
        "rich",
    ],
    "pytest": ["pytest"],
    "mypy": ["mypy"],
}


def extract_imports(file_path: Path) -> Tuple[Set[str], Set[str]]:
    """Extract imports and identify which are in try/except blocks.

    Returns:
        Tuple of (all_imports, protected_imports)
    """
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        all_imports = set()
        protected_imports = set()

        def visit_node(node, in_try=False):
            """Visit AST nodes recursively, tracking try/except context."""
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                all_imports.add(module)
                if in_try:
                    protected_imports.add(module)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    all_imports.add(alias.name)
                    if in_try:
                        protected_imports.add(alias.name)

            elif isinstance(node, ast.Try):
                # Process try block - mark imports as protected
                for child in ast.walk(node):
                    if isinstance(child, (ast.ImportFrom, ast.Import)):
                        visit_node(child, in_try=True)

            # Recurse into child nodes
            for child in ast.iter_child_nodes(node):
                visit_node(child, in_try)

        visit_node(tree)
        return all_imports, protected_imports

    except Exception:
        return set(), set()


def check_optional_dependencies(file_path: Path) -> List[str]:
    """Check if optional dependencies have proper try/except handling."""
    errors = []

    try:
        all_imports, protected_imports = extract_imports(file_path)

        # Check each optional dependency
        for dep_name, dep_modules in OPTIONAL_DEPENDENCIES.items():
            # Find if any of this dependency's modules are imported
            imported_modules = []
            for module in all_imports:
                for dep_module in dep_modules:
                    if module == dep_module or module.startswith(f"{dep_module}."):
                        imported_modules.append(module)

            # If imported, check if protected
            for module in imported_modules:
                if module not in protected_imports:
                    errors.append(
                        f"{file_path}: Optional dependency '{dep_name}' imported without try/except\n"
                        f"  Module: {module}\n"
                        f"  Fix: Wrap import in try/except ImportError block\n"
                        f"  Example:\n"
                        f"    try:\n"
                        f"        from {module} import ...\n"
                        f"    except ImportError:\n"
                        f"        # Handle missing dependency\n"
                        f"        pass"
                    )

    except Exception as e:
        errors.append(f"{file_path}: Error checking dependencies: {e}")

    return errors


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("No files to check")
        sys.exit(0)

    files = [Path(f) for f in sys.argv[1:] if f.endswith(".py")]

    if not files:
        print("No Python files to check")
        sys.exit(0)

    print(f"Checking optional dependencies for {len(files)} file(s)...")

    all_errors = []
    for file_path in files:
        errors = check_optional_dependencies(file_path)
        if errors:
            all_errors.extend(errors)
            print(f"  ❌ {file_path}: {len(errors)} issue(s)")
        else:
            print(f"  ✅ {file_path}: OK")

    if all_errors:
        print("\n" + "=" * 60)
        print("❌ DEPENDENCY VALIDATION FAILED - FIX BEFORE COMMITTING")
        print("=" * 60)
        print("\nOptional Dependency Issues:")
        for error in all_errors:
            print(f"\n{error}")
        sys.exit(1)

    print("\n✅ All optional dependencies properly handled!")
    sys.exit(0)


if __name__ == "__main__":
    main()
