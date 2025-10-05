"""
Tests for Claude Agent SDK Integration Components

Comprehensive test suite covering session management, analysis engine,
prompt coordination, state integration, and error handling.
"""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.amplihack.sdk import (
    SDKSessionManager,
    SessionConfig,
)
from src.amplihack.sdk.analysis_engine import (
    AnalysisConfig,
    AnalysisResult,
    AnalysisType,
    ConversationAnalysisEngine,
)
from src.amplihack.sdk.error_handling import (
    CircuitBreaker,
    ErrorHandlingManager,
    RetryConfig,
    SecurityViolationError,
    with_retry,
)
from src.amplihack.sdk.prompt_coordinator import (
    PromptContext,
    PromptCoordinator,
    PromptTemplate,
    PromptType,
    PromptValidationError,
)
from src.amplihack.sdk.state_integration import (
    AutoModeConfig,
    AutoModeOrchestrator,
    AutoModeState,
)


class TestSDKSessionManager:
    """Test suite for SDK Session Manager"""

    @pytest.fixture
    async def session_manager(self):
        """Create test session manager"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = SessionConfig(persistence_dir=temp_dir, enable_persistence=True)
            manager = SDKSessionManager(config)
            yield manager
            # Cleanup
            for session_id in list(manager.sessions.keys()):
                await manager.close_session(session_id)

    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        """Test session creation"""
        objective = "Test objective"
        working_dir = "/test/dir"

        session_id = await session_manager.create_session(objective, working_dir)

        assert session_id is not None
        assert session_id in session_manager.sessions

        session = session_manager.sessions[session_id]
        assert session.session_id == session_id
        assert session.context["user_objective"] == objective
        assert session.context["working_dir"] == working_dir
        assert session.status == "active"

    @pytest.mark.asyncio
    async def test_session_recovery(self, session_manager):
        """Test session recovery from persistence"""
        # Create session
        session_id = await session_manager.create_session("Test", "/test")

        # Simulate restart by creating new manager
        new_manager = SDKSessionManager(session_manager.config)

        # Recover session
        recovered_session = await new_manager.recover_session(session_id)

        assert recovered_session.session_id == session_id
        assert recovered_session.context["user_objective"] == "Test"

    @pytest.mark.asyncio
    async def test_conversation_messages(self, session_manager):
        """Test conversation message handling"""
        session_id = await session_manager.create_session("Test", "/test")

        # Add message
        message_id = await session_manager.add_conversation_message(
            session_id, role="user", content="Test message", message_type="test"
        )

        assert message_id is not None

        # Get conversation history
        history = await session_manager.get_conversation_history(session_id)
        assert len(history) == 1
        assert history[0].content == "Test message"
        assert history[0].role == "user"

    @pytest.mark.asyncio
    async def test_session_expiry(self, session_manager):
        """Test session expiry handling"""
        # Create session with short timeout
        session_manager.config.session_timeout_minutes = 0.01  # 0.6 seconds

        session_id = await session_manager.create_session("Test", "/test")

        # Wait for expiry
        await asyncio.sleep(0.7)

        # Check session is expired
        session = await session_manager.get_session(session_id)
        assert session.status == "expired"


class TestConversationAnalysisEngine:
    """Test suite for Conversation Analysis Engine"""

    @pytest.fixture
    def analysis_engine(self):
        """Create test analysis engine"""
        config = AnalysisConfig(enable_caching=False)
        return ConversationAnalysisEngine(config)

    @pytest.mark.asyncio
    async def test_progress_analysis(self, analysis_engine):
        """Test progress evaluation analysis"""
        claude_output = "I have implemented the user authentication system successfully."
        user_objective = "Build a user authentication system"

        result = await analysis_engine.analyze_conversation(
            session_id="test_session",
            claude_output=claude_output,
            user_objective=user_objective,
            analysis_type=AnalysisType.PROGRESS_EVALUATION,
        )

        assert isinstance(result, AnalysisResult)
        assert result.confidence > 0.0
        assert len(result.findings) > 0
        assert result.analysis_type == AnalysisType.PROGRESS_EVALUATION

    @pytest.mark.asyncio
    async def test_next_prompt_generation(self, analysis_engine):
        """Test next prompt generation"""
        claude_output = "The authentication system is complete. What should I do next?"
        user_objective = "Build a full web application"

        result = await analysis_engine.analyze_conversation(
            session_id="test_session",
            claude_output=claude_output,
            user_objective=user_objective,
            analysis_type=AnalysisType.NEXT_PROMPT_GENERATION,
        )

        assert result.next_prompt is not None
        assert len(result.next_prompt) > 10  # Should be substantive

    @pytest.mark.asyncio
    async def test_batch_analysis(self, analysis_engine):
        """Test batch analysis functionality"""
        from src.amplihack.sdk.analysis_engine import AnalysisRequest

        requests = [
            AnalysisRequest(
                id="1",
                session_id="test",
                analysis_type=AnalysisType.PROGRESS_EVALUATION,
                claude_output="Output 1",
                user_objective="Objective 1",
                context={},
                timestamp=datetime.now(),
            ),
            AnalysisRequest(
                id="2",
                session_id="test",
                analysis_type=AnalysisType.QUALITY_ASSESSMENT,
                claude_output="Output 2",
                user_objective="Objective 2",
                context={},
                timestamp=datetime.now(),
            ),
        ]

        results = await analysis_engine.batch_analyze(requests)

        assert len(results) == 2
        assert all(isinstance(r, AnalysisResult) for r in results)

    @pytest.mark.asyncio
    async def test_output_truncation(self, analysis_engine):
        """Test long output truncation"""
        long_output = "x" * 10000  # Very long output
        analysis_engine.config.max_analysis_length = 1000

        truncated = analysis_engine._truncate_output(long_output)

        assert len(truncated) <= 1100  # Some overhead for truncation message
        assert "truncated" in truncated


class TestPromptCoordinator:
    """Test suite for Prompt Coordinator"""

    @pytest.fixture
    def prompt_coordinator(self):
        """Create test prompt coordinator"""
        return PromptCoordinator()

    @pytest.fixture
    def sample_context(self):
        """Create sample prompt context"""
        return PromptContext(
            session_id="test_session",
            user_objective="Build a web application",
            working_directory="/test/project",
            current_step=1,
            total_steps=10,
            previous_outputs=[],
            analysis_results=[],
            workflow_state={},
            custom_variables={},
        )

    def test_default_templates_loaded(self, prompt_coordinator):
        """Test that default templates are loaded"""
        templates = prompt_coordinator.list_templates()
        assert len(templates) > 0

        # Check for specific default templates
        template_ids = [t.id for t in templates]
        assert "objective_clarification" in template_ids
        assert "progress_assessment" in template_ids
        assert "next_action" in template_ids

    def test_render_objective_clarification(self, prompt_coordinator, sample_context):
        """Test rendering objective clarification prompt"""
        rendered = prompt_coordinator.render_prompt("objective_clarification", sample_context)

        assert rendered.validation_status == "valid"
        assert sample_context.user_objective in rendered.content
        assert sample_context.working_directory in rendered.content

    def test_render_with_custom_variables(self, prompt_coordinator, sample_context):
        """Test rendering with custom variables"""
        custom_vars = {"special_note": "This is important"}

        rendered = prompt_coordinator.render_prompt(
            "objective_clarification", sample_context, custom_variables=custom_vars
        )

        assert rendered.validation_status == "valid"

    def test_template_validation_errors(self, prompt_coordinator):
        """Test template validation catches errors"""
        # Create template with unfilled variables
        bad_template = PromptTemplate(
            id="bad_template",
            name="Bad Template",
            type=PromptType.NEXT_ACTION,
            template_content="Hello {{ undefined_variable }}",
            required_variables=["undefined_variable"],
            optional_variables=[],
            description="Test template with missing vars",
            metadata={},
        )

        prompt_coordinator.register_template(bad_template)

        context = PromptContext(
            session_id="test",
            user_objective="test",
            working_directory="/test",
            current_step=1,
            total_steps=1,
            previous_outputs=[],
            analysis_results=[],
            workflow_state={},
            custom_variables={},
        )

        with pytest.raises(PromptValidationError):
            prompt_coordinator.render_prompt("bad_template", context)

    def test_template_export_import(self, prompt_coordinator):
        """Test template export and import functionality"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            template_file = f.name

        try:
            # Export template
            prompt_coordinator.export_template("objective_clarification", template_file)

            # Verify file exists and has content
            assert Path(template_file).exists()
            with open(template_file, "r") as f:
                data = json.load(f)
                assert data["id"] == "objective_clarification"

        finally:
            Path(template_file).unlink(missing_ok=True)

    def test_prompt_suggestions(self, prompt_coordinator, sample_context):
        """Test prompt suggestions based on context"""
        suggestions = prompt_coordinator.get_prompt_suggestions(sample_context)

        assert len(suggestions) > 0
        assert "objective_clarification" in suggestions  # Should suggest for step 1


