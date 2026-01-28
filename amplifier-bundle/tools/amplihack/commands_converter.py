#!/usr/bin/env python3
"""
Commands Converter for GitHub Copilot CLI Integration

Converts Claude Code slash commands from .claude/commands/ to Copilot-friendly
documentation in .github/commands/.

Philosophy:
- Single source of truth: .claude/commands/
- Generated output: .github/commands/
- No duplication: Commands are converted, not copied
- Ruthlessly simple: Plain text conversion, no complex systems

Usage:
    python3 commands_converter.py [--watch] [--command NAME]

Options:
    --watch: Watch for changes and auto-convert
    --command NAME: Convert specific command only
"""

import argparse
import re
import sys
from pathlib import Path


class CommandsConverter:
    """Converts Claude Code commands to Copilot-friendly docs."""

    def __init__(self, root_dir: Path | None = None):
        """Initialize converter.

        Args:
            root_dir: Repository root (default: auto-detect)
        """
        self.root_dir = root_dir or self._find_root()
        self.commands_source = self.root_dir / ".claude" / "commands" / "amplihack"
        self.commands_target = self.root_dir / ".github" / "commands"

    def _find_root(self) -> Path:
        """Find repository root directory."""
        current = Path.cwd()
        while current != current.parent:
            if (current / ".claude").exists():
                return current
            current = current.parent
        raise RuntimeError("Could not find repository root (.claude/ directory)")

    def convert_all(self) -> dict[str, bool]:
        """Convert all commands.

        Returns:
            Dict mapping command name to success status
        """
        if not self.commands_source.exists():
            print(f"Error: Commands source directory not found: {self.commands_source}")
            return {}

        # Ensure target directory exists
        self.commands_target.mkdir(parents=True, exist_ok=True)

        results = {}
        for command_file in self.commands_source.glob("*.md"):
            command_name = command_file.stem
            try:
                self.convert_command(command_name)
                results[command_name] = True
                print(f"✓ Converted: {command_name}")
            except Exception as e:
                results[command_name] = False
                print(f"✗ Failed: {command_name} - {e}")

        return results

    def convert_command(self, command_name: str) -> None:
        """Convert a single command.

        Args:
            command_name: Name of command (without extension)
        """
        source_file = self.commands_source / f"{command_name}.md"
        target_file = self.commands_target / f"{command_name}.md"

        if not source_file.exists():
            raise FileNotFoundError(f"Command not found: {source_file}")

        # Read source content
        content = source_file.read_text()

        # Convert to Copilot-friendly format
        converted = self._convert_content(content, command_name)

        # Write to target
        target_file.write_text(converted)

    def _convert_content(self, content: str, command_name: str) -> str:
        """Convert command content to Copilot-friendly format.

        Args:
            content: Original command content
            command_name: Name of command

        Returns:
            Converted content
        """
        # Extract frontmatter if present
        frontmatter = self._extract_frontmatter(content)

        # Remove frontmatter from content
        content_without_frontmatter = self._remove_frontmatter(content)

        # Build converted document
        lines = []

        # Add header
        lines.append(f"# GitHub Copilot Command Reference: {command_name}")
        lines.append("")
        lines.append(f"**Source**: `.claude/commands/amplihack/{command_name}.md`")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Add metadata from frontmatter
        if frontmatter:
            lines.append("## Command Metadata")
            lines.append("")
            for key, value in frontmatter.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Add note about usage
        lines.append("## Usage with GitHub Copilot CLI")
        lines.append("")
        lines.append("This command is designed for Claude Code but the patterns and approaches")
        lines.append("can be referenced when using GitHub Copilot CLI.")
        lines.append("")
        lines.append("**Example**:")
        lines.append("```bash")
        lines.append("# Reference this command's approach")
        lines.append(f"gh copilot explain .github/commands/{command_name}.md")
        lines.append("")
        lines.append("# Use patterns from this command")
        lines.append(f'gh copilot suggest --context .github/commands/{command_name}.md "your task"')
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Add original content (with @ notation converted)
        lines.append("## Original Command Documentation")
        lines.append("")
        converted_content = self._convert_at_notation(content_without_frontmatter)
        lines.append(converted_content)

        return "\n".join(lines)

    def _extract_frontmatter(self, content: str) -> dict[str, str]:
        """Extract YAML frontmatter.

        Args:
            content: File content

        Returns:
            Frontmatter as dictionary
        """
        if not content.startswith("---"):
            return {}

        # Find end of frontmatter
        end_match = re.search(r"\n---\n", content)
        if not end_match:
            return {}

        frontmatter_text = content[3 : end_match.start()]

        # Parse simple YAML (key: value pairs)
        frontmatter = {}
        for line in frontmatter_text.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip()

        return frontmatter

    def _remove_frontmatter(self, content: str) -> str:
        """Remove frontmatter from content.

        Args:
            content: File content

        Returns:
            Content without frontmatter
        """
        if not content.startswith("---"):
            return content

        # Find end of frontmatter
        end_match = re.search(r"\n---\n", content)
        if not end_match:
            return content

        return content[end_match.end() :]

    def _convert_at_notation(self, content: str) -> str:
        """Convert @ notation to relative paths.

        Args:
            content: Content with @ notation

        Returns:
            Content with relative paths
        """
        # Replace @.claude/ with relative path from .github/commands/
        content = content.replace("@.claude/", "../../.claude/")

        # Replace [@file](path) with relative path
        content = re.sub(r"\[@([^\]]+)\]\(([^)]+)\)", r"[\1](../../\2)", content)

        return content

    def create_index(self) -> None:
        """Create index of all commands."""
        if not self.commands_target.exists():
            return

        # Collect all commands
        commands = []
        for command_file in sorted(self.commands_target.glob("*.md")):
            if command_file.name == "README.md":
                continue

            command_name = command_file.stem

            # Read first few lines to get description
            content = command_file.read_text()
            description = self._extract_description(content)

            commands.append(
                {"name": command_name, "file": command_file.name, "description": description}
            )

        # Create README
        lines = []
        lines.append("# GitHub Copilot Commands Reference")
        lines.append("")
        lines.append("Converted from Claude Code slash commands in `.claude/commands/amplihack/`.")
        lines.append("")
        lines.append("## Available Commands")
        lines.append("")

        for cmd in commands:
            lines.append(f"### {cmd['name']}")
            lines.append("")
            lines.append(f"**File**: `{cmd['file']}`")
            lines.append("")
            if cmd["description"]:
                lines.append(cmd["description"])
                lines.append("")
            lines.append(f"**View**: `gh copilot explain .github/commands/{cmd['file']}`")
            lines.append("")
            lines.append("---")
            lines.append("")

        readme_path = self.commands_target / "README.md"
        readme_path.write_text("\n".join(lines))
        print(f"✓ Created index: {readme_path}")

    def _extract_description(self, content: str) -> str:
        """Extract description from content.

        Args:
            content: File content

        Returns:
            Description (first paragraph after # header)
        """
        lines = content.split("\n")

        # Find first # header
        in_description = False
        description_lines = []

        for line in lines:
            if line.startswith("# "):
                in_description = True
                continue

            if in_description:
                if line.strip() == "":
                    if description_lines:
                        break
                    continue

                if line.startswith("#"):
                    break

                description_lines.append(line)

        return " ".join(description_lines).strip()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Claude Code commands to Copilot-friendly docs"
    )
    parser.add_argument("--watch", action="store_true", help="Watch for changes and auto-convert")
    parser.add_argument("--command", help="Convert specific command only")

    args = parser.parse_args()

    converter = CommandsConverter()

    if args.command:
        # Convert specific command
        try:
            converter.convert_command(args.command)
            print(f"✓ Converted command: {args.command}")
        except Exception as e:
            print(f"✗ Failed to convert {args.command}: {e}")
            sys.exit(1)
    elif args.watch:
        # Watch mode (simple polling)
        print("Watch mode not implemented yet. Use --command for single conversion.")
        print("Run without arguments to convert all commands.")
        sys.exit(1)
    else:
        # Convert all commands
        results = converter.convert_all()

        # Create index
        converter.create_index()

        # Print summary
        total = len(results)
        success = sum(1 for v in results.values() if v)
        failed = total - success

        print("")
        print(f"Conversion complete: {success}/{total} succeeded, {failed} failed")

        if failed > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
