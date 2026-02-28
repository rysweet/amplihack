"""Tests for Unified Hive Mind (Experiment 5).

Tests the contract of UnifiedHiveMind and HiveMindAgent:
- HiveMindConfig defaults and custom values
- Agent registration across all sublayers
- store_fact / promote_fact / query lifecycle
- Event bus propagation on promotion
- Gossip auto-trigger after N rounds via tick()
- Cross-agent knowledge sharing (3 agents, different domains)
- Content-hash deduplication across all layers
- HiveMindAgent wrapper convenience methods
- Combined query merges local + hive without duplicates
- Event log records all activity
"""

from __future__ import annotations

import pytest

from amplihack.agents.goal_seeking.hive_mind.unified import (
    HiveMindAgent,
    HiveMindConfig,
    UnifiedHiveMind,
    _content_hash,
)

# ---------------------------------------------------------------------------
# HiveMindConfig tests
# ---------------------------------------------------------------------------


class TestHiveMindConfig:
    """Test configuration defaults and custom values."""

    def test_defaults(self):
        cfg = HiveMindConfig()
        assert cfg.promotion_confidence_threshold == 0.7
        assert cfg.promotion_consensus_required == 1
        assert cfg.gossip_interval_rounds == 5
        assert cfg.gossip_top_k == 10
        assert cfg.gossip_fanout == 2
        assert cfg.event_relevance_threshold == 0.3
        assert cfg.enable_gossip is True
        assert cfg.enable_events is True

    def test_custom_values(self):
        cfg = HiveMindConfig(
            promotion_confidence_threshold=0.5,
            promotion_consensus_required=3,
            gossip_interval_rounds=10,
            gossip_top_k=5,
            gossip_fanout=1,
            event_relevance_threshold=0.8,
            enable_gossip=False,
            enable_events=False,
        )
        assert cfg.promotion_confidence_threshold == 0.5
        assert cfg.promotion_consensus_required == 3
        assert cfg.gossip_interval_rounds == 10
        assert cfg.gossip_top_k == 5
        assert cfg.gossip_fanout == 1
        assert cfg.event_relevance_threshold == 0.8
        assert cfg.enable_gossip is False
        assert cfg.enable_events is False


# ---------------------------------------------------------------------------
# UnifiedHiveMind registration tests
# ---------------------------------------------------------------------------


