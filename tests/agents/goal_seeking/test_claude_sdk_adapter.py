"""Tests for Claude SDK adapter and GoalSeekingAgent framework.

Philosophy:
- Test without requiring API keys or live SDK connections
- Mock Claude Agent SDK for predictable results
- Verify tool registration, goal formation, memory integration
- Test factory pattern for creating agents
- Test all 7 learning tools
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestAgentTool:
    """Tests for AgentTool dataclass."""

    def test_agent_tool_creation(self):
        """Test creating an AgentTool with required fields."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import AgentTool

        tool = AgentTool(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            function=lambda: None,
        )
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.requires_approval is False
        assert tool.category == "core"

    def test_agent_tool_with_category(self):
        """Test AgentTool with custom category."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import AgentTool

        tool = AgentTool(
            name="learn",
            description="Learn from content",
            parameters={"type": "object", "properties": {}},
            function=lambda: None,
            category="learning",
        )
        assert tool.category == "learning"


class TestAgentResult:
    """Tests for AgentResult dataclass."""

    def test_default_result(self):
        """Test default AgentResult values."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import AgentResult

        result = AgentResult()
        assert result.response == ""
        assert result.goal_achieved is False
        assert result.tools_used == []
        assert result.turns == 0
        assert result.metadata == {}

    def test_result_with_values(self):
        """Test AgentResult with populated fields."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import AgentResult

        result = AgentResult(
            response="Answer found",
            goal_achieved=True,
            tools_used=["search_memory", "store_fact"],
            turns=3,
            metadata={"sdk": "claude"},
        )
        assert result.response == "Answer found"
        assert result.goal_achieved is True
        assert len(result.tools_used) == 2
        assert result.turns == 3


class TestGoal:
    """Tests for Goal dataclass."""

    def test_goal_creation(self):
        """Test creating a Goal."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import Goal

        goal = Goal(description="Learn about photosynthesis")
        assert goal.description == "Learn about photosynthesis"
        assert goal.status == "pending"
        assert goal.plan == []

    def test_goal_with_plan(self):
        """Test Goal with plan steps."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import Goal

        goal = Goal(
            description="Learn about photosynthesis",
            success_criteria="Can explain photosynthesis",
            plan=["Read content", "Extract facts", "Answer questions"],
            status="in_progress",
        )
        assert len(goal.plan) == 3
        assert goal.status == "in_progress"


class TestSDKType:
    """Tests for SDKType enum."""

    def test_sdk_types(self):
        """Test SDK type enum values."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import SDKType

        assert SDKType.CLAUDE.value == "claude"
        assert SDKType.MINI.value == "mini"

    def test_sdk_type_from_string(self):
        """Test creating SDKType from string."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import SDKType

        assert SDKType("claude") == SDKType.CLAUDE
        assert SDKType("mini") == SDKType.MINI


class TestGoalSeekingAgentBase:
    """Tests for GoalSeekingAgent abstract base class."""

    def test_learning_tools_registered(self):
        """Test that 7 learning tools are registered by base class."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import (
            AgentTool,
            GoalSeekingAgent,
            SDKType,
        )

        # Create a concrete implementation for testing
        class TestAgent(GoalSeekingAgent):
            def _create_sdk_agent(self):
                pass

            async def _run_sdk_agent(self, task, max_turns=10):
                from amplihack.agents.goal_seeking.sdk_adapters.base import AgentResult
                return AgentResult(response="test")

            def _get_native_tools(self):
                return []

            def _register_tool_with_sdk(self, tool):
                pass

        with patch(
            "amplihack.agents.goal_seeking.sdk_adapters.base.GoalSeekingAgent._init_memory"
        ):
            agent = TestAgent(
                name="test", sdk_type=SDKType.CLAUDE, enable_memory=False
            )

        tool_names = [t.name for t in agent._tools]
        assert "learn_from_content" in tool_names
        assert "search_memory" in tool_names
        assert "explain_knowledge" in tool_names
        assert "find_knowledge_gaps" in tool_names
        assert "verify_fact" in tool_names
        assert "store_fact" in tool_names
        assert "get_memory_summary" in tool_names
        assert len(tool_names) == 7

    def test_form_goal(self):
        """Test goal formation from user intent."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import (
            GoalSeekingAgent,
            SDKType,
        )

        class TestAgent(GoalSeekingAgent):
            def _create_sdk_agent(self):
                pass

            async def _run_sdk_agent(self, task, max_turns=10):
                from amplihack.agents.goal_seeking.sdk_adapters.base import AgentResult
                return AgentResult(response="test")

            def _get_native_tools(self):
                return []

            def _register_tool_with_sdk(self, tool):
                pass

        agent = TestAgent(
            name="test", sdk_type=SDKType.CLAUDE, enable_memory=False
        )

        goal = agent.form_goal("Learn about the solar system")
        assert goal.description == "Learn about the solar system"
        assert goal.status == "in_progress"
        assert agent.current_goal is goal

    def test_tool_learn_without_memory(self):
        """Test _tool_learn returns error when memory not initialized."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import (
            GoalSeekingAgent,
            SDKType,
        )

        class TestAgent(GoalSeekingAgent):
            def _create_sdk_agent(self):
                pass

            async def _run_sdk_agent(self, task, max_turns=10):
                from amplihack.agents.goal_seeking.sdk_adapters.base import AgentResult
                return AgentResult(response="test")

            def _get_native_tools(self):
                return []

            def _register_tool_with_sdk(self, tool):
                pass

        agent = TestAgent(
            name="test", sdk_type=SDKType.CLAUDE, enable_memory=False
        )

        result = agent._tool_learn("some content")
        assert result == {"error": "Memory not initialized"}

    def test_tool_search_without_memory(self):
        """Test _tool_search returns empty when memory not initialized."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import (
            GoalSeekingAgent,
            SDKType,
        )

        class TestAgent(GoalSeekingAgent):
            def _create_sdk_agent(self):
                pass

            async def _run_sdk_agent(self, task, max_turns=10):
                from amplihack.agents.goal_seeking.sdk_adapters.base import AgentResult
                return AgentResult(response="test")

            def _get_native_tools(self):
                return []

            def _register_tool_with_sdk(self, tool):
                pass

        agent = TestAgent(
            name="test", sdk_type=SDKType.CLAUDE, enable_memory=False
        )

        result = agent._tool_search("query")
        assert result == []

    def test_tool_summary_without_memory(self):
        """Test _tool_summary returns error when no memory."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import (
            GoalSeekingAgent,
            SDKType,
        )

        class TestAgent(GoalSeekingAgent):
            def _create_sdk_agent(self):
                pass

            async def _run_sdk_agent(self, task, max_turns=10):
                from amplihack.agents.goal_seeking.sdk_adapters.base import AgentResult
                return AgentResult(response="test")

            def _get_native_tools(self):
                return []

            def _register_tool_with_sdk(self, tool):
                pass

        agent = TestAgent(
            name="test", sdk_type=SDKType.CLAUDE, enable_memory=False
        )

        result = agent._tool_summary()
        assert result == {"error": "Memory not initialized"}


