"""Tests for the six-type cognitive memory system."""

import time

import pytest
from amplihack_memory import CognitiveMemory


@pytest.fixture
def cm(tmp_path):
    """Create a CognitiveMemory instance with an isolated temp database."""
    db = tmp_path / "test_cognitive_db"
    mem = CognitiveMemory(agent_name="test-agent", db_path=db)
    yield mem
    mem.close()


@pytest.fixture
def cm_other(tmp_path):
    """Second CognitiveMemory instance for agent-isolation tests."""
    db = tmp_path / "test_cognitive_db"
    mem = CognitiveMemory(agent_name="other-agent", db_path=db)
    yield mem
    mem.close()


# ==================================================================
# Initialisation
# ==================================================================


class TestInit:
    def test_empty_agent_name_raises(self, tmp_path):
        with pytest.raises(ValueError, match="agent_name"):
            CognitiveMemory(agent_name="", db_path=tmp_path / "db")

    def test_whitespace_agent_name_raises(self, tmp_path):
        with pytest.raises(ValueError, match="agent_name"):
            CognitiveMemory(agent_name="   ", db_path=tmp_path / "db")

    def test_creates_db_directory(self, tmp_path):
        db_path = tmp_path / "new_dir" / "db"
        cm = CognitiveMemory(agent_name="a", db_path=db_path)
        assert db_path.exists()
        cm.close()


# ==================================================================
# SENSORY MEMORY
# ==================================================================


class TestSensoryMemory:
    def test_record_and_retrieve(self, cm):
        nid = cm.record_sensory("text", "Hello world")
        assert nid.startswith("sen_")

        items = cm.get_recent_sensory(limit=5)
        assert len(items) == 1
        assert items[0].node_id == nid
        assert items[0].modality == "text"
        assert items[0].raw_data == "Hello world"

    def test_ordering(self, cm):
        cm.record_sensory("a", "first")
        cm.record_sensory("b", "second")
        cm.record_sensory("c", "third")

        items = cm.get_recent_sensory(limit=10)
        assert len(items) == 3
        # Most recent first
        assert items[0].raw_data == "third"
        assert items[2].raw_data == "first"

    def test_expired_not_returned(self, cm):
        cm.record_sensory("text", "ephemeral", ttl_seconds=0)
        # TTL=0 means expires_at == created_at; already expired
        time.sleep(0.1)
        items = cm.get_recent_sensory()
        assert len(items) == 0

    def test_prune_expired(self, cm):
        cm.record_sensory("text", "will expire", ttl_seconds=0)
        cm.record_sensory("text", "will survive", ttl_seconds=600)
        time.sleep(0.1)
        pruned = cm.prune_expired_sensory()
        assert pruned == 1
        items = cm.get_recent_sensory()
        assert len(items) == 1
        assert items[0].raw_data == "will survive"

    def test_attend_to_sensory_promotes_to_episode(self, cm):
        sid = cm.record_sensory("error", "segfault detected", ttl_seconds=600)
        ep_id = cm.attend_to_sensory(sid, "critical error")
        assert ep_id is not None
        assert ep_id.startswith("epi_")

        episodes = cm.get_episodes()
        assert len(episodes) == 1
        assert "segfault detected" in episodes[0].content
        assert "critical error" in episodes[0].content

    def test_attend_to_missing_returns_none(self, cm):
        result = cm.attend_to_sensory("nonexistent", "reason")
        assert result is None


# ==================================================================
# WORKING MEMORY
# ==================================================================


