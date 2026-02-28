"""Tests for Hierarchical Knowledge Graph with Promotion/Pull mechanics.

Tests the contract, not implementation details:
- PromotionPolicy threshold and consensus logic
- PromotionManager propose/vote/promote lifecycle
- PullManager query relevance and pull tracking
- HierarchicalKnowledgeGraph end-to-end with multiple agents
- Isolation: unpromoted facts stay local
- Visibility: promoted facts visible to all agents
- Consensus voting: 2-of-3 agents agree
- Confidence aggregation correctness
"""

from __future__ import annotations

import pytest

from amplihack.agents.goal_seeking.hive_mind.hierarchical import (
    HierarchicalKnowledgeGraph,
    HiveFact,
    PendingPromotion,
    PromotionManager,
    PromotionPolicy,
    PullManager,
)

# ---------------------------------------------------------------------------
# PromotionPolicy tests
# ---------------------------------------------------------------------------


class TestPromotionPolicy:
    """Test configurable promotion rules."""

    def test_default_thresholds(self):
        policy = PromotionPolicy()
        assert policy.confidence_threshold == 0.7
        assert policy.consensus_required == 1

    def test_custom_thresholds(self):
        policy = PromotionPolicy(confidence_threshold=0.5, consensus_required=3)
        assert policy.confidence_threshold == 0.5
        assert policy.consensus_required == 3

    def test_invalid_confidence_threshold(self):
        with pytest.raises(ValueError, match="confidence_threshold"):
            PromotionPolicy(confidence_threshold=1.5)
        with pytest.raises(ValueError, match="confidence_threshold"):
            PromotionPolicy(confidence_threshold=-0.1)

    def test_invalid_consensus_required(self):
        with pytest.raises(ValueError, match="consensus_required"):
            PromotionPolicy(consensus_required=0)

    def test_aggregate_confidence_empty(self):
        policy = PromotionPolicy()
        assert policy.aggregate_confidence([]) == 0.0

    def test_aggregate_confidence_single(self):
        policy = PromotionPolicy()
        assert policy.aggregate_confidence([0.9]) == 0.9

    def test_aggregate_confidence_multiple(self):
        policy = PromotionPolicy()
        result = policy.aggregate_confidence([0.8, 0.6, 1.0])
        assert abs(result - 0.8) < 1e-9

    def test_should_promote_single_agent_high_confidence(self):
        policy = PromotionPolicy(confidence_threshold=0.7, consensus_required=1)
        pending = PendingPromotion(
            fact_id="f1",
            content="test",
            proposer_agent_id="a1",
            confidence=0.9,
        )
        assert policy.should_promote(pending, {"a1": True}) is True

    def test_should_promote_fails_low_confidence(self):
        policy = PromotionPolicy(confidence_threshold=0.9, consensus_required=1)
        pending = PendingPromotion(
            fact_id="f1",
            content="test",
            proposer_agent_id="a1",
            confidence=0.5,
        )
        # 0.5 < 0.9 threshold
        assert policy.should_promote(pending, {"a1": True}) is False

    def test_should_promote_fails_insufficient_consensus(self):
        policy = PromotionPolicy(confidence_threshold=0.5, consensus_required=3)
        pending = PendingPromotion(
            fact_id="f1",
            content="test",
            proposer_agent_id="a1",
            confidence=0.9,
        )
        # Only 2 approve, need 3
        assert policy.should_promote(pending, {"a1": True, "a2": True, "a3": False}) is False

    def test_should_promote_passes_with_consensus(self):
        policy = PromotionPolicy(confidence_threshold=0.5, consensus_required=2)
        pending = PendingPromotion(
            fact_id="f1",
            content="test",
            proposer_agent_id="a1",
            confidence=0.8,
        )
        assert policy.should_promote(pending, {"a1": True, "a2": True}) is True

    def test_reject_votes_dont_count_toward_consensus(self):
        policy = PromotionPolicy(confidence_threshold=0.5, consensus_required=2)
        pending = PendingPromotion(
            fact_id="f1",
            content="test",
            proposer_agent_id="a1",
            confidence=0.8,
        )
        # a1 approves, a2 rejects, a3 approves -> 2 approve, meets consensus
        votes = {"a1": True, "a2": False, "a3": True}
        assert policy.should_promote(pending, votes) is True


