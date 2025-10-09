"""
Test suite for ClaudeAgentSDKClient.

Tests Claude Agent SDK integration including:
- Connection management and authentication
- Session creation and management
- Conversation context updates
- Analysis requests and synthesis
- Error handling and recovery
"""

import time
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from amplihack.auto_mode.sdk_integration import (
    ClaudeAgentSDKClient,
    SDKConnectionState,
    SDKMessage,
    SDKSession,
)


class TestSDKDataModels:
    """Test SDK data models and structures"""

    def test_sdk_message_creation(self):
        """Test SDKMessage creation and defaults"""
        message = SDKMessage(message_type="test_message", content={"test": "data"})

        assert message.message_type == "test_message"
        assert message.content == {"test": "data"}
        assert message.message_id is not None
        assert message.timestamp > 0
        assert message.response_to is None

    def test_sdk_session_creation(self):
        """Test SDKSession creation and defaults"""
        session = SDKSession(
            session_id="auto_session_123",
            claude_session_id="claude_session_456",
            user_id="test_user",
        )

        assert session.session_id == "auto_session_123"
        assert session.claude_session_id == "claude_session_456"
        assert session.user_id == "test_user"
        assert session.created_at > 0
        assert session.last_activity > 0
        assert len(session.conversation_context) == 0


class TestSDKClientInitialization:
    """Test SDK client initialization and connection"""

    @pytest.fixture
    def sdk_client(self):
        return ClaudeAgentSDKClient()

    def test_client_creation(self, sdk_client):
        """Test SDK client creation with defaults"""
        assert sdk_client.connection_state == SDKConnectionState.DISCONNECTED
        assert sdk_client.api_key is None
        assert sdk_client.base_url == "https://api.anthropic.com"
        assert len(sdk_client.active_sessions) == 0

    @pytest.mark.asyncio
    async def test_initialization_success_with_api_key(self, sdk_client):
        """Test successful initialization with API key"""
        with patch.dict(
            "os.environ",
            {"CLAUDE_API_KEY": "test_api_key"},  # pragma: allowlist secret
        ):
            success = await sdk_client.initialize()

            assert success is True
            assert sdk_client.connection_state == SDKConnectionState.AUTHENTICATED
            assert sdk_client.api_key == "test_api_key"  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_initialization_success_without_api_key(self, sdk_client):
        """Test initialization without API key (mock mode)"""
        with patch.dict("os.environ", {}, clear=True):
            success = await sdk_client.initialize()

            assert success is True
            assert sdk_client.connection_state == SDKConnectionState.AUTHENTICATED
            assert sdk_client.api_key == "mock_api_key"  # pragma: allowlist secret

    @pytest.mark.asyncio
    async def test_initialization_with_custom_parameters(self, sdk_client):
        """Test initialization with custom timeout and retry parameters"""
        success = await sdk_client.initialize(timeout=5.0, retry_attempts=2)

        assert success is True
        assert sdk_client.connection_timeout == 5.0
        assert sdk_client.retry_attempts == 2

    @pytest.mark.asyncio
    async def test_connection_establishment(self, sdk_client):
        """Test connection establishment process"""
        with patch.object(sdk_client, "_authenticate", new_callable=AsyncMock, return_value=True):
            success = await sdk_client._establish_connection()

            assert success is True
            assert sdk_client.connection_state == SDKConnectionState.AUTHENTICATED
            assert sdk_client.connection_attempts > 0

    @pytest.mark.asyncio
    async def test_authentication_success(self, sdk_client):
        """Test successful authentication"""
        sdk_client.api_key = "test_key"  # pragma: allowlist secret

        success = await sdk_client._authenticate()

        assert success is True

    @pytest.mark.asyncio
    async def test_authentication_failure(self, sdk_client):
        """Test authentication failure handling"""
        sdk_client.api_key = "invalid_key"  # pragma: allowlist secret

        # Mock authentication failure
        with patch.object(sdk_client, "_authenticate", new_callable=AsyncMock, return_value=False):
            success = await sdk_client._establish_connection()

            assert success is False
            assert sdk_client.connection_state == SDKConnectionState.ERROR