class TestClaudeGoalSeekingAgent:
    """Tests for ClaudeGoalSeekingAgent."""

    @patch("amplihack.agents.goal_seeking.sdk_adapters.claude_sdk.HAS_CLAUDE_SDK", False)
    def test_raises_import_error_without_sdk(self):
        """Test raises ImportError when claude-agents not installed."""
        from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import (
            ClaudeGoalSeekingAgent,
        )

        with pytest.raises(ImportError, match="Claude Agent SDK not installed"):
            ClaudeGoalSeekingAgent(name="test")

    def _setup_claude_mocks(self):
        """Helper to setup Claude SDK mocks when SDK is not installed."""
        import amplihack.agents.goal_seeking.sdk_adapters.claude_sdk as claude_mod

        mock_agent_cls = MagicMock()
        mock_tool_cls = MagicMock(side_effect=lambda **kwargs: MagicMock(**kwargs))

        claude_mod.HAS_CLAUDE_SDK = True
        claude_mod.ClaudeAgent = mock_agent_cls
        claude_mod.ClaudeTool = mock_tool_cls

        return mock_agent_cls, mock_tool_cls

    def test_creates_agent_with_tools(self):
        """Test creating agent registers tools with Claude SDK."""
        import amplihack.agents.goal_seeking.sdk_adapters.claude_sdk as claude_mod
        from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import (
            ClaudeGoalSeekingAgent,
        )

        mock_agent_cls, mock_tool_cls = self._setup_claude_mocks()

        try:
            agent = ClaudeGoalSeekingAgent(
                name="test_learner",
                instructions="Test instructions",
                enable_memory=False,
            )

            assert mock_agent_cls.called
            call_kwargs = mock_agent_cls.call_args[1]
            assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"
            assert "system" in call_kwargs

            allowed = call_kwargs["allowed_tools"]
            assert "bash" in allowed
            assert "read_file" in allowed
            assert "learn_from_content" in allowed
            assert "search_memory" in allowed
        finally:
            claude_mod.HAS_CLAUDE_SDK = False

    def test_native_tools_list(self):
        """Test native tools list is correct."""
        import amplihack.agents.goal_seeking.sdk_adapters.claude_sdk as claude_mod
        from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import (
            ClaudeGoalSeekingAgent,
        )

        mock_agent_cls, mock_tool_cls = self._setup_claude_mocks()

        try:
            agent = ClaudeGoalSeekingAgent(name="test", enable_memory=False)
            native = agent._get_native_tools()
            assert native == ["bash", "read_file", "write_file", "edit_file", "glob", "grep"]
        finally:
            claude_mod.HAS_CLAUDE_SDK = False

    def test_system_prompt_includes_capabilities(self):
        """Test system prompt includes all four capability sections."""
        import amplihack.agents.goal_seeking.sdk_adapters.claude_sdk as claude_mod
        from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import (
            ClaudeGoalSeekingAgent,
        )

        mock_agent_cls, mock_tool_cls = self._setup_claude_mocks()

        try:
            agent = ClaudeGoalSeekingAgent(
                name="test",
                instructions="Custom instruction",
                enable_memory=False,
            )

            prompt = agent._build_system_prompt()
            assert "GOAL SEEKING:" in prompt
            assert "LEARNING:" in prompt
            assert "TEACHING:" in prompt
            assert "APPLYING:" in prompt
            assert "Custom instruction" in prompt
        finally:
            claude_mod.HAS_CLAUDE_SDK = False

    @pytest.mark.asyncio
    async def test_run_sdk_agent_success(self):
        """Test successful SDK agent execution."""
        import amplihack.agents.goal_seeking.sdk_adapters.claude_sdk as claude_mod
        from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import (
            ClaudeGoalSeekingAgent,
        )

        mock_agent_cls, mock_tool_cls = self._setup_claude_mocks()
        mock_result = MagicMock()
        mock_result.response = "The answer is 42"
        mock_agent_cls.return_value.run.return_value = mock_result

        try:
            agent = ClaudeGoalSeekingAgent(name="test", enable_memory=False)
            result = await agent._run_sdk_agent("What is the answer?")
            assert result.response == "The answer is 42"
            assert result.goal_achieved is True
            assert result.metadata["sdk"] == "claude"
        finally:
            claude_mod.HAS_CLAUDE_SDK = False

    @pytest.mark.asyncio
    async def test_run_sdk_agent_failure(self):
        """Test SDK agent execution handles errors."""
        import amplihack.agents.goal_seeking.sdk_adapters.claude_sdk as claude_mod
        from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import (
            ClaudeGoalSeekingAgent,
        )

        mock_agent_cls, mock_tool_cls = self._setup_claude_mocks()
        mock_agent_cls.return_value.run.side_effect = RuntimeError("Connection failed")

        try:
            agent = ClaudeGoalSeekingAgent(name="test", enable_memory=False)
            result = await agent._run_sdk_agent("What is the answer?")
            assert result.goal_achieved is False
            assert "Connection failed" in result.response
            assert "error" in result.metadata
        finally:
            claude_mod.HAS_CLAUDE_SDK = False


