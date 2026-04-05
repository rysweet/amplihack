"""Tests for the Memory facade and MemoryConfig.

Tests cover:
- Memory with defaults (single topology, cognitive backend)
- remember() stores facts, recall() finds them
- Config from env vars (mock os.environ)
- Config from YAML file (tempfile)
- Config priority: kwargs > env > file > defaults
- Distributed topology creates DistributedHiveGraph
- Multiple Memory instances share a hive (distributed)
- close() cleans up
- stats() returns data
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

from amplihack.memory import Memory, MemoryConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_adapter():
    """Create a simple mock adapter that mimics in-memory remember/recall."""
    facts: list[str] = []

    adapter = MagicMock()

    def store_fact(concept, content):
        if content not in facts:
            facts.append(content)

    def search(question, limit=20):
        q_words = set(question.lower().split())
        scored: list[tuple[int, dict]] = []
        for fact in facts:
            hits = sum(1 for w in q_words if w in fact.lower())
            if hits > 0:
                scored.append((hits, {"content": fact}))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    adapter.store_fact = store_fact
    adapter.search = search
    adapter.close = MagicMock()
    adapter._facts = facts  # expose for stats tests
    return adapter


def _cognitive_memory(agent_name: str = "test-agent", **kwargs) -> Memory:
    """Create a Memory with backend=cognitive, using a mock adapter for tests."""
    mock_adapter = _make_mock_adapter()
    with patch.object(Memory, "_build_cognitive", return_value=mock_adapter):
        return Memory(agent_name, backend="cognitive", **kwargs)


# ---------------------------------------------------------------------------
# MemoryConfig tests
# ---------------------------------------------------------------------------


class TestMemoryConfigDefaults:
    def test_default_backend(self):
        cfg = MemoryConfig()
        assert cfg.backend == "cognitive"

    def test_default_topology(self):
        cfg = MemoryConfig()
        assert cfg.topology == "single"

    def test_default_kuzu_buffer(self):
        cfg = MemoryConfig()
        assert cfg.kuzu_buffer_pool_mb == 256

    def test_default_replication_factor(self):
        cfg = MemoryConfig()
        assert cfg.replication_factor == 3

    def test_default_query_fanout(self):
        cfg = MemoryConfig()
        assert cfg.query_fanout == 5

    def test_default_gossip_enabled(self):
        cfg = MemoryConfig()
        assert cfg.gossip_enabled is True

    def test_default_gossip_rounds(self):
        cfg = MemoryConfig()
        assert cfg.gossip_rounds == 3


class TestMemoryConfigFromEnv:
    def test_backend_from_env(self):
        with patch.dict(os.environ, {"AMPLIHACK_MEMORY_BACKEND": "hierarchical"}):
            cfg = MemoryConfig.from_env()
        assert cfg.backend == "hierarchical"

    def test_topology_from_env(self):
        with patch.dict(os.environ, {"AMPLIHACK_MEMORY_TOPOLOGY": "distributed"}):
            cfg = MemoryConfig.from_env()
        assert cfg.topology == "distributed"

    def test_storage_path_from_env(self):
        with patch.dict(os.environ, {"AMPLIHACK_MEMORY_STORAGE_PATH": "/custom/path"}):
            cfg = MemoryConfig.from_env()
        assert cfg.storage_path == "/custom/path"

    def test_kuzu_buffer_from_env(self):
        with patch.dict(os.environ, {"AMPLIHACK_MEMORY_KUZU_BUFFER_MB": "512"}):
            cfg = MemoryConfig.from_env()
        assert cfg.kuzu_buffer_pool_mb == 512

    def test_replication_from_env(self):
        with patch.dict(os.environ, {"AMPLIHACK_MEMORY_REPLICATION": "5"}):
            cfg = MemoryConfig.from_env()
        assert cfg.replication_factor == 5

    def test_fanout_from_env(self):
        with patch.dict(os.environ, {"AMPLIHACK_MEMORY_QUERY_FANOUT": "10"}):
            cfg = MemoryConfig.from_env()
        assert cfg.query_fanout == 10

    def test_gossip_true_from_env(self):
        with patch.dict(os.environ, {"AMPLIHACK_MEMORY_GOSSIP": "true"}):
            cfg = MemoryConfig.from_env()
        assert cfg.gossip_enabled is True

    def test_gossip_false_from_env(self):
        with patch.dict(os.environ, {"AMPLIHACK_MEMORY_GOSSIP": "false"}):
            cfg = MemoryConfig.from_env()
        assert cfg.gossip_enabled is False

    def test_gossip_rounds_from_env(self):
        with patch.dict(os.environ, {"AMPLIHACK_MEMORY_GOSSIP_ROUNDS": "7"}):
            cfg = MemoryConfig.from_env()
        assert cfg.gossip_rounds == 7

    def test_missing_env_vars_use_defaults(self):
        clean = {k: v for k, v in os.environ.items() if not k.startswith("AMPLIHACK_MEMORY")}
        with patch.dict(os.environ, clean, clear=True):
            cfg = MemoryConfig.from_env()
        assert cfg.backend == "cognitive"
        assert cfg.topology == "single"


class TestMemoryConfigFromFile:
    def test_nonexistent_file_returns_defaults(self):
        cfg = MemoryConfig.from_file("/nonexistent/path/memory.yaml")
        assert cfg.backend == "cognitive"

    def test_yaml_file_loaded(self):
        yaml_content = "backend: hierarchical\ntopology: distributed\nkuzu_buffer_pool_mb: 128\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            tmp_path = f.name
        try:
            cfg = MemoryConfig.from_file(tmp_path)
            assert cfg.backend == "hierarchical"
            assert cfg.topology == "distributed"
            assert cfg.kuzu_buffer_pool_mb == 128
        finally:
            os.unlink(tmp_path)

    def test_yaml_gossip_bool(self):
        yaml_content = "gossip_enabled: false\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            tmp_path = f.name
        try:
            cfg = MemoryConfig.from_file(tmp_path)
            assert cfg.gossip_enabled is False
        finally:
            os.unlink(tmp_path)


class TestMemoryConfigResolvePriority:
    """kwargs > env > file > defaults."""

    def test_kwargs_override_env(self):
        with patch.dict(os.environ, {"AMPLIHACK_MEMORY_BACKEND": "hierarchical"}):
            cfg = MemoryConfig.resolve("agent", backend="cognitive")
        assert cfg.backend == "cognitive"

    def test_env_overrides_file(self):
        yaml_content = "backend: hierarchical\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            tmp_path = f.name
        try:
            with patch.dict(os.environ, {"AMPLIHACK_MEMORY_BACKEND": "cognitive"}):
                cfg = MemoryConfig.resolve("agent", config_file=tmp_path)
            assert cfg.backend == "cognitive"
        finally:
            os.unlink(tmp_path)

    def test_file_overrides_defaults(self):
        yaml_content = "kuzu_buffer_pool_mb: 64\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            tmp_path = f.name
        try:
            cfg = MemoryConfig.resolve("agent", config_file=tmp_path)
            assert cfg.kuzu_buffer_pool_mb == 64
        finally:
            os.unlink(tmp_path)

    def test_default_storage_path_derived_from_agent_name(self):
        cfg = MemoryConfig.resolve("my-agent")
        assert "my-agent" in cfg.storage_path

    def test_explicit_storage_path_wins(self):
        cfg = MemoryConfig.resolve("agent", storage_path="/custom/store")
        assert cfg.storage_path == "/custom/store"


# ---------------------------------------------------------------------------
# Memory facade — cognitive backend (mocked adapter for fast tests)
# ---------------------------------------------------------------------------


class TestMemoryDefaults:
    def test_creates_with_defaults(self):
        mem = _cognitive_memory()
        assert mem is not None
        mem.close()

    def test_stats_returns_dict(self):
        mem = _cognitive_memory()
        s = mem.stats()
        assert isinstance(s, dict)
        assert "agent_name" in s
        mem.close()

    def test_stats_backend_field(self):
        mem = _cognitive_memory("stats-agent")
        s = mem.stats()
        assert s["backend"] == "cognitive"
        assert s["agent_name"] == "stats-agent"
        mem.close()


class TestRememberRecall:
    def test_remember_and_recall_basic(self):
        mem = _cognitive_memory()
        mem.remember("The sky is blue")
        results = mem.recall("sky colour")
        assert any("sky" in r.lower() for r in results)
        mem.close()

    def test_recall_returns_list(self):
        mem = _cognitive_memory()
        results = mem.recall("anything")
        assert isinstance(results, list)
        mem.close()

    def test_recall_empty_query_returns_empty(self):
        mem = _cognitive_memory()
        mem.remember("some fact")
        assert mem.recall("") == []
        mem.close()

    def test_remember_empty_content_is_ignored(self):
        mem = _cognitive_memory()
        mem.remember("")
        mem.remember("   ")
        assert mem.recall("fact") == []
        mem.close()

    def test_multiple_facts_recalled(self):
        mem = _cognitive_memory()
        mem.remember("Python is a programming language")
        mem.remember("Python uses indentation for blocks")
        results = mem.recall("Python", limit=5)
        assert len(results) >= 1
        mem.close()

    def test_recall_limit_respected(self):
        mem = _cognitive_memory()
        for i in range(10):
            mem.remember(f"fact number {i} about topic")
        results = mem.recall("fact topic", limit=3)
        assert len(results) <= 3
        mem.close()

    def test_deduplication(self):
        mem = _cognitive_memory()
        mem.remember("unique fact")
        mem.remember("unique fact")  # duplicate
        results = mem.recall("unique fact")
        # Should appear only once
        assert results.count("unique fact") == 1
        mem.close()


class TestContextManager:
    def test_context_manager(self):
        with _cognitive_memory() as mem:
            mem.remember("inside context")
            results = mem.recall("context")
            assert any("context" in r for r in results)

    def test_close_is_idempotent(self):
        mem = _cognitive_memory()
        mem.close()
        mem.close()  # should not raise


class TestClose:
    def test_close_runs_without_error(self):
        mem = _cognitive_memory()
        mem.close()

    def test_stats_works_before_close(self):
        mem = _cognitive_memory()
        s = mem.stats()
        assert isinstance(s, dict)
        mem.close()


# ---------------------------------------------------------------------------
# Memory facade — distributed topology
# ---------------------------------------------------------------------------


class TestDistributedTopology:
    def test_creates_distributed_hive(self):
        mock_adapter = _make_mock_adapter()
        with patch.object(Memory, "_build_cognitive", return_value=mock_adapter):
            mem = Memory(
                "dist-agent-1",
                backend="cognitive",
                topology="distributed",
            )
        assert mem._hive is not None
        mem.close()

    def test_shared_hive_passed_directly(self):
        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            DistributedHiveGraph,
        )

        hive = DistributedHiveGraph(hive_id="shared-test-hive")

        mock_a = _make_mock_adapter()
        mock_b = _make_mock_adapter()
        with patch.object(Memory, "_build_cognitive", return_value=mock_a):
            mem_a = Memory("agent-a", backend="cognitive", shared_hive=hive)
        with patch.object(Memory, "_build_cognitive", return_value=mock_b):
            mem_b = Memory("agent-b", backend="cognitive", shared_hive=hive)

        assert mem_a._hive is hive
        assert mem_b._hive is hive

        mem_a.close()
        mem_b.close()

    def test_run_gossip_no_error_for_distributed(self):
        mock_adapter = _make_mock_adapter()
        with patch.object(Memory, "_build_cognitive", return_value=mock_adapter):
            mem = Memory(
                "gossip-agent",
                backend="cognitive",
                topology="distributed",
            )
        mem.run_gossip()  # should not raise
        mem.close()

    def test_run_gossip_no_error_for_single(self):
        mem = _cognitive_memory("single-gossip")
        mem.run_gossip()  # no-op, should not raise
        mem.close()

    def test_distributed_stats_includes_hive_stats(self):
        mock_adapter = _make_mock_adapter()
        with patch.object(Memory, "_build_cognitive", return_value=mock_adapter):
            mem = Memory(
                "stats-dist-agent",
                backend="cognitive",
                topology="distributed",
            )
        s = mem.stats()
        assert "topology" in s
        assert s["topology"] == "distributed"
        mem.close()


class TestMultipleAgentsSharedHive:
    def test_two_agents_share_same_hive_object(self):
        from amplihack.agents.goal_seeking.hive_mind.hive_graph import InMemoryHiveGraph

        hive = InMemoryHiveGraph("multi-agent-hive")

        mock_a = _make_mock_adapter()
        mock_b = _make_mock_adapter()
        with patch.object(Memory, "_build_cognitive", return_value=mock_a):
            mem_a = Memory("alpha", backend="cognitive", shared_hive=hive)
        with patch.object(Memory, "_build_cognitive", return_value=mock_b):
            mem_b = Memory("beta", backend="cognitive", shared_hive=hive)

        assert mem_a._hive is mem_b._hive

        mem_a.close()
        mem_b.close()


# ---------------------------------------------------------------------------
# Config env var integration with Memory constructor
# ---------------------------------------------------------------------------


class TestMemoryEnvVarConfig:
    def test_env_backend_affects_config(self):
        mock_adapter = _make_mock_adapter()
        with patch.object(Memory, "_build_cognitive", return_value=mock_adapter):
            with patch.dict(os.environ, {"AMPLIHACK_MEMORY_BACKEND": "cognitive"}):
                mem = Memory("env-test-agent")
        assert mem._cfg.backend == "cognitive"
        mem.close()

    def test_env_topology_affects_config(self):
        with patch.dict(os.environ, {"AMPLIHACK_MEMORY_TOPOLOGY": "single"}):
            mem = _cognitive_memory("env-topo-agent")
        assert mem._cfg.topology == "single"
        mem.close()

    def test_explicit_kwarg_overrides_env(self):
        with patch.dict(os.environ, {"AMPLIHACK_MEMORY_BACKEND": "hierarchical"}):
            mock_adapter = _make_mock_adapter()
            with patch.object(Memory, "_build_cognitive", return_value=mock_adapter):
                mem = Memory("override-agent", backend="cognitive")
        assert mem._cfg.backend == "cognitive"
        mem.close()