# ---------------------------------------------------------------------------
# PromotionManager tests
# ---------------------------------------------------------------------------


class TestPromotionManager:
    """Test propose/vote/promote lifecycle."""

    def test_propose_creates_pending(self):
        pm = PromotionManager()
        fact_id = pm.propose_promotion("agent_a", "test fact", 0.9)
        pending = pm.get_pending_promotions()
        assert len(pending) == 1
        assert pending[0].fact_id == fact_id
        assert pending[0].content == "test fact"
        assert pending[0].proposer_agent_id == "agent_a"
        assert pending[0].confidence == 0.9

    def test_proposer_auto_votes_approve(self):
        pm = PromotionManager()
        pm.propose_promotion("agent_a", "test", 0.9)
        pending = pm.get_pending_promotions()
        assert pending[0].votes == {"agent_a": True}

    def test_vote_recorded(self):
        pm = PromotionManager(policy=PromotionPolicy(consensus_required=2))
        fact_id = pm.propose_promotion("a1", "test", 0.9)
        result = pm.vote_on_promotion("a2", fact_id, True)
        assert result is True
        pending = pm.get_pending_promotions()
        assert "a2" in pending[0].votes

    def test_vote_on_nonexistent_fact(self):
        pm = PromotionManager()
        assert pm.vote_on_promotion("a1", "nonexistent", True) is False

    def test_duplicate_vote_raises(self):
        pm = PromotionManager(policy=PromotionPolicy(consensus_required=2))
        fact_id = pm.propose_promotion("a1", "test", 0.9)
        with pytest.raises(ValueError, match="already voted"):
            pm.vote_on_promotion("a1", fact_id, True)

    def test_check_and_promote_immediate(self):
        """With consensus_required=1, proposer alone can promote."""
        pm = PromotionManager(policy=PromotionPolicy(consensus_required=1))
        fact_id = pm.propose_promotion("a1", "test fact", 0.9)
        result = pm.check_and_promote(fact_id)
        assert result is not None
        assert isinstance(result, HiveFact)
        assert result.content == "test fact"
        assert "a1" in result.source_agents
        # Should no longer be pending
        assert len(pm.get_pending_promotions()) == 0

    def test_check_and_promote_needs_consensus(self):
        """With consensus_required=2, one vote is not enough."""
        pm = PromotionManager(policy=PromotionPolicy(consensus_required=2))
        fact_id = pm.propose_promotion("a1", "test", 0.8)
        # Only proposer voted so far
        result = pm.check_and_promote(fact_id)
        assert result is None
        assert len(pm.get_pending_promotions()) == 1

    def test_promote_after_second_vote(self):
        pm = PromotionManager(
            policy=PromotionPolicy(consensus_required=2, confidence_threshold=0.5)
        )
        fact_id = pm.propose_promotion("a1", "test", 0.8)
        pm.vote_on_promotion("a2", fact_id, True)
        result = pm.check_and_promote(fact_id)
        assert result is not None
        assert result.promotion_count == 2
        assert set(result.source_agents) == {"a1", "a2"}

    def test_check_nonexistent_returns_none(self):
        pm = PromotionManager()
        assert pm.check_and_promote("fake") is None

    def test_promoted_facts_tracked(self):
        pm = PromotionManager(policy=PromotionPolicy(consensus_required=1))
        fid = pm.propose_promotion("a1", "promoted fact", 0.9)
        pm.check_and_promote(fid)
        promoted = pm.get_promoted_facts()
        assert fid in promoted
        assert promoted[fid].content == "promoted fact"


# ---------------------------------------------------------------------------
# PullManager tests
# ---------------------------------------------------------------------------