class TestFactory:
    """Tests for create_agent factory function."""

    def test_create_claude_agent(self):
        """Test factory creates Claude agent."""
        import amplihack.agents.goal_seeking.sdk_adapters.claude_sdk as claude_mod
        from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import (
            ClaudeGoalSeekingAgent,
        )
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        mock_agent_cls = MagicMock()
        mock_tool_cls = MagicMock(side_effect=lambda **kwargs: MagicMock(**kwargs))
        claude_mod.HAS_CLAUDE_SDK = True
        claude_mod.ClaudeAgent = mock_agent_cls
        claude_mod.ClaudeTool = mock_tool_cls

        try:
            agent = create_agent(
                name="test",
                sdk="claude",
                instructions="Test",
                enable_memory=False,
            )
            assert isinstance(agent, ClaudeGoalSeekingAgent)
        finally:
            claude_mod.HAS_CLAUDE_SDK = False

    @patch("amplihack.agents.goal_seeking.sdk_adapters.factory._MiniFrameworkAdapter._create_sdk_agent")
    def test_create_mini_agent(self, mock_create):
        """Test factory creates mini-framework agent."""
        from amplihack.agents.goal_seeking.sdk_adapters.factory import (
            _MiniFrameworkAdapter,
            create_agent,
        )

        agent = create_agent(
            name="test",
            sdk="mini",
            enable_memory=False,
        )
        assert isinstance(agent, _MiniFrameworkAdapter)

    def test_create_unknown_sdk_raises(self):
        """Test factory raises on unknown SDK."""
        from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

        with pytest.raises(ValueError):
            create_agent(name="test", sdk="unknown")


