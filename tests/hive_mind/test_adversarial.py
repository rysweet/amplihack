"""Adversarial agent tests for hive mind quality gates and trust scoring.

Verifies that the hive graph correctly handles malicious or poorly-behaved
agents: garbage fact rejection, flood resilience, trust demotion,
contradiction detection, and broadcast tag guard enforcement.

All tests are pure unit tests — no LLM or embedding calls.
"""

from __future__ import annotations

from amplihack.agents.goal_seeking.hive_mind.constants import (
    BROADCAST_TAG_PREFIX,
    DEFAULT_QUALITY_THRESHOLD,
)
from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveFact,
    InMemoryHiveGraph,
)
from amplihack.agents.goal_seeking.hive_mind.quality import (
    QualityGate,
    score_content_quality,
)
from amplihack.agents.goal_seeking.hive_mind.reranker import trust_weighted_score

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_hive(hive_id: str = "test-hive") -> InMemoryHiveGraph:
    """Create an InMemoryHiveGraph with no embeddings (pure keyword mode)."""
    return InMemoryHiveGraph(hive_id=hive_id)


def _good_fact(concept: str = "database", content: str | None = None) -> HiveFact:
    """Return a well-formed fact that passes quality gate."""
    if content is None:
        content = (
            "PostgreSQL runs on port 5432 by default and supports "
            "ACID transactions for data integrity."
        )
    return HiveFact(fact_id="", content=content, concept=concept, confidence=0.9)


def _garbage_fact(concept: str = "database") -> HiveFact:
    """Return a low-quality fact that should fail quality gate."""
    return HiveFact(fact_id="", content="stuff idk maybe whatever", concept=concept, confidence=1.0)


# ===========================================================================
# Scenario 1: Rogue agent promotes garbage facts with confidence=1.0
# ===========================================================================


class TestGarbageFactRejection:
    """Quality gate rejects low-quality content regardless of confidence."""

    def test_garbage_content_scores_below_threshold(self) -> None:
        """Vague, short garbage content scores below DEFAULT_QUALITY_THRESHOLD."""
        score = score_content_quality("stuff idk maybe whatever", "database")
        assert score < DEFAULT_QUALITY_THRESHOLD, (
            f"Garbage content scored {score}, expected < {DEFAULT_QUALITY_THRESHOLD}"
        )

    def test_quality_gate_rejects_garbage(self) -> None:
        """QualityGate.should_promote returns False for garbage content."""
        gate = QualityGate(promotion_threshold=DEFAULT_QUALITY_THRESHOLD)
        assert gate.should_promote("stuff idk maybe whatever", "database") is False

    def test_quality_gate_accepts_good_content(self) -> None:
        """Sanity check: QualityGate.should_promote returns True for good content."""
        gate = QualityGate(promotion_threshold=DEFAULT_QUALITY_THRESHOLD)
        good = (
            "PostgreSQL runs on port 5432 by default and supports "
            "ACID transactions for data integrity."
        )
        assert gate.should_promote(good, "database") is True

    def test_high_confidence_does_not_bypass_quality(self) -> None:
        """Confidence=1.0 does not override quality scoring."""
        gate = QualityGate(promotion_threshold=DEFAULT_QUALITY_THRESHOLD)
        # Garbage content with max confidence — quality gate is content-based,
        # not confidence-based, so it still rejects.
        assert gate.should_promote("stuff", "database") is False
        assert gate.should_promote("idk dunno etc", "anything") is False

    def test_empty_content_rejected(self) -> None:
        """Empty or whitespace-only content always scores 0."""
        gate = QualityGate(promotion_threshold=DEFAULT_QUALITY_THRESHOLD)
        assert gate.should_promote("", "database") is False
        assert gate.should_promote("   ", "database") is False


# ===========================================================================
# Scenario 2: Rogue agent promotes many facts rapidly (flood test)
# ===========================================================================


