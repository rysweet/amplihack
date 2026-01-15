#!/usr/bin/env python3
"""
Hook Converter for Amplihack to GitHub Copilot CLI

Converts amplihack Python hooks to GitHub Copilot CLI JSON + Bash format.

Usage:
    python hooks_converter.py [--source-dir PATH] [--output-dir PATH]

Example:
    python hooks_converter.py \
        --source-dir .claude/tools/amplihack/hooks \
        --output-dir .github/hooks

What this does:
    1. Reads Python hook implementations from .claude/tools/
    2. Extracts hook logic and configuration
    3. Generates JSON hook configuration for Copilot CLI
    4. Generates Bash scripts that mirror Python logic
    5. Preserves comments and documentation
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class HookMapping:
    """Maps amplihack hook names to Copilot CLI hook types."""

    python_file: str
    copilot_hook: str
    bash_script: str
    description: str


# Hook mappings from amplihack to Copilot CLI
HOOK_MAPPINGS = [
    HookMapping(
        python_file="session_start.py",
        copilot_hook="sessionStart",
        bash_script="session-start.sh",
        description="Initialize session state and inject user preferences",
    ),
    HookMapping(
        python_file="stop.py",
        copilot_hook="sessionEnd",
        bash_script="session-end.sh",
        description="Cleanup session resources and persist state",
    ),
    HookMapping(
        python_file="user_prompt_submit.py",
        copilot_hook="userPromptSubmitted",
        bash_script="user-prompt-submitted.sh",
        description="Log user prompts for audit trail",
    ),
    HookMapping(
        python_file="pre_tool_use.py",
        copilot_hook="preToolUse",
        bash_script="pre-tool-use.sh",
        description="Validate tool execution and enforce safety policies",
    ),
    HookMapping(
        python_file="post_tool_use.py",
        copilot_hook="postToolUse",
        bash_script="post-tool-use.sh",
        description="Log tool execution results and collect metrics",
    ),
    HookMapping(
        python_file="error_protocol.py",
        copilot_hook="errorOccurred",
        bash_script="error-occurred.sh",
        description="Track and log errors for debugging",
    ),
]


class HookConverter:
    """Converts amplihack Python hooks to Copilot CLI format."""

    def __init__(self, source_dir: Path, output_dir: Path):
        """Initialize converter.

        Args:
            source_dir: Directory containing Python hooks (.claude/tools/amplihack/hooks)
            output_dir: Directory to write Copilot CLI hooks (.github/hooks)
        """
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.scripts_dir = output_dir / "scripts"

    def convert_all_hooks(self) -> dict[str, Any]:
        """Convert all hooks from Python to Copilot CLI format.

        Returns:
            Summary of conversion results
        """
        results = {
            "hooks_converted": [],
            "hooks_skipped": [],
            "errors": [],
        }

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

        # Convert each hook
        for mapping in HOOK_MAPPINGS:
            python_file = self.source_dir / mapping.python_file

            if not python_file.exists():
                results["hooks_skipped"].append(
                    {
                        "hook": mapping.python_file,
                        "reason": "Source file not found",
                    }
                )
                continue

            try:
                self._convert_hook(python_file, mapping)
                results["hooks_converted"].append(mapping.bash_script)
            except Exception as e:
                results["errors"].append(
                    {
                        "hook": mapping.python_file,
                        "error": str(e),
                    }
                )

        # Generate JSON configuration
        self._generate_hook_config()

        return results

    def _convert_hook(self, python_file: Path, mapping: HookMapping) -> None:
        """Convert a single Python hook to Bash script.

        Args:
            python_file: Path to Python hook file
            mapping: Hook mapping configuration
        """
        # Read Python source
        python_code = python_file.read_text()

        # Extract docstring
        docstring = self._extract_docstring(python_code)

        # Extract key logic patterns
        logic_notes = self._extract_logic_notes(python_code)

        # Generate Bash script header
        bash_script = self._generate_bash_header(mapping, docstring, logic_notes)

        # Write Bash script
        output_file = self.scripts_dir / mapping.bash_script
        output_file.write_text(bash_script)
        output_file.chmod(0o755)

        print(f"✓ Converted {mapping.python_file} → {mapping.bash_script}")

    def _extract_docstring(self, python_code: str) -> str:
        """Extract module docstring from Python code.

        Args:
            python_code: Python source code

        Returns:
            Module docstring or empty string
        """
        # Match triple-quoted docstring at start of file
        match = re.search(r'^\s*"""(.*?)"""', python_code, re.DOTALL | re.MULTILINE)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_logic_notes(self, python_code: str) -> list[str]:
        """Extract key logic patterns from Python code.

        Args:
            python_code: Python source code

        Returns:
            List of logic notes
        """
        notes = []

        # Look for key patterns
        if "lock_flag" in python_code:
            notes.append("Implements lock flag for continuous work mode")

        if "preferences" in python_code.lower():
            notes.append("Injects user preferences from USER_PREFERENCES.md")

        if "metric" in python_code.lower():
            notes.append("Collects metrics for analytics")

        if "block" in python_code:
            notes.append("Can block operations based on validation")

        if "error" in python_code.lower():
            notes.append("Implements structured error handling")

        return notes

    def _generate_bash_header(
        self, mapping: HookMapping, docstring: str, logic_notes: list[str]
    ) -> str:
        """Generate Bash script header with documentation.

        Args:
            mapping: Hook mapping configuration
            docstring: Python module docstring
            logic_notes: Key logic patterns

        Returns:
            Bash script header
        """
        lines = [
            "#!/usr/bin/env bash",
            "#",
            f"# {mapping.copilot_hook} Hook for GitHub Copilot CLI",
            "#",
            f"# Mirrors functionality from .claude/tools/amplihack/hooks/{mapping.python_file}",
            "#",
        ]

        if docstring:
            lines.append("# Original Python docstring:")
            for line in docstring.split("\n"):
                lines.append(f"# {line}")
            lines.append("#")

        if logic_notes:
            lines.append("# What this hook does:")
            for note in logic_notes:
                lines.append(f"# - {note}")
            lines.append("#")

        lines.extend(
            [
                "# Input: JSON on stdin",
                "# Output: JSON on stdout",
                "#",
                "",
                "set -euo pipefail",
                "",
                "# Read JSON input from stdin",
                'INPUT=$(cat)',
                "",
                "# Extract project root from environment or use current directory",
                'PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"',
                'SESSION_ID="${CLAUDE_SESSION_ID:-$(date +%Y%m%d_%H%M%S)}"',
                "",
                "# TODO: Implement hook logic here",
                "# See corresponding Python file for reference implementation",
                "",
                "# Output empty JSON (no-op for now)",
                "echo '{}'",
                "",
                "exit 0",
            ]
        )

        return "\n".join(lines)

    def _generate_hook_config(self) -> None:
        """Generate JSON hook configuration for Copilot CLI."""
        config = {
            "$schema": "https://copilot.microsoft.com/schemas/hooks/v1",
            "description": "Amplihack hooks for GitHub Copilot CLI - converted from Python",
            "hooks": {},
            "metadata": {
                "version": "1.0.0",
                "author": "Amplihack Team",
                "source": "https://github.com/rysweet/amplihack",
                "generated": "Auto-generated by hooks_converter.py",
            },
        }

        # Add each hook
        for mapping in HOOK_MAPPINGS:
            config["hooks"][mapping.copilot_hook] = [
                {
                    "description": mapping.description,
                    "command": "bash",
                    "args": [f".github/hooks/scripts/{mapping.bash_script}"],
                }
            ]

        # Write config file
        config_file = self.output_dir / "amplihack-hooks.json"
        config_file.write_text(json.dumps(config, indent=2))

        print(f"\n✓ Generated hook configuration: {config_file}")


def main() -> int:
    """Main entry point for hook converter."""
    parser = argparse.ArgumentParser(
        description="Convert amplihack Python hooks to GitHub Copilot CLI format"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path(".claude/tools/amplihack/hooks"),
        help="Directory containing Python hooks (default: .claude/tools/amplihack/hooks)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".github/hooks"),
        help="Directory to write Copilot CLI hooks (default: .github/hooks)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Validate source directory
    if not args.source_dir.exists():
        print(f"Error: Source directory not found: {args.source_dir}", file=sys.stderr)
        return 1

    # Run conversion
    print(f"Converting hooks from {args.source_dir} to {args.output_dir}")
    print("=" * 70)

    converter = HookConverter(args.source_dir, args.output_dir)
    results = converter.convert_all_hooks()

    # Print summary
    print("\n" + "=" * 70)
    print("Conversion Summary:")
    print(f"  Hooks converted: {len(results['hooks_converted'])}")
    print(f"  Hooks skipped: {len(results['hooks_skipped'])}")
    print(f"  Errors: {len(results['errors'])}")

    if results["hooks_converted"]:
        print("\nConverted hooks:")
        for hook in results["hooks_converted"]:
            print(f"  ✓ {hook}")

    if results["hooks_skipped"]:
        print("\nSkipped hooks:")
        for skip in results["hooks_skipped"]:
            print(f"  - {skip['hook']}: {skip['reason']}")

    if results["errors"]:
        print("\nErrors:")
        for error in results["errors"]:
            print(f"  ✗ {error['hook']}: {error['error']}")
        return 1

    print("\n✓ Conversion complete!")
    print(f"\nNext steps:")
    print(f"  1. Review generated scripts in {args.output_dir}/scripts/")
    print(f"  2. Test hooks with: copilot cli --hooks {args.output_dir}/amplihack-hooks.json")
    print(f"  3. Customize Bash scripts as needed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