class TestSimilarity:
    """Tests for similarity computation."""

    def test_word_similarity_identical(self):
        """Test word similarity for identical texts."""
        from amplihack.agents.goal_seeking.similarity import compute_word_similarity

        score = compute_word_similarity(
            "plants use photosynthesis for energy",
            "plants use photosynthesis for energy",
        )
        assert score == 1.0

    def test_word_similarity_different(self):
        """Test word similarity for completely different texts."""
        from amplihack.agents.goal_seeking.similarity import compute_word_similarity

        score = compute_word_similarity(
            "quantum computing uses qubits",
            "medieval castle architecture features",
        )
        assert score == 0.0

    def test_word_similarity_partial(self):
        """Test word similarity for partially overlapping texts."""
        from amplihack.agents.goal_seeking.similarity import compute_word_similarity

        score = compute_word_similarity(
            "plants convert sunlight into energy",
            "plants produce energy from light",
        )
        assert 0.0 < score < 1.0

    def test_tag_similarity(self):
        """Test tag similarity computation."""
        from amplihack.agents.goal_seeking.similarity import compute_tag_similarity

        score = compute_tag_similarity(
            ["biology", "plants", "energy"],
            ["biology", "plants", "photosynthesis"],
        )
        assert 0.0 < score < 1.0

    def test_composite_similarity(self):
        """Test composite similarity with content, tags, and concept."""
        from amplihack.agents.goal_seeking.similarity import compute_similarity

        node_a = {
            "content": "Plants use photosynthesis",
            "concept": "biology",
            "tags": ["plants"],
        }
        node_b = {
            "content": "Animals need oxygen to breathe",
            "concept": "biology",
            "tags": ["animals"],
        }
        score = compute_similarity(node_a, node_b)
        assert 0.0 < score < 1.0


