"""Scale tests for hive_mind -- no LLM, no network, deterministic.

Exercises InMemoryHiveGraph at scale with hardcoded facts:
1. 20 agents x 100 facts flat hive (2000 facts retrievable)
2. 20 agents in 4 federated groups (cross-group query)
3. 50 agents with gossip (>95% convergence in 10 rounds)
4. 100 agents x 50 facts with TTL + GC (expired removed, fresh kept)
5. 5000-fact keyword search timing (<1 second)
6. CRDT merge of 10 replicas x 500 facts (union completeness)
"""

from __future__ import annotations

import random
import time

from amplihack.agents.goal_seeking.hive_mind.gossip import (
    GossipProtocol,
    convergence_check,
    run_gossip_round,
)
from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveFact,
    InMemoryHiveGraph,
)


def _make_fact(agent_idx: int, fact_idx: int, **overrides) -> HiveFact:
    """Create a deterministic fact with keyword-searchable content."""
    defaults = {
        "fact_id": f"f-{agent_idx:04d}-{fact_idx:04d}",
        "content": (
            f"fact agent{agent_idx} idx{fact_idx} domain{agent_idx % 10} kw{fact_idx % 20}"
        ),
        "concept": f"concept-{agent_idx % 10}",
        "confidence": 0.8,
        "source_agent": f"agent-{agent_idx:04d}",
    }
    defaults.update(overrides)
    return HiveFact(**defaults)


# ---------------------------------------------------------------------------
# Test 1: Flat hive with 20 agents x 100 facts
# ---------------------------------------------------------------------------


class TestFlatHive20Agents:
    """20 agents, 100 facts each, flat hive -- all 2000 facts retrievable."""

    def test_all_2000_facts_retrievable(self):
        hive = InMemoryHiveGraph(hive_id="flat-20")

        for a in range(20):
            agent_id = f"agent-{a:04d}"
            hive.register_agent(agent_id, domain=f"domain-{a % 5}")
            for f in range(100):
                hive.promote_fact(agent_id, _make_fact(a, f))

        all_facts = hive.query_facts("", limit=100_000)
        assert len(all_facts) == 2000

        # Spot-check individual retrieval
        for a in [0, 9, 19]:
            for f in [0, 49, 99]:
                fact = hive.get_fact(f"f-{a:04d}-{f:04d}")
                assert fact is not None
                assert fact.status == "promoted"

        stats = hive.get_stats()
        assert stats["agent_count"] == 20
        assert stats["fact_count"] == 2000
        assert stats["active_facts"] == 2000


# ---------------------------------------------------------------------------
# Test 2: Federated groups (4 groups of 5 agents)
# ---------------------------------------------------------------------------


class TestFederatedGroups:
    """20 agents in 4 groups of 5, federated -- cross-group query."""

    def test_query_federated_across_all_groups(self):
        root = InMemoryHiveGraph(hive_id="root")
        root.register_agent("root-coord", domain="coordinator")

        children: list[InMemoryHiveGraph] = []
        for g in range(4):
            child = InMemoryHiveGraph(hive_id=f"group-{g}")
            root.add_child(child)
            child.set_parent(root)

            for a in range(5):
                idx = g * 5 + a
                agent_id = f"agent-{idx:04d}"
                child.register_agent(agent_id, domain=f"grp{g}")
                for f_idx in range(10):
                    child.promote_fact(
                        agent_id,
                        HiveFact(
                            fact_id=f"f-g{g}-a{a}-{f_idx}",
                            content=f"alpha grp{g} agent{idx} idx{f_idx}",
                            concept=f"topic-{g}",
                            confidence=0.7,
                        ),
                    )
            children.append(child)

        # 4 groups x 5 agents x 10 facts = 200 total
        # Query from root for the common keyword "alpha"
        results = root.query_federated("alpha", limit=200)
        groups_found = {g for g in range(4) if any(f"grp{g}" in f.content for f in results)}
        assert groups_found == {0, 1, 2, 3}, f"Missing groups: {set(range(4)) - groups_found}"
        assert len(results) >= 100  # substantial coverage of 200

        # Query from child[0] should find child[2] facts via parent
        cross = children[0].query_federated("grp2", limit=200)
        assert any("grp2" in f.content for f in cross), "Child 0 should find group-2 facts"


# ---------------------------------------------------------------------------
# Test 3: Gossip convergence (50 hives, 10 rounds)
# ---------------------------------------------------------------------------


class TestGossipConvergence:
    """50 agents with gossip, 10 rounds -- convergence >95%."""

    def test_convergence_above_95_percent(self):
        random.seed(42)  # deterministic peer selection

        n_hives = 50
        # fanout=25 (half the network) combats trust-weighted selection bias
        # from relay agents accumulating in frequently-gossiped peers.
        protocol = GossipProtocol(top_k=100, fanout=25, min_confidence=0.3)

        hives: list[InMemoryHiveGraph] = []
        for i in range(n_hives):
            h = InMemoryHiveGraph(hive_id=f"gossip-{i:03d}")
            h.register_agent(f"agent-{i:03d}", domain=f"domain-{i % 5}")
            h.promote_fact(
                f"agent-{i:03d}",
                HiveFact(
                    fact_id=f"uniq-{i:03d}",
                    content=f"knowledge-{i}",
                    concept=f"topic-{i % 10}",
                    confidence=0.9,
                ),
            )
            hives.append(h)

        for _round in range(10):
            for hive in hives:
                peers = [h for h in hives if h.hive_id != hive.hive_id]
                run_gossip_round(hive, peers, protocol)

        conv = convergence_check(hives)
        assert conv > 0.95, f"Convergence {conv:.3f} not >95%"