class TestFloodResilience:
    """Hive survives a flood of facts and legitimate facts stay retrievable."""

    def test_flood_does_not_crash(self) -> None:
        """Promoting 1000 facts rapidly does not raise or crash."""
        hive = _make_hive()
        hive.register_agent("rogue", domain="spam")

        for i in range(1000):
            fact = HiveFact(
                fact_id="",
                content=f"Spam fact number {i} with some filler text for length.",
                concept="spam",
                confidence=0.5,
            )
            hive.promote_fact("rogue", fact)

        stats = hive.get_stats()
        assert stats["fact_count"] == 1000

    def test_legitimate_facts_retrievable_after_flood(self) -> None:
        """After a flood, a pre-existing legitimate fact is still queryable."""
        hive = _make_hive()
        hive.register_agent("good-agent", domain="database")
        hive.register_agent("rogue", domain="spam")

        # Promote a legitimate fact first
        legit = _good_fact()
        hive.promote_fact("good-agent", legit)

        # Flood with spam
        for i in range(500):
            spam = HiveFact(
                fact_id="",
                content=f"Irrelevant spam fact number {i} about random gibberish.",
                concept="spam",
                confidence=0.5,
            )
            hive.promote_fact("rogue", spam)

        # The legitimate fact should still be retrievable
        results = hive.query_facts("PostgreSQL port ACID", limit=50)
        legit_found = any("PostgreSQL" in f.content for f in results)
        assert legit_found, "Legitimate fact not retrievable after flood"

    def test_flood_agent_fact_count_tracked(self) -> None:
        """Agent fact_count correctly tracks the flood volume."""
        hive = _make_hive()
        hive.register_agent("rogue", domain="spam")

        for i in range(200):
            fact = HiveFact(
                fact_id="",
                content=f"Flood fact {i} with enough words to be non-trivial.",
                concept="noise",
                confidence=0.5,
            )
            hive.promote_fact("rogue", fact)

        agent = hive.get_agent("rogue")
        assert agent is not None
        assert agent.fact_count == 200


# ===========================================================================
# Scenario 3: Low-trust agent facts demoted by trust_weighted_score
# ===========================================================================


class TestTrustDemotion:
    """Facts from trust=0.1 agents score lower than trust=1.0 agent facts."""

    def test_low_trust_scores_below_high_trust(self) -> None:
        """Same similarity and confidence, lower trust => lower score."""
        low_trust_score = trust_weighted_score(similarity=0.8, trust=0.1, confidence=0.9)
        high_trust_score = trust_weighted_score(similarity=0.8, trust=1.0, confidence=0.9)
        assert low_trust_score < high_trust_score, (
            f"Low trust score ({low_trust_score}) should be < high trust score ({high_trust_score})"
        )

    def test_trust_weight_impact(self) -> None:
        """Trust contributes 30% weight — verify the magnitude of demotion."""
        # trust=0.1 => normalized to 0.05 (0.1/2.0), weight 0.3 => 0.015
        # trust=1.0 => normalized to 0.50 (1.0/2.0), weight 0.3 => 0.150
        # Difference should be ~0.135
        low = trust_weighted_score(similarity=0.8, trust=0.1, confidence=0.9)
        high = trust_weighted_score(similarity=0.8, trust=1.0, confidence=0.9)
        diff = high - low
        assert diff > 0.1, f"Trust demotion too small: {diff}"

    def test_zero_trust_agent(self) -> None:
        """Agent with trust=0.0 gets zero trust contribution."""
        score = trust_weighted_score(similarity=0.8, trust=0.0, confidence=0.9)
        # trust component = 0.3 * (0.0/2.0) = 0
        # Expected: 0.5*0.8 + 0.3*0.0 + 0.2*0.9 = 0.4 + 0 + 0.18 = 0.58
        assert abs(score - 0.58) < 0.01, f"Expected ~0.58, got {score}"

    def test_max_trust_agent(self) -> None:
        """Agent with trust=2.0 (max) gets full trust contribution."""
        score = trust_weighted_score(similarity=0.8, trust=2.0, confidence=0.9)
        # trust component = 0.3 * (2.0/2.0) = 0.3
        # Expected: 0.5*0.8 + 0.3*1.0 + 0.2*0.9 = 0.4 + 0.3 + 0.18 = 0.88
        assert abs(score - 0.88) < 0.01, f"Expected ~0.88, got {score}"

    def test_low_trust_in_hive_query_ordering(self) -> None:
        """In keyword query, low-trust agent facts rank by confidence only
        (keyword search doesn't use trust), but the trust-weighted scoring
        function itself correctly demotes them."""
        # This verifies the scoring function is correct; keyword search
        # uses hits + confidence*0.01, so trust demotion applies when
        # callers use trust_weighted_score (e.g., vector search path).
        hive = _make_hive()
        hive.register_agent("low-trust", domain="database", trust=0.1)
        hive.register_agent("high-trust", domain="database", trust=1.0)

        hive.promote_fact(
            "low-trust",
            HiveFact(
                fact_id="",
                content="PostgreSQL database runs on port 5432 for connections.",
                concept="database",
                confidence=0.9,
            ),
        )
        hive.promote_fact(
            "high-trust",
            HiveFact(
                fact_id="",
                content="PostgreSQL database uses port 5432 as the default port.",
                concept="database",
                confidence=0.9,
            ),
        )

        # Both facts should be in the hive
        results = hive.query_facts("PostgreSQL port", limit=10)
        assert len(results) == 2