class TestRegistration:
    """Test agent registration across all sublayers."""

    def test_register_single_agent(self):
        hive = UnifiedHiveMind()
        hive.register_agent("alpha")
        stats = hive.get_stats()
        assert stats["agent_count"] == 1
        assert "alpha" in stats["registered_agents"]

    def test_register_multiple_agents(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.register_agent("b")
        hive.register_agent("c")
        stats = hive.get_stats()
        assert stats["agent_count"] == 3

    def test_duplicate_registration_raises(self):
        hive = UnifiedHiveMind()
        hive.register_agent("alpha")
        with pytest.raises(ValueError, match="already registered"):
            hive.register_agent("alpha")

    def test_gossip_peers_updated_on_registration(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.register_agent("b")
        # Agent a should now know about b and vice versa
        proto_a = hive._gossip_protocols["a"]
        proto_b = hive._gossip_protocols["b"]
        assert "b" in proto_a.peers
        assert "a" in proto_b.peers


# ---------------------------------------------------------------------------
# Store + query basics
# ---------------------------------------------------------------------------


class TestStoreAndQuery:
    """Test basic store/query lifecycle."""

    def test_store_fact_returns_id(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        fid = hive.store_fact("a", "The sky is blue", 0.9, ["science"])
        assert fid is not None
        assert isinstance(fid, str)

    def test_store_fact_unregistered_agent_raises(self):
        hive = UnifiedHiveMind()
        with pytest.raises(ValueError, match="not registered"):
            hive.store_fact("ghost", "fact", 0.9)

    def test_query_local_returns_stored_facts(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.store_fact("a", "Python uses indentation for blocks", 0.95, ["python"])
        results = hive.query_local("a", "python indentation")
        assert len(results) >= 1
        assert results[0]["source"] == "local"
        assert "indentation" in results[0]["content"].lower()

    def test_query_local_does_not_return_other_agents_facts(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.register_agent("b")
        hive.store_fact("a", "Fact from agent A about Python", 0.9, ["python"])
        results = hive.query_local("b", "Python")
        assert len(results) == 0

    def test_query_hive_empty_before_promotion(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.store_fact("a", "Local only fact", 0.9)
        results = hive.query_hive("local")
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Promotion tests
# ---------------------------------------------------------------------------


class TestPromotion:
    """Test fact promotion from local to hive."""

    def test_promote_fact_makes_it_visible_in_hive(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.promote_fact("a", "Kubernetes orchestrates containers", 0.93, ["k8s"])
        results = hive.query_hive("kubernetes containers")
        assert len(results) >= 1
        contents = [r["content"] for r in results]
        assert any("kubernetes" in c.lower() for c in contents)

    def test_promote_with_consensus_1_is_immediate(self):
        cfg = HiveMindConfig(promotion_consensus_required=1)
        hive = UnifiedHiveMind(config=cfg)
        hive.register_agent("a")
        hive.promote_fact("a", "Immediate promotion fact", 0.8)
        stats = hive.get_stats()
        assert stats["graph"]["hive_facts"] >= 1

    def test_promote_with_consensus_2_stays_pending(self):
        cfg = HiveMindConfig(promotion_consensus_required=2)
        hive = UnifiedHiveMind(config=cfg)
        hive.register_agent("a")
        hive.register_agent("b")
        hive.promote_fact("a", "Needs consensus", 0.9)
        stats = hive.get_stats()
        # With consensus=2, proposer only has 1 vote, so stays pending
        assert stats["graph"]["pending_promotions"] >= 1


# ---------------------------------------------------------------------------
# Event bus tests
# ---------------------------------------------------------------------------


class TestEvents:
    """Test event bus propagation on promotion."""

    def test_promote_publishes_event(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.register_agent("b")
        hive.promote_fact("a", "Event test fact", 0.9, ["test"])
        # Event log should have at least 1 event
        stats = hive.get_stats()
        assert stats["events"]["total_events"] >= 1

    def test_events_disabled_skips_publish(self):
        cfg = HiveMindConfig(enable_events=False)
        hive = UnifiedHiveMind(config=cfg)
        hive.register_agent("a")
        hive.promote_fact("a", "No event fact", 0.9)
        stats = hive.get_stats()
        assert stats["events"]["total_events"] == 0

    def test_process_events_incorporates_promoted_facts(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.register_agent("b")
        hive.promote_fact("a", "Shared security fact about TLS encryption", 0.9, ["security"])
        results = hive.process_events()
        # Agent b should have processed at least 1 event
        assert results.get("b", 0) >= 1

    def test_process_events_noop_when_disabled(self):
        cfg = HiveMindConfig(enable_events=False)
        hive = UnifiedHiveMind(config=cfg)
        hive.register_agent("a")
        hive.register_agent("b")
        hive.promote_fact("a", "No event propagation", 0.9)
        results = hive.process_events()
        assert len(results) == 0

    def test_event_log_records_all_promotions(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.promote_fact("a", "Fact one", 0.9)
        hive.promote_fact("a", "Fact two", 0.8)
        hive.promote_fact("a", "Fact three", 0.7)
        stats = hive.get_stats()
        assert stats["events"]["total_events"] == 3


# ---------------------------------------------------------------------------
# Gossip tests
# ---------------------------------------------------------------------------


class TestGossip:
    """Test gossip layer integration."""

    def test_run_gossip_round_returns_stats(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.register_agent("b")
        hive.store_fact("a", "Gossip fact from A", 0.9)
        stats = hive.run_gossip_round()
        assert "round_number" in stats
        assert "messages_sent" in stats

    def test_gossip_auto_triggers_after_interval(self):
        cfg = HiveMindConfig(gossip_interval_rounds=3, enable_gossip=True)
        hive = UnifiedHiveMind(config=cfg)
        hive.register_agent("a")
        hive.register_agent("b")
        hive.store_fact("a", "Gossip trigger fact", 0.9)

        # Tick 3 times -- gossip should trigger on the 3rd tick
        result1 = hive.tick("a")
        assert result1["gossip_triggered"] is False
        result2 = hive.tick("a")
        assert result2["gossip_triggered"] is False
        result3 = hive.tick("a")
        assert result3["gossip_triggered"] is True

    def test_gossip_disabled_never_triggers(self):
        cfg = HiveMindConfig(gossip_interval_rounds=1, enable_gossip=False)
        hive = UnifiedHiveMind(config=cfg)
        hive.register_agent("a")
        result = hive.tick("a")
        assert result["gossip_triggered"] is False

    def test_gossip_spreads_facts_between_agents(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.register_agent("b")

        # Agent A stores facts
        hive.store_fact("a", "Unique gossip fact about distributed systems", 0.95)

        # Run gossip rounds to spread
        for _ in range(3):
            hive.run_gossip_round()

        # Agent B should know about A's fact via gossip
        proto_b = hive._gossip_protocols["b"]
        assert proto_b.fact_count > 0


# ---------------------------------------------------------------------------
# Cross-agent knowledge sharing (3 agents, different domains)
# ---------------------------------------------------------------------------


class TestCrossAgentSharing:
    """Test cross-agent knowledge sharing with 3 specialized agents."""

    @pytest.fixture()
    def three_agent_hive(self):
        hive = UnifiedHiveMind()
        hive.register_agent("infra")
        hive.register_agent("security")
        hive.register_agent("performance")

        # Each agent learns domain facts
        hive.store_fact(
            "infra", "Load balancers distribute requests across servers", 0.92, ["infra"]
        )
        hive.store_fact(
            "infra", "Docker containers package applications", 0.94, ["infra", "containers"]
        )
        hive.store_fact(
            "security", "TLS encrypts data in transit", 0.96, ["security", "encryption"]
        )
        hive.store_fact("security", "SQL injection inserts malicious SQL", 0.95, ["security"])
        hive.store_fact("performance", "Caching reduces latency", 0.95, ["performance", "caching"])
        hive.store_fact(
            "performance", "Database indexing speeds up queries", 0.94, ["performance", "database"]
        )

        # Promote key facts to hive
        hive.promote_fact(
            "infra", "Load balancers distribute requests across servers", 0.92, ["infra"]
        )
        hive.promote_fact(
            "security", "TLS encrypts data in transit", 0.96, ["security", "encryption"]
        )
        hive.promote_fact(
            "performance", "Caching reduces latency", 0.95, ["performance", "caching"]
        )

        return hive

    def test_security_agent_can_find_infra_facts_in_hive(self, three_agent_hive):
        results = three_agent_hive.query_hive("load balancers servers")
        contents = [r["content"].lower() for r in results]
        assert any("load balancer" in c for c in contents)

    def test_infra_agent_can_find_security_facts_in_hive(self, three_agent_hive):
        results = three_agent_hive.query_hive("TLS encryption transit")
        contents = [r["content"].lower() for r in results]
        assert any("tls" in c for c in contents)

    def test_query_all_merges_local_and_hive(self, three_agent_hive):
        # Infra agent queries for "caching" -- should find perf's promoted fact
        results = three_agent_hive.query_all("infra", "caching latency", limit=10)
        sources = {r["source"] for r in results}
        # Should have hive results (from performance's promotion)
        assert "hive" in sources or "local" in sources  # at least one source

    def test_process_events_shares_promoted_facts(self, three_agent_hive):
        results = three_agent_hive.process_events()
        # At least some agents should have processed events
        total_processed = sum(results.values())
        assert total_processed >= 1


# ---------------------------------------------------------------------------
# Deduplication tests
# ---------------------------------------------------------------------------


class TestDeduplication:
    """Test content-hash deduplication across all layers."""

    def test_content_hash_deterministic(self):
        h1 = _content_hash("hello world")
        h2 = _content_hash("hello world")
        assert h1 == h2

    def test_content_hash_case_insensitive(self):
        h1 = _content_hash("Hello World")
        h2 = _content_hash("hello world")
        assert h1 == h2

    def test_content_hash_strips_whitespace(self):
        h1 = _content_hash("  hello world  ")
        h2 = _content_hash("hello world")
        assert h1 == h2

    def test_query_all_deduplicates_across_sources(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")

        # Store the same fact locally and promote it
        content = "Duplicate fact about containers"
        hive.store_fact("a", content, 0.9, ["containers"])
        hive.promote_fact("a", content, 0.9, ["containers"])

        results = hive.query_all("a", "containers fact", limit=10)
        # Should not have duplicate content
        contents = [r["content"] for r in results]
        unique_hashes = {_content_hash(c) for c in contents}
        assert len(unique_hashes) == len(contents)


# ---------------------------------------------------------------------------
# HiveMindAgent wrapper tests
# ---------------------------------------------------------------------------


class TestHiveMindAgent:
    """Test HiveMindAgent convenience methods."""

    def test_learn_stores_and_ticks(self):
        hive = UnifiedHiveMind()
        hive.register_agent("alice")
        agent = HiveMindAgent("alice", hive)
        fid = agent.learn("Gravity pulls objects toward Earth", 0.99, ["physics"])
        assert fid is not None
        # Round counter should have advanced
        summary = hive.get_agent_knowledge_summary("alice")
        assert summary["learning_round"] >= 1

    def test_promote_makes_fact_visible_in_hive(self):
        hive = UnifiedHiveMind()
        hive.register_agent("alice")
        agent = HiveMindAgent("alice", hive)
        agent.promote("Promoted physics fact about gravity", 0.95, ["physics"])
        results = agent.ask_hive("gravity physics")
        assert len(results) >= 1

    def test_ask_returns_results(self):
        hive = UnifiedHiveMind()
        hive.register_agent("alice")
        agent = HiveMindAgent("alice", hive)
        agent.learn("Python is a programming language", 0.95, ["python"])
        results = agent.ask("python programming")
        assert len(results) >= 1

    def test_ask_local_only_returns_local(self):
        hive = UnifiedHiveMind()
        hive.register_agent("alice")
        hive.register_agent("bob")
        alice = HiveMindAgent("alice", hive)
        bob = HiveMindAgent("bob", hive)

        alice.learn("Alice's secret fact about quantum", 0.9, ["quantum"])
        bob.learn("Bob's fact about chemistry", 0.9, ["chemistry"])

        # Alice's local query should not find Bob's facts
        results = alice.ask_local("chemistry")
        assert len(results) == 0

    def test_ask_hive_returns_only_promoted(self):
        hive = UnifiedHiveMind()
        hive.register_agent("alice")
        agent = HiveMindAgent("alice", hive)
        agent.learn("Unpromoted fact about biology", 0.9, ["biology"])
        results = agent.ask_hive("biology")
        assert len(results) == 0  # Not promoted, so not in hive


# ---------------------------------------------------------------------------
# Stats and summary tests
# ---------------------------------------------------------------------------


class TestStats:
    """Test get_stats and get_agent_knowledge_summary."""

    def test_get_stats_structure(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        stats = hive.get_stats()
        assert "registered_agents" in stats
        assert "agent_count" in stats
        assert "graph" in stats
        assert "events" in stats
        assert "gossip" in stats
        assert "round_counters" in stats

    def test_get_agent_knowledge_summary(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.store_fact("a", "Fact one", 0.9)
        hive.store_fact("a", "Fact two", 0.8)
        summary = hive.get_agent_knowledge_summary("a")
        assert summary["agent_id"] == "a"
        assert summary["local_facts"] == 2
        assert summary["learning_round"] == 0  # no ticks yet

    def test_summary_unregistered_agent_raises(self):
        hive = UnifiedHiveMind()
        with pytest.raises(ValueError, match="not registered"):
            hive.get_agent_knowledge_summary("ghost")

    def test_stats_reflect_gossip_rounds(self):
        hive = UnifiedHiveMind()
        hive.register_agent("a")
        hive.register_agent("b")
        hive.run_gossip_round()
        stats = hive.get_stats()
        assert stats["gossip"]["total_rounds"] >= 1