class TestWorkingMemory:
    def test_push_and_get(self, cm):
        nid = cm.push_working("goal", "finish report", "task-1")
        assert nid.startswith("wrk_")

        slots = cm.get_working("task-1")
        assert len(slots) == 1
        assert slots[0].content == "finish report"
        assert slots[0].task_id == "task-1"

    def test_relevance_ordering(self, cm):
        cm.push_working("a", "low", "t1", relevance=0.1)
        cm.push_working("b", "high", "t1", relevance=0.9)
        cm.push_working("c", "mid", "t1", relevance=0.5)

        slots = cm.get_working("t1")
        assert slots[0].content == "high"
        assert slots[-1].content == "low"

    def test_capacity_eviction(self, cm):
        # Fill to capacity
        for i in range(CognitiveMemory.WORKING_MEMORY_CAPACITY):
            cm.push_working("item", f"slot-{i}", "t1", relevance=float(i))

        slots = cm.get_working("t1")
        assert len(slots) == CognitiveMemory.WORKING_MEMORY_CAPACITY

        # Push one more -- the slot with relevance 0.0 should be evicted
        cm.push_working("item", "new-slot", "t1", relevance=100.0)
        slots = cm.get_working("t1")
        assert len(slots) == CognitiveMemory.WORKING_MEMORY_CAPACITY
        contents = {s.content for s in slots}
        assert "new-slot" in contents
        assert "slot-0" not in contents  # lowest relevance evicted

    def test_clear_working(self, cm):
        cm.push_working("a", "x", "t1")
        cm.push_working("b", "y", "t1")
        cm.push_working("c", "z", "t2")

        cleared = cm.clear_working("t1")
        assert cleared == 2
        assert len(cm.get_working("t1")) == 0
        assert len(cm.get_working("t2")) == 1

    def test_task_isolation(self, cm):
        cm.push_working("a", "for t1", "t1")
        cm.push_working("b", "for t2", "t2")

        assert len(cm.get_working("t1")) == 1
        assert len(cm.get_working("t2")) == 1


# ==================================================================
# EPISODIC MEMORY
# ==================================================================


class TestEpisodicMemory:
    def test_store_and_retrieve(self, cm):
        eid = cm.store_episode("User asked about weather", "user-session")
        assert eid.startswith("epi_")

        episodes = cm.get_episodes()
        assert len(episodes) == 1
        assert episodes[0].content == "User asked about weather"
        assert episodes[0].source_label == "user-session"
        assert episodes[0].compressed is False

    def test_temporal_ordering(self, cm):
        cm.store_episode("first", "s")
        cm.store_episode("second", "s")
        cm.store_episode("third", "s")

        episodes = cm.get_episodes()
        assert episodes[0].content == "third"
        assert episodes[2].content == "first"

    def test_explicit_temporal_index(self, cm):
        cm.store_episode("a", "s", temporal_index=100)
        cm.store_episode("b", "s", temporal_index=50)

        episodes = cm.get_episodes()
        assert episodes[0].temporal_index == 100
        assert episodes[1].temporal_index == 50

    def test_metadata_roundtrip(self, cm):
        cm.store_episode("meta test", "s", metadata={"key": "value", "n": 42})
        ep = cm.get_episodes()[0]
        assert ep.metadata == {"key": "value", "n": 42}

    def test_consolidation(self, cm):
        # Store exactly batch_size episodes
        for i in range(5):
            cm.store_episode(f"episode-{i}", "batch-test")

        cons_id = cm.consolidate_episodes(batch_size=5)
        assert cons_id is not None
        assert cons_id.startswith("con_")

        # Compressed episodes excluded by default
        remaining = cm.get_episodes(include_compressed=False)
        assert len(remaining) == 0

        # Including compressed shows them
        all_eps = cm.get_episodes(include_compressed=True)
        assert len(all_eps) == 5
        assert all(e.compressed for e in all_eps)

    def test_consolidation_with_custom_summarizer(self, cm):
        for i in range(3):
            cm.store_episode(f"ep-{i}", "s")

        def my_summarizer(texts):
            return f"Summary of {len(texts)} items"

        cons_id = cm.consolidate_episodes(batch_size=3, summarizer=my_summarizer)
        assert cons_id is not None

    def test_consolidation_returns_none_when_insufficient(self, cm):
        cm.store_episode("only one", "s")
        assert cm.consolidate_episodes(batch_size=5) is None


# ==================================================================
# SEMANTIC MEMORY
# ==================================================================


