"""
Test suite for SessionManager.

Tests session lifecycle, persistence, and state management including:
- Session creation and initialization
- Session state updates and persistence
- Session cleanup and expiration
- Storage operations and recovery
"""

import json
import tempfile
import time
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from amplihack.auto_mode.session import SessionManager, SessionState, SessionStorage


class TestSessionState:
    """Test SessionState data model and serialization"""

    def test_session_state_creation(self):
        """Test creating new session state"""
        session_state = SessionState(session_id="test_session", user_id="test_user")

        assert session_state.session_id == "test_session"
        assert session_state.user_id == "test_user"
        assert session_state.analysis_cycles == 0
        assert session_state.current_quality_score == 0.0
        assert len(session_state.conversation_history) == 0

    def test_session_state_serialization(self):
        """Test session state to_dict conversion"""
        session_state = SessionState(
            session_id="test_session",
            user_id="test_user",
            analysis_cycles=5,
            current_quality_score=0.8,
        )

        # Add some mock analysis history
        from amplihack.auto_mode.analysis import ConversationAnalysis
        from amplihack.auto_mode.orchestrator import AnalysisCycleResult

        mock_result = AnalysisCycleResult(
            cycle_id="cycle_1",
            session_id="test_session",
            timestamp=time.time(),
            analysis=ConversationAnalysis(quality_score=0.8),
            quality_gates=[],
            interventions_suggested=[],
        )
        session_state.analysis_history.append(mock_result)

        data = session_state.to_dict()

        assert data["session_id"] == "test_session"
        assert data["user_id"] == "test_user"
        assert data["analysis_cycles"] == 5
        assert data["current_quality_score"] == 0.8
        assert len(data["analysis_history"]) == 1
        assert data["analysis_history"][0]["cycle_id"] == "cycle_1"

    def test_session_state_deserialization(self):
        """Test session state from_dict conversion"""
        data = {
            "session_id": "test_session",
            "user_id": "test_user",
            "created_at": time.time(),
            "analysis_cycles": 3,
            "current_quality_score": 0.7,
            "conversation_history": [],
            "analysis_history": [],
            "total_interventions": 1,
            "user_preferences": {},
            "learned_patterns": [],
            "sensitive_data_flags": [],
            "permission_grants": {},
        }

        session_state = SessionState.from_dict(data)

        assert session_state.session_id == "test_session"
        assert session_state.user_id == "test_user"
        assert session_state.analysis_cycles == 3
        assert session_state.current_quality_score == 0.7


