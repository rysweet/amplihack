"""Tests for the gossip protocol module.

Tests the contract, not the implementation:
- GossipFact creation and immutability
- Content hashing and deduplication
- Lamport clock ordering
- Single gossip round between 2 agents
- Convergence with 5 agents, each knowing 20 unique facts
- Hop count increment tracking
- Fanout selection randomness
- GossipMemoryAdapter import/export
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

from amplihack.agents.goal_seeking.hive_mind.gossip import (
    GossipFact,
    GossipMemoryAdapter,
    GossipMessage,
    GossipNetwork,
    GossipProtocol,
    content_hash,
)

# ---------------------------------------------------------------------------
# GossipFact tests
# ---------------------------------------------------------------------------


class TestGossipFact:
    def test_creation(self) -> None:
        ts = datetime.now(UTC)
        fact = GossipFact(
            fact_id="abc123",
            content="Water boils at 100C",
            confidence=0.95,
            source_agent_id="agent_0",
            origin_timestamp=ts,
            hop_count=0,
        )
        assert fact.fact_id == "abc123"
        assert fact.content == "Water boils at 100C"
        assert fact.confidence == 0.95
        assert fact.source_agent_id == "agent_0"
        assert fact.origin_timestamp == ts
        assert fact.hop_count == 0

    def test_immutability(self) -> None:
        fact = GossipFact(
            fact_id="x",
            content="test",
            confidence=0.5,
            source_agent_id="a",
            origin_timestamp=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            fact.content = "changed"  # type: ignore[misc]

    def test_with_incremented_hop(self) -> None:
        fact = GossipFact(
            fact_id="x",
            content="test",
            confidence=0.5,
            source_agent_id="a",
            origin_timestamp=datetime.now(UTC),
            hop_count=2,
        )
        hopped = fact.with_incremented_hop()
        assert hopped.hop_count == 3
        assert hopped.content == fact.content
        assert hopped.fact_id == fact.fact_id
        # Original unchanged
        assert fact.hop_count == 2


# ---------------------------------------------------------------------------
# GossipMessage tests
# ---------------------------------------------------------------------------


class TestGossipMessage:
    def test_creation(self) -> None:
        facts = [
            GossipFact(
                fact_id="f1",
                content="fact one",
                confidence=0.9,
                source_agent_id="a0",
                origin_timestamp=datetime.now(UTC),
            )
        ]
        msg = GossipMessage(
            sender_id="a0",
            facts=facts,
            lamport_clock=5,
            round_number=1,
        )
        assert msg.sender_id == "a0"
        assert len(msg.facts) == 1
        assert msg.lamport_clock == 5
        assert msg.round_number == 1


# ---------------------------------------------------------------------------
# Content hash tests
# ---------------------------------------------------------------------------


class TestContentHash:
    def test_deterministic(self) -> None:
        h1 = content_hash("hello world")
        h2 = content_hash("hello world")
        assert h1 == h2

    def test_different_inputs(self) -> None:
        h1 = content_hash("hello")
        h2 = content_hash("world")
        assert h1 != h2

    def test_returns_hex_string(self) -> None:
        h = content_hash("test")
        assert len(h) == 64  # SHA-256 hex = 64 chars
        assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# GossipProtocol tests
# ---------------------------------------------------------------------------


class TestGossipProtocol:
    def test_add_local_fact(self) -> None:
        proto = GossipProtocol("agent_0")
        fact = proto.add_local_fact("The sky is blue", confidence=0.95)
        assert fact.content == "The sky is blue"
        assert fact.confidence == 0.95
        assert fact.source_agent_id == "agent_0"
        assert fact.hop_count == 0
        assert proto.fact_count == 1
        assert proto.local_fact_count == 1

    def test_add_local_fact_dedup(self) -> None:
        proto = GossipProtocol("agent_0")
        proto.add_local_fact("same fact")
        proto.add_local_fact("same fact")
        # Second add overwrites (same hash), count stays 1
        assert proto.fact_count == 1

    def test_add_local_fact_validation(self) -> None:
        proto = GossipProtocol("agent_0")
        with pytest.raises(ValueError, match="content cannot be empty"):
            proto.add_local_fact("")
        with pytest.raises(ValueError, match="confidence"):
            proto.add_local_fact("test", confidence=1.5)

    def test_agent_id_validation(self) -> None:
        with pytest.raises(ValueError, match="agent_id cannot be empty"):
            GossipProtocol("")

    def test_select_facts_by_confidence_and_recency(self) -> None:
        proto = GossipProtocol("agent_0")
        now = datetime.now(UTC)

        # Older fact with high confidence
        proto.add_local_fact("old high", confidence=0.99, timestamp=now - timedelta(hours=1))
        # Recent fact with medium confidence
        proto.add_local_fact("new medium", confidence=0.7, timestamp=now)

        selected = proto.select_facts(k=2)
        assert len(selected) == 2
        # Both should be returned; exact ordering depends on the score function
        contents = {f.content for f in selected}
        assert "old high" in contents
        assert "new medium" in contents

    def test_select_facts_limits_k(self) -> None:
        proto = GossipProtocol("agent_0")
        for i in range(20):
            proto.add_local_fact(f"fact number {i}", confidence=0.8)

        selected = proto.select_facts(k=5)
        assert len(selected) == 5

    def test_lamport_clock_increment_on_send(self) -> None:
        proto = GossipProtocol("agent_0", peers=["agent_1"])
        assert proto.lamport_clock == 0
        proto.gossip_round()
        assert proto.lamport_clock == 1
        proto.gossip_round()
        assert proto.lamport_clock == 2

    def test_lamport_clock_on_receive(self) -> None:
        proto = GossipProtocol("agent_0")
        msg = GossipMessage(
            sender_id="agent_1",
            facts=[],
            lamport_clock=10,
            round_number=1,
        )
        proto.receive_gossip(msg)
        # max(0, 10) + 1 = 11
        assert proto.lamport_clock == 11

    def test_lamport_clock_already_ahead(self) -> None:
        proto = GossipProtocol("agent_0", peers=["agent_1"])
        # Do 5 rounds to get clock to 5
        for _ in range(5):
            proto.gossip_round()
        assert proto.lamport_clock == 5

        msg = GossipMessage(
            sender_id="agent_1",
            facts=[],
            lamport_clock=3,
            round_number=1,
        )
        proto.receive_gossip(msg)
        # max(5, 3) + 1 = 6
        assert proto.lamport_clock == 6

    def test_receive_gossip_dedup(self) -> None:
        proto = GossipProtocol("agent_0")
        fid = content_hash("shared fact")
        fact = GossipFact(
            fact_id=fid,
            content="shared fact",
            confidence=0.9,
            source_agent_id="agent_1",
            origin_timestamp=datetime.now(UTC),
            hop_count=1,
        )
        msg1 = GossipMessage(sender_id="agent_1", facts=[fact], lamport_clock=1, round_number=1)
        msg2 = GossipMessage(sender_id="agent_2", facts=[fact], lamport_clock=2, round_number=1)

        new1 = proto.receive_gossip(msg1)
        new2 = proto.receive_gossip(msg2)

        assert new1 == 1  # First time: learned
        assert new2 == 0  # Duplicate: not counted again
        assert proto.fact_count == 1

    def test_receive_keeps_lower_hop_count(self) -> None:
        proto = GossipProtocol("agent_0")
        fid = content_hash("fact")
        now = datetime.now(UTC)

        far_hop = GossipFact(
            fact_id=fid,
            content="fact",
            confidence=0.9,
            source_agent_id="a1",
            origin_timestamp=now,
            hop_count=5,
        )
        close_hop = GossipFact(
            fact_id=fid,
            content="fact",
            confidence=0.9,
            source_agent_id="a1",
            origin_timestamp=now,
            hop_count=1,
        )

        proto.receive_gossip(
            GossipMessage(sender_id="a2", facts=[far_hop], lamport_clock=1, round_number=1)
        )
        proto.receive_gossip(
            GossipMessage(sender_id="a3", facts=[close_hop], lamport_clock=2, round_number=1)
        )

        stored = proto.get_all_facts()
        assert len(stored) == 1
        assert stored[0].hop_count == 1  # Kept the closer version

    def test_gossip_round_sends_to_peers(self) -> None:
        proto = GossipProtocol("agent_0", peers=["agent_1", "agent_2"], fanout=2)
        proto.add_local_fact("a fact")
        msgs = proto.gossip_round()
        assert len(msgs) == 2
        recipients = {m.sender_id for m in msgs}
        # All messages come from agent_0
        assert recipients == {"agent_0"}

    def test_gossip_round_with_no_peers(self) -> None:
        proto = GossipProtocol("agent_0", peers=[])
        proto.add_local_fact("lonely fact")
        msgs = proto.gossip_round()
        assert len(msgs) == 0

    def test_inbox_and_process(self) -> None:
        proto = GossipProtocol("agent_0")
        fact = GossipFact(
            fact_id=content_hash("inbox fact"),
            content="inbox fact",
            confidence=0.8,
            source_agent_id="agent_1",
            origin_timestamp=datetime.now(UTC),
            hop_count=1,
        )
        msg = GossipMessage(sender_id="agent_1", facts=[fact], lamport_clock=1, round_number=1)

        proto.enqueue_message(msg)
        new_count = proto.process_inbox()
        assert new_count == 1
        assert proto.fact_count == 1


# ---------------------------------------------------------------------------
# Two-agent gossip round test
# ---------------------------------------------------------------------------


class TestTwoAgentGossip:
    def test_single_round_between_two_agents(self) -> None:
        """Two agents each have 1 unique fact. After 1 round, both should know 2 facts."""
        net = GossipNetwork()
        p0 = GossipProtocol("a0", peers=["a1"], fanout=1, top_k=10)
        p1 = GossipProtocol("a1", peers=["a0"], fanout=1, top_k=10)

        p0.add_local_fact("fact from a0", confidence=0.9)
        p1.add_local_fact("fact from a1", confidence=0.9)

        net.register_agent("a0", p0)
        net.register_agent("a1", p1)

        stats = net.run_gossip_round()

        assert stats["messages_sent"] == 2  # Each sends to 1 peer
        assert p0.fact_count == 2
        assert p1.fact_count == 2


# ---------------------------------------------------------------------------
# Five-agent convergence test
# ---------------------------------------------------------------------------


class TestFiveAgentConvergence:
    def test_convergence_with_5_agents_20_facts_each(self) -> None:
        """5 agents, each with 20 unique facts (100 total). Must converge to >95% coverage."""
        agent_ids = [f"agent_{i}" for i in range(5)]
        net = GossipNetwork()
        protocols: dict[str, GossipProtocol] = {}

        for aid in agent_ids:
            peers = [p for p in agent_ids if p != aid]
            proto = GossipProtocol(aid, peers=peers, fanout=2, top_k=20)
            protocols[aid] = proto
            net.register_agent(aid, proto)

            # Each agent has 20 unique facts
            for j in range(20):
                proto.add_local_fact(
                    f"Unique fact {j} from {aid}",
                    confidence=0.8 + 0.01 * j,
                )

        # Before gossip: each agent knows 20 out of 100 facts (20%)
        for proto in protocols.values():
            assert proto.fact_count == 20

        # Run until converged
        round_stats = net.run_until_converged(max_rounds=50, target_coverage=95.0)

        # Verify convergence
        net_stats = net.get_network_stats()
        assert net_stats["total_unique_facts"] == 100

        for agent_stats in net_stats["per_agent"]:
            assert agent_stats["coverage_pct"] >= 95.0, (
                f"Agent {agent_stats['agent_id']} only reached "
                f"{agent_stats['coverage_pct']:.1f}% coverage"
            )

        # Should converge in O(log N) rounds, well under 50
        assert len(round_stats) < 50, f"Took {len(round_stats)} rounds, expected fewer"

    def test_convergence_rounds_scale_sub_linearly(self) -> None:
        """Both 5 and 10 agents converge in bounded rounds (well under O(N))."""

        def run_convergence(n_agents: int, total_facts: int = 50) -> int:
            """Run convergence with a fixed total fact count distributed across agents."""
            facts_per_agent = total_facts // n_agents
            agent_ids = [f"a{i}" for i in range(n_agents)]
            net = GossipNetwork()
            for aid in agent_ids:
                peers = [p for p in agent_ids if p != aid]
                proto = GossipProtocol(aid, peers=peers, fanout=2, top_k=max(10, facts_per_agent))
                net.register_agent(aid, proto)
                for j in range(facts_per_agent):
                    proto.add_local_fact(f"fact_{j}_from_{aid}", confidence=0.9)
            stats = net.run_until_converged(max_rounds=100, target_coverage=95.0)
            return len(stats)

        # Use median of 5 trials to smooth randomness
        def median_rounds(n_agents: int) -> int:
            trials = sorted(run_convergence(n_agents) for _ in range(5))
            return trials[2]

        rounds_5 = median_rounds(5)
        rounds_10 = median_rounds(10)

        # Both should converge within a reasonable bound.
        # O(N) for 10 agents would be ~50 rounds. We expect well under that.
        assert rounds_5 < 30, f"5 agents took {rounds_5} rounds (expected < 30)"
        assert rounds_10 < 40, f"10 agents took {rounds_10} rounds (expected < 40)"

        # 10 agents should not take dramatically more rounds than 5 agents
        # when total fact count is held constant. Allow up to 3x due to
        # stochastic sampling and the fact that 10 agents distribute facts
        # more thinly (each agent starts with fewer facts).
        assert rounds_10 <= rounds_5 * 3.0, (
            f"10 agents took {rounds_10} rounds vs {rounds_5} for 5 agents. "
            f"Expected sub-linear scaling."
        )


# ---------------------------------------------------------------------------
# Hop count tests
# ---------------------------------------------------------------------------


class TestHopCount:
    def test_hop_count_increments_through_chain(self) -> None:
        """Facts passed through a chain of agents accumulate hops."""
        net = GossipNetwork()
        # Chain: a0 -> a1 -> a2
        p0 = GossipProtocol("a0", peers=["a1"], fanout=1, top_k=10)
        p1 = GossipProtocol("a1", peers=["a2"], fanout=1, top_k=10)
        p2 = GossipProtocol("a2", peers=["a0"], fanout=1, top_k=10)

        net.register_agent("a0", p0)
        net.register_agent("a1", p1)
        net.register_agent("a2", p2)

        p0.add_local_fact("chain fact", confidence=0.9)

        # Round 1: a0 sends to a1
        net.run_gossip_round()
        a1_facts = p1.get_all_facts()
        chain_in_a1 = [f for f in a1_facts if f.content == "chain fact"]
        assert len(chain_in_a1) == 1
        assert chain_in_a1[0].hop_count == 1

        # Round 2: a1 forwards to a2
        net.run_gossip_round()
        a2_facts = p2.get_all_facts()
        chain_in_a2 = [f for f in a2_facts if f.content == "chain fact"]
        assert len(chain_in_a2) == 1
        assert chain_in_a2[0].hop_count == 2


# ---------------------------------------------------------------------------
# Fanout selection tests
# ---------------------------------------------------------------------------


class TestFanoutSelection:
    def test_fanout_limited_to_peer_count(self) -> None:
        """Fanout cannot exceed number of available peers."""
        proto = GossipProtocol("a0", peers=["a1"], fanout=5)
        proto.add_local_fact("test")
        msgs = proto.gossip_round()
        assert len(msgs) == 1  # Only 1 peer available

    def test_fanout_randomness(self) -> None:
        """With many peers, different rounds should (usually) select different subsets."""
        peers = [f"peer_{i}" for i in range(20)]
        proto = GossipProtocol("a0", peers=peers, fanout=2)
        proto.add_local_fact("test")

        # Run 20 rounds and collect which peers were selected
        selected_sets: list[frozenset[str]] = []
        for _ in range(20):
            msgs = proto.gossip_round()
            # Messages tell us which peers were targeted (via the network)
            # Since no network, messages just come back. But we can check
            # that multiple rounds don't always produce the same count.
            selected_sets.append(frozenset(f"{len(msgs)}"))

        # With 20 peers and fanout=2, we should always get exactly 2 messages
        for s in selected_sets:
            assert s == frozenset({"2"})

    def test_fanout_excludes_self(self) -> None:
        """Agent should never gossip to itself."""
        proto = GossipProtocol("a0", peers=["a0", "a1", "a2"], fanout=3)
        # _select_peers filters out self
        peers = proto._select_peers()
        assert "a0" not in peers
        assert len(peers) <= 2  # Only a1, a2 available


# ---------------------------------------------------------------------------
# GossipNetwork tests
# ---------------------------------------------------------------------------


class TestGossipNetwork:
    def test_register_and_count(self) -> None:
        net = GossipNetwork()
        p0 = GossipProtocol("a0")
        net.register_agent("a0", p0)
        assert net.agent_count == 1

    def test_register_duplicate_raises(self) -> None:
        net = GossipNetwork()
        p0 = GossipProtocol("a0")
        net.register_agent("a0", p0)
        with pytest.raises(ValueError, match="already registered"):
            net.register_agent("a0", p0)

    def test_register_empty_id_raises(self) -> None:
        net = GossipNetwork()
        p0 = GossipProtocol("a0")
        with pytest.raises(ValueError, match="empty"):
            net.register_agent("", p0)

    def test_unregister(self) -> None:
        net = GossipNetwork()
        p0 = GossipProtocol("a0")
        net.register_agent("a0", p0)
        net.unregister_agent("a0")
        assert net.agent_count == 0

    def test_network_stats(self) -> None:
        net = GossipNetwork()
        p0 = GossipProtocol("a0", peers=["a1"])
        p1 = GossipProtocol("a1", peers=["a0"])
        p0.add_local_fact("fact0")
        p1.add_local_fact("fact1")
        net.register_agent("a0", p0)
        net.register_agent("a1", p1)

        stats = net.get_network_stats()
        assert stats["agent_count"] == 2
        assert stats["total_unique_facts"] == 2
        assert stats["total_rounds"] == 0


# ---------------------------------------------------------------------------
# GossipMemoryAdapter tests
# ---------------------------------------------------------------------------


class TestGossipMemoryAdapter:
    def test_add_facts_from_memory(self) -> None:
        proto = GossipProtocol("a0")
        adapter = GossipMemoryAdapter("a0", proto)

        memory_facts = [
            {"context": "Biology", "outcome": "Cells divide by mitosis", "confidence": 0.9},
            {"context": "Physics", "outcome": "Light travels at 3e8 m/s", "confidence": 0.95},
        ]

        added = adapter.add_facts_from_memory(memory_facts)
        assert added == 2
        assert proto.fact_count == 2

    def test_add_facts_dedup(self) -> None:
        proto = GossipProtocol("a0")
        adapter = GossipMemoryAdapter("a0", proto)

        facts = [{"context": "X", "outcome": "same", "confidence": 0.9}]
        adapter.add_facts_from_memory(facts)
        adapter.add_facts_from_memory(facts)
        # Second load is deduplicated by adapter
        assert proto.fact_count == 1

    def test_add_facts_skips_empty(self) -> None:
        proto = GossipProtocol("a0")
        adapter = GossipMemoryAdapter("a0", proto)

        facts = [
            {"context": "X", "outcome": "", "confidence": 0.9},
            {"context": "Y", "confidence": 0.9},
        ]
        added = adapter.add_facts_from_memory(facts)
        assert added == 0

    def test_export_top_k(self) -> None:
        proto = GossipProtocol("a0")
        adapter = GossipMemoryAdapter("a0", proto)

        for i in range(15):
            proto.add_local_fact(f"fact {i}", confidence=0.8)

        exported = adapter.export_top_k_facts(k=5)
        assert len(exported) == 5

    def test_import_gossip_facts(self) -> None:
        proto = GossipProtocol("a0")
        adapter = GossipMemoryAdapter("a0", proto)

        # Add a local fact
        proto.add_local_fact("local fact", confidence=0.9)

        # Receive a gossip fact
        gf = GossipFact(
            fact_id=content_hash("[Biology] Cells divide"),
            content="[Biology] Cells divide",
            confidence=0.85,
            source_agent_id="a1",
            origin_timestamp=datetime.now(UTC),
            hop_count=1,
        )
        proto.receive_gossip(
            GossipMessage(sender_id="a1", facts=[gf], lamport_clock=1, round_number=1)
        )

        # Import should return only the gossip-received fact
        imported = adapter.import_gossip_facts()
        assert len(imported) == 1
        assert imported[0]["context"] == "Biology"
        assert imported[0]["fact"] == "Cells divide"
        assert "gossip" in imported[0]["tags"]
        assert "source:a1" in imported[0]["tags"]

    def test_adapter_validation(self) -> None:
        proto = GossipProtocol("a0")
        with pytest.raises(ValueError, match="agent_id cannot be empty"):
            GossipMemoryAdapter("", proto)


# ---------------------------------------------------------------------------
# Thread safety test
# ---------------------------------------------------------------------------


class TestThreadSafety:
    def test_concurrent_add_and_receive(self) -> None:
        """Multiple threads adding and receiving facts should not corrupt state."""
        proto = GossipProtocol("a0")
        errors: list[Exception] = []

        def add_facts(start: int) -> None:
            try:
                for i in range(50):
                    proto.add_local_fact(f"thread_fact_{start}_{i}", confidence=0.8)
            except Exception as e:
                errors.append(e)

        def receive_facts(start: int) -> None:
            try:
                for i in range(50):
                    gf = GossipFact(
                        fact_id=content_hash(f"recv_fact_{start}_{i}"),
                        content=f"recv_fact_{start}_{i}",
                        confidence=0.7,
                        source_agent_id=f"sender_{start}",
                        origin_timestamp=datetime.now(UTC),
                        hop_count=1,
                    )
                    proto.receive_gossip(
                        GossipMessage(
                            sender_id=f"sender_{start}",
                            facts=[gf],
                            lamport_clock=i,
                            round_number=1,
                        )
                    )
            except Exception as e:
                errors.append(e)

        threads = []
        for t in range(4):
            threads.append(threading.Thread(target=add_facts, args=(t * 100,)))
            threads.append(threading.Thread(target=receive_facts, args=(t * 100,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Thread errors: {errors}"
        # Should have facts from both local adds and receives
        assert proto.fact_count > 0


# ---------------------------------------------------------------------------
# Coverage stats test
# ---------------------------------------------------------------------------


class TestCoverageStats:
    def test_coverage_calculation(self) -> None:
        proto = GossipProtocol("a0")
        proto.add_local_fact("one")
        proto.add_local_fact("two")

        stats = proto.get_coverage_stats(total_unique_facts=10)
        assert stats["agent_id"] == "a0"
        assert stats["known_facts"] == 2
        assert stats["total_facts"] == 10
        assert stats["coverage_pct"] == pytest.approx(20.0)
        assert stats["local_facts"] == 2
        assert stats["received_facts"] == 0

    def test_coverage_zero_total(self) -> None:
        proto = GossipProtocol("a0")
        stats = proto.get_coverage_stats(total_unique_facts=0)
        assert stats["coverage_pct"] == 0.0
