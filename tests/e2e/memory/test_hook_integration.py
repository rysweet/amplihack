"""End-to-end tests fer hook integration with memory system.

Tests automatic memory operations triggered by hooks:
- UserPromptSubmit: Inject relevant memories
- SessionStop: Extract learnings
- TodoWriteComplete: Extract learnings

Philosophy:
- Test real hook behavior
- Validate automatic memory operations
- No user intervention required
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

# These imports will fail until implementation exists (TDD)
try:
    from amplihack.memory.hooks import (
        SessionStopHook,
        TodoWriteCompleteHook,
        UserPromptSubmitHook,
    )

    from amplihack.memory.coordinator import MemoryCoordinator
    from amplihack.memory.database import MemoryDatabase
    from amplihack.memory.types import MemoryType
except ImportError:
    pytest.skip("Memory hooks not implemented yet", allow_module_level=True)


class TestUserPromptSubmitHook:
    """Test UserPromptSubmit hook integration."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database."""
        db_path = tmp_path / "test_memory.db"
        db = MemoryDatabase(db_path)
        db.initialize()
        yield db
        db.close()

    @pytest.fixture
    def coordinator(self, temp_db):
        """Create coordinator."""
        return MemoryCoordinator(database=temp_db)

    @pytest.fixture
    def hook(self, coordinator):
        """Create UserPromptSubmit hook."""
        return UserPromptSubmitHook(coordinator=coordinator)

    @pytest.fixture
    def mock_agents(self):
        """Mock agent responses."""
        mock_task = AsyncMock()
        mock_task.return_value = {
            "importance_score": 8,
            "reasoning": "Good",
        }
        return mock_task

    @pytest.mark.asyncio
    async def test_hook_injects_relevant_memories(self, hook, coordinator, mock_agents, temp_db):
        """Hook injects relevant memories before agent invocation."""
        with patch("amplihack.memory.storage_pipeline.Task", mock_agents):
            # Pre-populate with memories
            from amplihack.memory.storage_pipeline import StorageRequest

            memories_to_store = [
                StorageRequest(
                    content="To fix CI: check logs, fix issue, rerun tests",
                    memory_type=MemoryType.PROCEDURAL,
                ),
                StorageRequest(
                    content="Always validate input before processing",
                    memory_type=MemoryType.SEMANTIC,
                ),
            ]

            for request in memories_to_store:
                await coordinator.store(request)

            # Simulate user prompt about CI
            user_prompt = "How do I fix CI failures?"
            context = {}

            # Hook should inject relevant memories
            injected_context = await hook.on_user_prompt_submit(prompt=user_prompt, context=context)

            # Should include procedural memory about CI
            assert "CI" in injected_context or "logs" in injected_context
            assert injected_context  # Not empty

    @pytest.mark.asyncio
    async def test_hook_respects_token_budget(self, hook, coordinator, mock_agents, temp_db):
        """Hook respects token budget fer injection."""
        with patch("amplihack.memory.storage_pipeline.Task", mock_agents):
            # Store many large memories
            from amplihack.memory.storage_pipeline import StorageRequest

            for i in range(20):
                request = StorageRequest(
                    content=f"Large memory content {i} " * 100,
                    memory_type=MemoryType.SEMANTIC,
                )
                await coordinator.store(request)

            # Hook with small budget
            user_prompt = "memory content"
            context = {"token_budget": 500}

            injected_context = await hook.on_user_prompt_submit(prompt=user_prompt, context=context)

            # Count tokens in injected context
            from amplihack.memory.token_budget import TokenCounter

            tokens = TokenCounter.count(injected_context)

            # Should not exceed budget
            assert tokens <= 500

    @pytest.mark.asyncio
    async def test_hook_no_injection_fer_irrelevant_prompt(
        self, hook, coordinator, mock_agents, temp_db
    ):
        """Hook does not inject fer irrelevant prompts."""
        with patch("amplihack.memory.storage_pipeline.Task", mock_agents):
            # Store memories about CI
            from amplihack.memory.storage_pipeline import StorageRequest

            request = StorageRequest(
                content="CI failure procedure",
                memory_type=MemoryType.PROCEDURAL,
            )
            await coordinator.store(request)

            # Prompt about completely different topic
            user_prompt = "What is quantum physics?"
            context = {}

            injected_context = await hook.on_user_prompt_submit(prompt=user_prompt, context=context)

            # Should be empty or minimal
            assert len(injected_context) < 100 or injected_context == ""


