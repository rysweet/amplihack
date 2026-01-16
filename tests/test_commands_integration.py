"""Tests for command integration with Copilot CLI.

Tests:
- Command parsing and validation
- Command conversion (Claude Code → Copilot CLI)
- Command invocation wrapper
- Registry generation
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from amplihack.adapters.copilot_command_converter import (
    parse_command,
    validate_command,
    adapt_command_for_copilot,
    convert_single_command,
    convert_commands,
    is_commands_synced,
    categorize_command,
)
from amplihack.copilot.command_wrapper import (
    invoke_copilot_command,
    list_available_commands,
    CommandResult,
)


@pytest.fixture
def sample_command(tmp_path):
    """Create a sample command file for testing."""
    command_file = tmp_path / "test-command.md"
    content = """---
name: amplihack:test
version: 1.0.0
description: Test command
triggers:
  - "test this"
  - "run test"
invokes:
  - type: subagent
    path: .claude/agents/test.md
---

# Test Command

## Usage

`/test <ARGS>`

## Process

1. Read @.claude/context/PHILOSOPHY.md
2. Use Task(subagent_type="test")
3. Use Skill(skill="test-skill")
"""
    command_file.write_text(content)
    return command_file


class TestCommandParsing:
    """Test command parsing functionality."""

    def test_parse_valid_command(self, sample_command):
        """Test parsing a valid command file."""
        result = parse_command(sample_command)

        assert 'frontmatter' in result
        assert 'body' in result
        assert result['frontmatter']['name'] == 'amplihack:test'
        assert result['frontmatter']['version'] == '1.0.0'
        assert 'Test Command' in result['body']

    def test_parse_command_without_frontmatter(self, tmp_path):
        """Test parsing a command without frontmatter fails."""
        command_file = tmp_path / "no-frontmatter.md"
        command_file.write_text("# Just a markdown file")

        with pytest.raises(ValueError, match="missing frontmatter"):
            parse_command(command_file)

    def test_parse_command_invalid_yaml(self, tmp_path):
        """Test parsing command with invalid YAML fails."""
        command_file = tmp_path / "invalid-yaml.md"
        command_file.write_text("---\n  invalid: yaml: syntax\n---\n\nContent")

        with pytest.raises(ValueError, match="Invalid YAML"):
            parse_command(command_file)


class TestCommandValidation:
    """Test command validation functionality."""

    def test_validate_valid_command(self, sample_command):
        """Test validating a valid command."""
        error = validate_command(sample_command)
        assert error is None

    def test_validate_missing_name(self, tmp_path):
        """Test validation fails for missing name."""
        command_file = tmp_path / "no-name.md"
        content = """---
description: Test command
---

Content
"""
        command_file.write_text(content)

        error = validate_command(command_file)
        assert error is not None
        assert "Missing 'name'" in error

    def test_validate_missing_description(self, tmp_path):
        """Test validation fails for missing description."""
        command_file = tmp_path / "no-description.md"
        content = """---
name: test-command
---

Content
"""
        command_file.write_text(content)

        error = validate_command(command_file)
        assert error is not None
        assert "Missing 'description'" in error

    def test_validate_invalid_name_format(self, tmp_path):
        """Test validation fails for invalid name format."""
        command_file = tmp_path / "invalid-name.md"
        content = """---
name: "invalid name with spaces!"
description: Test
---