# ---------------------------------------------------------------------------
# Test 4: TTL + garbage collection (100 agents x 50 facts)
# ---------------------------------------------------------------------------


class TestTTLGarbageCollection:
    """100 agents, 50 facts each, TTL enabled -- GC removes expired, keeps fresh."""

    def test_gc_removes_expired_keeps_fresh(self):
        hive = InMemoryHiveGraph(hive_id="ttl-100", enable_ttl=True)
        now = time.time()

        expired_ids: set[str] = set()
        fresh_ids: set[str] = set()

        for a in range(100):
            agent_id = f"agent-{a:04d}"
            hive.register_agent(agent_id, domain=f"domain-{a % 10}")

            for f in range(50):
                fact_id = f"f-{a:04d}-{f:04d}"
                hive.promote_fact(
                    agent_id,
                    HiveFact(
                        fact_id=fact_id,
                        content=f"data agent{a} idx{f}",
                        concept=f"topic-{a % 10}",
                        confidence=0.8,
                    ),
                )

                if f < 25:
                    # Backdate to 25 hours ago (exceeds 24-hour max age)
                    hive._ttl_registry[fact_id].created_at = now - 25 * 3600
                    expired_ids.add(fact_id)
                else:
                    fresh_ids.add(fact_id)

        assert len(expired_ids) == 2500
        assert len(fresh_ids) == 2500

        removed = hive.gc()
        assert set(removed) == expired_ids

        # Fresh facts still active
        for fid in list(fresh_ids)[:20]:
            fact = hive.get_fact(fid)
            assert fact is not None
            assert fact.status != "retracted"

        # Expired facts are retracted
        for fid in list(expired_ids)[:20]:
            fact = hive.get_fact(fid)
            assert fact is not None
            assert fact.status == "retracted"


# ---------------------------------------------------------------------------
# Test 5: Timing -- keyword search over 5000 facts < 1 second
# ---------------------------------------------------------------------------


class TestQueryPerformance:
    """query_facts with 5000 facts should complete in <1 second."""

    def test_keyword_search_under_1_second(self):
        hive = InMemoryHiveGraph(hive_id="perf-5k")

        for a in range(50):
            agent_id = f"agent-{a:04d}"
            hive.register_agent(agent_id, domain=f"domain-{a % 10}")
            for f in range(100):
                hive.promote_fact(
                    agent_id,
                    HiveFact(
                        fact_id=f"f-{a:04d}-{f:04d}",
                        content=(f"alpha beta gamma agent{a} idx{f} domain{a % 10} kw{f % 20}"),
                        concept=f"concept-{a % 10}",
                        confidence=0.8,
                    ),
                )

        assert len(hive.query_facts("", limit=100_000)) == 5000

        start = time.monotonic()
        results = hive.query_facts("alpha gamma kw5", limit=100)
        elapsed = time.monotonic() - start

        assert elapsed < 1.0, f"Query took {elapsed:.3f}s, expected <1s"
        assert len(results) > 0


# ---------------------------------------------------------------------------
# Test 6: CRDT merge at scale (10 replicas x 500 facts)
# ---------------------------------------------------------------------------


class TestCRDTMergeAtScale:
    """Merge 10 replicas each with 500 facts -- verify union completeness."""

    def test_merge_union_completeness(self):
        replicas: list[InMemoryHiveGraph] = []
        all_fact_ids: set[str] = set()

        for r in range(10):
            replica = InMemoryHiveGraph(hive_id=f"replica-{r}")
            for a in range(5):
                agent_id = f"agent-r{r}-a{a}"
                replica.register_agent(agent_id, domain=f"domain-{r}")
                for f in range(100):
                    fact_id = f"f-r{r}-a{a}-{f:03d}"
                    replica.promote_fact(
                        agent_id,
                        HiveFact(
                            fact_id=fact_id,
                            content=f"replica{r} agent{a} fact{f}",
                            concept=f"topic-{r}",
                            confidence=0.8,
                        ),
                    )
                    all_fact_ids.add(fact_id)
            replicas.append(replica)

        # 10 replicas x 5 agents x 100 facts = 5000
        assert len(all_fact_ids) == 5000

        target = replicas[0]
        for other in replicas[1:]:
            target.merge_state(other)

        merged_facts = target.query_facts("", limit=100_000)
        merged_ids = {f.fact_id for f in merged_facts}

        missing = all_fact_ids - merged_ids
        assert not missing, f"Missing {len(missing)} facts after merge"
        assert len(merged_ids) >= 5000
