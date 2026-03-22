"""Tests for the distributed hive mind: DHT, bloom filter, DistributedHiveGraph.

Testing pyramid:
- 80% unit tests (fast, no external deps)
- 20% integration tests (full pipeline)
"""

from __future__ import annotations

from unittest.mock import patch

from amplihack.agents.goal_seeking.hive_mind.bloom import BloomFilter
from amplihack.agents.goal_seeking.hive_mind.dht import (
    DHTRouter,
    HashRing,
    ShardFact,
    ShardStore,
)
from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
    DistributedHiveGraph,
)
from amplihack.agents.goal_seeking.hive_mind.hive_graph import HiveFact

# ============================================================================
# HashRing tests
# ============================================================================


class TestHashRing:
    def test_add_agent(self):
        ring = HashRing()
        ring.add_agent("agent_0")
        assert ring.agent_count == 1
        assert "agent_0" in ring.agent_ids

    def test_remove_agent(self):
        ring = HashRing()
        ring.add_agent("agent_0")
        ring.remove_agent("agent_0")
        assert ring.agent_count == 0

    def test_get_agents_returns_replication_factor(self):
        ring = HashRing(replication_factor=3)
        for i in range(5):
            ring.add_agent(f"agent_{i}")
        agents = ring.get_agents("some_key")
        assert len(agents) == 3
        assert len(set(agents)) == 3  # All distinct

    def test_get_agents_with_fewer_agents_than_rf(self):
        ring = HashRing(replication_factor=5)
        ring.add_agent("agent_0")
        ring.add_agent("agent_1")
        agents = ring.get_agents("key")
        assert len(agents) == 2  # Can't replicate to 5 with only 2 agents

    def test_consistent_routing(self):
        ring = HashRing()
        for i in range(10):
            ring.add_agent(f"agent_{i}")
        # Same key always routes to same agents
        a1 = ring.get_agents("test_key")
        a2 = ring.get_agents("test_key")
        assert a1 == a2

    def test_empty_ring(self):
        ring = HashRing()
        assert ring.get_agents("key") == []
        assert ring.get_primary_agent("key") is None


# ============================================================================
# ShardStore tests
# ============================================================================


class TestShardStore:
    def test_store_and_get(self):
        store = ShardStore("agent_0")
        fact = ShardFact(fact_id="f1", content="Test fact", confidence=0.9)
        assert store.store(fact) is True
        assert store.get("f1") is not None
        assert store.get("f1").content == "Test fact"

    def test_dedup(self):
        store = ShardStore("agent_0")
        f1 = ShardFact(fact_id="f1", content="Same content", confidence=0.9)
        f2 = ShardFact(fact_id="f2", content="Same content", confidence=0.8)
        assert store.store(f1) is True
        assert store.store(f2) is False  # Duplicate content
        assert store.fact_count == 1

    def test_search(self):
        store = ShardStore("agent_0")
        store.store(ShardFact(fact_id="f1", content="Sarah Chen birthday March"))
        store.store(ShardFact(fact_id="f2", content="James OBrien gluten allergy"))
        store.store(ShardFact(fact_id="f3", content="DuckDB OLAP database"))

        results = store.search("birthday Sarah")
        assert len(results) == 1
        assert results[0].fact_id == "f1"

    def test_search_empty(self):
        store = ShardStore("agent_0")
        assert store.search("nothing") == []


# ============================================================================
# BloomFilter tests
# ============================================================================


class TestBloomFilter:
    def test_add_and_contains(self):
        bf = BloomFilter(expected_items=100)
        bf.add("hello")
        assert bf.might_contain("hello") is True
        assert bf.might_contain("world") is False

    def test_no_false_negatives(self):
        bf = BloomFilter(expected_items=1000)
        items = [f"item_{i}" for i in range(500)]
        bf.add_all(items)
        for item in items:
            assert bf.might_contain(item) is True

    def test_missing_from(self):
        bf = BloomFilter(expected_items=100)
        bf.add_all(["a", "b", "c"])
        missing = bf.missing_from(["a", "b", "c", "d", "e"])
        assert "d" in missing
        assert "e" in missing
        assert "a" not in missing

    def test_serialization(self):
        bf = BloomFilter(expected_items=100)
        bf.add("test")
        data = bf.to_bytes()
        bf2 = BloomFilter.from_bytes(data, expected_items=100)
        assert bf2.might_contain("test") is True


