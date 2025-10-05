"""
Test suite for AutoModeOrchestrator.

Tests the core orchestration functionality including:
- Session lifecycle management
- Agentic analysis loops
- Quality gate coordination
- SDK integration
- Metrics and monitoring
"""

import pytest
import pytest_asyncio
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from amplihack.auto_mode.orchestrator import (
    AutoModeOrchestrator,
    OrchestratorConfig,
    OrchestratorState,
    AnalysisCycleResult
)
from amplihack.auto_mode.session import SessionState
from amplihack.auto_mode.analysis import ConversationAnalysis


class TestOrchestratorInitialization:
    """Test orchestrator initialization and configuration"""

    @pytest.mark.asyncio
    async def test_orchestrator_creation_with_default_config(self):
        """Test creating orchestrator with default configuration"""
        orchestrator = AutoModeOrchestrator()

        assert orchestrator.state == OrchestratorState.INACTIVE
        assert orchestrator.config is not None
        assert isinstance(orchestrator.config, OrchestratorConfig)
        assert len(orchestrator.active_sessions) == 0

    @pytest.mark.asyncio
    async def test_orchestrator_creation_with_custom_config(self):
        """Test creating orchestrator with custom configuration"""
        config = OrchestratorConfig(
            analysis_interval_seconds=15.0,
            max_concurrent_sessions=5
        )
        orchestrator = AutoModeOrchestrator(config)

        assert orchestrator.config.analysis_interval_seconds == 15.0
        assert orchestrator.config.max_concurrent_sessions == 5

    @pytest.mark.asyncio
    async def test_orchestrator_initialization_success(self):
        """Test successful orchestrator initialization"""
        orchestrator = AutoModeOrchestrator()

        # Mock component initialization
        with patch.object(orchestrator.session_manager, 'initialize', new_callable=AsyncMock) as mock_session_init, \
             patch.object(orchestrator.analysis_engine, 'initialize', new_callable=AsyncMock) as mock_analysis_init, \
             patch.object(orchestrator.quality_gate_evaluator, 'initialize', new_callable=AsyncMock) as mock_gates_init, \
             patch.object(orchestrator.sdk_client, 'initialize', new_callable=AsyncMock, return_value=True) as mock_sdk_init:

            success = await orchestrator.initialize()

            assert success is True
            assert orchestrator.state == OrchestratorState.ACTIVE
            mock_session_init.assert_called_once()
            mock_analysis_init.assert_called_once()
            mock_gates_init.assert_called_once()
            mock_sdk_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrator_initialization_failure(self):
        """Test orchestrator initialization failure"""
        orchestrator = AutoModeOrchestrator()

        # Mock SDK initialization failure
        with patch.object(orchestrator.sdk_client, 'initialize', new_callable=AsyncMock, return_value=False):
            success = await orchestrator.initialize()

            # Should still succeed without SDK
            assert success is True
            assert orchestrator.state == OrchestratorState.ACTIVE

    @pytest.mark.asyncio
    async def test_orchestrator_initialization_exception(self):
        """Test orchestrator initialization with exception"""
        orchestrator = AutoModeOrchestrator()

        # Mock component initialization exception
        with patch.object(orchestrator.session_manager, 'initialize', new_callable=AsyncMock, side_effect=Exception("Init failed")):
            success = await orchestrator.initialize()

            assert success is False
            assert orchestrator.state == OrchestratorState.ERROR


