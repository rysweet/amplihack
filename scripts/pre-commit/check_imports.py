#!/usr/bin/env python3
"""Import smoke test for pre-commit hook.

Validates all Python files can be imported without errors.
Catches missing type hint imports (Any, Optional, etc.).

Usage:
    python scripts/pre-commit/check_imports.py file1.py file2.py

Exit Codes:
    0: All imports successful
    1: Import errors found
"""

import ast
import json
import subprocess
import sys
from pathlib import Path

# Type hints that must be imported
REQUIRED_TYPE_IMPORTS = {
    "Any": "typing",
    "Optional": "typing",
    "Union": "typing",
    "List": "typing",
    "Dict": "typing",
    "Tuple": "typing",
    "TYPE_CHECKING": "typing",
}


def extract_used_types(file_path: Path) -> set:
    """Extract all type hints used in file using AST."""
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        used_types = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id in REQUIRED_TYPE_IMPORTS:
                    used_types.add(node.id)

        return used_types
    except Exception as e:
        # Log parse failures but return empty set to allow check to continue
        import logging

        logging.debug(f"Failed to extract type usage from {file_path}: {e}")
        return set()


def extract_actual_imports(file_path: Path) -> dict[str, set]:
    """Extract actual imports from file using AST.

    Returns:
        Dict mapping module names to sets of imported names
    """
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        imports = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module
                if module not in imports:
                    imports[module] = set()

                for alias in node.names:
                    imports[module].add(alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.name] = {"*"}  # Treat as importing everything

        return imports
    except Exception as e:
        # Log parse failures but return empty dict to allow check to continue
        import logging

        logging.debug(f"Failed to extract imports from {file_path}: {e}")
        return {}


def check_type_imports(file_path: Path) -> list[str]:
    """Check if used type hints are imported."""
    errors = []

    try:
        used_types = extract_used_types(file_path)
        actual_imports = extract_actual_imports(file_path)

        for type_name in used_types:
            module = REQUIRED_TYPE_IMPORTS[type_name]

            # Check if type is imported
            is_imported = (
                # Check "from module import type_name"
                (module in actual_imports and type_name in actual_imports[module])
                # Check "from module import *"
                or (module in actual_imports and "*" in actual_imports[module])
                # Check "import module" (allows module.TypeName usage)
                or (module in actual_imports and {"*"} == actual_imports.get(module, set()))
            )

            if not is_imported:
                errors.append(
                    f"{file_path}: {type_name} used but not imported\n"
                    f"  Fix: from {module} import {type_name}"
                )

    except Exception as e:
        errors.append(f"{file_path}: Error checking imports: {e}")

    return errors


def test_import(file_path: Path) -> tuple[Path, bool, str]:
    """Test if file can be imported successfully."""
    # Security: Validate file path is within repository
    try:
        file_path = file_path.resolve()
        repo_root = Path.cwd().resolve()
        file_path.relative_to(repo_root)
    except (ValueError, RuntimeError):
        return file_path, False, "Path traversal: File outside repository"

    # Convert to module name - handle both absolute and relative paths
    if file_path.is_absolute():
        try:
            rel_path = file_path.relative_to(Path.cwd())
        except ValueError:
            return file_path, False, "Cannot resolve relative path"
    else:
        rel_path = file_path

    if rel_path.parts[0] == "src":
        module_parts = rel_path.parts[1:-1] + (rel_path.stem,)
    else:
        module_parts = rel_path.parts[:-1] + (rel_path.stem,)

    module_name = ".".join(module_parts)

    # Security: Use json to safely pass module name (prevents code injection)
    # Instead of f-string interpolation, pass module name as argument
    code = """
import sys
import json
sys.path.insert(0, 'src')
module_name = json.loads(sys.argv[1])
try:
    __import__(module_name)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
"""

    try:
        result = subprocess.run(
            [sys.executable, "-c", code, json.dumps(module_name)],
            capture_output=True,
            text=True,
            timeout=15,  # Increased from 5 to 15 seconds
        )

        if result.returncode == 0:
            return file_path, True, ""
        return file_path, False, result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        return file_path, False, "Import timeout (>15s)"
    except Exception as e:
        return file_path, False, f"Test error: {e!s}"


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("No files to check")
        sys.exit(0)

    files = [Path(f) for f in sys.argv[1:] if f.endswith(".py")]

    if not files:
        print("No Python files to check")
        sys.exit(0)

    print(f"Checking imports for {len(files)} file(s)...")

    # Check type hint imports
    print("\n1. Validating type hint imports...")
    type_errors = []
    for file_path in files:
        errors = check_type_imports(file_path)
        type_errors.extend(errors)

    if type_errors:
        print("\n❌ Type import errors:")
        for error in type_errors:
            print(f"  {error}")

    # Test actual imports
    print("\n2. Testing module imports...")
    import_errors = []

    for file_path in files:
        file_path, success, error_msg = test_import(file_path)

        if not success:
            import_errors.append((file_path, error_msg))
            print(f"  ❌ {file_path}: FAILED")
        else:
            print(f"  ✅ {file_path}: OK")

    # Report results
    if import_errors or type_errors:
        print("\n" + "=" * 60)
        print("❌ IMPORT VALIDATION FAILED - FIX BEFORE COMMITTING")
        print("=" * 60)

        if type_errors:
            print("\nMissing Type Imports:")
            for error in type_errors:
                print(f"  {error}")

        if import_errors:
            print("\nImport Errors:")
            for file_path, error in import_errors:
                print(f"\n  {file_path}:")
                print(f"    {error}")

        sys.exit(1)

    print("\n✅ All imports valid!")
    sys.exit(0)


if __name__ == "__main__":
    main()