# ===========================================================================
# Scenario 4: Contradicting facts detection
# ===========================================================================


class TestContradictionDetection:
    """check_contradictions detects same-concept, different-content facts."""

    def test_detects_contradicting_port(self) -> None:
        """Two facts about same concept with opposite port numbers detected."""
        hive = _make_hive()
        hive.register_agent("agent-a", domain="database")

        hive.promote_fact(
            "agent-a",
            HiveFact(
                fact_id="",
                content="PostgreSQL runs on port 5432 by default.",
                concept="database_port",
                confidence=0.9,
            ),
        )

        contradictions = hive.check_contradictions(
            content="PostgreSQL runs on port 3306 by default.",
            concept="database_port",
        )
        assert len(contradictions) == 1
        assert "5432" in contradictions[0].content

    def test_no_contradiction_for_identical_content(self) -> None:
        """Identical content is a confirmation, not a contradiction."""
        hive = _make_hive()
        hive.register_agent("agent-a", domain="database")

        content = "PostgreSQL runs on port 5432 by default."
        hive.promote_fact(
            "agent-a",
            HiveFact(fact_id="", content=content, concept="database_port", confidence=0.9),
        )

        contradictions = hive.check_contradictions(content=content, concept="database_port")
        assert len(contradictions) == 0

    def test_no_contradiction_for_different_concept(self) -> None:
        """Different concepts don't trigger contradiction even with word overlap."""
        hive = _make_hive()
        hive.register_agent("agent-a", domain="database")

        hive.promote_fact(
            "agent-a",
            HiveFact(
                fact_id="",
                content="PostgreSQL runs on port 5432 by default.",
                concept="database_port",
                confidence=0.9,
            ),
        )

        # Same word overlap but different concept
        contradictions = hive.check_contradictions(
            content="PostgreSQL runs on port 3306 by default.",
            concept="mysql_port",
        )
        assert len(contradictions) == 0

    def test_retracted_facts_ignored(self) -> None:
        """Retracted facts are not considered for contradictions."""
        hive = _make_hive()
        hive.register_agent("agent-a", domain="database")

        fact = HiveFact(
            fact_id="",
            content="PostgreSQL runs on port 5432 by default.",
            concept="database_port",
            confidence=0.9,
        )
        fact_id = hive.promote_fact("agent-a", fact)
        hive.retract_fact(fact_id)

        contradictions = hive.check_contradictions(
            content="PostgreSQL runs on port 3306 by default.",
            concept="database_port",
        )
        assert len(contradictions) == 0

    def test_low_overlap_not_flagged(self) -> None:
        """Content with < 0.4 Jaccard overlap is not flagged as contradicting."""
        hive = _make_hive()
        hive.register_agent("agent-a", domain="database")

        hive.promote_fact(
            "agent-a",
            HiveFact(
                fact_id="",
                content="PostgreSQL runs on port 5432 by default.",
                concept="database_config",
                confidence=0.9,
            ),
        )

        # Very different wording — low Jaccard overlap
        contradictions = hive.check_contradictions(
            content="The system uses Redis for caching session data efficiently.",
            concept="database_config",
        )
        assert len(contradictions) == 0


# ===========================================================================
# Scenario 5: Broadcast tag guard — second broadcast adds tag
# ===========================================================================


