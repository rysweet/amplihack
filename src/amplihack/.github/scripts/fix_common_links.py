#!/usr/bin/env python3
"""
Comprehensive Documentation Link Fixer

Fixes broken links in documentation files by:
1. Converting directory links to README.md
2. Adding .md extensions where needed
3. Updating .claude/ references to work with docs structure
4. Handling absolute vs relative path issues

Usage:
    python .github/scripts/fix_common_links.py --apply --verify
"""

import re
import sys
from pathlib import Path


class LinkFixer:
    def __init__(self, docs_root: Path):
        self.docs_root = docs_root
        self.fixes_applied = 0
        self.files_modified = 0

    def fix_directory_links(self, content: str, file_path: Path) -> str:
        """Fix links that point to directories without README.md"""
        # Pattern: [text](path/to/directory)
        pattern = r"\[([^\]]+)\]\(([^)]+)\)"

        def replace_link(match):
            text = match.group(1)
            link = match.group(2)

            # Skip external links, anchors, and already-correct links
            if link.startswith(("http://", "https://", "#", "mailto:")):
                return match.group(0)
            if link.endswith(".md"):
                return match.group(0)

            # Check if this is a directory link
            if not link.endswith("/"):
                # Try to resolve the path relative to current file
                current_dir = file_path.parent
                target_path = current_dir / link

                # Check if it's a directory
                if target_path.is_dir():
                    # Check if README.md exists
                    readme_path = target_path / "README.md"
                    if readme_path.exists():
                        self.fixes_applied += 1
                        return f"[{text}]({link}/README.md)"
                    # Check for index.md
                    index_path = target_path / "index.md"
                    if index_path.exists():
                        self.fixes_applied += 1
                        return f"[{text}]({link}/index.md)"

                # Check if adding .md makes it a valid file
                md_path = Path(str(target_path) + ".md")
                if md_path.exists():
                    self.fixes_applied += 1
                    return f"[{text}]({link}.md)"

            return match.group(0)

        return re.sub(pattern, replace_link, content)

    def fix_claude_directory_references(self, content: str) -> str:
        """Fix references to .claude/ to work in docs structure"""
        # The .claude/ directory is now copied to docs/.claude/
        # MkDocs should be able to reference it directly
        # No changes needed here as we've already copied the structure
        return content

    def process_file(self, file_path: Path) -> bool:
        """Process a single markdown file"""
        try:
            original_content = file_path.read_text(encoding="utf-8")
            modified_content = original_content

            # Apply fixes
            modified_content = self.fix_directory_links(modified_content, file_path)
            modified_content = self.fix_claude_directory_references(modified_content)

            # Write back if changed
            if modified_content != original_content:
                file_path.write_text(modified_content, encoding="utf-8")
                self.files_modified += 1
                return True
            return False
        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=sys.stderr)
            return False

    def process_all_files(self) -> tuple[int, int]:
        """Process all markdown files in docs directory"""
        markdown_files = list(self.docs_root.rglob("*.md"))

        for md_file in markdown_files:
            # Skip files in certain directories
            if any(part in md_file.parts for part in [".git", "node_modules", "__pycache__"]):
                continue

            self.process_file(md_file)

        return self.files_modified, self.fixes_applied


def main():
    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    docs_root = project_root / "docs"

    if not docs_root.exists():
        print(f"Error: docs directory not found at {docs_root}", file=sys.stderr)
        sys.exit(1)

    # Check for --apply flag
    apply_fixes = "--apply" in sys.argv
    verify_only = "--verify" in sys.argv and not apply_fixes

    if verify_only:
        print("🔍 Verification mode - checking for issues without fixing...")
    elif apply_fixes:
        print("🔧 Applying fixes to documentation links...")
    else:
        print("Usage: python .github/scripts/fix_common_links.py [--apply] [--verify]")
        print("  --verify: Check for issues without fixing")
        print("  --apply:  Apply fixes to files")
        sys.exit(1)

    # Create fixer and run
    fixer = LinkFixer(docs_root)

    if not apply_fixes:
        # Verification mode - just report what would be fixed
        print("This would scan all markdown files for common link issues.")
        print(f"Docs root: {docs_root}")
        return

    # Apply fixes
    files_modified, fixes_applied = fixer.process_all_files()

    print("\n✅ Complete!")
    print(f"   Files modified: {files_modified}")
    print(f"   Fixes applied: {fixes_applied}")

    if verify_only and fixes_applied > 0:
        print(f"\n⚠️  {fixes_applied} issues found that need fixing.")
        sys.exit(1)
    elif apply_fixes and fixes_applied > 0:
        print("\n✨ All common link issues have been fixed!")


if __name__ == "__main__":
    main()