Content
"""
        command_file.write_text(content)

        error = validate_command(command_file)
        assert error is not None
        assert "Invalid command name" in error


class TestCommandAdaptation:
    """Test command adaptation for Copilot CLI."""

    def test_adapt_replaces_claude_references(self, sample_command):
        """Test adaptation replaces .claude/ with .github/."""
        cmd = parse_command(sample_command)
        adapted = adapt_command_for_copilot(cmd)

        assert '@.github/context/' in adapted['body']
        assert '@.claude/context/' not in adapted['body']

    def test_adapt_replaces_docs_references(self):
        """Test adaptation replaces @docs/ with @."""
        cmd = {
            'frontmatter': {'name': 'test'},
            'body': 'Reference @docs/guide.md'
        }
        adapted = adapt_command_for_copilot(cmd)

        assert '@guide.md' in adapted['body'] or '@docs/' not in adapted['body']

    def test_adapt_preserves_frontmatter(self, sample_command):
        """Test adaptation preserves frontmatter."""
        cmd = parse_command(sample_command)
        adapted = adapt_command_for_copilot(cmd)

        assert adapted['frontmatter'] == cmd['frontmatter']

    def test_adapt_updates_skill_invocations(self):
        """Test adaptation updates Skill() patterns."""
        cmd = {
            'frontmatter': {'name': 'test'},
            'body': 'Use Skill(skill="test-skill")'
        }
        adapted = adapt_command_for_copilot(cmd)

        assert 'copilot --allow-all-tools -p' in adapted['body']
        assert '.github/skills/' in adapted['body']

    def test_adapt_updates_task_invocations(self):
        """Test adaptation updates Task() patterns."""
        cmd = {
            'frontmatter': {'name': 'test'},
            'body': 'Use Task(subagent_type="architect")'
        }
        adapted = adapt_command_for_copilot(cmd)

        assert 'copilot --allow-all-tools -p' in adapted['body']
        assert '.github/agents/' in adapted['body']


class TestCommandCategorization:
    """Test command categorization."""

    def test_categorize_amplihack_command(self):
        """Test categorization of core amplihack command."""
        path = Path(".claude/commands/amplihack/ultrathink.md")
        category = categorize_command(path)
        assert category == "core"

    def test_categorize_ddd_command(self):
        """Test categorization of DDD command."""
        path = Path(".claude/commands/ddd/1-plan.md")
        category = categorize_command(path)
        assert category == "ddd"

    def test_categorize_custom_command(self):
        """Test categorization of custom command."""
        path = Path(".claude/commands/custom/my-command.md")
        category = categorize_command(path)
        assert category == "custom"


class TestCommandConversion:
    """Test command conversion functionality."""

    def test_convert_single_command_success(self, sample_command, tmp_path):
        """Test successful single command conversion."""
        target_dir = tmp_path / "target"

        result = convert_single_command(sample_command, target_dir, force=False)

        assert result.status == "success"
        assert result.command_name == "test-command"
        assert result.target_path.exists()

    def test_convert_single_command_skip_existing(self, sample_command, tmp_path):
        """Test skipping existing command without force."""
        target_dir = tmp_path / "target"

        # First conversion
        convert_single_command(sample_command, target_dir, force=False)

        # Second conversion without force
        result = convert_single_command(sample_command, target_dir, force=False)

        assert result.status == "skipped"
        assert "Target exists" in result.reason

    def test_convert_single_command_force_overwrite(self, sample_command, tmp_path):
        """Test force overwriting existing command."""
        target_dir = tmp_path / "target"

        # First conversion
        convert_single_command(sample_command, target_dir, force=False)

        # Second conversion with force
        result = convert_single_command(sample_command, target_dir, force=True)

        assert result.status == "success"

    def test_convert_commands_success(self, tmp_path):
        """Test converting multiple commands."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"

        # Create sample commands
        for i in range(3):
            cmd_file = source_dir / f"cmd{i}.md"
            content = f"""---
name: test-cmd-{i}
description: Test command {i}
---

Content {i}
"""
            cmd_file.write_text(content)

        report = convert_commands(source_dir, target_dir, force=True)

        assert report.total == 3
        assert report.succeeded == 3
        assert report.failed == 0
        assert (target_dir / "COMMANDS_REGISTRY.json").exists()

    def test_convert_commands_missing_source(self, tmp_path):
        """Test converting commands with missing source directory."""
        source_dir = tmp_path / "nonexistent"
        target_dir = tmp_path / "target"

        with pytest.raises(FileNotFoundError):
            convert_commands(source_dir, target_dir)

    def test_convert_commands_validation_failure(self, tmp_path):
        """Test conversion fails with invalid commands."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"

        # Create invalid command (missing name)
        cmd_file = source_dir / "invalid.md"
        content = """---
description: Invalid command
---

Content
"""
        cmd_file.write_text(content)

        report = convert_commands(source_dir, target_dir)

        assert report.failed == 1
        assert len(report.errors) > 0

    def test_convert_commands_registry_generation(self, tmp_path):
        """Test registry generation during conversion."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"

        # Create sample command
        cmd_file = source_dir / "test.md"
        content = """---
name: test-command
description: Test command
version: 1.0.0
triggers:
  - "test"
---

Content
"""
        cmd_file.write_text(content)

        report = convert_commands(source_dir, target_dir, force=True)

        # Check registry
        registry_path = target_dir / "COMMANDS_REGISTRY.json"
        assert registry_path.exists()

        registry = json.loads(registry_path.read_text())
        assert registry['version'] == '1.0.0'
        assert len(registry['commands']) == 1
        assert registry['commands'][0]['name'] == 'test-command'
        assert registry['metadata']['total_commands'] == 1


class TestCommandSync:
    """Test command synchronization checking."""

    def test_is_commands_synced_false_no_registry(self, tmp_path):
        """Test sync check returns false when registry doesn't exist."""
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()

        assert is_commands_synced(source_dir, target_dir) is False

    def test_is_commands_synced_true_up_to_date(self, tmp_path):
        """Test sync check returns true when commands are up to date."""
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create registry
        registry_path = target_dir / "COMMANDS_REGISTRY.json"
        registry_path.write_text("{}")

        # Create source command older than registry
        cmd_file = source_dir / "test.md"
        content = """---
name: test
description: Test
---

Content
"""
        cmd_file.write_text(content)

        # Touch registry to make it newer
        registry_path.touch()

        assert is_commands_synced(source_dir, target_dir) is True

    def test_is_commands_synced_false_outdated(self, tmp_path):
        """Test sync check returns false when commands are outdated."""
        import time

        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()
        target_dir.mkdir()

        # Create registry
        registry_path = target_dir / "COMMANDS_REGISTRY.json"
        registry_path.write_text("{}")

        time.sleep(0.1)

        # Create source command newer than registry
        cmd_file = source_dir / "test.md"
        content = """---
name: test
description: Test
---

Content
"""
        cmd_file.write_text(content)

        assert is_commands_synced(source_dir, target_dir) is False


class TestCommandInvocation:
    """Test command invocation wrapper."""

    def test_invoke_copilot_command_missing_file(self):
        """Test invocation with missing command file."""
        with pytest.raises(FileNotFoundError, match="Command not found"):
            invoke_copilot_command("nonexistent-command-that-does-not-exist")


class TestListCommands:
    """Test listing available commands."""

    def test_list_available_commands(self):
        """Test listing available commands (uses actual .github/commands)."""
        commands = list_available_commands()

        # We expect at least some commands if conversion ran
        # Check for core commands that should exist after conversion
        if len(commands) > 0:
            # Commands should be sorted
            assert commands == sorted(commands)
            # Should contain both core and ddd commands
            core_commands = [c for c in commands if c.startswith("amplihack/")]
            ddd_commands = [c for c in commands if c.startswith("ddd/")]
            assert len(core_commands) > 0 or len(ddd_commands) > 0