class TestJsonUtils:
    """Tests for JSON parsing utilities."""

    def test_parse_raw_json(self):
        """Test parsing raw JSON."""
        from amplihack.agents.goal_seeking.json_utils import parse_llm_json

        result = parse_llm_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_from_code_block(self):
        """Test parsing JSON from markdown code block."""
        from amplihack.agents.goal_seeking.json_utils import parse_llm_json

        text = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        result = parse_llm_json(text)
        assert result == {"key": "value"}

    def test_parse_json_from_braces(self):
        """Test parsing JSON extracted from first brace match."""
        from amplihack.agents.goal_seeking.json_utils import parse_llm_json

        text = 'The result is {"answer": 42} as expected.'
        result = parse_llm_json(text)
        assert result == {"answer": 42}

    def test_parse_invalid_json_returns_none(self):
        """Test None returned for unparseable text."""
        from amplihack.agents.goal_seeking.json_utils import parse_llm_json

        result = parse_llm_json("This is not JSON at all")
        assert result is None

    def test_parse_empty_returns_none(self):
        """Test None returned for empty string."""
        from amplihack.agents.goal_seeking.json_utils import parse_llm_json

        assert parse_llm_json("") is None
        assert parse_llm_json(None) is None

    def test_parse_json_list(self):
        """Test parsing JSON list."""
        from amplihack.agents.goal_seeking.json_utils import parse_llm_json_list

        result = parse_llm_json_list('[{"a": 1}, {"b": 2}]')
        assert len(result) == 2
        assert result[0] == {"a": 1}


class TestMemoryClassifier:
    """Tests for MemoryClassifier."""

    def test_classify_procedural(self):
        """Test procedural classification."""
        from amplihack.agents.goal_seeking.hierarchical_memory import (
            MemoryCategory,
            MemoryClassifier,
        )

        classifier = MemoryClassifier()
        category = classifier.classify("Step 1: Preheat oven. Step 2: Mix ingredients.")
        assert category == MemoryCategory.PROCEDURAL

    def test_classify_semantic_default(self):
        """Test semantic classification is default."""
        from amplihack.agents.goal_seeking.hierarchical_memory import (
            MemoryCategory,
            MemoryClassifier,
        )

        classifier = MemoryClassifier()
        category = classifier.classify("Water is composed of hydrogen and oxygen atoms.")
        assert category == MemoryCategory.SEMANTIC

    def test_classify_episodic(self):
        """Test episodic classification."""
        from amplihack.agents.goal_seeking.hierarchical_memory import (
            MemoryCategory,
            MemoryClassifier,
        )

        classifier = MemoryClassifier()
        category = classifier.classify("The event occurred yesterday at noon.")
        assert category == MemoryCategory.EPISODIC


class TestKnowledgeSubgraph:
    """Tests for KnowledgeSubgraph."""

    def test_empty_subgraph_context(self):
        """Test empty subgraph returns 'no knowledge' message."""
        from amplihack.agents.goal_seeking.hierarchical_memory import KnowledgeSubgraph

        subgraph = KnowledgeSubgraph(query="test")
        assert subgraph.to_llm_context() == "No relevant knowledge found."

    def test_subgraph_with_nodes(self):
        """Test subgraph formats nodes as context."""
        from amplihack.agents.goal_seeking.hierarchical_memory import (
            KnowledgeNode,
            KnowledgeSubgraph,
            MemoryCategory,
        )

        node = KnowledgeNode(
            node_id="abc123",
            category=MemoryCategory.SEMANTIC,
            content="Plants use photosynthesis",
            concept="Biology",
            confidence=0.9,
        )
        subgraph = KnowledgeSubgraph(nodes=[node], query="photosynthesis")
        context = subgraph.to_llm_context()

        assert "photosynthesis" in context
        assert "Biology" in context
        assert "0.9" in context