class TestSemanticMemory:
    def test_store_and_retrieve(self, cm):
        fid = cm.store_fact("Python", "Python is a programming language", confidence=0.95)
        assert fid.startswith("sem_")

        facts = cm.get_all_facts()
        assert len(facts) == 1
        assert facts[0].concept == "Python"
        assert facts[0].confidence == 0.95

    def test_search_by_keyword(self, cm):
        cm.store_fact("Python", "Python is interpreted", confidence=0.9)
        cm.store_fact("Rust", "Rust is compiled", confidence=0.8)
        cm.store_fact("Go", "Go has goroutines", confidence=0.7)

        results = cm.search_facts("Python")
        assert len(results) >= 1
        assert results[0].concept == "Python"

    def test_search_min_confidence(self, cm):
        cm.store_fact("A", "low conf fact", confidence=0.2)
        cm.store_fact("B", "high conf fact", confidence=0.9)

        results = cm.search_facts("fact", min_confidence=0.5)
        assert len(results) == 1
        assert results[0].concept == "B"

    def test_tags_roundtrip(self, cm):
        cm.store_fact("X", "tagged fact", tags=["tag1", "tag2"])
        fact = cm.get_all_facts()[0]
        assert fact.tags == ["tag1", "tag2"]

    def test_metadata_roundtrip(self, cm):
        cm.store_fact("X", "meta fact", temporal_metadata={"year": 2025})
        fact = cm.get_all_facts()[0]
        assert fact.metadata == {"year": 2025}


# ==================================================================
# PROCEDURAL MEMORY
# ==================================================================


class TestProceduralMemory:
    def test_store_and_recall(self, cm):
        pid = cm.store_procedure(
            name="deploy to prod",
            steps=["run tests", "build image", "push to registry", "deploy"],
            prerequisites=["all tests pass"],
        )
        assert pid.startswith("proc_")

        procs = cm.recall_procedure("deploy")
        assert len(procs) == 1
        assert procs[0].name == "deploy to prod"
        assert len(procs[0].steps) == 4
        assert procs[0].prerequisites == ["all tests pass"]

    def test_usage_count_increments(self, cm):
        cm.store_procedure("test proc", ["step1"])

        # First recall
        procs = cm.recall_procedure("test proc")
        assert len(procs) == 1
        # After recall, usage_count in DB is incremented
        # The returned object still has the pre-increment value (0)

        # Second recall should show incremented count
        procs2 = cm.recall_procedure("test proc")
        assert procs2[0].usage_count == 1  # was 0, incremented by first recall

    def test_empty_query_returns_most_used(self, cm):
        cm.store_procedure("often used", ["a"])
        cm.store_procedure("rarely used", ["b"])

        # Recall "often used" to bump its count
        cm.recall_procedure("often used")

        procs = cm.recall_procedure("")
        assert procs[0].name == "often used"


# ==================================================================
# PROSPECTIVE MEMORY
# ==================================================================


class TestProspectiveMemory:
    def test_store_and_check_trigger(self, cm):
        nid = cm.store_prospective(
            description="Remind about meeting",
            trigger_condition="meeting calendar",
            action_on_trigger="Send reminder email",
            priority=5,
        )
        assert nid.startswith("pro_")

        triggered = cm.check_triggers("Check the calendar for today's meeting")
        assert len(triggered) == 1
        assert triggered[0].status == "triggered"
        assert triggered[0].description == "Remind about meeting"

    def test_no_trigger_on_unrelated_content(self, cm):
        cm.store_prospective(
            description="Deploy when ready",
            trigger_condition="deployment approval",
            action_on_trigger="Run deploy script",
        )

        triggered = cm.check_triggers("The weather is nice today")
        assert len(triggered) == 0

    def test_resolve_prospective(self, cm):
        nid = cm.store_prospective(
            description="Test resolve",
            trigger_condition="trigger word",
            action_on_trigger="do something",
        )

        # Trigger it
        cm.check_triggers("the trigger word appeared")

        # Resolve it
        cm.resolve_prospective(nid)

        # Should not trigger again
        triggered = cm.check_triggers("trigger word again")
        assert len(triggered) == 0

    def test_priority_ordering(self, cm):
        cm.store_prospective("low", "alpha", "act-low", priority=1)
        cm.store_prospective("high", "alpha", "act-high", priority=10)

        triggered = cm.check_triggers("alpha word")
        assert len(triggered) == 2
        assert triggered[0].priority > triggered[1].priority


# ==================================================================
# STATISTICS
# ==================================================================