class TestSessionManagement:
    """Test SDK session management"""

    @pytest_asyncio.fixture(scope="function")
    async def authenticated_client(self):
        """Fixture providing authenticated SDK client"""
        client = ClaudeAgentSDKClient()
        await client.initialize()
        try:
            yield client
        finally:
            await client.shutdown()

    @pytest.mark.asyncio
    async def test_create_persistent_session_success(self, authenticated_client):
        """Test successful persistent session creation"""
        client = authenticated_client

        session = await client.create_persistent_session(
            auto_mode_session_id="auto_session_123",
            user_id="test_user",
            initial_context={"messages": [], "goals": []},
        )

        assert session is not None
        assert session.session_id == "auto_session_123"
        assert session.user_id == "test_user"
        assert session.claude_session_id.startswith("claude_session_")
        assert "auto_session_123" in client.active_sessions

    @pytest.mark.asyncio
    async def test_create_session_not_authenticated(self):
        """Test session creation when not authenticated"""
        client = ClaudeAgentSDKClient()
        # Don't initialize - stays in DISCONNECTED state

        session = await client.create_persistent_session(
            auto_mode_session_id="auto_session_123", user_id="test_user", initial_context={}
        )

        assert session is None

    @pytest.mark.asyncio
    async def test_update_conversation_context_success(self, authenticated_client):
        """Test successful conversation context update"""
        client = authenticated_client

        # Create session first
        session = await client.create_persistent_session(
            auto_mode_session_id="auto_session_123", user_id="test_user", initial_context={}
        )

        # Update conversation context
        conversation_update = {
            "new_messages": [{"role": "user", "content": "Hello"}],
            "goals": [{"id": "goal1", "description": "Test goal"}],
        }

        success = await client.update_conversation_context("auto_session_123", conversation_update)

        assert success is True
        assert "new_messages" in session.conversation_context
        assert session.last_activity > session.created_at

    @pytest.mark.asyncio
    async def test_update_conversation_nonexistent_session(self, authenticated_client):
        """Test updating conversation for non-existent session"""
        client = authenticated_client

        success = await client.update_conversation_context("nonexistent", {"test": "data"})

        assert success is False

    @pytest.mark.asyncio
    async def test_close_session_success(self, authenticated_client):
        """Test successful session closure"""
        client = authenticated_client

        # Create session first
        await client.create_persistent_session(
            auto_mode_session_id="auto_session_123", user_id="test_user", initial_context={}
        )

        assert "auto_session_123" in client.active_sessions

        # Close session
        success = await client.close_session("auto_session_123")

        assert success is True
        assert "auto_session_123" not in client.active_sessions

    @pytest.mark.asyncio
    async def test_close_nonexistent_session(self, authenticated_client):
        """Test closing non-existent session"""
        client = authenticated_client

        success = await client.close_session("nonexistent")

        assert success is False