class TestPullManager:
    """Test query and pull mechanics."""

    def _make_hive_store(self) -> dict[str, HiveFact]:
        facts = {}
        for i, (content, tags) in enumerate(
            [
                ("Python is an interpreted language", ["python", "language"]),
                ("TCP uses three-way handshake", ["networking", "tcp"]),
                ("SQL injection is a security vulnerability", ["security", "sql"]),
                ("Load balancers distribute traffic", ["infrastructure", "networking"]),
            ]
        ):
            fid = f"hf_{i}"
            facts[fid] = HiveFact(
                fact_id=fid,
                content=content,
                confidence=0.85,
                source_agents=["a1"],
                promotion_count=1,
                tags=tags,
            )
        return facts

    def test_query_hive_returns_relevant(self):
        store = self._make_hive_store()
        pm = PullManager(hive_store=store)
        results = pm.query_hive("networking traffic")
        assert len(results) > 0
        # "Load balancers distribute traffic" should be highly relevant
        contents = [r.content for r in results]
        assert any("traffic" in c for c in contents)

    def test_query_hive_empty_query(self):
        store = self._make_hive_store()
        pm = PullManager(hive_store=store)
        assert pm.query_hive("") == []

    def test_query_hive_no_match(self):
        store = self._make_hive_store()
        pm = PullManager(hive_store=store)
        results = pm.query_hive("quantum entanglement photon")
        assert len(results) == 0

    def test_query_hive_limit(self):
        store = self._make_hive_store()
        pm = PullManager(hive_store=store)
        results = pm.query_hive("networking security", limit=1)
        assert len(results) <= 1

    def test_pull_to_local_records_history(self):
        store = self._make_hive_store()
        pm = PullManager(hive_store=store)
        result = pm.pull_to_local("agent_a", "hf_0")
        assert result is not None
        assert result.fact_id == "hf_0"
        assert "hf_0" in pm.get_pull_history("agent_a")

    def test_pull_nonexistent_returns_none(self):
        pm = PullManager()
        assert pm.pull_to_local("a1", "fake") is None

    def test_pull_history_empty_for_unknown_agent(self):
        pm = PullManager()
        assert pm.get_pull_history("unknown") == []

    def test_pull_idempotent(self):
        store = self._make_hive_store()
        pm = PullManager(hive_store=store)
        pm.pull_to_local("a1", "hf_0")
        pm.pull_to_local("a1", "hf_0")
        assert pm.get_pull_history("a1").count("hf_0") == 1

    def test_set_hive_store(self):
        pm = PullManager()
        assert pm.query_hive("anything") == []
        store = self._make_hive_store()
        pm.set_hive_store(store)
        assert len(pm.query_hive("Python language")) > 0


# ---------------------------------------------------------------------------
# HierarchicalKnowledgeGraph tests
# ---------------------------------------------------------------------------


