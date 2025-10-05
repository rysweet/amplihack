"""
Integration tests for Auto-Mode.

Tests end-to-end functionality and component integration:
- Full auto-mode workflow from start to finish
- Component interaction and data flow
- Real-world usage scenarios
- Performance and reliability under load
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from amplihack.auto_mode.analysis import ConversationAnalysis, ConversationSignal
from amplihack.auto_mode.command_handler import AutoModeCommandHandler
from amplihack.auto_mode.orchestrator import AutoModeOrchestrator, OrchestratorConfig


class TestFullWorkflow:
    """Test complete auto-mode workflow"""

    @pytest_asyncio.fixture(scope="function")
    async def orchestrator(self):
        """Fixture providing initialized orchestrator"""
        config = OrchestratorConfig(
            analysis_interval_seconds=0.1,  # Fast for testing
            max_analysis_cycles=5,  # Limited for testing
            session_timeout_minutes=1,
        )
        orchestrator = AutoModeOrchestrator(config)

        # Mock component initialization to avoid real I/O
        with patch.object(
            orchestrator.session_manager, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.analysis_engine, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.quality_gate_evaluator, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.sdk_client, "initialize", new_callable=AsyncMock, return_value=True
        ):
            await orchestrator.initialize()

        try:
            yield orchestrator
        finally:
            await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_complete_session_lifecycle(self, orchestrator):
        """Test complete session from start to finish"""
        user_id = "test_user"
        conversation_context = {
            "messages": [
                {"role": "user", "content": "Hello, I need help with my code"},
                {"role": "assistant", "content": "Sure! What specific issue are you having?"},
            ],
            "goals": [{"id": "goal1", "description": "Fix the bug", "status": "pending"}],
        }

        # 1. Start session
        session_id = await orchestrator.start_session(user_id, conversation_context)
        assert session_id is not None
        assert session_id in orchestrator.active_sessions
        assert session_id in orchestrator.analysis_tasks

        # 2. Update conversation
        conversation_update = {
            "messages": [
                {"role": "user", "content": "The error is in line 42"},
                {"role": "assistant", "content": "Let me help you debug that"},
            ]
        }
        success = await orchestrator.update_conversation(session_id, conversation_update)
        assert success is True

        # 3. Let analysis run for a bit
        await asyncio.sleep(0.3)

        # 4. Check session status
        status = await orchestrator.get_session_status(session_id)
        assert status is not None
        assert status["session_id"] == session_id
        assert status["user_id"] == user_id

        # 5. Stop session
        success = await orchestrator.stop_session(session_id)
        assert success is True
        assert session_id not in orchestrator.active_sessions
        assert session_id not in orchestrator.analysis_tasks

    @pytest.mark.asyncio
    async def test_analysis_loop_execution(self, orchestrator):
        """Test analysis loop execution and quality gate evaluation"""
        user_id = "test_user"
        conversation_context = {
            "messages": [
                {"role": "user", "content": "I'm confused and frustrated"},
                {"role": "assistant", "content": "Let me help clarify"},
                {"role": "user", "content": "This isn't working at all"},
            ]
        }

        # Mock analysis engine to return poor quality analysis
        mock_analysis = ConversationAnalysis(
            quality_score=0.3,  # Poor quality
            detected_signals=[
                ConversationSignal.CONFUSION_INDICATOR,
                ConversationSignal.FRUSTRATION_SIGNAL,
            ],
            conversation_length=3,
        )

        with patch.object(
            orchestrator.analysis_engine,
            "analyze_conversation",
            new_callable=AsyncMock,
            return_value=mock_analysis,
        ):
            # Start session
            session_id = await orchestrator.start_session(user_id, conversation_context)

            # Let analysis cycles run
            await asyncio.sleep(0.5)

            # Check that analysis was performed
            session_state = orchestrator.active_sessions[session_id]
            assert session_state.analysis_cycles > 0
            assert session_state.current_quality_score == 0.3

            # Stop session
            await orchestrator.stop_session(session_id)

    @pytest.mark.asyncio
    async def test_quality_gate_intervention_flow(self, orchestrator):
        """Test quality gate triggering and intervention suggestions"""
        interventions_received = []

        async def intervention_callback(session_id, gate_result):
            interventions_received.append((session_id, gate_result))

        orchestrator.on_intervention_suggested.append(intervention_callback)

        # Create problematic conversation context
        conversation_context = {
            "messages": [
                {"role": "user", "content": "I don't understand"},
                {"role": "assistant", "content": "Let me explain"},
                {"role": "user", "content": "Still confused"},
            ]
        }

        # Mock poor quality analysis
        mock_analysis = ConversationAnalysis(
            quality_score=0.4, detected_signals=[ConversationSignal.CONFUSION_INDICATOR]
        )

        with patch.object(
            orchestrator.analysis_engine,
            "analyze_conversation",
            new_callable=AsyncMock,
            return_value=mock_analysis,
        ):
            session_id = await orchestrator.start_session("test_user", conversation_context)

            # Wait for analysis and quality gate evaluation
            await asyncio.sleep(0.3)

            # Check if interventions were suggested
            assert len(interventions_received) > 0
            session_id_callback, gate_result = interventions_received[0]
            assert session_id_callback == session_id
            assert gate_result.triggered is True

            await orchestrator.stop_session(session_id)

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, orchestrator):
        """Test handling multiple concurrent sessions"""
        orchestrator.config.max_concurrent_sessions = 3

        sessions = []
        for i in range(3):
            user_id = f"user_{i}"
            conversation_context = {"messages": [], "goals": []}

            session_id = await orchestrator.start_session(user_id, conversation_context)
            sessions.append(session_id)

        # All sessions should be active
        assert len(orchestrator.active_sessions) == 3
        assert len(orchestrator.analysis_tasks) == 3

        # Let analysis run briefly
        await asyncio.sleep(0.2)

        # Stop all sessions
        for session_id in sessions:
            await orchestrator.stop_session(session_id)

        assert len(orchestrator.active_sessions) == 0


class TestCommandHandlerIntegration:
    """Test command handler integration with orchestrator"""

    @pytest.fixture
    def handler(self):
        return AutoModeCommandHandler()

    @pytest.mark.asyncio
    async def test_start_stop_command_flow(self, handler):
        """Test start and stop commands working together"""
        context = {"user_id": "test_user", "conversation_context": {}}

        # Start auto-mode
        result = await handler.handle_command("start --config default", context)
        assert result.success is True
        assert "session_id" in result.data

        session_id = result.data["session_id"]

        # Check status
        result = await handler.handle_command("status", context)
        assert result.success is True
        assert result.data["status"] == "active"
        assert result.data["active_sessions"] > 0

        # Stop auto-mode
        result = await handler.handle_command(f"stop --session-id {session_id}", context)
        assert result.success is True

        # Check status again
        result = await handler.handle_command("status", context)
        assert result.success is True
        assert result.data["active_sessions"] == 0

    @pytest.mark.asyncio
    async def test_configure_command_integration(self, handler):
        """Test configuration commands with orchestrator"""
        context = {"user_id": "test_user", "conversation_context": {}}

        # Start auto-mode
        result = await handler.handle_command("start", context)
        assert result.success is True

        # Configure settings
        result = await handler.handle_command("configure intervention_threshold 0.8", context)
        assert result.success is True

        result = await handler.handle_command("configure background_mode false", context)
        assert result.success is True

        # Verify configuration was applied
        assert handler.orchestrator.config.intervention_confidence_threshold == 0.8
        assert handler.orchestrator.config.background_analysis_enabled is False

        # Stop auto-mode
        result = await handler.handle_command("stop", context)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_analyze_command_integration(self, handler):
        """Test analyze command with active session"""
        context = {
            "user_id": "test_user",
            "conversation_context": {
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                ]
            },
        }

        # Start auto-mode
        result = await handler.handle_command("start", context)
        assert result.success is True

        # Mock analysis result
        mock_analysis = ConversationAnalysis(quality_score=0.8, conversation_length=2)

        with patch.object(
            handler.orchestrator.analysis_engine,
            "analyze_conversation",
            new_callable=AsyncMock,
            return_value=mock_analysis,
        ):
            # Request analysis
            result = await handler.handle_command("analyze --output json", context)
            assert result.success is True
            assert "quality_score" in result.data
            assert result.data["quality_score"] == 0.8

        # Stop auto-mode
        result = await handler.handle_command("stop", context)
        assert result.success is True


class TestDataFlowIntegration:
    """Test data flow between components"""

    @pytest.mark.asyncio
    async def test_session_persistence_flow(self):
        """Test session data persistence flow"""
        import tempfile

        with tempfile.TemporaryDirectory():
            # Create orchestrator with custom storage
            config = OrchestratorConfig()
            orchestrator = AutoModeOrchestrator(config)

            # Mock initialization
            with patch.object(
                orchestrator.session_manager, "initialize", new_callable=AsyncMock
            ), patch.object(
                orchestrator.analysis_engine, "initialize", new_callable=AsyncMock
            ), patch.object(
                orchestrator.quality_gate_evaluator, "initialize", new_callable=AsyncMock
            ), patch.object(
                orchestrator.sdk_client, "initialize", new_callable=AsyncMock, return_value=True
            ):
                await orchestrator.initialize()

            # Create session with data
            user_id = "test_user"
            conversation_context = {
                "messages": [{"role": "user", "content": "Test message"}],
                "goals": [{"id": "goal1", "status": "pending"}],
            }

            session_id = await orchestrator.start_session(user_id, conversation_context)

            # Update session data
            update_data = {"new_field": "new_value"}
            await orchestrator.update_conversation(session_id, update_data)

            # Verify data was updated
            session_state = orchestrator.active_sessions[session_id]
            assert "new_field" in session_state.conversation_context

            await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_analysis_to_quality_gates_flow(self):
        """Test data flow from analysis to quality gates"""
        config = OrchestratorConfig()
        orchestrator = AutoModeOrchestrator(config)

        # Mock initialization
        with patch.object(
            orchestrator.session_manager, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.analysis_engine, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.quality_gate_evaluator, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.sdk_client, "initialize", new_callable=AsyncMock, return_value=True
        ):
            await orchestrator.initialize()

        # Create analysis result with specific characteristics
        mock_analysis = ConversationAnalysis(
            quality_score=0.3,  # Low quality to trigger gates
            detected_signals=[ConversationSignal.CONFUSION_INDICATOR],
            conversation_length=5,
        )

        # Mock quality gate evaluation
        from amplihack.auto_mode.quality_gates import GatePriority, QualityGateResult

        mock_gate_result = QualityGateResult(
            gate_id="quality_drop",
            gate_name="Quality Drop",
            triggered=True,
            confidence=0.8,
            priority=GatePriority.HIGH,
            suggested_actions=[{"type": "clarification", "title": "Ask for clarification"}],
        )

        with patch.object(
            orchestrator.analysis_engine,
            "analyze_conversation",
            new_callable=AsyncMock,
            return_value=mock_analysis,
        ), patch.object(
            orchestrator.quality_gate_evaluator,
            "evaluate",
            new_callable=AsyncMock,
            return_value=[mock_gate_result],
        ):
            # Create session and let analysis run
            session_id = await orchestrator.start_session("test_user", {})

            # Execute single analysis cycle
            result = await orchestrator._execute_analysis_cycle(session_id, "test_cycle")

            # Verify data flow
            assert result.analysis == mock_analysis
            assert len(result.quality_gates) == 1
            assert result.quality_gates[0].triggered is True
            assert len(result.interventions_suggested) > 0

            await orchestrator.stop_session(session_id)

        await orchestrator.shutdown()


class TestErrorRecovery:
    """Test error handling and recovery scenarios"""

    @pytest.mark.asyncio
    async def test_analysis_error_recovery(self):
        """Test recovery from analysis errors"""
        config = OrchestratorConfig(analysis_interval_seconds=0.1, max_analysis_cycles=3)
        orchestrator = AutoModeOrchestrator(config)

        # Mock initialization
        with patch.object(
            orchestrator.session_manager, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.analysis_engine, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.quality_gate_evaluator, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.sdk_client, "initialize", new_callable=AsyncMock, return_value=True
        ):
            await orchestrator.initialize()

        # Mock analysis engine to fail first, then succeed
        call_count = 0

        def analysis_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Analysis failed")
            return ConversationAnalysis(quality_score=0.8)

        with patch.object(
            orchestrator.analysis_engine, "analyze_conversation", side_effect=analysis_side_effect
        ):
            session_id = await orchestrator.start_session("test_user", {})

            # Let analysis run and recover
            await asyncio.sleep(0.5)

            # Session should still be active despite error
            assert session_id in orchestrator.active_sessions

            # Should have attempted multiple analysis cycles
            assert call_count > 1

            await orchestrator.stop_session(session_id)

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_session_cleanup_on_error(self):
        """Test session cleanup when errors occur"""
        config = OrchestratorConfig()
        orchestrator = AutoModeOrchestrator(config)

        # Mock initialization
        with patch.object(
            orchestrator.session_manager, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.analysis_engine, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.quality_gate_evaluator, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.sdk_client, "initialize", new_callable=AsyncMock, return_value=True
        ):
            await orchestrator.initialize()

        # Mock session manager to fail during session creation
        with patch.object(
            orchestrator.session_manager,
            "create_session",
            new_callable=AsyncMock,
            side_effect=Exception("Session creation failed"),
        ):
            with pytest.raises(Exception, match="Session creation failed"):
                await orchestrator.start_session("test_user", {})

            # Should not have any active sessions
            assert len(orchestrator.active_sessions) == 0

        await orchestrator.shutdown()


class TestPerformanceCharacteristics:
    """Test performance and scalability characteristics"""

    @pytest.mark.asyncio
    async def test_rapid_session_creation_cleanup(self):
        """Test rapid session creation and cleanup"""
        config = OrchestratorConfig(max_concurrent_sessions=10, analysis_interval_seconds=0.1)
        orchestrator = AutoModeOrchestrator(config)

        # Mock initialization
        with patch.object(
            orchestrator.session_manager, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.analysis_engine, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.quality_gate_evaluator, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.sdk_client, "initialize", new_callable=AsyncMock, return_value=True
        ):
            await orchestrator.initialize()

        # Create and immediately stop sessions rapidly
        session_ids = []
        for i in range(5):
            session_id = await orchestrator.start_session(f"user_{i}", {})
            session_ids.append(session_id)

        # Verify all sessions created
        assert len(orchestrator.active_sessions) == 5

        # Stop all sessions
        for session_id in session_ids:
            await orchestrator.stop_session(session_id)

        # Verify cleanup
        assert len(orchestrator.active_sessions) == 0
        assert len(orchestrator.analysis_tasks) == 0

        await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_analysis_loop_performance(self):
        """Test analysis loop performance under load"""
        config = OrchestratorConfig(
            analysis_interval_seconds=0.05,  # Very fast
            max_analysis_cycles=10,
        )
        orchestrator = AutoModeOrchestrator(config)

        # Mock initialization
        with patch.object(
            orchestrator.session_manager, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.analysis_engine, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.quality_gate_evaluator, "initialize", new_callable=AsyncMock
        ), patch.object(
            orchestrator.sdk_client, "initialize", new_callable=AsyncMock, return_value=True
        ):
            await orchestrator.initialize()

        # Mock fast analysis
        mock_analysis = ConversationAnalysis(quality_score=0.8)

        with patch.object(
            orchestrator.analysis_engine,
            "analyze_conversation",
            new_callable=AsyncMock,
            return_value=mock_analysis,
        ), patch.object(
            orchestrator.quality_gate_evaluator, "evaluate", new_callable=AsyncMock, return_value=[]
        ):
            session_id = await orchestrator.start_session("test_user", {})

            # Let analysis cycles run
            start_time = time.time()
            await asyncio.sleep(0.5)
            end_time = time.time()

            # Check analysis performance
            session_state = orchestrator.active_sessions[session_id]
            cycles_per_second = session_state.analysis_cycles / (end_time - start_time)

            # Should achieve reasonable analysis rate
            assert cycles_per_second > 5  # At least 5 cycles per second

            await orchestrator.stop_session(session_id)

        await orchestrator.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])