class TestSessionStorage:
    """Test session persistence and storage operations"""

    @pytest.fixture
    def temp_storage_dir(self):
        """Fixture providing temporary storage directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def session_storage(self, temp_storage_dir):
        """Fixture providing session storage with temp directory"""
        return SessionStorage(temp_storage_dir)

    @pytest.mark.asyncio
    async def test_save_session_success(self, session_storage):
        """Test successful session save"""
        session_state = SessionState(
            session_id="test_session",
            user_id="test_user",
            analysis_cycles=2,
            current_quality_score=0.75,
        )

        success = await session_storage.save_session(session_state)

        assert success is True

        # Verify file was created
        session_file = session_storage._get_session_file("test_session")
        assert session_file.exists()

        # Verify content
        with open(session_file, "r") as f:
            saved_data = json.load(f)

        assert saved_data["session_id"] == "test_session"
        assert saved_data["user_id"] == "test_user"
        assert saved_data["analysis_cycles"] == 2

    @pytest.mark.asyncio
    async def test_load_session_success(self, session_storage):
        """Test successful session load"""
        # First save a session
        original_session = SessionState(
            session_id="test_session",
            user_id="test_user",
            analysis_cycles=3,
            current_quality_score=0.8,
        )

        await session_storage.save_session(original_session)

        # Then load it
        loaded_session = await session_storage.load_session("test_session")

        assert loaded_session is not None
        assert loaded_session.session_id == "test_session"
        assert loaded_session.user_id == "test_user"
        assert loaded_session.analysis_cycles == 3
        assert loaded_session.current_quality_score == 0.8

    @pytest.mark.asyncio
    async def test_load_nonexistent_session(self, session_storage):
        """Test loading non-existent session"""
        loaded_session = await session_storage.load_session("nonexistent")
        assert loaded_session is None

    @pytest.mark.asyncio
    async def test_delete_session_success(self, session_storage):
        """Test successful session deletion"""
        # Save a session first
        session_state = SessionState(session_id="test_session", user_id="test_user")
        await session_storage.save_session(session_state)

        # Verify it exists
        session_file = session_storage._get_session_file("test_session")
        assert session_file.exists()

        # Delete it
        success = await session_storage.delete_session("test_session")

        assert success is True
        assert not session_file.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, session_storage):
        """Test deleting non-existent session"""
        success = await session_storage.delete_session("nonexistent")
        assert success is True  # Should succeed silently

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, session_storage):
        """Test listing sessions when none exist"""
        sessions = await session_storage.list_sessions()
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_list_sessions_with_data(self, session_storage):
        """Test listing sessions with existing data"""
        # Save multiple sessions
        session1 = SessionState(session_id="session1", user_id="user1")
        session2 = SessionState(session_id="session2", user_id="user2")
        session3 = SessionState(session_id="session3", user_id="user1")

        await session_storage.save_session(session1)
        await session_storage.save_session(session2)
        await session_storage.save_session(session3)

        # List all sessions
        all_sessions = await session_storage.list_sessions()
        assert len(all_sessions) == 3

        # List sessions for specific user
        user1_sessions = await session_storage.list_sessions(user_id="user1")
        assert len(user1_sessions) == 2

        user2_sessions = await session_storage.list_sessions(user_id="user2")
        assert len(user2_sessions) == 1

    @pytest.mark.asyncio
    async def test_save_load_cycle_preserves_data(self, session_storage):
        """Test that save/load cycle preserves all important data"""
        original_session = SessionState(
            session_id="test_session",
            user_id="test_user",
            analysis_cycles=5,
            current_quality_score=0.85,
            total_interventions=3,
        )

        # Add conversation history
        original_session.conversation_history.append(
            {"timestamp": time.time(), "update": {"new_message": "test message"}}
        )

        # Add user preferences
        original_session.user_preferences.update(
            {"communication_style": "technical", "detail_level": "high"}
        )

        # Add learned patterns
        original_session.learned_patterns.append(
            {"pattern_type": "systematic_approach", "confidence": 0.9, "learned_at": time.time()}
        )

        # Save and load
        await session_storage.save_session(original_session)
        loaded_session = await session_storage.load_session("test_session")

        # Verify all data preserved
        assert loaded_session.session_id == original_session.session_id
        assert loaded_session.user_id == original_session.user_id
        assert loaded_session.analysis_cycles == original_session.analysis_cycles
        assert loaded_session.current_quality_score == original_session.current_quality_score
        assert loaded_session.total_interventions == original_session.total_interventions
        assert len(loaded_session.conversation_history) == 1
        assert loaded_session.user_preferences["communication_style"] == "technical"
        assert len(loaded_session.learned_patterns) == 1


class TestSessionManager:
    """Test SessionManager functionality"""

    @pytest.fixture
    def temp_storage_dir(self):
        """Fixture providing temporary storage directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest_asyncio.fixture(scope="function")
    async def session_manager(self, temp_storage_dir):
        """Fixture providing initialized session manager"""
        manager = SessionManager(temp_storage_dir)
        await manager.initialize()
        try:
            yield manager
        finally:
            await manager.shutdown()

    @pytest.mark.asyncio
    async def test_session_manager_initialization(self, temp_storage_dir):
        """Test session manager initialization"""
        manager = SessionManager(temp_storage_dir)

        assert len(manager.active_sessions) == 0
        assert manager._cleanup_task is None

        await manager.initialize()

        assert manager._cleanup_task is not None
        assert not manager._cleanup_task.done()

        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_create_session_success(self, session_manager):
        """Test successful session creation"""
        session_id = "test_session"
        user_id = "test_user"
        initial_context = {"messages": [], "goals": []}

        session_state = await session_manager.create_session(session_id, user_id, initial_context)

        assert session_state.session_id == session_id
        assert session_state.user_id == user_id
        assert session_state.conversation_context == initial_context
        assert session_id in session_manager.active_sessions

    @pytest.mark.asyncio
    async def test_create_duplicate_session(self, session_manager):
        """Test creating session with duplicate ID"""
        session_id = "test_session"
        user_id = "test_user"

        # Create first session
        await session_manager.create_session(session_id, user_id, {})

        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await session_manager.create_session(session_id, user_id, {})

    @pytest.mark.asyncio
    async def test_user_session_limit(self, session_manager):
        """Test user session limit enforcement"""
        session_manager.max_sessions_per_user = 2
        user_id = "test_user"

        # Create sessions up to limit
        await session_manager.create_session("session1", user_id, {})
        await session_manager.create_session("session2", user_id, {})

        assert len(session_manager.active_sessions) == 2

        # Create third session - should clean up oldest
        with patch.object(
            session_manager, "close_session", new_callable=AsyncMock, return_value=True
        ) as mock_close:
            await session_manager.create_session("session3", user_id, {})

            # Should have closed oldest session
            mock_close.assert_called_once()
            assert len(session_manager.active_sessions) == 2

    @pytest.mark.asyncio
    async def test_get_session_active(self, session_manager):
        """Test getting active session"""
        session_id = "test_session"
        user_id = "test_user"

        # Create session
        created_session = await session_manager.create_session(session_id, user_id, {})

        # Get session
        retrieved_session = await session_manager.get_session(session_id)

        assert retrieved_session is not None
        assert retrieved_session.session_id == session_id
        assert retrieved_session is created_session  # Should be same object

    @pytest.mark.asyncio
    async def test_get_session_from_storage(self, session_manager):
        """Test getting session from persistent storage"""
        session_id = "test_session"
        user_id = "test_user"

        # Create and save session
        original_session = SessionState(session_id=session_id, user_id=user_id)
        await session_manager.storage.save_session(original_session)

        # Get session (not in active sessions)
        retrieved_session = await session_manager.get_session(session_id)

        assert retrieved_session is not None
        assert retrieved_session.session_id == session_id
        assert session_id in session_manager.active_sessions  # Should be restored to active

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, session_manager):
        """Test getting non-existent session"""
        retrieved_session = await session_manager.get_session("nonexistent")
        assert retrieved_session is None

    @pytest.mark.asyncio
    async def test_update_conversation_success(self, session_manager):
        """Test successful conversation update"""
        session_id = "test_session"
        user_id = "test_user"

        # Create session
        session_state = await session_manager.create_session(session_id, user_id, {})

        conversation_update = {"new_message": "Hello world", "timestamp": time.time()}

        success = await session_manager.update_conversation(session_state, conversation_update)

        assert success is True
        assert "new_message" in session_state.conversation_context
        assert len(session_state.conversation_history) == 1

    @pytest.mark.asyncio
    async def test_update_user_preferences_success(self, session_manager):
        """Test successful user preferences update"""
        session_id = "test_session"
        user_id = "test_user"

        # Create session
        session_state = await session_manager.create_session(session_id, user_id, {})

        preferences = {"communication_style": "casual", "detail_level": "medium"}

        success = await session_manager.update_user_preferences(session_state, preferences)

        assert success is True
        assert session_state.user_preferences["communication_style"] == "casual"
        assert session_state.user_preferences["detail_level"] == "medium"

    @pytest.mark.asyncio
    async def test_add_learned_pattern_success(self, session_manager):
        """Test successful learned pattern addition"""
        session_id = "test_session"
        user_id = "test_user"

        # Create session
        session_state = await session_manager.create_session(session_id, user_id, {})

        pattern = {
            "pattern_type": "prefers_examples",
            "confidence": 0.8,
            "evidence": "User frequently asks for examples",
        }

        success = await session_manager.add_learned_pattern(session_state, pattern)

        assert success is True
        assert len(session_state.learned_patterns) == 1
        assert session_state.learned_patterns[0]["pattern_type"] == "prefers_examples"
        assert "learned_at" in session_state.learned_patterns[0]

    @pytest.mark.asyncio
    async def test_close_session_success(self, session_manager):
        """Test successful session closure"""
        session_id = "test_session"
        user_id = "test_user"

        # Create session
        session_state = await session_manager.create_session(session_id, user_id, {})

        assert session_id in session_manager.active_sessions

        success = await session_manager.close_session(session_state)

        assert success is True
        assert session_id not in session_manager.active_sessions

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_manager):
        """Test cleanup of expired sessions"""
        session_manager.session_timeout_minutes = 0.01  # 0.6 seconds for testing

        # Create session
        session_id = "test_session"
        user_id = "test_user"
        session_state = await session_manager.create_session(session_id, user_id, {})

        # Manually set old timestamp
        session_state.last_updated = time.time() - 120  # 2 minutes ago

        # Run cleanup
        cleaned_up = await session_manager.cleanup_expired_sessions()

        assert cleaned_up == 1
        assert session_id not in session_manager.active_sessions

    @pytest.mark.asyncio
    async def test_session_count_tracking(self, session_manager):
        """Test session count tracking"""
        user_id1 = "user1"
        user_id2 = "user2"

        assert session_manager.get_active_session_count() == 0
        assert session_manager.get_user_session_count(user_id1) == 0

        # Create sessions
        await session_manager.create_session("session1", user_id1, {})
        await session_manager.create_session("session2", user_id1, {})
        await session_manager.create_session("session3", user_id2, {})

        assert session_manager.get_active_session_count() == 3
        assert session_manager.get_user_session_count(user_id1) == 2
        assert session_manager.get_user_session_count(user_id2) == 1

    @pytest.mark.asyncio
    async def test_session_manager_shutdown(self, temp_storage_dir):
        """Test session manager shutdown"""
        manager = SessionManager(temp_storage_dir)
        await manager.initialize()

        # Create session
        session_state = await manager.create_session("test_session", "test_user", {})

        # Mock storage save
        with patch.object(
            manager.storage, "save_session", new_callable=AsyncMock, return_value=True
        ) as mock_save:
            await manager.shutdown()

            # Should save all active sessions
            mock_save.assert_called_once_with(session_state)

        # Cleanup task should be cancelled
        assert manager._cleanup_task.cancelled()
        assert len(manager.active_sessions) == 0


if __name__ == "__main__":
    pytest.main([__file__])