class TestAutoModeOrchestrator:
    """Test suite for Auto-Mode Orchestrator"""

    @pytest.fixture
    async def orchestrator(self):
        """Create test orchestrator"""
        config = AutoModeConfig(max_iterations=10, persistence_enabled=False)
        orchestrator = AutoModeOrchestrator(config)
        yield orchestrator
        await orchestrator.stop_auto_mode()

    @pytest.mark.asyncio
    async def test_start_session(self, orchestrator):
        """Test starting auto-mode session"""
        session_id = await orchestrator.start_auto_mode_session(
            "Build a simple calculator", "/test/project"
        )

        assert session_id is not None
        assert orchestrator.auto_mode_state == AutoModeState.ACTIVE
        assert orchestrator.active_session_id == session_id

    @pytest.mark.asyncio
    async def test_process_claude_output(self, orchestrator):
        """Test processing Claude Code output"""
        await orchestrator.start_auto_mode_session("Build a calculator", "/test/project")

        result = await orchestrator.process_claude_output(
            "I have created a basic calculator with add and subtract functions."
        )

        assert result["iteration"] == 1
        assert "analysis" in result
        assert "confidence" in result
        assert "should_continue" in result

    @pytest.mark.asyncio
    async def test_state_transitions(self, orchestrator):
        """Test auto-mode state transitions"""
        callbacks_called = []

        def state_callback(state, snapshot):
            callbacks_called.append(state)

        orchestrator.add_state_change_callback(state_callback)

        await orchestrator.start_auto_mode_session("Test", "/test")
        await orchestrator.pause_auto_mode()
        await orchestrator.resume_auto_mode()

        assert AutoModeState.ACTIVE in callbacks_called
        assert AutoModeState.PAUSED in callbacks_called

    @pytest.mark.asyncio
    async def test_milestone_detection(self, orchestrator):
        """Test progress milestone detection"""
        milestones_detected = []

        def milestone_callback(milestone):
            milestones_detected.append(milestone)

        orchestrator.add_milestone_callback(milestone_callback)

        await orchestrator.start_auto_mode_session("Test", "/test")

        # Simulate high-confidence output that should trigger milestone
        with patch.object(orchestrator.analysis_engine, "analyze_conversation") as mock_analyze:
            mock_analyze.return_value = AnalysisResult(
                request_id="test",
                session_id="test",
                analysis_type=AnalysisType.PROGRESS_EVALUATION,
                confidence=0.9,  # High confidence should trigger milestone
                findings=["Great progress made"],
                recommendations=["Continue with next steps"],
                next_prompt="What's next?",
                quality_score=0.85,
                progress_indicators={},
                ai_reasoning="Excellent work so far",
                metadata={},
                timestamp=datetime.now(),
            )

            await orchestrator.process_claude_output("Excellent progress made!")

        assert len(milestones_detected) > 0