class TestSessionManagement:
    """Test session lifecycle management"""

    @pytest_asyncio.fixture(scope="function")
    async def initialized_orchestrator(self):
        """Fixture providing initialized orchestrator"""
        orchestrator = AutoModeOrchestrator()

        with patch.object(orchestrator.session_manager, 'initialize', new_callable=AsyncMock), \
             patch.object(orchestrator.analysis_engine, 'initialize', new_callable=AsyncMock), \
             patch.object(orchestrator.quality_gate_evaluator, 'initialize', new_callable=AsyncMock), \
             patch.object(orchestrator.sdk_client, 'initialize', new_callable=AsyncMock, return_value=True):

            await orchestrator.initialize()
            try:
                yield orchestrator
            finally:
                await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_start_session_success(self, initialized_orchestrator):
        """Test successful session creation"""
        orchestrator = initialized_orchestrator
        user_id = "test_user"
        conversation_context = {"messages": [], "goals": []}

        # Mock session manager
        mock_session_state = SessionState(
            session_id="test_session",
            user_id=user_id,
            conversation_context=conversation_context
        )

        with patch.object(orchestrator.session_manager, 'create_session', new_callable=AsyncMock, return_value=mock_session_state):
            session_id = await orchestrator.start_session(user_id, conversation_context)

            assert session_id is not None
            assert session_id in orchestrator.active_sessions
            assert session_id in orchestrator.analysis_tasks
            assert orchestrator.metrics['total_sessions'] == 1

    @pytest.mark.asyncio
    async def test_start_session_max_concurrent_limit(self, initialized_orchestrator):
        """Test session creation with max concurrent limit"""
        orchestrator = initialized_orchestrator
        orchestrator.config.max_concurrent_sessions = 1

        # Create first session
        mock_session_state1 = SessionState(session_id="session1", user_id="user1")
        with patch.object(orchestrator.session_manager, 'create_session', new_callable=AsyncMock, return_value=mock_session_state1):
            session_id1 = await orchestrator.start_session("user1", {})
            assert session_id1 is not None

        # Try to create second session - should fail
        with patch.object(orchestrator.session_manager, 'create_session', new_callable=AsyncMock, side_effect=RuntimeError("Maximum concurrent sessions reached")):
            with pytest.raises(RuntimeError, match="Maximum concurrent sessions reached"):
                await orchestrator.start_session("user2", {})

    @pytest.mark.asyncio
    async def test_update_conversation_success(self, initialized_orchestrator):
        """Test successful conversation update"""
        orchestrator = initialized_orchestrator

        # Create session
        mock_session_state = SessionState(session_id="test_session", user_id="test_user")
        orchestrator.active_sessions["test_session"] = mock_session_state

        conversation_update = {"new_message": "Hello world"}

        with patch.object(orchestrator.session_manager, 'update_conversation', new_callable=AsyncMock, return_value=True):
            success = await orchestrator.update_conversation("test_session", conversation_update)

            assert success is True

    @pytest.mark.asyncio
    async def test_update_conversation_nonexistent_session(self, initialized_orchestrator):
        """Test conversation update for non-existent session"""
        orchestrator = initialized_orchestrator

        success = await orchestrator.update_conversation("nonexistent", {})
        assert success is False

    @pytest.mark.asyncio
    async def test_get_session_status_existing(self, initialized_orchestrator):
        """Test getting status for existing session"""
        orchestrator = initialized_orchestrator

        # Create mock session
        mock_session_state = SessionState(
            session_id="test_session",
            user_id="test_user",
            analysis_cycles=5,
            current_quality_score=0.8,
            total_interventions=2
        )
        orchestrator.active_sessions["test_session"] = mock_session_state

        status = await orchestrator.get_session_status("test_session")

        assert status is not None
        assert status['session_id'] == "test_session"
        assert status['user_id'] == "test_user"
        assert status['analysis_cycles'] == 5
        assert status['current_quality_score'] == 0.8
        assert status['total_interventions'] == 2

    @pytest.mark.asyncio
    async def test_get_session_status_nonexistent(self, initialized_orchestrator):
        """Test getting status for non-existent session"""
        orchestrator = initialized_orchestrator

        status = await orchestrator.get_session_status("nonexistent")
        assert status is None

    @pytest.mark.asyncio
    async def test_stop_session_success(self, initialized_orchestrator):
        """Test successful session stopping"""
        orchestrator = initialized_orchestrator

        # Create mock session and task
        mock_session_state = SessionState(session_id="test_session", user_id="test_user")
        mock_task = AsyncMock()

        orchestrator.active_sessions["test_session"] = mock_session_state
        orchestrator.analysis_tasks["test_session"] = mock_task

        with patch.object(orchestrator.session_manager, 'close_session', new_callable=AsyncMock, return_value=True):
            success = await orchestrator.stop_session("test_session")

            assert success is True
            assert "test_session" not in orchestrator.active_sessions
            assert "test_session" not in orchestrator.analysis_tasks
            mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_session_nonexistent(self, initialized_orchestrator):
        """Test stopping non-existent session"""
        orchestrator = initialized_orchestrator

        success = await orchestrator.stop_session("nonexistent")
        assert success is False