# ============================================================================
# DHTRouter tests
# ============================================================================


class TestDHTRouter:
    def test_add_agent_creates_shard(self):
        router = DHTRouter()
        shard = router.add_agent("agent_0")
        assert shard is not None
        assert router.get_shard("agent_0") is shard

    def test_store_fact_replicates(self):
        router = DHTRouter(replication_factor=3)
        for i in range(5):
            router.add_agent(f"agent_{i}")

        fact = ShardFact(fact_id="f1", content="Test fact about Sarah Chen")
        stored_on = router.store_fact(fact)
        assert len(stored_on) <= 3  # At most replication_factor

    def test_query_finds_stored_facts(self):
        router = DHTRouter(replication_factor=2, query_fanout=5)
        for i in range(5):
            router.add_agent(f"agent_{i}")

        router.store_fact(ShardFact(fact_id="f1", content="Sarah Chen birthday is March 15"))
        results = router.query("Sarah Chen birthday")
        assert len(results) >= 1
        assert "Sarah" in results[0].content


# ============================================================================
# DistributedHiveGraph tests
# ============================================================================


class TestDistributedHiveGraph:
    def test_register_agent(self):
        dhg = DistributedHiveGraph("test")
        dhg.register_agent("agent_0", domain="security")
        assert dhg.get_agent("agent_0") is not None
        assert dhg.get_agent("agent_0").domain == "security"

    def test_promote_and_query(self):
        dhg = DistributedHiveGraph("test", replication_factor=2)
        dhg.register_agent("agent_0")
        dhg.register_agent("agent_1")

        fid = dhg.promote_fact(
            "agent_0",
            HiveFact(fact_id="", content="PostgreSQL runs on port 5432"),
        )
        assert fid  # Non-empty fact_id returned

        results = dhg.query_facts("PostgreSQL port")
        assert len(results) >= 1
        assert "PostgreSQL" in results[0].content

    def test_query_workers_are_capped_by_env(self):
        target_ids = [f"agent_{i}" for i in range(5)]
        seen: dict[str, int] = {}

        class _Future:
            def __init__(self, value):
                self._value = value

            def result(self):
                return self._value

        class _Executor:
            def __init__(self, max_workers: int):
                seen["max_workers"] = max_workers

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def submit(self, fetcher, agent_id):
                return _Future(fetcher(agent_id))

        with (
            patch.dict("os.environ", {"AMPLIHACK_MEMORY_QUERY_MAX_WORKERS": "3"}),
            patch(
                "amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph.concurrent.futures.ThreadPoolExecutor",
                _Executor,
            ),
            patch(
                "amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph.concurrent.futures.as_completed",
                lambda futures: list(futures),
            ),
        ):
            dhg = DistributedHiveGraph("test")
            results = dhg._collect_shard_fact_results(target_ids, lambda agent_id: [])

        assert seen["max_workers"] == 3
        assert sorted(results) == target_ids

    def test_gossip_propagation(self):
        dhg = DistributedHiveGraph("test", replication_factor=1, enable_gossip=True)
        for i in range(5):
            dhg.register_agent(f"agent_{i}")

        # Store facts (each on 1 agent due to RF=1)
        for i in range(10):
            dhg.promote_fact(
                f"agent_{i % 5}",
                HiveFact(fact_id="", content=f"Unique fact number {i}"),
            )

        # Before gossip: low convergence
        pre_conv = dhg.convergence_score()

        # Run gossip rounds
        total_propagated = 0
        for _ in range(5):
            result = dhg.run_gossip_round()
            total_propagated += sum(result.values())

        post_conv = dhg.convergence_score()
        assert post_conv >= pre_conv
        assert total_propagated > 0

    def test_gossip_peer_selection_is_deterministic(self):
        dhg = DistributedHiveGraph("test", replication_factor=1, enable_gossip=True)
        for i in range(5):
            dhg.register_agent(f"agent_{i}")

        peers = ["agent_1", "agent_2", "agent_3", "agent_4"]
        first = dhg._select_gossip_peers("agent_0", peers, 2)
        second = dhg._select_gossip_peers("agent_0", list(reversed(peers)), 2)

        assert first == second
        assert len(first) == 2

    def test_federation(self):
        root = DistributedHiveGraph("root")
        child = DistributedHiveGraph("child")
        child.set_parent(root)
        root.add_child(child)

        child.register_agent("agent_0")
        root.register_agent("root_agent")

        # High-confidence fact should escalate to parent
        child.promote_fact(
            "agent_0",
            HiveFact(
                fact_id="",
                content="Critical security finding in prod",
                confidence=0.95,
            ),
        )

        # Query federated should find it from root
        results = root.query_federated("security finding")
        assert len(results) >= 1

    def test_100_agents_no_oom(self):
        """The key test: 100 agents should work without OOM."""
        dhg = DistributedHiveGraph("test", replication_factor=3)
        for i in range(100):
            dhg.register_agent(f"agent_{i}")

        # Store 500 facts
        for i in range(500):
            dhg.promote_fact(
                f"agent_{i % 100}",
                HiveFact(
                    fact_id="",
                    content=f"Fact {i} about topic {i % 20} with detail {i * 7}",
                ),
            )

        stats = dhg.get_stats()
        assert stats["agent_count"] == 100
        assert stats["fact_count"] > 0
        assert stats["avg_shard_size"] > 0

    def test_unregister_redistributes(self):
        dhg = DistributedHiveGraph("test", replication_factor=2)
        dhg.register_agent("a")
        dhg.register_agent("b")
        dhg.register_agent("c")

        dhg.promote_fact("a", HiveFact(fact_id="", content="Fact to redistribute"))

        dhg.unregister_agent("a")
        post_count = dhg.get_stats()["fact_count"]

        # Facts should be redistributed, count may change due to replication
        assert post_count > 0

    def test_stats(self):
        dhg = DistributedHiveGraph("test")
        dhg.register_agent("a")
        stats = dhg.get_stats()
        assert stats["type"] == "distributed"
        assert stats["hive_id"] == "test"
        assert stats["agent_count"] == 1