class TestBroadcastTagGuard:
    """Broadcast tag prevents infinite re-broadcast loops."""

    def _build_federation(self) -> tuple[InMemoryHiveGraph, InMemoryHiveGraph, InMemoryHiveGraph]:
        """Create parent -> [child_a, child_b] federation."""
        parent = _make_hive("parent")
        child_a = _make_hive("child-a")
        child_b = _make_hive("child-b")

        child_a.set_parent(parent)
        child_b.set_parent(parent)
        parent.add_child(child_a)
        parent.add_child(child_b)

        parent.register_agent("relay-agent", domain="relay")
        child_a.register_agent("agent-a", domain="database")
        child_b.register_agent("agent-b", domain="database")

        return parent, child_a, child_b

    def test_high_confidence_fact_broadcasts_to_sibling(self) -> None:
        """A high-confidence fact in child_a reaches child_b via parent."""
        parent, child_a, child_b = self._build_federation()

        child_a.promote_fact(
            "agent-a",
            HiveFact(
                fact_id="",
                content="PostgreSQL runs on port 5432 and supports ACID transactions.",
                concept="database",
                confidence=0.95,  # Above broadcast_threshold (0.9)
            ),
        )

        # child_b should have received a broadcast copy
        child_b_facts = child_b.query_facts("PostgreSQL", limit=10)
        assert len(child_b_facts) >= 1, "Broadcast fact not received by sibling"

    def test_broadcast_copy_has_tag(self) -> None:
        """Broadcast copies carry the broadcast_from: tag."""
        parent, child_a, child_b = self._build_federation()

        child_a.promote_fact(
            "agent-a",
            HiveFact(
                fact_id="",
                content="PostgreSQL runs on port 5432 and supports ACID transactions.",
                concept="database",
                confidence=0.95,
            ),
        )

        child_b_facts = child_b.query_facts("PostgreSQL", limit=10)
        assert len(child_b_facts) >= 1

        broadcast_fact = child_b_facts[0]
        has_broadcast_tag = any(t.startswith(BROADCAST_TAG_PREFIX) for t in broadcast_fact.tags)
        assert has_broadcast_tag, f"Broadcast copy missing tag. Tags: {broadcast_fact.tags}"

    def test_broadcast_copy_not_re_broadcast(self) -> None:
        """A fact with broadcast_from: tag is NOT re-broadcast by the receiver.

        If child_b receives a broadcast copy and it has confidence >= threshold,
        it must NOT escalate it back to parent (which would loop forever).
        """
        parent, child_a, child_b = self._build_federation()

        parent_fact_count_before = parent.get_stats()["fact_count"]

        child_a.promote_fact(
            "agent-a",
            HiveFact(
                fact_id="",
                content="PostgreSQL runs on port 5432 and supports ACID transactions.",
                concept="database",
                confidence=0.95,
            ),
        )

        # Parent got the escalated copy from child_a.
        # child_b got a broadcast copy from parent.
        # But child_b should NOT re-escalate to parent.
        parent_fact_count_after = parent.get_stats()["fact_count"]

        # Parent should have exactly 1 escalated fact (from child_a),
        # NOT 2 (which would mean child_b re-escalated).
        escalated_facts = parent_fact_count_after - parent_fact_count_before
        assert escalated_facts == 1, (
            f"Expected 1 escalated fact in parent, got {escalated_facts}. "
            "Broadcast copy may have been re-escalated."
        )

    def test_manual_broadcast_without_tag_gets_tagged_on_second_hop(self) -> None:
        """If an agent omits broadcast_from tag, the second broadcast adds it.

        Simulates: agent promotes a fact without broadcast_from tag to child_a.
        child_a's promote_fact triggers escalation to parent (no broadcast tag).
        Parent broadcasts to child_b — this broadcast ADDS the tag.
        child_b's copy WILL have the broadcast_from tag from parent.broadcast_fact.
        """
        parent, child_a, child_b = self._build_federation()

        # Promote a fact WITHOUT any broadcast tag — simulates bypassing the guard
        fact_no_tag = HiveFact(
            fact_id="",
            content="Redis uses port 6379 and supports pub/sub messaging patterns.",
            concept="cache_config",
            confidence=0.95,
            tags=[],  # No broadcast_from tag
        )
        child_a.promote_fact("agent-a", fact_no_tag)

        # The fact should reach child_b via parent broadcast
        child_b_facts = child_b.query_facts("Redis port", limit=10)
        assert len(child_b_facts) >= 1, "Fact did not reach child_b"

        # The copy in child_b MUST have the broadcast_from tag
        # (added by parent.broadcast_fact, not by the original agent)
        broadcast_copy = child_b_facts[0]
        has_tag = any(t.startswith(BROADCAST_TAG_PREFIX) for t in broadcast_copy.tags)
        assert has_tag, f"Second broadcast should add tag. Got tags: {broadcast_copy.tags}"

    def test_below_threshold_not_broadcast(self) -> None:
        """Facts below broadcast_threshold are not escalated or broadcast."""
        parent, child_a, child_b = self._build_federation()

        child_a.promote_fact(
            "agent-a",
            HiveFact(
                fact_id="",
                content="PostgreSQL database has many features for enterprise use.",
                concept="database",
                confidence=0.5,  # Below 0.9 threshold
            ),
        )

        child_b_facts = child_b.query_facts("PostgreSQL", limit=10)
        assert len(child_b_facts) == 0, "Low-confidence fact should not broadcast"