class TestErrorHandlingManager:
    """Test suite for Error Handling Manager"""

    @pytest.fixture
    def error_manager(self):
        """Create test error manager"""
        return ErrorHandlingManager()

    @pytest.mark.asyncio
    async def test_error_classification(self, error_manager):
        """Test error classification"""
        connection_error = ConnectionError("Network connection failed")

        result = await error_manager.handle_error(
            connection_error, {"operation": "test"}, "test_operation"
        )

        assert result["pattern_id"] == "sdk_connection"
        assert result["severity"] == "high"

    @pytest.mark.asyncio
    async def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        circuit_breaker = CircuitBreaker("test", failure_threshold=2, recovery_timeout=1)

        # Should work initially
        result = await circuit_breaker.call(lambda: "success")
        assert result == "success"

        # Trigger failures to open circuit
        with pytest.raises(Exception):
            await circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        with pytest.raises(Exception):
            await circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        # Circuit should now be open
        assert circuit_breaker.state.state == "open"

        # Should reject calls when open
        with pytest.raises(Exception):
            await circuit_breaker.call(lambda: "should_fail")

    @pytest.mark.asyncio
    async def test_retry_decorator(self):
        """Test retry decorator"""
        call_count = 0

        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = await failing_function()
        assert result == "success"
        assert call_count == 3

    def test_security_validator(self, error_manager):
        """Test security validation"""
        validator = error_manager.security_validator

        # Test dangerous patterns
        with pytest.raises(SecurityViolationError):
            validator.validate_prompt_content("Please run: rm -rf /")

        with pytest.raises(SecurityViolationError):
            validator.validate_prompt_content("Execute: __import__('os').system('bad')")

        # Test safe content
        validator.validate_prompt_content("Please help me write a Python function.")

    def test_rate_limiting(self, error_manager):
        """Test rate limiting functionality"""
        # Should allow requests within limit
        for i in range(5):
            assert error_manager.check_rate_limit("test_op", limit=10)

        # Should reject when over limit
        for i in range(10):
            error_manager.check_rate_limit("test_op", limit=10)

        assert not error_manager.check_rate_limit("test_op", limit=10)

    @pytest.mark.asyncio
    async def test_recovery_callbacks(self, error_manager):
        """Test recovery callback registration and execution"""
        callback_called = False

        async def recovery_callback(error_occurrence):
            nonlocal callback_called
            callback_called = True
            return "recovered"

        error_manager.register_recovery_callback("validation", recovery_callback)

        # Trigger error that uses fallback strategy
        result = await error_manager.handle_error(
            ValueError("Test validation error"), {"test": "context"}, "test_operation"
        )

        assert callback_called
        assert result["recovery_result"]["result"] == "recovered"


