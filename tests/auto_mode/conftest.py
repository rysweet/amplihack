"""
Pytest configuration and shared fixtures for auto-mode tests.

Provides common test fixtures, configurations, and utilities
for all auto-mode test modules.
"""

import tempfile
import time
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from amplihack.auto_mode.analysis import (
    ConversationAnalysis,
    ConversationPattern,
    ConversationSignal,
    QualityDimension,
)
from amplihack.auto_mode.orchestrator import AutoModeOrchestrator, OrchestratorConfig
from amplihack.auto_mode.quality_gates import QualityGateEvaluator
from amplihack.auto_mode.sdk_integration import ClaudeAgentSDKClient
from amplihack.auto_mode.session import SessionManager, SessionState

# Note: pytest_plugins should be defined in root conftest.py, not here
# It's handled by the root conftest.py to avoid pytest deprecation warnings


# Set the default fixture loop scope to function to avoid deprecation warnings
def pytest_configure(config):
    """Configure pytest with asyncio settings and custom markers."""
    config.option.asyncio_default_fixture_loop_scope = "function"

    # Add custom test markers
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_sdk: mark test as requiring SDK connection")


@pytest.fixture
def temp_storage_dir():
    """Fixture providing temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def basic_orchestrator_config():
    """Fixture providing basic orchestrator configuration for testing."""
    return OrchestratorConfig(
        analysis_interval_seconds=0.1,  # Fast for testing
        max_analysis_cycles=5,  # Limited for testing
        min_quality_threshold=0.5,
        intervention_confidence_threshold=0.7,
        session_timeout_minutes=1,
        max_concurrent_sessions=3,
        background_analysis_enabled=True,
        detailed_logging=False,
    )


@pytest.fixture
def sample_conversation_context():
    """Fixture providing sample conversation context for testing."""
    return {
        "messages": [
            {"role": "user", "content": "Hello, I need help with my Python code"},
            {
                "role": "assistant",
                "content": "I'd be happy to help! What specific issue are you having?",
            },
            {"role": "user", "content": "I'm getting an error when I try to run my script"},
            {"role": "assistant", "content": "Can you share the error message you're seeing?"},
        ],
        "goals": [
            {"id": "goal1", "description": "Fix the Python script error", "status": "pending"},
            {"id": "goal2", "description": "Understand the root cause", "status": "pending"},
        ],
        "tool_usage": [
            {"tool_name": "bash", "timestamp": time.time(), "status": "success"},
            {"tool_name": "edit", "timestamp": time.time(), "status": "success"},
        ],
        "domain": "programming",
        "user_preferences": {"communication_style": "technical", "detail_level": "high"},
    }


@pytest.fixture
def sample_session_state():
    """Fixture providing sample session state for testing."""
    return SessionState(
        session_id="test_session_123",
        user_id="test_user",
        analysis_cycles=3,
        current_quality_score=0.75,
        total_interventions=1,
        conversation_context={"messages": [{"role": "user", "content": "Test message"}]},
        user_preferences={"communication_style": "casual", "detail_level": "medium"},
        learned_patterns=[
            {"pattern_type": "prefers_examples", "confidence": 0.8, "learned_at": time.time()}
        ],
    )


@pytest.fixture
def sample_conversation_analysis():
    """Fixture providing sample conversation analysis for testing."""
    return ConversationAnalysis(
        timestamp=time.time(),
        conversation_length=4,
        user_message_count=2,
        assistant_message_count=2,
        quality_score=0.75,
        quality_dimensions=[
            QualityDimension(
                dimension="clarity",
                score=0.8,
                evidence=["Clear communication"],
                improvement_suggestions=["Continue current approach"],
            ),
            QualityDimension(
                dimension="effectiveness",
                score=0.7,
                evidence=["Good progress toward goals"],
                improvement_suggestions=["Focus on completion"],
            ),
            QualityDimension(
                dimension="engagement",
                score=0.8,
                evidence=["Active user participation"],
                improvement_suggestions=["Maintain engagement level"],
            ),
        ],
        identified_patterns=[
            ConversationPattern(
                pattern_type="technical_focus",
                description="User is focused on technical problem-solving",
                frequency=2,
                confidence=0.85,
                impact_level="medium",
                examples=["Python code help", "Error debugging"],
            )
        ],
        detected_signals=[ConversationSignal.POSITIVE_ENGAGEMENT],
        improvement_opportunities=[
            {
                "area": "code_review",
                "description": "Consider suggesting code review best practices",
                "priority": "medium",
                "confidence": 0.7,
            }
        ],
        conversation_activity_level=1.2,
        user_expertise_assessment="intermediate",
        domain_context="programming",
        satisfaction_signals={
            "overall_sentiment": "positive",
            "confidence": 0.8,
            "indicators": ["positive_engagement"],
        },
    )


@pytest.fixture
def mock_orchestrator():
    """Fixture providing mocked orchestrator for testing."""
    orchestrator = Mock(spec=AutoModeOrchestrator)
    orchestrator.state.value = "active"
    orchestrator.active_sessions = {}
    orchestrator.analysis_tasks = {}
    orchestrator.config = OrchestratorConfig()

    # Mock async methods
    orchestrator.initialize = AsyncMock(return_value=True)
    orchestrator.start_session = AsyncMock(return_value="test_session_123")
    orchestrator.stop_session = AsyncMock(return_value=True)
    orchestrator.update_conversation = AsyncMock(return_value=True)
    orchestrator.get_session_status = AsyncMock(
        return_value={"session_id": "test_session_123", "status": "active"}
    )
    orchestrator.shutdown = AsyncMock()

    # Mock metrics
    orchestrator.get_metrics = Mock(
        return_value={
            "total_sessions": 1,
            "total_analysis_cycles": 5,
            "total_interventions": 1,
            "average_quality_score": 0.75,
            "uptime_seconds": 300,
            "active_sessions": 1,
        }
    )

    return orchestrator


@pytest_asyncio.fixture
async def session_manager(temp_storage_dir):
    """Fixture providing initialized session manager."""
    manager = SessionManager(temp_storage_dir)
    await manager.initialize()
    try:
        yield manager
    finally:
        await manager.shutdown()


@pytest.fixture
def quality_gate_evaluator():
    """Fixture providing quality gate evaluator."""
    return QualityGateEvaluator()


@pytest_asyncio.fixture
async def sdk_client():
    """Fixture providing initialized SDK client."""
    client = ClaudeAgentSDKClient()
    await client.initialize()
    try:
        yield client
    finally:
        await client.shutdown()


@pytest.fixture
def mock_command_context():
    """Fixture providing command execution context."""
    return {
        "user_id": "test_user",
        "session_id": "current_session_123",
        "conversation_context": {"messages": [{"role": "user", "content": "Hello"}]},
        "timestamp": time.time(),
    }


# Test utilities


def create_test_session_state(session_id="test_session", user_id="test_user", **kwargs):
    """Utility function to create test session state with custom attributes."""
    defaults = {
        "session_id": session_id,
        "user_id": user_id,
        "analysis_cycles": 0,
        "current_quality_score": 0.0,
        "total_interventions": 0,
    }
    defaults.update(kwargs)
    return SessionState(**defaults)


def create_test_analysis(quality_score=0.75, signals=None, patterns=None, **kwargs):
    """Utility function to create test conversation analysis."""
    defaults = {
        "quality_score": quality_score,
        "detected_signals": signals or [],
        "identified_patterns": patterns or [],
        "conversation_length": 4,
        "user_message_count": 2,
        "assistant_message_count": 2,
    }
    defaults.update(kwargs)
    return ConversationAnalysis(**defaults)


def create_mock_quality_gate_result(gate_id="test_gate", triggered=True, confidence=0.8):
    """Utility function to create mock quality gate result."""
    from amplihack.auto_mode.quality_gates import GatePriority, QualityGateResult

    return QualityGateResult(
        gate_id=gate_id,
        gate_name=f"Test Gate {gate_id}",
        triggered=triggered,
        confidence=confidence,
        priority=GatePriority.MEDIUM,
        suggested_actions=[
            {
                "type": "test_action",
                "title": "Test Action",
                "description": "Test action description",
                "confidence": confidence,
            }
        ]
        if triggered
        else [],
    )


# Pytest markers


# pytest_configure function defined earlier with both asyncio and marker configuration


# Test collection customization


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test characteristics."""
    for item in items:
        # Mark integration tests
        if "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)

        # Mark slow tests
        if any(keyword in item.name.lower() for keyword in ["performance", "load", "stress"]):
            item.add_marker(pytest.mark.slow)

        # Mark SDK tests
        if "sdk" in item.nodeid.lower():
            item.add_marker(pytest.mark.requires_sdk)


# Custom assertion helpers


def assert_valid_session_state(session_state):
    """Assert that session state is valid."""
    assert session_state.session_id is not None
    assert session_state.user_id is not None
    assert session_state.created_at > 0
    assert session_state.last_updated > 0
    assert session_state.analysis_cycles >= 0
    assert 0.0 <= session_state.current_quality_score <= 1.0
    assert session_state.total_interventions >= 0


def assert_valid_analysis(analysis):
    """Assert that conversation analysis is valid."""
    assert isinstance(analysis, ConversationAnalysis)
    assert 0.0 <= analysis.quality_score <= 1.0
    assert analysis.conversation_length >= 0
    assert analysis.user_message_count >= 0
    assert analysis.assistant_message_count >= 0
    assert analysis.timestamp > 0
    assert analysis.conversation_activity_level > 0


def assert_valid_command_result(result):
    """Assert that command result is valid."""
    from amplihack.auto_mode.command_handler import CommandResult

    assert isinstance(result, CommandResult)
    assert isinstance(result.success, bool)
    assert isinstance(result.message, str)

    if not result.success:
        assert result.error_code is not None
