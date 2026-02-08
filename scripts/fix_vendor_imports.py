#!/usr/bin/env python3
"""Fix vendored blarify imports to use relative imports instead of absolute 'blarify' imports.

The vendored blarify code uses 'from blarify.foo import Bar' which fails when the code
is vendored under 'amplihack.vendor.blarify'. This script converts those to relative imports.
"""

import re
import sys
from pathlib import Path


def calculate_relative_import(file_path: Path, vendor_root: Path, import_module: str) -> str:
    """Calculate relative import path from current file to target module.

    Args:
        file_path: Path to the file being edited
        vendor_root: Root of the vendor/blarify directory
        import_module: The module being imported (e.g., 'blarify.utils.path_calculator')

    Returns:
        Relative import string (e.g., '..utils.path_calculator')
    """
    # Remove 'blarify.' prefix from import_module
    if import_module.startswith("blarify."):
        import_module = import_module[len("blarify.") :]

    # Calculate depth from file to vendor root
    file_relative = file_path.relative_to(vendor_root)
    depth = len(file_relative.parents) - 1  # -1 because we don't count the file itself

    # Build relative import
    if depth == 0:
        # Same directory
        return f".{import_module}"
    # Parent directories
    return f"{'.' * (depth + 1)}{import_module}"


def fix_imports_in_file(file_path: Path, vendor_root: Path, dry_run: bool = False) -> int:
    """Fix blarify imports in a single file.

    Args:
        file_path: Path to Python file
        vendor_root: Root of vendor/blarify directory
        dry_run: If True, only show what would be changed

    Returns:
        Number of imports fixed
    """
    content = file_path.read_text()
    original_content = content
    fixes = 0

    # Pattern 1: from blarify.module import something
    pattern1 = re.compile(r"from blarify\.([a-zA-Z0-9_.]+) import (.+)")

    def replace_import(match):
        nonlocal fixes
        module = f"blarify.{match.group(1)}"
        imports = match.group(2)

        # Calculate relative import
        relative = calculate_relative_import(file_path, vendor_root, module)
        fixes += 1

        return f"from {relative} import {imports}"

    content = pattern1.sub(replace_import, content)

    # Pattern 2: import blarify.module (less common but handle it)
    pattern2 = re.compile(r"import blarify\.([a-zA-Z0-9_.]+)")

    def replace_direct_import(match):
        nonlocal fixes
        # For direct imports, we'd need to know what's being imported
        # For now, flag it for manual conversion
        fixes += 1
        return f"# FIXME: convert to relative import: import blarify.{match.group(1)}"

    content = pattern2.sub(replace_direct_import, content)

    if fixes > 0 and content != original_content:
        if dry_run:
            print(f"\n{file_path.relative_to(vendor_root.parent.parent.parent)}:")
            print(f"  Would fix {fixes} imports")
        else:
            file_path.write_text(content)
            print(
                f"✅ {file_path.relative_to(vendor_root.parent.parent.parent)}: Fixed {fixes} imports"
            )

    return fixes


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Fix vendored blarify imports")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--vendor-root",
        type=Path,
        default=Path(__file__).parent.parent / "src" / "amplihack" / "vendor" / "blarify",
        help="Path to vendor/blarify directory",
    )

    args = parser.parse_args()

    vendor_root = args.vendor_root.resolve()
    if not vendor_root.exists():
        print(f"❌ Vendor root not found: {vendor_root}")
        return 1

    print(f"🔍 Scanning {vendor_root}")

    # Find all Python files
    py_files = list(vendor_root.rglob("*.py"))
    print(f"📄 Found {len(py_files)} Python files")

    if args.dry_run:
        print("\n🔬 DRY RUN - No files will be modified\n")

    total_fixes = 0
    files_modified = 0

    for py_file in py_files:
        fixes = fix_imports_in_file(py_file, vendor_root, args.dry_run)
        if fixes > 0:
            total_fixes += fixes
            files_modified += 1

    print(f"\n{'=' * 60}")
    if args.dry_run:
        print(f"Would fix {total_fixes} imports in {files_modified} files")
    else:
        print(f"✅ Fixed {total_fixes} imports in {files_modified} files")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
