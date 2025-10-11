"""
Test suite for Real Claude Agent SDK Integration.

Tests the ACTUAL implementation in amplihack/sdk/ that uses
the real claude-agent-sdk package, NOT mock implementations.
"""

import pytest
import pytest_asyncio

from amplihack.sdk import (
    AnalysisConfig,
    AnalysisRequest,
    AnalysisType,
    AutoModeConfig,
    AutoModeOrchestrator,
    ConversationAnalysisEngine,
    SDKSessionManager,
)


class TestAnalysisEngine:
    """Test ConversationAnalysisEngine with real Claude SDK"""

    @pytest_asyncio.fixture
    async def analysis_engine(self):
        """Create analysis engine instance"""
        config = AnalysisConfig(enable_caching=False)
        engine = ConversationAnalysisEngine(config)
        return engine

    @pytest.mark.asyncio
    async def test_engine_initialization(self, analysis_engine):
        """Test that analysis engine initializes correctly"""
        assert analysis_engine is not None
        assert analysis_engine.config is not None
        assert isinstance(analysis_engine.analysis_cache, dict)
        assert isinstance(analysis_engine.analysis_history, list)

    @pytest.mark.asyncio
    async def test_build_analysis_prompt(self, analysis_engine):
        """Test that analysis prompts are built correctly"""
        from datetime import datetime

        request = AnalysisRequest(
            id="test-123",
            session_id="session-456",
            analysis_type=AnalysisType.PROGRESS_EVALUATION,
            claude_output="I've created a hello world function.",
            user_objective="Create a Python hello world function",
            context={},
            timestamp=datetime.now(),
        )

        prompt = analysis_engine._build_analysis_prompt(request)

        assert "Create a Python hello world function" in prompt
        assert "I've created a hello world function" in prompt
        assert "PROGRESS_EVALUATION" in prompt or "progress_evaluation" in prompt
        assert "JSON" in prompt

    def test_sanitize_input(self, analysis_engine):
        """Test input sanitization"""
        dangerous = "<script>alert('xss')</script>"
        safe = analysis_engine._sanitize_input(dangerous)

        assert "<script>" not in safe
        assert "&lt;script&gt;" in safe

    def test_truncate_output(self, analysis_engine):
        """Test output truncation"""
        long_output = "x" * 10000
        truncated = analysis_engine._truncate_output(long_output)

        assert len(truncated) <= analysis_engine.config.max_analysis_length + 100
        assert "truncated" in truncated.lower()


class TestSessionManager:
    """Test SDKSessionManager"""

    @pytest_asyncio.fixture
    async def session_manager(self):
        """Create session manager instance"""
        manager = SDKSessionManager()
        return manager

    @pytest.mark.asyncio
    async def test_session_creation(self, session_manager):
        """Test session creation"""
        session_id = await session_manager.create_session(
            user_objective="Test objective", working_dir="/tmp/test"
        )

        assert session_id is not None
        assert len(session_id) > 0
        assert session_id in session_manager.sessions

    @pytest.mark.asyncio
    async def test_get_session(self, session_manager):
        """Test retrieving session"""
        session_id = await session_manager.create_session(
            user_objective="Test", working_dir="/tmp/test"
        )

        session = await session_manager.get_session(session_id)

        assert session is not None
        assert session.session_id == session_id
        assert session.context["user_objective"] == "Test"
        assert session.context["working_dir"] == "/tmp/test"

    @pytest.mark.asyncio
    async def test_update_session_activity(self, session_manager):
        """Test updating session activity"""
        session_id = await session_manager.create_session(
            user_objective="Test", working_dir="/tmp/test"
        )

        session = await session_manager.get_session(session_id)
        original_activity = session.last_activity

        # Small delay to ensure timestamp differs
        import asyncio

        await asyncio.sleep(0.1)

        await session_manager.update_session_activity(session_id)

        updated_session = await session_manager.get_session(session_id)
        assert updated_session.last_activity > original_activity

    @pytest.mark.asyncio
    async def test_close_session(self, session_manager):
        """Test closing session"""
        session_id = await session_manager.create_session(
            user_objective="Test", working_dir="/tmp/test"
        )

        assert session_id in session_manager.sessions

        await session_manager.close_session(session_id)

        session = await session_manager.get_session(session_id)
        assert session.status == "closed"


class TestAutoModeOrchestrator:
    """Test AutoModeOrchestrator end-to-end"""

    @pytest_asyncio.fixture
    async def orchestrator(self):
        """Create orchestrator instance"""
        config = AutoModeConfig(max_iterations=3, persistence_enabled=False)
        orch = AutoModeOrchestrator(config)
        return orch

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes correctly"""
        assert orchestrator is not None
        assert orchestrator.config is not None
        assert orchestrator.session_manager is not None
        assert orchestrator.analysis_engine is not None

    @pytest.mark.asyncio
    async def test_start_session(self, orchestrator):
        """Test starting auto-mode session"""
        session_id = await orchestrator.start_auto_mode_session(
            user_objective="Test objective", working_directory="/tmp/test"
        )

        assert session_id is not None
        assert len(session_id) > 0

    @pytest.mark.asyncio
    async def test_get_current_state(self, orchestrator):
        """Test getting current state"""
        session_id = await orchestrator.start_auto_mode_session(
            user_objective="Test", working_directory="/tmp/test"
        )

        state = orchestrator.get_current_state()

        assert state is not None
        assert state["session_id"] == session_id
        assert state["state"] in [
            "initializing",
            "active",
            "paused",
            "error",
            "completed",
            "stopped",
        ]
        assert "iteration" in state
        assert "error_count" in state

    @pytest.mark.asyncio
    async def test_get_progress_summary(self, orchestrator):
        """Test getting progress summary"""
        await orchestrator.start_auto_mode_session(
            user_objective="Test", working_directory="/tmp/test"
        )

        summary = orchestrator.get_progress_summary()

        assert summary is not None
        assert "milestones" in summary
        assert "progress_percentage" in summary

    @pytest.mark.asyncio
    async def test_stop_auto_mode(self, orchestrator):
        """Test stopping auto-mode"""
        await orchestrator.start_auto_mode_session(
            user_objective="Test", working_directory="/tmp/test"
        )

        await orchestrator.stop_auto_mode()

        # Verify session is closed
        assert orchestrator.active_session_id is None


class TestIntegration:
    """Integration tests for complete workflow"""

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete auto-mode workflow"""
        # Create orchestrator
        config = AutoModeConfig(max_iterations=2, persistence_enabled=False)
        orchestrator = AutoModeOrchestrator(config)

        # Start session
        session_id = await orchestrator.start_auto_mode_session(
            user_objective="Create a simple test", working_directory="/tmp/test"
        )

        assert session_id is not None

        # Get state
        state = orchestrator.get_current_state()
        assert state["session_id"] == session_id

        # Stop
        await orchestrator.stop_auto_mode()
        assert orchestrator.active_session_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