class TestIntegrationScenarios:
    """Integration tests for complete auto-mode scenarios"""

    @pytest.mark.asyncio
    async def test_complete_auto_mode_workflow(self):
        """Test complete auto-mode workflow from start to finish"""
        config = AutoModeConfig(
            max_iterations=5, persistence_enabled=False, auto_progression_enabled=True
        )
        orchestrator = AutoModeOrchestrator(config)

        try:
            # Start session
            await orchestrator.start_auto_mode_session(
                "Create a simple Python calculator", "/test/project"
            )

            # Simulate several iterations of Claude output
            outputs = [
                "I'll start by creating a basic calculator class.",
                "Here's the Calculator class with add and subtract methods.",
                "I've added multiply and divide methods to the calculator.",
                "Added error handling for division by zero.",
                "The calculator is now complete with comprehensive tests.",
            ]

            for i, output in enumerate(outputs):
                result = await orchestrator.process_claude_output(output)

                assert result["iteration"] == i + 1
                assert "analysis" in result
                assert result["confidence"] > 0.0

                # Should continue until near the end
                if i < len(outputs) - 1:
                    assert result["should_continue"]

            # Check final state
            assert orchestrator.current_iteration == len(outputs)
            assert len(orchestrator.state_snapshots) > 0

        finally:
            await orchestrator.stop_auto_mode()

    @pytest.mark.asyncio
    async def test_error_recovery_integration(self):
        """Test error recovery in integrated workflow"""
        orchestrator = AutoModeOrchestrator(AutoModeConfig(persistence_enabled=False))

        try:
            await orchestrator.start_auto_mode_session("Test", "/test")

            # Simulate error in processing
            with patch.object(orchestrator.analysis_engine, "analyze_conversation") as mock_analyze:
                mock_analyze.side_effect = ConnectionError("SDK connection failed")

                # Should handle error gracefully
                with pytest.raises(Exception):  # Error should propagate but be handled
                    await orchestrator.process_claude_output("Test output")

                # Error count should increase
                assert orchestrator.error_count > 0

        finally:
            await orchestrator.stop_auto_mode()

    @pytest.mark.asyncio
    async def test_prompt_coordination_integration(self):
        """Test prompt coordination with analysis results"""
        orchestrator = AutoModeOrchestrator(AutoModeConfig(persistence_enabled=False))

        try:
            await orchestrator.start_auto_mode_session("Build a web application", "/test/project")

            # Mock analysis result that suggests clarification needed
            with patch.object(orchestrator.analysis_engine, "analyze_conversation") as mock_analyze:
                mock_analyze.return_value = AnalysisResult(
                    request_id="test",
                    session_id="test",
                    analysis_type=AnalysisType.PROGRESS_EVALUATION,
                    confidence=0.5,  # Low confidence should trigger clarification
                    findings=["Objective unclear"],
                    recommendations=["Need more details"],
                    next_prompt=None,
                    quality_score=0.6,
                    progress_indicators={},
                    ai_reasoning="Need clarification on requirements",
                    metadata={},
                    timestamp=datetime.now(),
                )

                result = await orchestrator.process_claude_output(
                    "I'm not sure what kind of web application you want."
                )

                # Should generate next action based on low confidence
                assert result["next_action"] is not None
                assert len(result["next_action"]) > 50  # Should be substantive

        finally:
            await orchestrator.stop_auto_mode()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