class TestHierarchicalKnowledgeGraph:
    """End-to-end tests with multiple agents."""

    def test_register_agents(self):
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        hkg.register_agent("a2")
        stats = hkg.get_stats()
        assert stats["registered_agents"] == 2

    def test_unregistered_agent_raises(self):
        hkg = HierarchicalKnowledgeGraph()
        with pytest.raises(ValueError, match="not registered"):
            hkg.store_local_fact("unknown", "test", 0.9)

    def test_store_local_fact(self):
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        fid = hkg.store_local_fact("a1", "Python is great", 0.9, ["python"])
        assert fid is not None
        stats = hkg.get_stats()
        assert stats["local_facts_per_agent"]["a1"] == 1

    def test_local_facts_isolated(self):
        """Facts stored by one agent are not visible to another via query_local."""
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        hkg.register_agent("a2")
        hkg.store_local_fact("a1", "Secret fact about Python", 0.9, ["python"])
        results_a1 = hkg.query_local("a1", "Python")
        results_a2 = hkg.query_local("a2", "Python")
        assert len(results_a1) == 1
        assert len(results_a2) == 0

    def test_promote_with_consensus_1(self):
        """With default consensus=1, promote is immediate."""
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        hkg.store_local_fact("a1", "TCP uses ports", 0.9, ["networking"])
        hkg.promote_fact("a1", "TCP uses ports", 0.9, ["networking"])
        # Should be in hive now
        results = hkg.query_hive("TCP networking ports")
        assert len(results) == 1
        assert "TCP" in results[0].content

    def test_promoted_facts_visible_to_all_agents(self):
        """Promoted facts should be queryable by any agent via query_hive."""
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        hkg.register_agent("a2")
        hkg.register_agent("a3")
        hkg.promote_fact("a1", "DNS resolves domain names", 0.85, ["networking", "dns"])
        # All agents should see it via hive query
        for agent in ["a1", "a2", "a3"]:
            results = hkg.query_hive("DNS domain names")
            assert len(results) >= 1
            assert any("DNS" in r.content for r in results)

    def test_unpromoted_facts_remain_local(self):
        """Facts that are not promoted should not appear in hive queries."""
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        hkg.store_local_fact("a1", "Local only secret fact about routing", 0.5, ["networking"])
        results = hkg.query_hive("routing networking")
        assert len(results) == 0

    def test_consensus_voting_2_of_3(self):
        """Test that 2-of-3 consensus works correctly."""
        policy = PromotionPolicy(confidence_threshold=0.5, consensus_required=2)
        hkg = HierarchicalKnowledgeGraph(promotion_policy=policy)
        hkg.register_agent("a1")
        hkg.register_agent("a2")
        hkg.register_agent("a3")

        # a1 proposes (auto-votes approve)
        fid = hkg.promote_fact("a1", "Load balancers improve availability", 0.8, ["infra"])
        # With consensus=2, should be pending still (only a1 voted)
        pending = hkg.get_pending_promotions()
        assert len(pending) == 1

        # a2 votes approve -> 2 of 3, meets consensus
        result = hkg.vote_on_promotion("a2", fid, True)
        assert result is not None  # Promoted
        assert result.content == "Load balancers improve availability"
        assert len(hkg.get_pending_promotions()) == 0

    def test_consensus_voting_rejected(self):
        """If not enough agents approve, fact stays pending."""
        policy = PromotionPolicy(confidence_threshold=0.5, consensus_required=3)
        hkg = HierarchicalKnowledgeGraph(promotion_policy=policy)
        hkg.register_agent("a1")
        hkg.register_agent("a2")
        hkg.register_agent("a3")

        fid = hkg.promote_fact("a1", "Controversial fact", 0.8)
        # a2 rejects
        result = hkg.vote_on_promotion("a2", fid, False)
        assert result is None  # Not promoted (1 approve, 1 reject, need 3)
        # a3 approves
        result = hkg.vote_on_promotion("a3", fid, True)
        assert result is None  # Still not promoted (2 approve, need 3)
        assert len(hkg.get_pending_promotions()) == 1

    def test_pull_hive_fact_to_local(self):
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        hkg.register_agent("a2")
        hkg.promote_fact("a1", "HTTP status 200 means success", 0.95, ["http"])
        hive_results = hkg.query_hive("HTTP status")
        assert len(hive_results) == 1

        # a2 pulls it
        pulled = hkg.pull_hive_fact("a2", hive_results[0].fact_id)
        assert pulled is not None
        assert pulled.from_hive is True
        assert pulled.content == "HTTP status 200 means success"

        # Now a2 should find it locally
        local_results = hkg.query_local("a2", "HTTP status")
        assert len(local_results) == 1

    def test_pull_avoids_duplicates(self):
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        hkg.register_agent("a2")
        hkg.promote_fact("a1", "Redis is an in-memory store", 0.9, ["redis"])
        hive_results = hkg.query_hive("Redis")
        fid = hive_results[0].fact_id

        pulled1 = hkg.pull_hive_fact("a2", fid)
        pulled2 = hkg.pull_hive_fact("a2", fid)
        # Should return same local fact, not create duplicate
        assert pulled1.fact_id == pulled2.fact_id
        stats = hkg.get_stats()
        assert stats["local_facts_per_agent"]["a2"] == 1

    def test_query_combined_merges_results(self):
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        hkg.register_agent("a2")
        # a1 has local fact
        hkg.store_local_fact("a1", "Python uses indentation for blocks", 0.9, ["python"])
        # a2 promotes a fact to hive
        hkg.promote_fact("a2", "Python supports list comprehensions", 0.85, ["python"])

        # a1 queries combined: should see local + hive
        combined = hkg.query_combined("a1", "Python")
        assert len(combined) == 2
        sources = {r["source"] for r in combined}
        assert sources == {"local", "hive"}

    def test_query_combined_deduplicates_pulled_facts(self):
        """Facts already pulled from hive should not appear twice in combined results."""
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        hkg.register_agent("a2")
        hkg.promote_fact("a1", "Kubernetes orchestrates containers", 0.9, ["k8s"])
        hive_results = hkg.query_hive("Kubernetes")
        hkg.pull_hive_fact("a2", hive_results[0].fact_id)

        combined = hkg.query_combined("a2", "Kubernetes containers")
        # Should appear once as local (pulled), not also as hive
        assert len(combined) == 1
        assert combined[0]["source"] == "local"

    def test_get_stats_comprehensive(self):
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        hkg.register_agent("a2")
        hkg.store_local_fact("a1", "Fact 1", 0.9)
        hkg.store_local_fact("a1", "Fact 2", 0.8)
        hkg.store_local_fact("a2", "Fact 3", 0.7)
        hkg.promote_fact("a1", "Promoted fact", 0.95)

        stats = hkg.get_stats()
        assert stats["registered_agents"] == 2
        assert stats["local_facts_per_agent"]["a1"] == 2
        assert stats["local_facts_per_agent"]["a2"] == 1
        assert stats["hive_facts"] == 1
        assert stats["total_local_facts"] == 3
        assert stats["promotion_rate"] == 1.0  # 1 promoted, 0 pending

    def test_three_agent_workflow(self):
        """Full workflow: 3 agents each learn, promote, pull, query."""
        policy = PromotionPolicy(confidence_threshold=0.6, consensus_required=2)
        hkg = HierarchicalKnowledgeGraph(promotion_policy=policy)

        agents = ["infra", "security", "performance"]
        for a in agents:
            hkg.register_agent(a)

        # Each agent stores local facts
        hkg.store_local_fact("infra", "Servers run on port 8080", 0.9, ["infra"])
        hkg.store_local_fact("security", "TLS encrypts traffic", 0.95, ["security", "tls"])
        hkg.store_local_fact("performance", "Caching reduces latency", 0.85, ["performance"])

        # infra proposes, security votes, performance votes
        fid = hkg.promote_fact("infra", "Load balancers distribute requests", 0.9, ["infra"])
        # Still pending (need 2 votes)
        assert len(hkg.get_pending_promotions()) == 1

        # security approves -> promoted
        result = hkg.vote_on_promotion("security", fid, True)
        assert result is not None
        assert len(hkg.get_pending_promotions()) == 0

        # performance pulls the promoted fact
        hive_facts = hkg.query_hive("load balancers requests")
        assert len(hive_facts) == 1
        hkg.pull_hive_fact("performance", hive_facts[0].fact_id)

        # Verify performance now has 2 local facts (own + pulled)
        stats = hkg.get_stats()
        assert stats["local_facts_per_agent"]["performance"] == 2
        assert stats["hive_facts"] == 1

    def test_confidence_aggregation_in_promoted_fact(self):
        """Verify promoted fact has correctly aggregated confidence."""
        policy = PromotionPolicy(confidence_threshold=0.5, consensus_required=2)
        hkg = HierarchicalKnowledgeGraph(promotion_policy=policy)
        hkg.register_agent("a1")
        hkg.register_agent("a2")

        fid = hkg.promote_fact("a1", "Test fact", 0.9, ["test"])
        result = hkg.vote_on_promotion("a2", fid, True)

        assert result is not None
        # Proposer confidence=0.9, approver gets 0.8 -> avg = 0.85
        assert abs(result.confidence - 0.85) < 1e-9


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_hive_query(self):
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        assert hkg.query_hive("anything") == []

    def test_empty_local_query(self):
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        assert hkg.query_local("a1", "anything") == []

    def test_empty_combined_query(self):
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        assert hkg.query_combined("a1", "anything") == []

    def test_pull_nonexistent_fact(self):
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        assert hkg.pull_hive_fact("a1", "fake_id") is None

    def test_vote_on_already_promoted_fact(self):
        """After promotion, voting should return None (fact no longer pending)."""
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        hkg.register_agent("a2")
        fid = hkg.promote_fact("a1", "Promoted already", 0.9)
        # Fact is already promoted (consensus=1), voting should return None
        result = hkg.vote_on_promotion("a2", fid, True)
        assert result is None

    def test_stats_with_no_agents(self):
        hkg = HierarchicalKnowledgeGraph()
        stats = hkg.get_stats()
        assert stats["registered_agents"] == 0
        assert stats["hive_facts"] == 0
        assert stats["total_local_facts"] == 0
        assert stats["promotion_rate"] == 0.0

    def test_many_local_facts_query_limit(self):
        hkg = HierarchicalKnowledgeGraph()
        hkg.register_agent("a1")
        for i in range(50):
            hkg.store_local_fact(
                "a1", f"Python feature number {i} coding", 0.5 + i * 0.01, ["python"]
            )
        results = hkg.query_local("a1", "Python coding feature", limit=5)
        assert len(results) == 5
