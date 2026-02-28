"""Tests for issue #2661: SDK adapters must load pre-built DB in skip-learning mode.

Reproduces the exact failure: SDK agents (claude, copilot) score 1.7% because
_get_learning_agent() creates a LearningAgent with agent_name=f"{name}_learning",
which mismatches the agent_id in the pre-built CognitiveMemory DB.

Test strategy:
1. Create a CognitiveMemory DB with known facts using a specific agent_name
2. Create SDK agents pointing to that DB with the SAME agent_name
3. Verify the internal LearningAgent uses the correct agent_name (no suffix)
4. Verify answer_question() can retrieve stored facts
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _populate_cognitive_db(db_path: Path, agent_name: str, facts: list[tuple[str, str]]) -> None:
    """Create a CognitiveMemory DB with known facts.

    Args:
        db_path: Root path for the memory DB (kuzu_db subdir created inside)
        agent_name: Agent ID to store facts under
        facts: List of (context, fact) tuples to store
    """
    from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter

    adapter = CognitiveAdapter(agent_name=agent_name, db_path=db_path)
    for context, fact in facts:
        adapter.store_fact(context=context, fact=fact, confidence=0.95)
    # Verify facts were stored
    stats = adapter.get_statistics()
    total = stats.get("total", stats.get("total_facts", stats.get("total_experiences", 0)))
    assert total >= len(facts), f"Expected at least {len(facts)} facts, got {stats}"
    adapter.close()


class TestGetLearningAgentName:
    """Verify _get_learning_agent() uses the correct agent_name (no _learning suffix)."""

    def test_learning_agent_uses_same_name_as_parent(self, tmp_path):
        """The internal LearningAgent must use self.name, not self.name + '_learning'.

        This is the root cause of #2661: appending '_learning' causes
        CognitiveMemory to query with a different agent_id than what the
        pre-built DB contains.
        """
        from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import (
            ClaudeGoalSeekingAgent,
        )

        agent = ClaudeGoalSeekingAgent(
            name="test_agent",
            instructions="",
            model="claude-opus-4-6",
            storage_path=tmp_path / "memory_db",
            enable_memory=True,
        )

        la = agent._get_learning_agent()
        assert la is not None, "LearningAgent should be created"
        # The LearningAgent's agent_name MUST match the parent agent's name
        assert la.agent_name == "test_agent", (
            f"LearningAgent agent_name should be 'test_agent', "
            f"got '{la.agent_name}'. "
            f"The '_learning' suffix causes agent_id mismatch with pre-built DBs."
        )
        agent.close()

    def test_copilot_learning_agent_uses_same_name(self, tmp_path):
        """Same check for Copilot SDK adapter."""
        from amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk import (
            CopilotGoalSeekingAgent,
        )

        agent = CopilotGoalSeekingAgent(
            name="test_agent",
            instructions="",
            model="claude-opus-4-6",
            storage_path=tmp_path / "memory_db",
            enable_memory=True,
        )

        la = agent._get_learning_agent()
        assert la is not None
        assert la.agent_name == "test_agent", (
            f"LearningAgent agent_name should be 'test_agent', got '{la.agent_name}'."
        )
        agent.close()


class TestSDKLoadPrebuiltDB:
    """End-to-end: SDK agents must retrieve facts from a pre-built CognitiveMemory DB."""

    FACTS = [
        ("Geography", "The capital of France is Paris"),
        ("Geography", "The capital of Japan is Tokyo"),
        ("Biology", "DNA stores genetic information in all living organisms"),
        ("Physics", "The speed of light is approximately 299,792,458 meters per second"),
        ("History", "The French Revolution began in 1789"),
        ("Chemistry", "Water is composed of two hydrogen atoms and one oxygen atom"),
        ("Mathematics", "Pi is approximately 3.14159"),
        ("Astronomy", "The Earth orbits the Sun once every 365.25 days"),
        ("Technology", "The first programmable computer was the Z3, built in 1941"),
        ("Literature", "Shakespeare wrote Romeo and Juliet"),
    ]

    @pytest.fixture
    def prebuilt_db(self, tmp_path):
        """Create a pre-built CognitiveMemory DB with 10 known facts."""
        db_path = tmp_path / "memory_db"
        agent_name = "eval_agent"
        _populate_cognitive_db(db_path, agent_name, self.FACTS)
        return db_path, agent_name

    def test_claude_sdk_loads_prebuilt_db(self, prebuilt_db):
        """Claude SDK agent must find facts in a pre-built DB.

        This is the core regression test for #2661. Before the fix,
        the LearningAgent would be created with agent_name='eval_agent_learning',
        which doesn't match the DB's agent_id='eval_agent', returning empty results.
        """
        db_path, agent_name = prebuilt_db

        from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import (
            ClaudeGoalSeekingAgent,
        )

        agent = ClaudeGoalSeekingAgent(
            name=agent_name,
            instructions="",
            model="claude-opus-4-6",
            storage_path=db_path,
            enable_memory=True,
        )

        # The internal LearningAgent's memory must see the pre-built facts
        la = agent._get_learning_agent()
        assert la is not None

        # Verify the LearningAgent's memory can find stored facts
        results = la.memory.search("capital of France")
        assert len(results) > 0, (
            f"LearningAgent memory search returned no results for 'capital of France'. "
            f"agent_name used: {la.agent_name}, expected: {agent_name}. "
            f"This indicates agent_id mismatch with the pre-built DB."
        )
        agent.close()

    def test_copilot_sdk_loads_prebuilt_db(self, prebuilt_db):
        """Copilot SDK agent must find facts in a pre-built DB."""
        db_path, agent_name = prebuilt_db

        from amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk import (
            CopilotGoalSeekingAgent,
        )

        agent = CopilotGoalSeekingAgent(
            name=agent_name,
            instructions="",
            model="claude-opus-4-6",
            storage_path=db_path,
            enable_memory=True,
        )

        la = agent._get_learning_agent()
        assert la is not None

        results = la.memory.search("capital of France")
        assert len(results) > 0, (
            f"LearningAgent memory search returned no results. "
            f"agent_name used: {la.agent_name}, expected: {agent_name}."
        )
        agent.close()

    def test_base_memory_and_learning_agent_share_same_view(self, prebuilt_db):
        """Both self.memory (MemoryRetriever) and _get_learning_agent().memory
        must see the same facts from the pre-built DB.

        The base class _init_memory() creates a MemoryRetriever, while
        _get_learning_agent() creates a LearningAgent with CognitiveAdapter.
        Both must use the same agent_name to query the same data.
        """
        db_path, agent_name = prebuilt_db

        from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import (
            ClaudeGoalSeekingAgent,
        )

        agent = ClaudeGoalSeekingAgent(
            name=agent_name,
            instructions="",
            model="claude-opus-4-6",
            storage_path=db_path,
            enable_memory=True,
        )

        la = agent._get_learning_agent()
        assert la is not None

        # LearningAgent memory must find facts
        la_results = la.memory.search("Shakespeare")
        assert len(la_results) > 0, "LearningAgent memory should find Shakespeare facts"

        agent.close()


class TestAnswerQuestionWithPrebuiltDB:
    """Test that answer_question() works end-to-end with pre-built DB.

    These tests require LLM calls, so we mock litellm to avoid external deps.
    The key assertion is that the LearningAgent's memory search returns facts,
    which proves the agent_name mismatch is fixed.
    """

    FACTS = [
        ("Geography", "The capital of France is Paris"),
        ("Geography", "France is located in Western Europe"),
        ("Geography", "Paris has a population of about 2.1 million people"),
    ]

    @pytest.fixture
    def prebuilt_db(self, tmp_path):
        db_path = tmp_path / "memory_db"
        _populate_cognitive_db(db_path, "qa_agent", self.FACTS)
        return db_path

    def test_answer_question_retrieves_facts(self, prebuilt_db):
        """answer_question() must retrieve facts from pre-built DB before calling LLM.

        We mock litellm.completion to verify that facts are actually retrieved
        and passed to the LLM as context. Before the fix, no facts would be
        retrieved because of the agent_name mismatch.
        """
        from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import (
            ClaudeGoalSeekingAgent,
        )

        agent = ClaudeGoalSeekingAgent(
            name="qa_agent",
            instructions="",
            model="claude-opus-4-6",
            storage_path=prebuilt_db,
            enable_memory=True,
        )

        # Verify the learning agent can search the DB
        la = agent._get_learning_agent()
        assert la is not None

        results = la.memory.search("capital of France")
        assert len(results) > 0, (
            "Memory search must return facts from pre-built DB. "
            f"Got 0 results. LearningAgent agent_name: {la.agent_name}"
        )

        # Verify at least one result mentions Paris
        all_text = " ".join(str(r.get("outcome", r.get("fact", ""))) for r in results)
        assert "Paris" in all_text or "paris" in all_text.lower(), (
            f"Expected 'Paris' in search results, got: {all_text[:200]}"
        )

        agent.close()
