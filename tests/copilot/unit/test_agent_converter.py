"""Unit tests for agent conversion (copilot_agent_converter.py).

Testing pyramid: UNIT (60%)
- Fast execution (< 100ms per test)
- Heavy mocking of external dependencies
- Focus on logic and edge cases
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.adapters.copilot_agent_converter import (
    AgentConversion,
    ConversionReport,
    convert_agents,
    convert_single_agent,
    is_agents_synced,
    validate_agent,
)


class TestAgentValidation:
    """Test agent validation logic."""

    def test_validate_valid_agent(self, temp_project: Path, sample_agent_markdown: str):
        """Test validation of valid agent file."""
        agent_file = temp_project / ".claude" / "agents" / "test.md"
        agent_file.write_text(sample_agent_markdown)

        error = validate_agent(agent_file)
        assert error is None

    def test_validate_missing_name(self, temp_project: Path):
        """Test validation fails when name is missing."""
        agent_file = temp_project / ".claude" / "agents" / "test.md"
        agent_file.write_text(
            """---
description: Test agent
---
# Test"""
        )

        error = validate_agent(agent_file)
        assert error is not None
        assert "name" in error.lower()

    def test_validate_missing_description(self, temp_project: Path):
        """Test validation fails when description is missing."""
        agent_file = temp_project / ".claude" / "agents" / "test.md"
        agent_file.write_text(
            """---
name: test-agent
---
# Test"""
        )

        error = validate_agent(agent_file)
        assert error is not None
        assert "description" in error.lower()

    def test_validate_invalid_name_format(self, temp_project: Path):
        """Test validation fails with invalid characters in name."""
        agent_file = temp_project / ".claude" / "agents" / "test.md"
        agent_file.write_text(
            """---
name: "test@agent!"
description: Test agent
---
# Test"""
        )

        error = validate_agent(agent_file)
        assert error is not None
        assert "invalid" in error.lower()

    def test_validate_nonexistent_file(self, temp_project: Path):
        """Test validation handles missing files gracefully."""
        agent_file = temp_project / "nonexistent.md"

        error = validate_agent(agent_file)
        assert error is not None