class TestSessionStopHook:
    """Test SessionStop hook integration."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database."""
        db_path = tmp_path / "test_memory.db"
        db = MemoryDatabase(db_path)
        db.initialize()
        yield db
        db.close()

    @pytest.fixture
    def coordinator(self, temp_db):
        """Create coordinator."""
        return MemoryCoordinator(database=temp_db)

    @pytest.fixture
    def hook(self, coordinator):
        """Create SessionStop hook."""
        return SessionStopHook(coordinator=coordinator)

    @pytest.fixture
    def mock_agents(self):
        """Mock agent responses."""
        mock_task = AsyncMock()
        mock_task.return_value = {
            "importance_score": 8,
            "reasoning": "Valuable learning",
        }
        return mock_task

    @pytest.mark.asyncio
    async def test_hook_extracts_learnings_on_session_stop(self, hook, coordinator, mock_agents):
        """Hook extracts learnings when session stops."""
        with patch("amplihack.memory.storage_pipeline.Task", mock_agents):
            # Simulate session with conversations
            session_data = {
                "session_id": "test-123",
                "conversations": [
                    {
                        "user": "How do I fix CI failures?",
                        "assistant": "Check logs, fix issue, rerun tests",
                    },
                    {
                        "user": "What about input validation?",
                        "assistant": "Always validate before processing",
                    },
                ],
                "commands_executed": [
                    {"command": "pytest", "exit_code": 0},
                ],
            }

            # Hook should extract learnings
            await hook.on_session_stop(session_data)

            # Verify learnings were stored
            from amplihack.memory.retrieval_pipeline import RetrievalQuery

            query = RetrievalQuery(query_text="CI failures", token_budget=5000)
            memories = await coordinator.retrieve(query)

            # Should have stored learnings
            assert len(memories) > 0

    @pytest.mark.asyncio
    async def test_hook_stores_episodic_memories(self, hook, coordinator, mock_agents):
        """Hook stores episodic memories fer conversations."""
        with patch("amplihack.memory.storage_pipeline.Task", mock_agents):
            session_data = {
                "session_id": "test-123",
                "conversations": [
                    {
                        "user": "Discuss authentication",
                        "assistant": "JWT tokens recommended",
                        "timestamp": datetime.now().isoformat(),
                    },
                ],
            }

            await hook.on_session_stop(session_data)

            # Query fer episodic memories
            from amplihack.memory.retrieval_pipeline import RetrievalQuery

            query = RetrievalQuery(
                query_text="authentication",
                memory_types=[MemoryType.EPISODIC],
                token_budget=5000,
            )

            memories = await coordinator.retrieve(query)

            # Should have episodic memory
            episodic = [m for m in memories if m.memory_type == MemoryType.EPISODIC]
            assert len(episodic) > 0

    @pytest.mark.asyncio
    async def test_hook_does_not_store_trivial_sessions(self, hook, coordinator, mock_agents):
        """Hook does not store trivial session data."""
        mock_task = AsyncMock()
        mock_task.side_effect = [
            {"importance_score": 1, "reasoning": "Trivial"},
            {"importance_score": 2, "reasoning": "No value"},
            {"importance_score": 1, "reasoning": "Not useful"},
        ]

        with patch("amplihack.memory.storage_pipeline.Task", mock_task):
            # Trivial session
            session_data = {
                "session_id": "test-123",
                "conversations": [
                    {"user": "Hello", "assistant": "Hi"},
                ],
            }

            await hook.on_session_stop(session_data)

            # Should not store anything
            from amplihack.memory.retrieval_pipeline import RetrievalQuery

            query = RetrievalQuery(query_text="hello", token_budget=5000)
            memories = await coordinator.retrieve(query)

            assert len(memories) == 0


