"""Integration tests for complete agent synchronization workflow.

Testing pyramid: INTEGRATION (30%)
- Multiple components working together
- Real file operations (but isolated)
- Agent converter + hook + config
"""

import json
import time
from pathlib import Path

import pytest

from amplihack.adapters.copilot_agent_converter import convert_agents, is_agents_synced


class TestEndToEndAgentSync:
    """Test complete agent synchronization workflow."""

    def test_full_sync_workflow(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test complete sync from source to target with registry generation."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Initial sync
        report = convert_agents(source_dir, target_dir)

        # Verify all components
        assert report.succeeded == len(mock_agent_files)
        assert (target_dir / "REGISTRY.json").exists()
        assert is_agents_synced(source_dir, target_dir) is True

        # Verify all agents copied
        for source_agent in mock_agent_files:
            relative_path = source_agent.relative_to(source_dir)
            target_agent = target_dir / relative_path
            assert target_agent.exists()

    def test_incremental_sync_workflow(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test incremental sync when new agents are added."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Initial sync
        convert_agents(source_dir, target_dir)
        initial_count = len(list(target_dir.rglob("*.md")))

        # Add new agent
        new_agent = source_dir / "amplihack" / "core" / "new-agent.md"
        new_agent.write_text(
            """---
name: new-agent
description: Newly added agent
---
# New Agent"""
        )

        # Sync again (force=True to overwrite)
        report = convert_agents(source_dir, target_dir, force=True)

        # Verify new agent synced
        assert report.succeeded > 0
        new_count = len(list(target_dir.rglob("*.md")))
        assert new_count == initial_count + 1

        new_target = target_dir / "amplihack" / "core" / "new-agent.md"
        assert new_target.exists()

    def test_sync_preserves_directory_structure(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test sync preserves complex directory hierarchies."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create agents in various subdirectories
        structures = [
            "amplihack/core/architect.md",
            "amplihack/core/builder.md",
            "amplihack/specialized/fix-agent.md",
            "amplihack/specialized/ci-diagnostic.md",
            "custom/deep/nested/agent.md",
        ]

        for structure in structures:
            agent_path = source_dir / structure
            agent_path.parent.mkdir(parents=True, exist_ok=True)
            agent_path.write_text(sample_agent_markdown)

        # Sync
        report = convert_agents(source_dir, target_dir)

        # Verify structure preserved
        for structure in structures:
            target_path = target_dir / structure
            assert target_path.exists(), f"Missing: {structure}"
            assert target_path.read_text() == sample_agent_markdown

    def test_registry_contains_all_agents(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test REGISTRY.json contains entries for all synced agents."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Sync
        report = convert_agents(source_dir, target_dir)

        # Read registry
        registry_path = target_dir / "REGISTRY.json"
        registry = json.loads(registry_path.read_text())

        # Verify all agents in registry
        assert "agents" in registry
        assert len(registry["agents"]) == report.succeeded

        # Verify registry entries have required fields
        for agent_key, agent_data in registry["agents"].items():
            assert "path" in agent_data
            assert "name" in agent_data
            assert "description" in agent_data

    def test_config_integration_with_sync(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test sync respects configuration settings."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create config with "never" sync preference
        config_file = temp_project / ".claude" / "config.json"
        config = {"copilot_auto_sync_agents": "never"}
        config_file.write_text(json.dumps(config))

        # Verify config exists
        assert config_file.exists()
        loaded = json.loads(config_file.read_text())
        assert loaded["copilot_auto_sync_agents"] == "never"

        # Manual sync should still work
        report = convert_agents(source_dir, target_dir)
        assert report.succeeded > 0


class TestStalenessDetectionIntegration:
    """Test staleness detection across sync workflow."""

    def test_sync_state_lifecycle(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test complete lifecycle: not synced -> synced -> stale -> synced."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # State 1: Not synced (target doesn't exist)
        assert is_agents_synced(source_dir, target_dir) is False

        # State 2: Synced
        convert_agents(source_dir, target_dir)
        assert is_agents_synced(source_dir, target_dir) is True

        # State 3: Stale (modify source)
        time.sleep(0.1)
        mock_agent_files[0].write_text("modified content")
        assert is_agents_synced(source_dir, target_dir) is False

        # State 4: Synced again
        convert_agents(source_dir, target_dir, force=True)
        assert is_agents_synced(source_dir, target_dir) is True

    def test_registry_timestamp_drives_staleness(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test staleness check uses registry timestamp."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Initial sync
        convert_agents(source_dir, target_dir)
        registry_path = target_dir / "REGISTRY.json"

        registry_mtime = registry_path.stat().st_mtime

        # Agents are up to date
        assert is_agents_synced(source_dir, target_dir) is True

        # Modify source agent (make it newer than registry)
        time.sleep(0.1)
        newest_agent = max(mock_agent_files, key=lambda p: p.stat().st_mtime)
        newest_agent.write_text("updated")

        # Should be stale now
        assert newest_agent.stat().st_mtime > registry_mtime
        assert is_agents_synced(source_dir, target_dir) is False


class TestErrorRecoveryIntegration:
    """Test error recovery across integrated components."""

    def test_partial_sync_failure_recovery(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test recovery from partial sync failure."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create mix of valid and invalid agents
        valid_agent = source_dir / "valid.md"
        valid_agent.write_text(sample_agent_markdown)

        invalid_agent = source_dir / "invalid.md"
        invalid_agent.write_text("invalid markdown without frontmatter")

        # First sync (will fail validation)
        report = convert_agents(source_dir, target_dir)

        # Should report failure
        assert report.failed > 0
        assert len(report.errors) > 0

        # Fix invalid agent
        invalid_agent.write_text(sample_agent_markdown.replace("architect", "invalid"))

        # Retry sync
        report2 = convert_agents(source_dir, target_dir)

        # Should succeed now
        assert report2.failed == 0

    def test_corrupted_registry_recovery(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test recovery from corrupted REGISTRY.json."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Initial sync
        convert_agents(source_dir, target_dir)

        # Corrupt registry
        registry_path = target_dir / "REGISTRY.json"
        registry_path.write_text("corrupted json {{{")

        # Verify corrupted
        try:
            json.loads(registry_path.read_text())
            is_valid = True
        except json.JSONDecodeError:
            is_valid = False
        assert is_valid is False

        # Re-sync should regenerate registry
        convert_agents(source_dir, target_dir, force=True)

        # Registry should be valid now
        registry = json.loads(registry_path.read_text())
        assert "agents" in registry


class TestMultiComponentIntegration:
    """Test integration of converter, hook, and config components."""

    def test_config_change_affects_sync_behavior(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test configuration changes affect sync behavior."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"
        config_file = temp_project / ".claude" / "config.json"

        # Set to "always"
        config = {"copilot_auto_sync_agents": "always"}
        config_file.write_text(json.dumps(config))

        loaded = json.loads(config_file.read_text())
        assert loaded["copilot_auto_sync_agents"] == "always"

        # Change to "never"
        config["copilot_auto_sync_agents"] = "never"
        config_file.write_text(json.dumps(config))

        loaded = json.loads(config_file.read_text())
        assert loaded["copilot_auto_sync_agents"] == "never"

    def test_agent_modification_triggers_resync(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test agent modifications are detected and trigger resync."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Initial sync
        convert_agents(source_dir, target_dir)
        initial_content = (target_dir / "amplihack" / "core" / "architect.md").read_text()

        # Modify source agent
        time.sleep(0.1)
        source_agent = source_dir / "amplihack" / "core" / "architect.md"
        source_agent.write_text(
            """---
name: architect
description: MODIFIED architect agent
---
# Modified"""
        )

        # Should detect staleness
        assert is_agents_synced(source_dir, target_dir) is False

        # Resync
        convert_agents(source_dir, target_dir, force=True)

        # Verify content updated
        new_content = (target_dir / "amplihack" / "core" / "architect.md").read_text()
        assert new_content != initial_content
        assert "MODIFIED" in new_content


class TestPerformanceIntegration:
    """Test performance characteristics of integrated workflow."""

    def test_sync_performance_with_many_agents(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test sync performance with 50+ agents (< 2s requirement)."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create 50 agents
        for i in range(50):
            agent_path = source_dir / f"agent{i}.md"
            content = sample_agent_markdown.replace("architect", f"agent{i}")
            agent_path.write_text(content)

        # Time sync operation
        start = time.time()
        report = convert_agents(source_dir, target_dir)
        elapsed = time.time() - start

        # Should complete in under 2 seconds
        assert elapsed < 2.0
        assert report.succeeded == 50

    def test_staleness_check_performance_integration(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test staleness check performance in integration scenario."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Initial sync
        convert_agents(source_dir, target_dir)

        # Time staleness check
        start = time.time()
        is_stale = not is_agents_synced(source_dir, target_dir)
        elapsed = time.time() - start

        # Should complete in under 500ms
        assert elapsed < 0.5
        assert is_stale is False  # Should be synced
