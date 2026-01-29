#!/usr/bin/env python3
"""Fix vendored blarify imports to use amplihack.vendor.blarify namespace."""

import re
from pathlib import Path


def fix_imports_in_file(file_path: Path) -> tuple[bool, int]:
    """Fix blarify imports in a single file.

    Returns:
        Tuple of (changed, num_replacements)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content
        replacements = 0

        # Pattern 1: from blarify. → from amplihack.vendor.blarify.
        pattern1 = r"^from blarify\."
        replacement1 = r"from amplihack.vendor.blarify."
        content, count1 = re.subn(pattern1, replacement1, content, flags=re.MULTILINE)
        replacements += count1

        # Pattern 2: import blarify. → import amplihack.vendor.blarify.
        pattern2 = r"^import blarify\."
        replacement2 = r"import amplihack.vendor.blarify."
        content, count2 = re.subn(pattern2, replacement2, content, flags=re.MULTILINE)
        replacements += count2

        # Pattern 3: from blarify import → from amplihack.vendor.blarify import
        pattern3 = r"^from blarify import"
        replacement3 = r"from amplihack.vendor.blarify import"
        content, count3 = re.subn(pattern3, replacement3, content, flags=re.MULTILINE)
        replacements += count3

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, replacements

        return False, 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def main():
    """Fix all imports in vendored blarify code."""
    vendor_path = Path("./src/amplihack/vendor/blarify")

    if not vendor_path.exists():
        print(f"Error: {vendor_path} does not exist")
        return 1

    total_files = 0
    total_replacements = 0
    changed_files = []

    # Find all Python files
    for py_file in vendor_path.rglob("*.py"):
        changed, count = fix_imports_in_file(py_file)
        if changed:
            total_files += 1
            total_replacements += count
            changed_files.append((py_file, count))
            print(f"✓ {py_file.relative_to(vendor_path)}: {count} replacements")

    print("\n📊 Summary:")
    print(f"  Files changed: {total_files}")
    print(f"  Total replacements: {total_replacements}")

    if changed_files:
        print("\n✅ Successfully fixed all imports!")
        return 0
    print("\n⚠️  No imports found to fix")
    return 1


if __name__ == "__main__":
    exit(main())