class TestTodoWriteCompleteHook:
    """Test TodoWriteComplete hook integration."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database."""
        db_path = tmp_path / "test_memory.db"
        db = MemoryDatabase(db_path)
        db.initialize()
        yield db
        db.close()

    @pytest.fixture
    def coordinator(self, temp_db):
        """Create coordinator."""
        return MemoryCoordinator(database=temp_db)

    @pytest.fixture
    def hook(self, coordinator):
        """Create TodoWriteComplete hook."""
        return TodoWriteCompleteHook(coordinator=coordinator)

    @pytest.fixture
    def mock_agents(self):
        """Mock agent responses."""
        mock_task = AsyncMock()
        mock_task.return_value = {
            "importance_score": 8,
            "reasoning": "Useful procedure",
        }
        return mock_task

    @pytest.mark.asyncio
    async def test_hook_extracts_learnings_on_task_complete(self, hook, coordinator, mock_agents):
        """Hook extracts learnings when task completes."""
        with patch("amplihack.memory.storage_pipeline.Task", mock_agents):
            # Simulate completed task
            task_data = {
                "task_id": "implement-auth-123",
                "task_description": "Implement JWT authentication",
                "steps_completed": [
                    "Created auth middleware",
                    "Added token validation",
                    "Wrote tests",
                ],
                "outcome": "success",
                "learnings": "JWT validation works best with proper error handling",
            }

            # Hook should extract learnings
            await hook.on_task_complete(task_data)

            # Verify procedural memory stored
            from amplihack.memory.retrieval_pipeline import RetrievalQuery

            query = RetrievalQuery(
                query_text="authentication",
                memory_types=[MemoryType.PROCEDURAL],
                token_budget=5000,
            )

            memories = await coordinator.retrieve(query)

            # Should have procedural memory
            procedural = [m for m in memories if m.memory_type == MemoryType.PROCEDURAL]
            assert len(procedural) > 0

    @pytest.mark.asyncio
    async def test_hook_clears_working_memory_on_complete(self, hook, coordinator, mock_agents):
        """Hook clears working memory when task completes."""
        with patch("amplihack.memory.storage_pipeline.Task", mock_agents):
            # Store working memory
            from amplihack.memory.storage_pipeline import StorageRequest

            request = StorageRequest(
                content="Currently working on auth.py",
                memory_type=MemoryType.WORKING,
                context={"task_id": "auth-123"},
            )
            await coordinator.store(request)

            # Complete task
            task_data = {
                "task_id": "auth-123",
                "outcome": "success",
            }

            await hook.on_task_complete(task_data)

            # Working memory should be cleared
            from amplihack.memory.retrieval_pipeline import RetrievalQuery

            query = RetrievalQuery(
                query_text="working",
                memory_types=[MemoryType.WORKING],
                token_budget=5000,
            )

            memories = await coordinator.retrieve(query)
            task_working = [m for m in memories if m.context.get("task_id") == "auth-123"]

            assert len(task_working) == 0

    @pytest.mark.asyncio
    async def test_hook_creates_prospective_memory_fer_follow_up(
        self, hook, coordinator, mock_agents
    ):
        """Hook creates prospective memory fer follow-up tasks."""
        with patch("amplihack.memory.storage_pipeline.Task", mock_agents):
            # Task with follow-up
            task_data = {
                "task_id": "implement-auth-123",
                "outcome": "success",
                "follow_up": "Refactor auth module after code review",
            }

            await hook.on_task_complete(task_data)

            # Should create prospective memory
            from amplihack.memory.retrieval_pipeline import RetrievalQuery

            query = RetrievalQuery(
                query_text="refactor auth",
                memory_types=[MemoryType.PROSPECTIVE],
                token_budget=5000,
            )

            memories = await coordinator.retrieve(query)

            # Should have prospective memory
            prospective = [m for m in memories if m.memory_type == MemoryType.PROSPECTIVE]
            assert len(prospective) > 0