class TestHierarchicalMemory:
    """Tests for HierarchicalMemory."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_invalid_agent_name(self):
        """Test raises on invalid agent name."""
        from amplihack.agents.goal_seeking.hierarchical_memory import HierarchicalMemory

        with pytest.raises(ValueError, match="agent_name cannot be empty"):
            HierarchicalMemory(agent_name="")

    def test_store_and_retrieve(self, temp_storage):
        """Test storing and retrieving knowledge."""
        from amplihack.agents.goal_seeking.hierarchical_memory import HierarchicalMemory

        mem = HierarchicalMemory(agent_name="test_agent", db_path=temp_storage)
        try:
            node_id = mem.store_knowledge(
                content="Plants use photosynthesis",
                concept="Biology",
                confidence=0.9,
            )
            assert node_id is not None

            subgraph = mem.retrieve_subgraph("photosynthesis")
            assert len(subgraph.nodes) > 0
            assert any("photosynthesis" in n.content.lower() for n in subgraph.nodes)
        finally:
            mem.close()

    def test_store_episode(self, temp_storage):
        """Test storing episodic memory."""
        from amplihack.agents.goal_seeking.hierarchical_memory import HierarchicalMemory

        mem = HierarchicalMemory(agent_name="test_agent", db_path=temp_storage)
        try:
            episode_id = mem.store_episode(
                content="Today we learned about cells.",
                source_label="Biology Lesson 1",
            )
            assert episode_id is not None
        finally:
            mem.close()

    def test_get_statistics(self, temp_storage):
        """Test memory statistics."""
        from amplihack.agents.goal_seeking.hierarchical_memory import HierarchicalMemory

        mem = HierarchicalMemory(agent_name="test_agent", db_path=temp_storage)
        try:
            mem.store_knowledge("Fact 1", concept="Topic A")
            mem.store_knowledge("Fact 2", concept="Topic B")

            stats = mem.get_statistics()
            assert stats["semantic_nodes"] == 2
            assert stats["agent_name"] == "test_agent"
        finally:
            mem.close()

    def test_detect_contradiction(self):
        """Test contradiction detection between facts."""
        from amplihack.agents.goal_seeking.hierarchical_memory import HierarchicalMemory

        result = HierarchicalMemory._detect_contradiction(
            "Norway has 8 gold medals",
            "Norway has 10 gold medals",
            "Norway medals",
            "Norway medals",
        )
        assert result.get("contradiction") is True


class TestFlatRetrieverAdapter:
    """Tests for FlatRetrieverAdapter."""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_store_and_search(self, temp_storage):
        """Test storing and searching facts via adapter."""
        from amplihack.agents.goal_seeking.flat_retriever_adapter import FlatRetrieverAdapter

        adapter = FlatRetrieverAdapter(agent_name="test_adapter", db_path=temp_storage)
        try:
            adapter.store_fact(
                context="Biology",
                fact="Cells are the basic unit of life",
                confidence=0.9,
            )
            results = adapter.search("cells")
            assert len(results) > 0
            assert results[0]["context"] == "Biology"
        finally:
            adapter.close()

    def test_empty_context_raises(self, temp_storage):
        """Test storing with empty context raises ValueError."""
        from amplihack.agents.goal_seeking.flat_retriever_adapter import FlatRetrieverAdapter

        adapter = FlatRetrieverAdapter(agent_name="test_adapter", db_path=temp_storage)
        try:
            with pytest.raises(ValueError, match="context cannot be empty"):
                adapter.store_fact(context="", fact="some fact")
        finally:
            adapter.close()

    def test_get_all_facts(self, temp_storage):
        """Test retrieving all facts."""
        from amplihack.agents.goal_seeking.flat_retriever_adapter import FlatRetrieverAdapter

        adapter = FlatRetrieverAdapter(agent_name="test_adapter", db_path=temp_storage)
        try:
            adapter.store_fact("Topic A", "Fact 1")
            adapter.store_fact("Topic B", "Fact 2")
            all_facts = adapter.get_all_facts()
            assert len(all_facts) == 2
        finally:
            adapter.close()