class TestAnalysisLoop:
    """Test agentic analysis loop functionality"""

    @pytest_asyncio.fixture(scope="function")
    async def orchestrator_with_session(self):
        """Fixture providing orchestrator with active session"""
        orchestrator = AutoModeOrchestrator()

        # Mock initialization
        with patch.object(orchestrator.session_manager, 'initialize', new_callable=AsyncMock), \
             patch.object(orchestrator.analysis_engine, 'initialize', new_callable=AsyncMock), \
             patch.object(orchestrator.quality_gate_evaluator, 'initialize', new_callable=AsyncMock), \
             patch.object(orchestrator.sdk_client, 'initialize', new_callable=AsyncMock, return_value=True):

            await orchestrator.initialize()

        # Create mock session
        mock_session_state = SessionState(session_id="test_session", user_id="test_user")
        orchestrator.active_sessions["test_session"] = mock_session_state

        try:
            yield orchestrator
        finally:
            await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_execute_analysis_cycle(self, orchestrator_with_session):
        """Test single analysis cycle execution"""
        orchestrator = orchestrator_with_session
        session_state = orchestrator.active_sessions["test_session"]

        # Mock analysis results
        mock_analysis = ConversationAnalysis(
            quality_score=0.8,
            conversation_activity_level=1.5
        )

        mock_quality_gates = []

        with patch.object(orchestrator.analysis_engine, 'analyze_conversation', new_callable=AsyncMock, return_value=mock_analysis), \
             patch.object(orchestrator.quality_gate_evaluator, 'evaluate', new_callable=AsyncMock, return_value=mock_quality_gates):

            result = await orchestrator._execute_analysis_cycle("test_session", "cycle_1")

            assert isinstance(result, AnalysisCycleResult)
            assert result.session_id == "test_session"
            assert result.cycle_id == "cycle_1"
            assert result.analysis == mock_analysis
            assert result.quality_gates == mock_quality_gates
            assert result.next_cycle_delay > 0

    @pytest.mark.asyncio
    async def test_analysis_loop_termination_conditions(self, orchestrator_with_session):
        """Test analysis loop termination conditions"""
        orchestrator = orchestrator_with_session
        orchestrator.config.max_analysis_cycles = 2  # Limit for testing

        # Mock short analysis cycles
        with patch.object(orchestrator, '_execute_analysis_cycle', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AnalysisCycleResult(
                cycle_id="test",
                session_id="test_session",
                timestamp=time.time(),
                analysis=ConversationAnalysis(),
                quality_gates=[],
                interventions_suggested=[],
                next_cycle_delay=0.1  # Very short delay for testing
            )

            # Start analysis loop
            loop_task = asyncio.create_task(orchestrator._run_analysis_loop("test_session"))

            # Wait a bit then check
            await asyncio.sleep(0.5)

            # Should have stopped due to max cycles
            assert loop_task.done()
            assert mock_execute.call_count == 2

    @pytest.mark.asyncio
    async def test_analysis_loop_cancellation(self, orchestrator_with_session):
        """Test analysis loop cancellation"""
        orchestrator = orchestrator_with_session

        # Mock analysis cycle with longer delay
        with patch.object(orchestrator, '_execute_analysis_cycle', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = AnalysisCycleResult(
                cycle_id="test",
                session_id="test_session",
                timestamp=time.time(),
                analysis=ConversationAnalysis(),
                quality_gates=[],
                interventions_suggested=[],
                next_cycle_delay=10.0  # Long delay
            )

            # Start analysis loop
            loop_task = asyncio.create_task(orchestrator._run_analysis_loop("test_session"))

            # Cancel after short time
            await asyncio.sleep(0.1)
            loop_task.cancel()

            # Should be cancelled
            with pytest.raises(asyncio.CancelledError):
                await loop_task


class TestQualityGateHandling:
    """Test quality gate evaluation and intervention handling"""

    @pytest_asyncio.fixture(scope="function")
    async def orchestrator_with_mocks(self):
        """Fixture providing orchestrator with mocked components"""
        orchestrator = AutoModeOrchestrator()

        # Mock all dependencies
        orchestrator.session_manager = AsyncMock()
        orchestrator.analysis_engine = AsyncMock()
        orchestrator.quality_gate_evaluator = AsyncMock()
        orchestrator.sdk_client = AsyncMock()

        orchestrator.state = OrchestratorState.ACTIVE

        try:
            yield orchestrator
        finally:
            await orchestrator.shutdown()

    @pytest.mark.asyncio
    async def test_quality_gate_intervention_suggestions(self, orchestrator_with_mocks):
        """Test quality gate intervention suggestions"""
        orchestrator = orchestrator_with_mocks

        # Create mock session
        mock_session_state = SessionState(session_id="test_session", user_id="test_user")
        orchestrator.active_sessions["test_session"] = mock_session_state

        # Mock triggered quality gate
        from amplihack.auto_mode.quality_gates import QualityGateResult, GatePriority

        mock_gate_result = QualityGateResult(
            gate_id="test_gate",
            gate_name="Test Gate",
            triggered=True,
            confidence=0.8,
            priority=GatePriority.HIGH,
            suggested_actions=[
                {
                    'type': 'clarification_suggestion',
                    'title': 'Ask for clarification',
                    'description': 'User seems confused',
                    'confidence': 0.8
                }
            ]
        )

        # Test intervention callback
        intervention_called = False

        async def mock_intervention_callback(session_id, gate_result):
            nonlocal intervention_called
            intervention_called = True
            assert session_id == "test_session"
            assert gate_result.triggered is True

        orchestrator.on_intervention_suggested.append(mock_intervention_callback)

        # Test quality gate handling
        await orchestrator._handle_quality_gates("test_session", [mock_gate_result])

        assert intervention_called is True
        assert mock_session_state.total_interventions == 1


class TestMetricsAndMonitoring:
    """Test metrics collection and monitoring functionality"""

    @pytest.mark.asyncio
    async def test_metrics_initialization(self):
        """Test metrics are properly initialized"""
        orchestrator = AutoModeOrchestrator()

        metrics = orchestrator.get_metrics()

        assert 'total_sessions' in metrics
        assert 'total_analysis_cycles' in metrics
        assert 'total_interventions' in metrics
        assert 'average_quality_score' in metrics
        assert 'uptime_seconds' in metrics
        assert metrics['total_sessions'] == 0
        assert metrics['total_analysis_cycles'] == 0

    @pytest.mark.asyncio
    async def test_metrics_updates_during_operation(self):
        """Test metrics are updated during orchestrator operation"""
        orchestrator = AutoModeOrchestrator()

        # Simulate session creation
        orchestrator.metrics['total_sessions'] += 1
        orchestrator.metrics['total_analysis_cycles'] += 5
        orchestrator.metrics['total_interventions'] += 2

        # Add mock session for quality calculation
        mock_session_state = SessionState(
            session_id="test_session",
            user_id="test_user",
            current_quality_score=0.8
        )
        orchestrator.active_sessions["test_session"] = mock_session_state

        metrics = orchestrator.get_metrics()

        assert metrics['total_sessions'] == 1
        assert metrics['total_analysis_cycles'] == 5
        assert metrics['total_interventions'] == 2
        assert metrics['average_quality_score'] == 0.8
        assert metrics['active_sessions'] == 1


class TestShutdown:
    """Test orchestrator shutdown functionality"""

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful orchestrator shutdown"""
        orchestrator = AutoModeOrchestrator()

        # Mock components
        orchestrator.sdk_client = AsyncMock()
        orchestrator.session_manager = AsyncMock()

        # Create mock active session and task
        mock_session_state = SessionState(session_id="test_session", user_id="test_user")
        mock_task = AsyncMock()

        orchestrator.active_sessions["test_session"] = mock_session_state
        orchestrator.analysis_tasks["test_session"] = mock_task

        with patch.object(orchestrator, 'stop_session', new_callable=AsyncMock, return_value=True) as mock_stop:
            await orchestrator.shutdown()

            # Verify cleanup
            mock_stop.assert_called_once_with("test_session")
            orchestrator.sdk_client.shutdown.assert_called_once()
            orchestrator.session_manager.shutdown.assert_called_once()
            assert orchestrator.state == OrchestratorState.INACTIVE

    @pytest.mark.asyncio
    async def test_shutdown_with_exception(self):
        """Test shutdown handling with exceptions"""
        orchestrator = AutoModeOrchestrator()

        # Mock components with exception
        orchestrator.sdk_client = AsyncMock()
        orchestrator.sdk_client.shutdown.side_effect = Exception("Shutdown failed")
        orchestrator.session_manager = AsyncMock()

        # Should not raise exception
        await orchestrator.shutdown()

        assert orchestrator.state == OrchestratorState.ERROR


if __name__ == "__main__":
    pytest.main([__file__])