class TestHookIntegrationPerformance:
    """Test performance requirements fer hook integration."""

    @pytest.mark.asyncio
    async def test_user_prompt_hook_low_overhead(self, coordinator, mock_agents, temp_db):
        """UserPromptSubmit hook adds <10% overhead."""
        import time

        hook = UserPromptSubmitHook(coordinator=coordinator)

        with patch("amplihack.memory.storage_pipeline.Task", mock_agents):
            # Baseline: prompt without hook
            user_prompt = "Test prompt"

            start = time.perf_counter()
            # Simulate processing prompt
            await asyncio.sleep(0.01)  # 10ms baseline
            baseline = time.perf_counter() - start

            # With hook
            start = time.perf_counter()
            await hook.on_user_prompt_submit(prompt=user_prompt, context={})
            await asyncio.sleep(0.01)  # Same baseline processing
            with_hook = time.perf_counter() - start

            # Hook overhead should be <10%
            overhead = (with_hook - baseline) / baseline
            assert overhead < 0.10

    @pytest.mark.asyncio
    async def test_session_stop_hook_completes_quickly(self, coordinator, mock_agents, temp_db):
        """SessionStop hook completes quickly (<1s)."""
        import time

        hook = SessionStopHook(coordinator=coordinator)

        with patch("amplihack.memory.storage_pipeline.Task", mock_agents):
            session_data = {
                "session_id": "test-123",
                "conversations": [
                    {
                        "user": f"Question {i}",
                        "assistant": f"Answer {i}",
                    }
                    for i in range(10)
                ],
            }

            start = time.perf_counter()
            await hook.on_session_stop(session_data)
            duration = time.perf_counter() - start

            # Should complete quickly even with 10 conversations
            assert duration < 1.0


class TestHookIntegrationErrorHandling:
    """Test error handling in hook integration."""

    @pytest.mark.asyncio
    async def test_hook_handles_db_errors_gracefully(self, temp_db):
        """Hooks handle database errors without crashing."""
        coordinator = MemoryCoordinator(database=temp_db)
        hook = UserPromptSubmitHook(coordinator=coordinator)

        # Mock database error
        with patch.object(coordinator, "retrieve", side_effect=Exception("DB error")):
            user_prompt = "Test prompt"
            context = {}

            # Should not crash
            injected = await hook.on_user_prompt_submit(prompt=user_prompt, context=context)

            # Should return empty or handle gracefully
            assert injected == "" or isinstance(injected, str)

    @pytest.mark.asyncio
    async def test_hook_handles_coordinator_unavailable(self):
        """Hooks handle coordinator being unavailable."""
        hook = UserPromptSubmitHook(coordinator=None)

        user_prompt = "Test prompt"
        context = {}

        # Should not crash
        injected = await hook.on_user_prompt_submit(prompt=user_prompt, context=context)

        # Should return empty
        assert injected == ""


class TestHookConfiguration:
    """Test hook configuration and registration."""

    def test_hooks_registered_automatically(self):
        """Memory hooks registered automatically on import."""
        from amplihack.memory.hooks import get_registered_hooks

        hooks = get_registered_hooks()

        # Should include memory hooks
        assert "UserPromptSubmit" in hooks
        assert "SessionStop" in hooks
        assert "TodoWriteComplete" in hooks

    @pytest.mark.asyncio
    async def test_hooks_can_be_disabled(self, temp_db):
        """Memory hooks can be disabled via configuration."""
        coordinator = MemoryCoordinator(database=temp_db)

        # Disable hooks
        coordinator.disable_hooks()

        hook = UserPromptSubmitHook(coordinator=coordinator)

        # Hook should be no-op when disabled
        user_prompt = "Test"
        context = {}

        injected = await hook.on_user_prompt_submit(prompt=user_prompt, context=context)

        assert injected == ""

    def test_hooks_token_budget_configurable(self, temp_db):
        """Hook token budget is configurable."""
        coordinator = MemoryCoordinator(database=temp_db)

        # Set custom budget
        hook = UserPromptSubmitHook(
            coordinator=coordinator,
            token_budget=1000,  # Custom budget
        )

        assert hook.token_budget == 1000
