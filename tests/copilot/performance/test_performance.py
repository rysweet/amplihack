"""Performance tests for Copilot CLI integration.

Performance Requirements:
- Staleness check: < 500ms
- Full sync (50 agents): < 2s
- Agent conversion: < 100ms per agent
- Registry generation: < 500ms
"""

import time
from pathlib import Path

import pytest

from amplihack.adapters.copilot_agent_converter import (
    convert_agents,
    convert_single_agent,
    is_agents_synced,
)


class TestAgentConversionPerformance:
    """Test performance of individual agent conversion."""

    def test_single_agent_conversion_speed(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test single agent converts in < 100ms."""
        source = temp_project / ".claude" / "agents" / "test.md"
        source.write_text(sample_agent_markdown)

        target_dir = temp_project / ".github" / "agents"

        # Warm up
        convert_single_agent(source, target_dir)

        # Measure
        start = time.time()
        result = convert_single_agent(source, target_dir, force=True)
        elapsed = time.time() - start

        assert elapsed < 0.1  # 100ms
        assert result.status == "success"

    def test_batch_conversion_speed(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test batch conversion performance."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create 10 agents
        for i in range(10):
            agent_path = source_dir / f"agent{i}.md"
            content = sample_agent_markdown.replace("architect", f"agent{i}")
            agent_path.write_text(content)

        # Measure
        start = time.time()
        report = convert_agents(source_dir, target_dir)
        elapsed = time.time() - start

        # Should be well under 1s for 10 agents
        assert elapsed < 1.0
        assert report.succeeded == 10

        # Average per agent
        avg_per_agent = elapsed / 10
        assert avg_per_agent < 0.1  # < 100ms per agent


class TestSyncPerformance:
    """Test performance of full sync operations."""

    def test_full_sync_50_agents(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test full sync of 50 agents completes in < 2s."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create 50 agents
        for i in range(50):
            agent_path = source_dir / f"agent{i}.md"
            content = sample_agent_markdown.replace("architect", f"agent{i}")
            agent_path.write_text(content)

        # Measure
        start = time.time()
        report = convert_agents(source_dir, target_dir)
        elapsed = time.time() - start

        # Requirement: < 2s for 50 agents
        assert elapsed < 2.0
        assert report.succeeded == 50

        print(f"\n✓ Synced 50 agents in {elapsed:.3f}s ({elapsed/50*1000:.1f}ms/agent)")

    def test_incremental_sync_performance(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test incremental sync performance."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Initial sync
        convert_agents(source_dir, target_dir)

        # Add 5 new agents
        for i in range(5):
            new_agent = source_dir / f"new{i}.md"
            new_agent.write_text(
                """---
name: new-agent
description: New agent
---
# New"""
            )

        # Measure incremental sync
        start = time.time()
        report = convert_agents(source_dir, target_dir, force=True)
        elapsed = time.time() - start

        # Incremental should be fast (< 1s)
        assert elapsed < 1.0

        print(f"\n✓ Incremental sync of 5 agents in {elapsed:.3f}s")