class TestAnalysisAndSynthesis:
    """Test analysis and synthesis requests"""

    @pytest_asyncio.fixture(scope="function")
    async def client_with_session(self):
        """Fixture providing client with active session"""
        client = ClaudeAgentSDKClient()
        await client.initialize()

        session = await client.create_persistent_session(
            auto_mode_session_id="auto_session_123",
            user_id="test_user",
            initial_context={"messages": []},
        )

        try:
            yield client, session
        finally:
            await client.shutdown()

    @pytest.mark.asyncio
    async def test_request_analysis_success(self, client_with_session):
        """Test successful analysis request"""
        client, session = client_with_session

        analysis_results = await client.request_analysis("auto_session_123", "comprehensive")

        assert analysis_results is not None
        assert "session_id" in analysis_results
        assert "quality_assessment" in analysis_results
        assert "detected_patterns" in analysis_results
        assert "improvement_opportunities" in analysis_results

        # Check that session analysis state was updated
        assert session.analysis_state["analysis_count"] == 1
        assert "last_analysis" in session.analysis_state

    @pytest.mark.asyncio
    async def test_request_analysis_nonexistent_session(self, client_with_session):
        """Test analysis request for non-existent session"""
        client, _ = client_with_session

        analysis_results = await client.request_analysis("nonexistent", "comprehensive")

        assert analysis_results is None

    @pytest.mark.asyncio
    async def test_synthesize_conversation_success(self, client_with_session):
        """Test successful conversation synthesis"""
        client, session = client_with_session

        synthesis_params = {"type": "summary", "scope": "full_conversation", "format": "structured"}

        synthesis_results = await client.synthesize_conversation(
            "auto_session_123", synthesis_params
        )

        assert synthesis_results is not None
        assert "summary" in synthesis_results
        assert "key_insights" in synthesis_results
        assert "recommendations" in synthesis_results
        assert "quality_metrics" in synthesis_results

    @pytest.mark.asyncio
    async def test_synthesize_conversation_nonexistent_session(self, client_with_session):
        """Test synthesis request for non-existent session"""
        client, _ = client_with_session

        synthesis_results = await client.synthesize_conversation("nonexistent", {})

        assert synthesis_results is None

    @pytest.mark.asyncio
    async def test_analysis_types_and_parameters(self, client_with_session):
        """Test different analysis types and parameters"""
        client, session = client_with_session

        analysis_types = ["quick", "comprehensive", "quality", "patterns"]

        for analysis_type in analysis_types:
            results = await client.request_analysis("auto_session_123", analysis_type)
            assert results is not None
            assert results["session_id"] == session.claude_session_id


class TestConnectionManagement:
    """Test connection management and heartbeat"""

    @pytest_asyncio.fixture(scope="function")
    async def authenticated_client(self):
        """Fixture providing authenticated client"""
        client = ClaudeAgentSDKClient()
        await client.initialize()
        try:
            yield client
        finally:
            await client.shutdown()

    @pytest.mark.asyncio
    async def test_heartbeat_success(self, authenticated_client):
        """Test successful heartbeat"""
        client = authenticated_client

        success = await client._send_heartbeat()

        assert success is True

    @pytest.mark.asyncio
    async def test_heartbeat_loop_running(self, authenticated_client):
        """Test that heartbeat loop is running after initialization"""
        client = authenticated_client

        # Heartbeat should be recent
        assert time.time() - client.last_heartbeat < 5.0

    @pytest.mark.asyncio
    async def test_connection_status_reporting(self, authenticated_client):
        """Test connection status reporting"""
        client = authenticated_client

        status = client.get_connection_status()

        assert status["connection_state"] == "authenticated"
        assert status["active_sessions"] >= 0
        assert status["connection_attempts"] > 0
        assert status["successful_requests"] >= 0
        assert status["last_heartbeat"] > 0

    @pytest.mark.asyncio
    async def test_session_info_retrieval(self, authenticated_client):
        """Test session information retrieval"""
        client = authenticated_client

        # Create session
        await client.create_persistent_session(
            auto_mode_session_id="auto_session_123", user_id="test_user", initial_context={}
        )

        # Get session info
        session_info = client.get_session_info("auto_session_123")

        assert session_info is not None
        assert session_info["session_id"] == "auto_session_123"
        assert session_info["user_id"] == "test_user"
        assert "claude_session_id" in session_info
        assert "created_at" in session_info
        assert "analysis_count" in session_info

    def test_session_info_nonexistent(self, authenticated_client):
        """Test session info for non-existent session"""
        client = authenticated_client

        session_info = client.get_session_info("nonexistent")

        assert session_info is None


