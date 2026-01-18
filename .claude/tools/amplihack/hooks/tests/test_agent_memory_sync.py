#!/usr/bin/env python3
"""
Tests for agent memory sync wrapper functions - TDD approach for Issue #1960.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)

This test file focuses on sync wrapper functions that safely handle async functions
in synchronous contexts. Tests are written BEFORE implementation (TDD) - they will
FAIL until the sync wrappers are created.

Issue #1960: inject_memory_for_agents() and extract_learnings_from_conversation()
are async functions being called from synchronous hook context, causing runtime errors.

Solution: Create sync wrapper functions that:
1. Handle "no event loop" case (create new loop)
2. Handle "loop already running" case (use nested_asyncio or thread)
3. Handle import errors gracefully (fail-open)
4. Verify database operations execute correctly
"""

import asyncio
import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

# Add hooks directory to path for imports
hooks_dir = Path(__file__).parent.parent
sys.path.insert(0, str(hooks_dir))

from agent_memory_hook import (
    detect_agent_references,
    detect_slash_command_agent,
    extract_learnings_from_conversation,
    inject_memory_for_agents,
)

# ============================================================================
# UNIT TESTS (60%) - Test sync wrappers in isolation
# ============================================================================


class TestInjectMemoryForAgentsSync:
    """Unit tests for inject_memory_for_agents_sync() wrapper function"""

    def test_sync_wrapper_exists(self):
        """Test that sync wrapper function exists and is importable"""
        from agent_memory_hook import inject_memory_for_agents_sync

        assert callable(inject_memory_for_agents_sync)

    def test_sync_wrapper_signature(self):
        """Test sync wrapper has same signature as async version"""
        from agent_memory_hook import inject_memory_for_agents_sync

        import inspect

        sig = inspect.signature(inject_memory_for_agents_sync)
        params = list(sig.parameters.keys())

        # Should have same parameters as async version
        assert "prompt" in params
        assert "agent_types" in params
        assert "session_id" in params

    def test_sync_wrapper_returns_tuple(self):
        """Test sync wrapper returns (enhanced_prompt, metadata) tuple"""
        from agent_memory_hook import inject_memory_for_agents_sync

        # Should return tuple even when memory system unavailable
        result = inject_memory_for_agents_sync(
            prompt="Test prompt", agent_types=["architect"], session_id="test_session"
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        enhanced_prompt, metadata = result
        assert isinstance(enhanced_prompt, str)
        assert isinstance(metadata, dict)

    def test_sync_wrapper_no_event_loop(self):
        """Test sync wrapper works when no event loop exists"""
        from agent_memory_hook import inject_memory_for_agents_sync

        # Ensure no event loop exists
        try:
            asyncio.get_running_loop()
            pytest.skip("Event loop already running")
        except RuntimeError:
            pass  # Good - no loop running

        with patch(
            "agent_memory_hook.inject_memory_for_agents",
            new_callable=AsyncMock,
            return_value=("Enhanced prompt", {"test": "metadata"}),
        ):
            result = inject_memory_for_agents_sync(
                prompt="Test prompt",
                agent_types=["architect"],
                session_id="test_session",
            )

            assert result == ("Enhanced prompt", {"test": "metadata"})

    def test_sync_wrapper_with_running_loop(self):
        """Test sync wrapper handles case when event loop already running"""
        from agent_memory_hook import inject_memory_for_agents_sync

        async def test_with_running_loop():
            # Inside this coroutine, an event loop IS running
            with patch(
                "agent_memory_hook.inject_memory_for_agents",
                new_callable=AsyncMock,
                return_value=("Enhanced", {"meta": "data"}),
            ):
                result = inject_memory_for_agents_sync(
                    prompt="Test", agent_types=["tester"], session_id="test"
                )

                # Should still work even with running loop
                assert result == ("Enhanced", {"meta": "data"})

        # Run test in async context (simulates running loop)
        asyncio.run(test_with_running_loop())

    def test_sync_wrapper_import_error_handling(self):
        """Test sync wrapper handles import errors gracefully (fail-open)"""
        from agent_memory_hook import inject_memory_for_agents_sync

        with patch(
            "agent_memory_hook.inject_memory_for_agents",
            side_effect=ImportError("Memory system not available"),
        ):
            prompt = "Test prompt"
            result = inject_memory_for_agents_sync(
                prompt=prompt, agent_types=["architect"], session_id="test"
            )

            enhanced_prompt, metadata = result

            # Should fail-open: return original prompt
            assert enhanced_prompt == prompt
            assert metadata.get("memory_available") is False
            assert "error" in metadata

    def test_sync_wrapper_general_exception_handling(self):
        """Test sync wrapper handles general exceptions gracefully"""
        from agent_memory_hook import inject_memory_for_agents_sync

        with patch(
            "agent_memory_hook.inject_memory_for_agents",
            side_effect=Exception("Database connection failed"),
        ):
            prompt = "Test prompt"
            result = inject_memory_for_agents_sync(
                prompt=prompt, agent_types=["builder"], session_id="test"
            )

            enhanced_prompt, metadata = result

            # Should fail-open: return original prompt
            assert enhanced_prompt == prompt
            assert metadata.get("memory_available") is False
            assert "error" in metadata

    def test_sync_wrapper_empty_agent_types(self):
        """Test sync wrapper handles empty agent_types list"""
        from agent_memory_hook import inject_memory_for_agents_sync

        result = inject_memory_for_agents_sync(
            prompt="Test prompt", agent_types=[], session_id="test"
        )

        enhanced_prompt, metadata = result

        # Should return prompt unchanged
        assert enhanced_prompt == "Test prompt"
        assert metadata == {}

    def test_sync_wrapper_none_session_id(self):
        """Test sync wrapper handles None session_id"""
        from agent_memory_hook import inject_memory_for_agents_sync

        with patch(
            "agent_memory_hook.inject_memory_for_agents",
            new_callable=AsyncMock,
            return_value=("Enhanced", {"test": "data"}),
        ):
            result = inject_memory_for_agents_sync(
                prompt="Test", agent_types=["architect"], session_id=None
            )

            assert result == ("Enhanced", {"test": "data"})


class TestExtractLearningsFromConversationSync:
    """Unit tests for extract_learnings_from_conversation_sync() wrapper"""

    def test_sync_wrapper_exists(self):
        """Test that sync wrapper function exists and is importable"""
        from agent_memory_hook import extract_learnings_from_conversation_sync

        assert callable(extract_learnings_from_conversation_sync)

    def test_sync_wrapper_signature(self):
        """Test sync wrapper has same signature as async version"""
        from agent_memory_hook import extract_learnings_from_conversation_sync

        import inspect

        sig = inspect.signature(extract_learnings_from_conversation_sync)
        params = list(sig.parameters.keys())

        # Should have same parameters as async version
        assert "conversation_text" in params
        assert "agent_types" in params
        assert "session_id" in params

    def test_sync_wrapper_returns_dict(self):
        """Test sync wrapper returns metadata dictionary"""
        from agent_memory_hook import extract_learnings_from_conversation_sync

        result = extract_learnings_from_conversation_sync(
            conversation_text="Test conversation",
            agent_types=["architect"],
            session_id="test",
        )

        assert isinstance(result, dict)

    def test_sync_wrapper_no_event_loop(self):
        """Test sync wrapper works when no event loop exists"""
        from agent_memory_hook import extract_learnings_from_conversation_sync

        # Ensure no event loop exists
        try:
            asyncio.get_running_loop()
            pytest.skip("Event loop already running")
        except RuntimeError:
            pass  # Good - no loop running

        with patch(
            "agent_memory_hook.extract_learnings_from_conversation",
            new_callable=AsyncMock,
            return_value={"learnings_stored": 2, "memory_available": True},
        ):
            result = extract_learnings_from_conversation_sync(
                conversation_text="Test",
                agent_types=["architect"],
                session_id="test",
            )

            assert result["learnings_stored"] == 2
            assert result["memory_available"] is True

    def test_sync_wrapper_with_running_loop(self):
        """Test sync wrapper handles case when event loop already running"""
        from agent_memory_hook import extract_learnings_from_conversation_sync

        async def test_with_running_loop():
            with patch(
                "agent_memory_hook.extract_learnings_from_conversation",
                new_callable=AsyncMock,
                return_value={"learnings_stored": 1, "memory_available": True},
            ):
                result = extract_learnings_from_conversation_sync(
                    conversation_text="Test",
                    agent_types=["tester"],
                    session_id="test",
                )

                assert result["learnings_stored"] == 1

        asyncio.run(test_with_running_loop())

    def test_sync_wrapper_import_error_handling(self):
        """Test sync wrapper handles import errors gracefully (fail-open)"""
        from agent_memory_hook import extract_learnings_from_conversation_sync

        with patch(
            "agent_memory_hook.extract_learnings_from_conversation",
            side_effect=ImportError("Memory system not available"),
        ):
            result = extract_learnings_from_conversation_sync(
                conversation_text="Test", agent_types=["architect"], session_id="test"
            )

            assert result.get("memory_available") is False
            assert "error" in result
            assert result.get("learnings_stored") == 0

    def test_sync_wrapper_general_exception_handling(self):
        """Test sync wrapper handles general exceptions gracefully"""
        from agent_memory_hook import extract_learnings_from_conversation_sync

        with patch(
            "agent_memory_hook.extract_learnings_from_conversation",
            side_effect=Exception("Database write failed"),
        ):
            result = extract_learnings_from_conversation_sync(
                conversation_text="Test", agent_types=["builder"], session_id="test"
            )

            assert result.get("memory_available") is False
            assert "error" in result

    def test_sync_wrapper_empty_agent_types(self):
        """Test sync wrapper handles empty agent_types list"""
        from agent_memory_hook import extract_learnings_from_conversation_sync

        result = extract_learnings_from_conversation_sync(
            conversation_text="Test conversation", agent_types=[], session_id="test"
        )

        # Should return minimal metadata
        assert result.get("learnings_stored") == 0
        assert result.get("agents") == []


# ============================================================================
# INTEGRATION TESTS (30%) - Test sync wrappers with real async functions
# ============================================================================


class TestSyncWrapperIntegration:
    """Integration tests for sync wrappers calling real async functions"""

    @pytest.mark.asyncio
    async def test_inject_memory_sync_calls_async_version(self):
        """Test sync wrapper correctly calls async version"""
        from agent_memory_hook import inject_memory_for_agents_sync

        # Mock the MemoryCoordinator to avoid actual database calls
        # Must patch where it's imported (inside the async function)
        with patch(
            "amplihack.memory.coordinator.MemoryCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = Mock()
            mock_coordinator.retrieve = AsyncMock(return_value=[])
            mock_coordinator_class.return_value = mock_coordinator

            # Call sync wrapper (which should call async function internally)
            result = inject_memory_for_agents_sync(
                prompt="Design authentication system",
                agent_types=["architect", "security"],
                session_id="integration_test",
            )

            enhanced_prompt, metadata = result

            # Verify coordinator was initialized
            assert mock_coordinator_class.called
            # Verify metadata structure
            assert "agents" in metadata
            assert "memory_available" in metadata

    @pytest.mark.asyncio
    async def test_extract_learnings_sync_calls_async_version(self):
        """Test sync wrapper correctly calls async version"""
        from agent_memory_hook import extract_learnings_from_conversation_sync

        # Must patch where it's imported (inside the async function)
        with patch(
            "amplihack.memory.coordinator.MemoryCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = Mock()
            mock_coordinator.store = AsyncMock(return_value="memory_id_123")
            mock_coordinator_class.return_value = mock_coordinator

            result = extract_learnings_from_conversation_sync(
                conversation_text="Successfully implemented auth",
                agent_types=["architect"],
                session_id="integration_test",
            )

            # Verify coordinator was initialized
            assert mock_coordinator_class.called
            # Verify metadata structure
            assert "agents" in result
            assert "learnings_stored" in result

    def test_sync_wrapper_thread_safety(self):
        """Test sync wrappers are thread-safe"""
        from agent_memory_hook import inject_memory_for_agents_sync
        import threading

        results = []
        errors = []

        def call_sync_wrapper(index):
            try:
                result = inject_memory_for_agents_sync(
                    prompt=f"Prompt {index}",
                    agent_types=["architect"],
                    session_id=f"thread_{index}",
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads calling sync wrapper
        threads = [threading.Thread(target=call_sync_wrapper, args=(i,)) for i in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All calls should succeed without errors
        assert len(errors) == 0
        assert len(results) == 5


# ============================================================================
# E2E TESTS (10%) - Test complete workflows with sync wrappers
# ============================================================================


class TestSyncWrapperEndToEnd:
    """End-to-end tests simulating real hook usage scenarios"""

    def test_user_prompt_submit_workflow(self):
        """Test complete user_prompt_submit hook workflow using sync wrappers"""
        from agent_memory_hook import (
            detect_agent_references,
            inject_memory_for_agents_sync,
        )

        user_prompt = "Use @.claude/agents/amplihack/core/architect.md to design a payment system"

        # Step 1: Detect agent references
        agent_types = detect_agent_references(user_prompt)
        assert "architect" in agent_types

        # Step 2: Inject memory using sync wrapper
        # Must patch where it's imported (inside the async function)
        with patch(
            "amplihack.memory.coordinator.MemoryCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = Mock()
            mock_coordinator.retrieve = AsyncMock(return_value=[])
            mock_coordinator_class.return_value = mock_coordinator

            enhanced_prompt, metadata = inject_memory_for_agents_sync(
                prompt=user_prompt, agent_types=agent_types, session_id="e2e_test"
            )

            # Verify workflow completed successfully
            assert isinstance(enhanced_prompt, str)
            assert "memory_available" in metadata

    def test_stop_hook_workflow(self):
        """Test complete stop hook workflow using sync wrappers"""
        from agent_memory_hook import extract_learnings_from_conversation_sync

        conversation_text = """
        User: Design authentication system
        Assistant: I'll use OAuth2 with JWT tokens...
        [Implementation details]
        """

        agent_types = ["architect", "security"]

        # Extract learnings using sync wrapper
        # Must patch where it's imported (inside the async function)
        with patch(
            "amplihack.memory.coordinator.MemoryCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = Mock()
            mock_coordinator.store = AsyncMock(return_value="memory_123")
            mock_coordinator_class.return_value = mock_coordinator

            metadata = extract_learnings_from_conversation_sync(
                conversation_text=conversation_text,
                agent_types=agent_types,
                session_id="e2e_test",
            )

            # Verify workflow completed successfully
            assert "learnings_stored" in metadata
            assert "agents" in metadata

    def test_complete_session_lifecycle(self):
        """Test complete session: prompt submission -> conversation -> extraction"""
        from agent_memory_hook import (
            detect_agent_references,
            extract_learnings_from_conversation_sync,
            inject_memory_for_agents_sync,
        )

        # Must patch where it's imported (inside the async functions)
        with patch(
            "amplihack.memory.coordinator.MemoryCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = Mock()
            mock_coordinator.retrieve = AsyncMock(return_value=[])
            mock_coordinator.store = AsyncMock(return_value="memory_456")
            mock_coordinator_class.return_value = mock_coordinator

            # Phase 1: User submits prompt
            user_prompt = "Use @.claude/agents/amplihack/core/architect.md to design API"
            agent_types = detect_agent_references(user_prompt)

            # Phase 2: Inject memory
            enhanced_prompt, inject_metadata = inject_memory_for_agents_sync(
                prompt=user_prompt, agent_types=agent_types, session_id="lifecycle_test"
            )

            assert inject_metadata.get("memory_available") is True

            # Phase 3: Conversation happens (simulated)
            conversation = f"{user_prompt}\n\nAssistant: I've designed the API..."

            # Phase 4: Extract learnings
            extract_metadata = extract_learnings_from_conversation_sync(
                conversation_text=conversation,
                agent_types=agent_types,
                session_id="lifecycle_test",
            )

            assert extract_metadata.get("learnings_stored", 0) > 0


# ============================================================================
# EDGE CASE TESTS - Boundary conditions and error scenarios
# ============================================================================


class TestSyncWrapperEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_sync_wrapper_with_very_long_prompt(self):
        """Test sync wrapper handles very long prompts"""
        from agent_memory_hook import inject_memory_for_agents_sync

        long_prompt = "Design system " * 10000  # Very long prompt

        result = inject_memory_for_agents_sync(
            prompt=long_prompt, agent_types=["architect"], session_id="test"
        )

        enhanced_prompt, metadata = result
        assert isinstance(enhanced_prompt, str)

    def test_sync_wrapper_with_special_characters(self):
        """Test sync wrapper handles special characters in prompts"""
        from agent_memory_hook import inject_memory_for_agents_sync

        special_prompt = "Design system with émojis 🚀 and unicode ™️"

        result = inject_memory_for_agents_sync(
            prompt=special_prompt, agent_types=["architect"], session_id="test"
        )

        enhanced_prompt, metadata = result
        assert isinstance(enhanced_prompt, str)

    def test_sync_wrapper_timeout_handling(self):
        """Test sync wrapper handles async operation timeouts"""
        from agent_memory_hook import inject_memory_for_agents_sync

        async def slow_async_function(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate slow operation
            return ("Enhanced", {"test": "data"})

        with patch(
            "agent_memory_hook.inject_memory_for_agents", side_effect=slow_async_function
        ):
            # Should handle timeout gracefully (if timeout implemented)
            # For now, just ensure it doesn't hang forever
            result = inject_memory_for_agents_sync(
                prompt="Test", agent_types=["architect"], session_id="test"
            )

            assert isinstance(result, tuple)

    def test_sync_wrapper_with_multiple_rapid_calls(self):
        """Test sync wrapper handles multiple rapid sequential calls"""
        from agent_memory_hook import inject_memory_for_agents_sync

        results = []
        for i in range(10):
            result = inject_memory_for_agents_sync(
                prompt=f"Prompt {i}",
                agent_types=["architect"],
                session_id=f"rapid_{i}",
            )
            results.append(result)

        # All calls should succeed
        assert len(results) == 10
        for result in results:
            assert isinstance(result, tuple)
            assert len(result) == 2


# ============================================================================
# PERFORMANCE TESTS - Verify sync wrappers don't add significant overhead
# ============================================================================


class TestSyncWrapperPerformance:
    """Test performance characteristics of sync wrappers"""

    def test_sync_wrapper_overhead_minimal(self):
        """Test sync wrapper adds minimal overhead compared to async version"""
        from agent_memory_hook import inject_memory_for_agents_sync
        import time

        start_time = time.time()

        for _ in range(10):
            inject_memory_for_agents_sync(
                prompt="Test", agent_types=[], session_id="perf_test"
            )

        elapsed = time.time() - start_time

        # Should complete 10 calls in under 1 second (generous threshold)
        assert elapsed < 1.0

    def test_sync_wrapper_no_memory_leaks(self):
        """Test sync wrapper doesn't leak event loops or resources"""
        from agent_memory_hook import inject_memory_for_agents_sync
        import gc

        # Capture initial object count
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Make many calls
        for i in range(100):
            inject_memory_for_agents_sync(
                prompt=f"Test {i}", agent_types=[], session_id=f"leak_test_{i}"
            )

        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())

        # Object count should not grow excessively (allow some growth for test overhead)
        assert final_objects < initial_objects * 1.5