# ============================================================================
# Integration tests
# ============================================================================


class TestIntegration:
    def test_federated_groups_with_gossip(self):
        """Test the full federated topology: root + 5 groups x 4 agents."""
        root = DistributedHiveGraph("root", replication_factor=2)
        groups = []
        for g in range(5):
            group = DistributedHiveGraph(f"group-{g}", replication_factor=2, enable_gossip=True)
            group.set_parent(root)
            root.add_child(group)
            groups.append(group)

            for a in range(4):
                group.register_agent(f"agent_{g}_{a}")

        # Each group learns different facts
        for g, group in enumerate(groups):
            for i in range(10):
                group.promote_fact(
                    f"agent_{g}_0",
                    HiveFact(
                        fact_id="",
                        content=f"Group {g} knowledge item {i} about topic {g}",
                        confidence=0.85,
                    ),
                )

        # Run gossip within groups
        for group in groups:
            for _ in range(3):
                group.run_gossip_round()

        # Federated query should find facts across groups
        results = root.query_federated("knowledge item", limit=50)
        assert len(results) >= 5  # At least 1 from each group

    def test_merge_state(self):
        """Test CRDT-style merge between two hives."""
        h1 = DistributedHiveGraph("h1")
        h2 = DistributedHiveGraph("h2")
        h1.register_agent("a")
        h2.register_agent("b")

        h1.promote_fact("a", HiveFact(fact_id="", content="Fact from hive 1"))
        h2.promote_fact("b", HiveFact(fact_id="", content="Fact from hive 2"))

        h1.merge_state(h2)
        results = h1.query_facts("Fact", limit=10)
        assert len(results) >= 2