class TestErrorHandling:
    """Test error handling and recovery"""

    @pytest.fixture
    def sdk_client(self):
        return ClaudeAgentSDKClient()

    @pytest.mark.asyncio
    async def test_initialization_exception_handling(self, sdk_client):
        """Test initialization exception handling"""
        with patch.object(
            sdk_client,
            "_establish_connection",
            new_callable=AsyncMock,
            side_effect=Exception("Connection failed"),
        ):
            success = await sdk_client.initialize()

            assert success is False
            assert sdk_client.connection_state == SDKConnectionState.ERROR

    @pytest.mark.asyncio
    async def test_session_creation_exception_handling(self, sdk_client):
        """Test session creation exception handling"""
        await sdk_client.initialize()

        # Force an exception during session creation
        with patch.object(
            sdk_client, "_generate_claude_session_id", side_effect=Exception("ID generation failed")
        ):
            session = await sdk_client.create_persistent_session("test", "user", {})

            assert session is None
            assert sdk_client.failed_requests > 0

    @pytest.mark.asyncio
    async def test_reconnection_attempts(self, sdk_client):
        """Test reconnection attempt mechanism"""
        sdk_client.connection_state = SDKConnectionState.AUTHENTICATED
        sdk_client.retry_attempts = 2

        # Mock failed reconnection attempts
        with patch.object(
            sdk_client, "_establish_connection", new_callable=AsyncMock, return_value=False
        ):
            await sdk_client._attempt_reconnection()

            assert sdk_client.connection_state == SDKConnectionState.ERROR

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, sdk_client):
        """Test graceful shutdown process"""
        await sdk_client.initialize()

        # Create some sessions
        await sdk_client.create_persistent_session("session1", "user1", {})
        await sdk_client.create_persistent_session("session2", "user2", {})

        assert len(sdk_client.active_sessions) == 2

        # Shutdown
        await sdk_client.shutdown()

        assert len(sdk_client.active_sessions) == 0
        assert sdk_client.connection_state == SDKConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_shutdown_with_exceptions(self, sdk_client):
        """Test shutdown handling with exceptions"""
        await sdk_client.initialize()

        # Mock exception during session closure
        with patch.object(
            sdk_client,
            "close_session",
            new_callable=AsyncMock,
            side_effect=Exception("Close failed"),
        ):
            # Should not raise exception
            await sdk_client.shutdown()

            assert sdk_client.connection_state == SDKConnectionState.DISCONNECTED


class TestMockAnalysisGeneration:
    """Test mock analysis generation for testing"""

    @pytest_asyncio.fixture(scope="function")
    async def client_with_session(self):
        """Fixture providing client with session"""
        client = ClaudeAgentSDKClient()
        await client.initialize()

        session = await client.create_persistent_session(
            auto_mode_session_id="auto_session_123",
            user_id="test_user",
            initial_context={"messages": []},
        )

        try:
            yield client, session
        finally:
            await client.shutdown()

    def test_claude_session_id_generation(self):
        """Test Claude session ID generation"""
        client = ClaudeAgentSDKClient()

        session_id1 = client._generate_claude_session_id("auto1", "user1")
        session_id2 = client._generate_claude_session_id("auto2", "user1")
        session_id3 = client._generate_claude_session_id("auto1", "user1")

        # Should be unique for different inputs
        assert session_id1 != session_id2

        # Should be different even for same inputs (due to timestamp)
        assert session_id1 != session_id3

        # Should have correct format
        assert session_id1.startswith("claude_session_")
        assert len(session_id1) > 20

    def test_mock_analysis_generation(self, client_with_session):
        """Test mock analysis result generation"""
        client, session = client_with_session

        analysis = client._generate_analysis_results(session)

        assert analysis["session_id"] == session.claude_session_id
        assert "analysis_timestamp" in analysis
        assert "quality_assessment" in analysis
        assert "detected_patterns" in analysis
        assert "improvement_opportunities" in analysis
        assert "user_insights" in analysis

        # Check quality assessment structure
        quality = analysis["quality_assessment"]
        assert "overall_score" in quality
        assert "dimensions" in quality
        assert 0.0 <= quality["overall_score"] <= 1.0

        # Check patterns structure
        patterns = analysis["detected_patterns"]
        assert isinstance(patterns, list)
        if patterns:
            pattern = patterns[0]
            assert "pattern_type" in pattern
            assert "confidence" in pattern
            assert "description" in pattern


if __name__ == "__main__":
    pytest.main([__file__])