class TestStalenessCheckPerformance:
    """Test performance of staleness detection."""

    def test_staleness_check_speed_empty(self, temp_project: Path):
        """Test staleness check with empty directories."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Measure
        start = time.time()
        is_stale = not is_agents_synced(source_dir, target_dir)
        elapsed = time.time() - start

        # Should be near instant
        assert elapsed < 0.1
        assert is_stale is True  # Missing target

    def test_staleness_check_speed_50_agents(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test staleness check with 50 agents (< 500ms)."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create 50 agents in both dirs
        for i in range(50):
            for dirname in [source_dir, target_dir]:
                agent_path = dirname / f"agent{i}.md"
                agent_path.parent.mkdir(parents=True, exist_ok=True)
                content = sample_agent_markdown.replace("architect", f"agent{i}")
                agent_path.write_text(content)

        # Create registry
        convert_agents(source_dir, target_dir, force=True)

        # Measure staleness check
        start = time.time()
        is_stale = not is_agents_synced(source_dir, target_dir)
        elapsed = time.time() - start

        # Requirement: < 500ms
        assert elapsed < 0.5
        assert is_stale is False  # Should be synced

        print(f"\n✓ Staleness check for 50 agents in {elapsed*1000:.1f}ms")

    def test_staleness_check_with_nested_structure(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test staleness check performance with deeply nested structure."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create nested structure with 30 agents
        for i in range(10):
            for subdir in ["core", "specialized", "experimental"]:
                agent_path = source_dir / "amplihack" / subdir / f"agent{i}.md"
                agent_path.parent.mkdir(parents=True, exist_ok=True)
                content = sample_agent_markdown.replace("architect", f"agent{i}")
                agent_path.write_text(content)

        # Sync
        convert_agents(source_dir, target_dir)

        # Measure staleness check
        start = time.time()
        is_stale = not is_agents_synced(source_dir, target_dir)
        elapsed = time.time() - start

        # Should still be fast
        assert elapsed < 0.5
        assert is_stale is False

        print(f"\n✓ Nested staleness check in {elapsed*1000:.1f}ms")


class TestRegistryPerformance:
    """Test performance of registry generation."""

    def test_registry_generation_speed(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Test registry generation completes quickly."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Measure full sync (includes registry generation)
        start = time.time()
        report = convert_agents(source_dir, target_dir)
        elapsed = time.time() - start

        # Verify registry created
        registry_path = target_dir / "REGISTRY.json"
        assert registry_path.exists()

        # Should be reasonably fast
        assert elapsed < 2.0

        print(
            f"\n✓ Synced {report.succeeded} agents + registry in {elapsed:.3f}s"
        )


class TestScalabilityLimits:
    """Test performance at scale limits."""

    @pytest.mark.slow
    def test_100_agent_sync(self, temp_project: Path, sample_agent_markdown: str):
        """Test sync performance with 100 agents (stress test)."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create 100 agents
        for i in range(100):
            agent_path = source_dir / f"agent{i:03d}.md"
            content = sample_agent_markdown.replace("architect", f"agent{i:03d}")
            agent_path.write_text(content)

        # Measure
        start = time.time()
        report = convert_agents(source_dir, target_dir)
        elapsed = time.time() - start

        # Should scale linearly (expect ~4s for 100 agents)
        assert elapsed < 5.0
        assert report.succeeded == 100

        print(
            f"\n✓ Synced 100 agents in {elapsed:.3f}s ({elapsed/100*1000:.1f}ms/agent)"
        )

    @pytest.mark.slow
    def test_deep_directory_hierarchy_performance(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test performance with very deep directory hierarchies."""
        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create 20 agents in 10-level deep hierarchy
        for i in range(20):
            # Create path like: a/b/c/d/e/f/g/h/i/j/agent{i}.md
            deep_path = source_dir
            for level in range(10):
                deep_path = deep_path / f"level{level}"

            agent_path = deep_path / f"agent{i}.md"
            agent_path.parent.mkdir(parents=True, exist_ok=True)
            content = sample_agent_markdown.replace("architect", f"agent{i}")
            agent_path.write_text(content)

        # Measure
        start = time.time()
        report = convert_agents(source_dir, target_dir)
        elapsed = time.time() - start

        # Should handle deep hierarchies efficiently
        assert elapsed < 2.0
        assert report.succeeded == 20

        print(f"\n✓ Deep hierarchy sync in {elapsed:.3f}s")


class TestComparativePerformance:
    """Compare Copilot CLI performance vs Claude Code."""

    def test_copilot_vs_claude_agent_access(
        self, temp_project: Path, mock_agent_files: list[Path]
    ):
        """Compare agent access patterns between Copilot and Claude."""
        claude_dir = temp_project / ".claude" / "agents"
        github_dir = temp_project / ".github" / "agents"

        # Sync agents
        convert_agents(claude_dir, github_dir)

        # Measure Claude Code pattern (direct .claude/agents/ access)
        start = time.time()
        claude_agents = list(claude_dir.rglob("*.md"))
        claude_elapsed = time.time() - start

        # Measure Copilot pattern (.github/agents/ access)
        start = time.time()
        copilot_agents = list(github_dir.rglob("*.md"))
        copilot_elapsed = time.time() - start

        # Both should be fast
        assert claude_elapsed < 0.1
        assert copilot_elapsed < 0.1

        # Same number of agents
        assert len(claude_agents) == len(copilot_agents)

        print(f"\n✓ Claude access: {claude_elapsed*1000:.1f}ms")
        print(f"✓ Copilot access: {copilot_elapsed*1000:.1f}ms")


class TestMemoryUsage:
    """Test memory efficiency of sync operations."""

    def test_memory_efficient_sync(
        self, temp_project: Path, sample_agent_markdown: str
    ):
        """Test sync doesn't consume excessive memory."""
        import tracemalloc

        source_dir = temp_project / ".claude" / "agents"
        target_dir = temp_project / ".github" / "agents"

        # Create 50 agents
        for i in range(50):
            agent_path = source_dir / f"agent{i}.md"
            content = sample_agent_markdown.replace("architect", f"agent{i}")
            agent_path.write_text(content)

        # Measure memory
        tracemalloc.start()

        report = convert_agents(source_dir, target_dir)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory usage should be reasonable (< 10MB for 50 agents)
        assert peak < 10 * 1024 * 1024  # 10MB
        assert report.succeeded == 50

        print(f"\n✓ Peak memory: {peak / 1024 / 1024:.2f}MB for 50 agents")