class TestSingleAgentConversion:
    """Test single agent conversion."""

    def test_convert_valid_agent(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test successful conversion of valid agent."""
        source = temp_project / ".claude" / "agents" / "architect.md"
        target_dir = temp_project / ".github" / "agents"

        source.write_text(sample_agent_markdown)

        result = convert_single_agent(source, target_dir)

        assert result.status == "success"
        assert result.agent_name == "architect"
        assert result.target_path.exists()

    def test_convert_preserves_directory_structure(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test conversion preserves directory hierarchy."""
        source = (
            temp_project
            / ".claude"
            / "agents"
            / "amplihack"
            / "core"
            / "architect.md"
        )
        source.parent.mkdir(parents=True)
        source.write_text(sample_agent_markdown)

        target_dir = temp_project / ".github" / "agents"

        result = convert_single_agent(source, target_dir)

        assert result.status == "success"
        expected_path = target_dir / "amplihack" / "core" / "architect.md"
        assert result.target_path == expected_path
        assert expected_path.exists()

    def test_convert_skips_existing_without_force(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test conversion skips existing files without force flag."""
        source = temp_project / ".claude" / "agents" / "architect.md"
        target_dir = temp_project / ".github" / "agents"

        source.write_text(sample_agent_markdown)

        # Create existing target
        target = target_dir / "architect.md"
        target.parent.mkdir(parents=True)
        target.write_text("existing content")

        result = convert_single_agent(source, target_dir, force=False)

        assert result.status == "skipped"
        assert "exists" in result.reason.lower()
        assert target.read_text() == "existing content"  # Unchanged

    def test_convert_overwrites_with_force(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test conversion overwrites existing files with force flag."""
        source = temp_project / ".claude" / "agents" / "architect.md"
        target_dir = temp_project / ".github" / "agents"

        source.write_text(sample_agent_markdown)

        # Create existing target
        target = target_dir / "architect.md"
        target.parent.mkdir(parents=True)
        target.write_text("existing content")

        result = convert_single_agent(source, target_dir, force=True)

        assert result.status == "success"
        assert target.read_text() != "existing content"  # Updated

    def test_convert_handles_invalid_agent(self, temp_project: Path):
        """Test conversion handles invalid agent gracefully."""
        source = temp_project / ".claude" / "agents" / "invalid.md"
        source.write_text("invalid markdown without frontmatter")

        target_dir = temp_project / ".github" / "agents"

        result = convert_single_agent(source, target_dir)

        assert result.status == "failed"
        assert result.reason is not None


class TestBatchAgentConversion:
    """Test batch agent conversion."""

    def test_convert_all_agents_success(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test successful conversion of all agents."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        report = convert_agents(source_dir, target_dir)

        assert report.total == len(mock_agent_files)
        assert report.succeeded == len(mock_agent_files)
        assert report.failed == 0
        assert report.skipped == 0
        assert len(report.errors) == 0

    def test_convert_agents_creates_registry(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test conversion creates REGISTRY.json."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        report = convert_agents(source_dir, target_dir)

        registry_path = target_dir / "REGISTRY.json"
        assert registry_path.exists()

        import json

        registry = json.loads(registry_path.read_text())
        assert "agents" in registry
        assert len(registry["agents"]) == report.succeeded

    def test_convert_agents_missing_source_dir(self, temp_project: Path):
        """Test conversion fails gracefully with missing source directory."""
        source_dir = temp_project / "nonexistent"
        target_dir = temp_project / ".github" / "agents"

        with pytest.raises(FileNotFoundError) as exc_info:
            convert_agents(source_dir, target_dir)

        assert "not found" in str(exc_info.value).lower()

    def test_convert_agents_validation_errors(self, temp_project: Path):
        """Test conversion reports validation errors for all agents."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create invalid agents
        for i in range(3):
            agent_file = source_dir / f"invalid{i}.md"
            agent_file.write_text("invalid markdown")

        report = convert_agents(source_dir, target_dir)

        assert report.failed == 3
        assert len(report.errors) > 0

    def test_convert_agents_skips_readme(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test conversion skips README.md files."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Add README
        readme = source_dir / "README.md"
        readme.write_text("# Agents README")

        report = convert_agents(source_dir, target_dir)

        # Should only convert agent files, not README
        assert report.total == len(mock_agent_files)


class TestAgentSyncCheck:
    """Test agent synchronization checking."""

    def test_agents_not_synced_when_missing(self, temp_project: Path):
        """Test sync check returns False when .github/agents/ missing."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create source but not target
        (source_dir / "test.md").write_text("test")

        assert is_agents_synced(source_dir, target_dir) is False

    def test_agents_not_synced_when_registry_missing(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test sync check returns False when REGISTRY.json missing."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create target dir but no registry
        target_dir.mkdir(parents=True)

        assert is_agents_synced(source_dir, target_dir) is False

    def test_agents_synced_when_up_to_date(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test sync check returns True when agents are up to date."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Convert agents (creates registry)
        convert_agents(source_dir, target_dir)

        # Should be synced immediately after conversion
        assert is_agents_synced(source_dir, target_dir) is True

    def test_agents_not_synced_when_source_newer(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test sync check returns False when source agents are newer."""
        import time

        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Initial conversion
        convert_agents(source_dir, target_dir)

        # Wait and modify source agent
        time.sleep(0.1)
        mock_agent_files[0].write_text("updated content")

        # Should detect staleness
        assert is_agents_synced(source_dir, target_dir) is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_source_directory(self, temp_project: Path):
        """Test handling of empty source directory."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        report = convert_agents(source_dir, target_dir)

        assert report.total == 0
        assert len(report.errors) > 0

    def test_unicode_in_agent_content(self, temp_project: Path):
        """Test handling of Unicode characters in agent content."""
        source = temp_project / ".claude" / "agents" / "unicode.md"
        source.write_text(
            """---
name: unicode-test
description: Test with unicode 🚀 中文
---
# Unicode Test

Content with emojis 🎉 and Chinese 你好
"""
        )

        target_dir = temp_project / ".github" / "agents"

        result = convert_single_agent(source, target_dir)

        assert result.status == "success"
        content = result.target_path.read_text()
        assert "🚀" in content
        assert "中文" in content

    def test_deeply_nested_agent_structure(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test handling of deeply nested directory structures."""
        source = (
            temp_project
            / ".claude"
            / "agents"
            / "a"
            / "b"
            / "c"
            / "d"
            / "deep.md"
        )
        source.parent.mkdir(parents=True)
        source.write_text(sample_agent_markdown)

        target_dir = temp_project / ".github" / "agents"

        result = convert_single_agent(source, target_dir)

        assert result.status == "success"
        assert result.target_path.exists()
        assert "a/b/c/d" in str(result.target_path)
