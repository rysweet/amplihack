"""Contract tests for user-facing CLI command documentation.

These tests pin the intended command surface for interactive entrypoints:

- `amplihack claude` is the preferred explicit Claude launcher in user-facing docs
- `amplihack copilot` is the explicit Copilot launcher
- `amplihack launch` remains an alias in the CLI, but should not be taught as the
  primary command in setup/guide-style documentation

The suite protects the preferred public command surface from future docs drift.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


USER_FACING_GUIDES = (
    REPO_ROOT / "docs" / "CLAUDE_CODE_SETUP.md",
    REPO_ROOT / "docs" / "PROFILE_MANAGEMENT.md",
    REPO_ROOT / "docs" / "MIGRATION_GUIDE.md",
    REPO_ROOT / "docs" / "AUTO_MODE.md",
)

CLI_REFERENCE = REPO_ROOT / "docs" / "reference" / "cli.md"


@dataclass(frozen=True)
class CommandOccurrence:
    line_number: int
    text: str


class DocCommandSurface:
    def __init__(self, path: Path):
        self.path = path

    def read(self) -> str:
        if not self.path.exists():
            raise FileNotFoundError(f"Documentation file not found: {self.path}")
        return self.path.read_text(encoding="utf-8")

    def command_examples(self, command: str) -> list[CommandOccurrence]:
        occurrences: list[CommandOccurrence] = []
        in_code_block = False

        for line_number, line in enumerate(self.read().splitlines(), start=1):
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block and command in line:
                occurrences.append(CommandOccurrence(line_number=line_number, text=line.strip()))

        return occurrences

    def prose_mentions(self, phrase: str) -> list[CommandOccurrence]:
        occurrences: list[CommandOccurrence] = []
        in_code_block = False

        for line_number, line in enumerate(self.read().splitlines(), start=1):
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue

            if not in_code_block and phrase in line:
                occurrences.append(CommandOccurrence(line_number=line_number, text=line.strip()))

        return occurrences


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _format_occurrences(occurrences: list[CommandOccurrence]) -> str:
    return ", ".join(f"L{item.line_number}: {item.text}" for item in occurrences)


class TestDocCommandSurfaceHelpers:
    def test_command_examples_only_report_fenced_code_blocks(self, tmp_path: Path):
        markdown = tmp_path / "guide.md"
        markdown.write_text(
            "\n".join(
                [
                    "Use `amplihack launch` only when discussing aliases.",
                    "",
                    "```bash",
                    "amplihack claude",
                    "```",
                ]
            ),
            encoding="utf-8",
        )

        surface = DocCommandSurface(markdown)

        assert surface.command_examples("amplihack launch") == []
        assert surface.command_examples("amplihack claude") == [
            CommandOccurrence(line_number=4, text="amplihack claude")
        ]

    def test_prose_mentions_ignore_code_fences(self, tmp_path: Path):
        markdown = tmp_path / "guide.md"
        markdown.write_text(
            "\n".join(
                [
                    "Compatibility alias: `amplihack launch` still works.",
                    "",
                    "```bash",
                    "amplihack launch",
                    "```",
                ]
            ),
            encoding="utf-8",
        )

        surface = DocCommandSurface(markdown)

        assert surface.prose_mentions("amplihack launch") == [
            CommandOccurrence(
                line_number=1,
                text="Compatibility alias: `amplihack launch` still works.",
            )
        ]

    def test_missing_doc_raises_clear_file_not_found_error(self, tmp_path: Path):
        missing = tmp_path / "missing.md"

        with pytest.raises(FileNotFoundError, match="Documentation file not found"):
            DocCommandSurface(missing).read()


class TestCommandSurfaceContract:
    def test_top_level_help_lists_documented_interactive_entrypoints(self):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT / "src")
        result = subprocess.run(
            [sys.executable, "-m", "amplihack", "--help"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, result.stderr
        assert "launch" in result.stdout
        assert "claude" in result.stdout
        assert "copilot" in result.stdout

    def test_claude_code_setup_uses_claude_not_launch(self):
        surface = DocCommandSurface(REPO_ROOT / "docs" / "CLAUDE_CODE_SETUP.md")

        assert surface.command_examples("amplihack claude"), (
            "docs/CLAUDE_CODE_SETUP.md should show `amplihack claude` in its verification example"
        )
        assert not surface.command_examples("amplihack launch"), (
            "docs/CLAUDE_CODE_SETUP.md should not teach `amplihack launch` anymore"
        )

    @pytest.mark.parametrize("doc_path", USER_FACING_GUIDES, ids=_relative)
    def test_user_facing_guides_do_not_teach_launch_as_primary_command(self, doc_path: Path):
        surface = DocCommandSurface(doc_path)
        launch_examples = surface.command_examples("amplihack launch")

        assert not launch_examples, (
            f"{_relative(doc_path)} still teaches `amplihack launch` in a code block: "
            f"{_format_occurrences(launch_examples)}"
        )

    def test_cli_reference_documents_alias_context_and_explicit_entrypoints(self):
        surface = DocCommandSurface(CLI_REFERENCE)

        assert surface.command_examples("amplihack claude"), (
            "docs/reference/cli.md should document the explicit Claude launcher"
        )
        assert surface.command_examples("amplihack copilot"), (
            "docs/reference/cli.md should document the explicit Copilot launcher"
        )
        assert surface.command_examples("amplihack launch"), (
            "docs/reference/cli.md should mention the legacy alias when documenting command parity"
        )
        assert surface.prose_mentions("compatibility alias"), (
            "docs/reference/cli.md must explain that `launch` is an alias, not the preferred form"
        )

    def test_plain_amplihack_default_command_is_not_misclassified_as_launch(self, tmp_path: Path):
        markdown = tmp_path / "guide.md"
        markdown.write_text(
            "\n".join(
                [
                    "```bash",
                    "amplihack",
                    "amplihack claude",
                    "```",
                ]
            ),
            encoding="utf-8",
        )

        surface = DocCommandSurface(markdown)

        assert surface.command_examples("amplihack launch") == []