class TestStatistics:
    def test_empty_stats(self, cm):
        stats = cm.get_statistics()
        assert stats["total"] == 0
        assert stats["sensory"] == 0
        assert stats["working"] == 0
        assert stats["episodic"] == 0
        assert stats["semantic"] == 0
        assert stats["procedural"] == 0
        assert stats["prospective"] == 0

    def test_counts_after_inserts(self, cm):
        cm.record_sensory("text", "hello")
        cm.push_working("goal", "x", "t1")
        cm.store_episode("episode", "s")
        cm.store_fact("concept", "content")
        cm.store_procedure("proc", ["step"])
        cm.store_prospective("desc", "trig", "act")

        stats = cm.get_statistics()
        assert stats["total"] == 6
        assert stats["sensory"] == 1
        assert stats["working"] == 1
        assert stats["episodic"] == 1
        assert stats["semantic"] == 1
        assert stats["procedural"] == 1
        assert stats["prospective"] == 1


# ==================================================================
# AGENT ISOLATION
# ==================================================================


class TestAgentIsolation:
    def test_different_agents_see_own_data(self, tmp_path):
        db = tmp_path / "shared_db"
        agent_a = CognitiveMemory(agent_name="agent-a", db_path=db)
        agent_b = CognitiveMemory(agent_name="agent-b", db_path=db)

        agent_a.store_fact("A-concept", "A-content")
        agent_b.store_fact("B-concept", "B-content")

        a_facts = agent_a.get_all_facts()
        b_facts = agent_b.get_all_facts()

        assert len(a_facts) == 1
        assert a_facts[0].concept == "A-concept"
        assert len(b_facts) == 1
        assert b_facts[0].concept == "B-concept"

        agent_a.close()
        agent_b.close()

    def test_sensory_isolation(self, tmp_path):
        db = tmp_path / "shared_db"
        a = CognitiveMemory(agent_name="a", db_path=db)
        b = CognitiveMemory(agent_name="b", db_path=db)

        a.record_sensory("text", "a-data")
        b.record_sensory("text", "b-data")

        assert len(a.get_recent_sensory()) == 1
        assert a.get_recent_sensory()[0].raw_data == "a-data"
        assert len(b.get_recent_sensory()) == 1
        assert b.get_recent_sensory()[0].raw_data == "b-data"

        a.close()
        b.close()

    def test_working_memory_isolation(self, tmp_path):
        db = tmp_path / "shared_db"
        a = CognitiveMemory(agent_name="a", db_path=db)
        b = CognitiveMemory(agent_name="b", db_path=db)

        a.push_working("goal", "a-goal", "t1")
        b.push_working("goal", "b-goal", "t1")

        assert len(a.get_working("t1")) == 1
        assert len(b.get_working("t1")) == 1

        a.close()
        b.close()

    def test_episode_isolation(self, tmp_path):
        db = tmp_path / "shared_db"
        a = CognitiveMemory(agent_name="a", db_path=db)
        b = CognitiveMemory(agent_name="b", db_path=db)

        a.store_episode("a-ep", "s")
        b.store_episode("b-ep", "s")

        assert len(a.get_episodes()) == 1
        assert len(b.get_episodes()) == 1

        a.close()
        b.close()

    def test_stats_isolation(self, tmp_path):
        db = tmp_path / "shared_db"
        a = CognitiveMemory(agent_name="a", db_path=db)
        b = CognitiveMemory(agent_name="b", db_path=db)

        a.store_fact("x", "y")
        a.store_fact("x2", "y2")
        b.store_fact("z", "w")

        assert a.get_statistics()["semantic"] == 2
        assert b.get_statistics()["semantic"] == 1

        a.close()
        b.close()


# ==================================================================
# BACKWARD COMPATIBILITY
# ==================================================================


class TestBackwardCompatibility:
    """Verify that existing ExperienceStore and MemoryConnector still work."""

    def test_experience_store_still_works(self, tmp_path):
        from amplihack_memory import Experience, ExperienceStore, ExperienceType

        store = ExperienceStore(
            agent_name="compat-test",
            storage_path=tmp_path / "compat_store",
        )
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="test context",
            outcome="test outcome",
            confidence=0.8,
        )
        exp_id = store.add(exp)
        assert exp_id is not None

    def test_memory_connector_still_works(self, tmp_path):
        from amplihack_memory import Experience, ExperienceType, MemoryConnector

        conn = MemoryConnector(
            agent_name="compat-test",
            storage_path=tmp_path / "compat_conn",
        )
        exp = Experience(
            experience_type=ExperienceType.INSIGHT,
            context="insight context",
            outcome="insight outcome",
            confidence=0.7,
        )
        exp_id = conn.store_experience(exp)
        assert exp_id is not None
        conn.close()
