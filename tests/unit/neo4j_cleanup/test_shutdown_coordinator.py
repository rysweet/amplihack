"""Unit tests for Neo4jShutdownCoordinator.

Tests shutdown decision logic, user prompting, and execution.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator


class TestNeo4jShutdownCoordinator:
    """Test suite for Neo4jShutdownCoordinator."""

    @pytest.fixture
    def mock_tracker(self):
        """Create mock connection tracker."""
        tracker = Mock()
        tracker.is_last_connection.return_value = True
        return tracker

    @pytest.fixture
    def mock_manager(self):
        """Create mock container manager."""
        manager = Mock()
        manager.stop.return_value = True
        return manager

    @pytest.fixture
    def coordinator(self, mock_tracker, mock_manager):
        """Create coordinator instance with mocks."""
        # Mock Path to prevent loading real preferences
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            MockPath.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            return Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=False,
            )

    @pytest.fixture
    def auto_coordinator(self, mock_tracker, mock_manager):
        """Create coordinator instance in auto mode."""
        # Mock Path to prevent loading real preferences
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            MockPath.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            return Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=True,
            )

    def test_should_prompt_shutdown_true(self, coordinator, mock_tracker):
        """Test prompt decision: interactive mode, last connection."""
        mock_tracker.is_last_connection.return_value = True

        result = coordinator.should_prompt_shutdown()

        assert result is True
        mock_tracker.is_last_connection.assert_called_once()

    def test_should_prompt_shutdown_auto_mode(self, auto_coordinator, mock_tracker):
        """Test prompt decision: auto mode (should skip)."""
        result = auto_coordinator.should_prompt_shutdown()

        assert result is False
        # Should not even check connections in auto mode
        mock_tracker.is_last_connection.assert_not_called()

    def test_should_prompt_shutdown_multiple_connections(self, coordinator, mock_tracker):
        """Test prompt decision: multiple connections (should skip)."""
        mock_tracker.is_last_connection.return_value = False

        result = coordinator.should_prompt_shutdown()

        assert result is False
        mock_tracker.is_last_connection.assert_called_once()

    def test_prompt_user_shutdown_yes(self, coordinator):
        """Test user prompt: user accepts with 'y'."""
        with patch("builtins.input", return_value="y"):
            result = coordinator.prompt_user_shutdown()

            assert result is True

    def test_prompt_user_shutdown_yes_uppercase(self, coordinator):
        """Test user prompt: user accepts with 'Y'."""
        with patch("builtins.input", return_value="Y"):
            result = coordinator.prompt_user_shutdown()

            assert result is True

    def test_prompt_user_shutdown_yes_full(self, coordinator):
        """Test user prompt: user accepts with 'yes'."""
        with patch("builtins.input", return_value="yes"):
            result = coordinator.prompt_user_shutdown()

            assert result is True

    def test_prompt_user_shutdown_no(self, coordinator):
        """Test user prompt: user declines with 'n'."""
        with patch("builtins.input", return_value="n"):
            result = coordinator.prompt_user_shutdown()

            assert result is False

    def test_prompt_user_shutdown_no_default(self, coordinator):
        """Test user prompt: user presses enter (default no)."""
        with patch("builtins.input", return_value=""):
            result = coordinator.prompt_user_shutdown()

            assert result is False

    def test_prompt_user_shutdown_invalid_input(self, coordinator):
        """Test user prompt: invalid input defaults to no."""
        with patch("builtins.input", return_value="maybe"):
            result = coordinator.prompt_user_shutdown()

            assert result is False

    def test_prompt_user_shutdown_timeout(self, coordinator):
        """Test user prompt: timeout defaults to no."""

        # Mock input that never returns (simulates timeout)
        def slow_input(prompt):
            import time

            time.sleep(15)  # Longer than 10s timeout
            return "y"

        with patch("builtins.input", side_effect=slow_input):
            result = coordinator.prompt_user_shutdown()

            # Should timeout and default to False
            assert result is False

    def test_prompt_user_shutdown_eoferror(self, coordinator):
        """Test user prompt: EOF error defaults to no."""
        with patch("builtins.input", side_effect=EOFError):
            result = coordinator.prompt_user_shutdown()

            assert result is False

    def test_prompt_user_shutdown_keyboard_interrupt(self, coordinator):
        """Test user prompt: keyboard interrupt defaults to no."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = coordinator.prompt_user_shutdown()

            assert result is False

    def test_execute_shutdown_success(self, coordinator, mock_manager):
        """Test successful shutdown execution."""
        mock_manager.stop.return_value = True

        result = coordinator.execute_shutdown()

        assert result is True
        mock_manager.stop.assert_called_once()

    def test_execute_shutdown_failure(self, coordinator, mock_manager):
        """Test failed shutdown execution."""
        mock_manager.stop.return_value = False

        result = coordinator.execute_shutdown()

        assert result is False
        mock_manager.stop.assert_called_once()

    def test_execute_shutdown_exception(self, coordinator, mock_manager):
        """Test shutdown execution with exception."""
        mock_manager.stop.side_effect = Exception("Container error")

        result = coordinator.execute_shutdown()

        assert result is False
        mock_manager.stop.assert_called_once()

    def test_handle_session_exit_full_flow_accept(self, coordinator, mock_tracker, mock_manager):
        """Test complete flow: prompt and accept shutdown."""
        mock_tracker.is_last_connection.return_value = True
        mock_manager.stop.return_value = True

        with patch("builtins.input", return_value="y"):
            coordinator.handle_session_exit()

            # Verify all steps executed
            mock_tracker.is_last_connection.assert_called_once()
            mock_manager.stop.assert_called_once()

    def test_handle_session_exit_full_flow_decline(self, coordinator, mock_tracker, mock_manager):
        """Test complete flow: prompt but decline shutdown."""
        mock_tracker.is_last_connection.return_value = True

        with patch("builtins.input", return_value="n"):
            coordinator.handle_session_exit()

            # Verify prompt happened but shutdown didn't
            mock_tracker.is_last_connection.assert_called_once()
            mock_manager.stop.assert_not_called()

    def test_handle_session_exit_auto_mode(self, auto_coordinator, mock_tracker, mock_manager):
        """Test complete flow: auto mode (skip everything)."""
        auto_coordinator.handle_session_exit()

        # Verify nothing executed in auto mode
        mock_tracker.is_last_connection.assert_not_called()
        mock_manager.stop.assert_not_called()

    def test_handle_session_exit_multiple_connections(
        self, coordinator, mock_tracker, mock_manager
    ):
        """Test complete flow: multiple connections (skip prompt)."""
        mock_tracker.is_last_connection.return_value = False

        coordinator.handle_session_exit()

        # Verify check happened but no prompt/shutdown
        mock_tracker.is_last_connection.assert_called_once()
        mock_manager.stop.assert_not_called()

    def test_handle_session_exit_exception_safe(self, coordinator, mock_tracker):
        """Test complete flow: exception handling (fail-safe)."""
        mock_tracker.is_last_connection.side_effect = Exception("Connection error")

        # Should not raise exception
        coordinator.handle_session_exit()

        # Verify it attempted the check
        mock_tracker.is_last_connection.assert_called_once()

    def test_initialization(self, mock_tracker, mock_manager):
        """Test coordinator initialization."""
        coordinator = Neo4jShutdownCoordinator(
            connection_tracker=mock_tracker,
            container_manager=mock_manager,
            auto_mode=True,
        )

        assert coordinator.connection_tracker is mock_tracker
        assert coordinator.container_manager is mock_manager
        assert coordinator.auto_mode is True

    def test_handle_session_exit_timeout_scenario(self, coordinator, mock_tracker, mock_manager):
        """Test complete flow: user prompt timeout."""
        mock_tracker.is_last_connection.return_value = True

        # Mock timeout scenario
        def slow_input(prompt):
            import time

            time.sleep(15)
            return "y"

        with patch("builtins.input", side_effect=slow_input):
            coordinator.handle_session_exit()

            # Verify prompt happened but shutdown didn't (timeout = no)
            mock_tracker.is_last_connection.assert_called_once()
            mock_manager.stop.assert_not_called()

    # Preference Loading Tests
    def test_load_preference_default(self, mock_tracker, mock_manager):
        """Test preference loading when no preference file exists."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            MockPath.home.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator = Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=False,
            )
            assert coordinator._preference == "ask"

    def test_load_preference_always(self, mock_tracker, mock_manager):
        """Test loading 'always' preference."""
        prefs_content = "neo4j_auto_shutdown: always"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator = Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=False,
            )
            assert coordinator._preference == "always"

    def test_load_preference_never(self, mock_tracker, mock_manager):
        """Test loading 'never' preference."""
        prefs_content = "**Current setting:** never\nneo4j_auto_shutdown: never"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator = Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=False,
            )
            assert coordinator._preference == "never"

    def test_load_preference_ask(self, mock_tracker, mock_manager):
        """Test loading 'ask' preference."""
        prefs_content = "neo4j_auto_shutdown: ask"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator = Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=False,
            )
            assert coordinator._preference == "ask"

    def test_load_preference_invalid_value(self, mock_tracker, mock_manager):
        """Test loading invalid preference defaults to 'ask'."""
        prefs_content = "neo4j_auto_shutdown: invalid"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator = Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=False,
            )
            assert coordinator._preference == "ask"

    # Preference Saving Tests
    def test_save_preference_always(self, coordinator):
        """Test saving 'always' preference."""
        prefs_content = """
### Neo4j Auto-Shutdown

Controls neo4j_auto_shutdown preference.

**Current setting:** ask

**Options:**
"""

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"

        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator._save_preference("always")
            mock_path.write_text.assert_called_once()
            written_content = mock_path.write_text.call_args[0][0]
            assert "always" in written_content

    def test_save_preference_never(self, coordinator):
        """Test saving 'never' preference."""
        prefs_content = """
### Neo4j Auto-Shutdown

Controls neo4j_auto_shutdown preference.

**Current setting:** ask

**Options:**
"""

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"

        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator._save_preference("never")
            mock_path.write_text.assert_called_once()
            written_content = mock_path.write_text.call_args[0][0]
            assert "never" in written_content

    def test_save_preference_file_not_found(self, coordinator):
        """Test saving preference when file doesn't exist."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False

        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            # Should not raise exception
            coordinator._save_preference("always")

    # Preference Behavior Tests
    def test_should_prompt_shutdown_preference_never(self, mock_tracker, mock_manager):
        """Test should_prompt_shutdown with 'never' preference."""
        prefs_content = "neo4j_auto_shutdown: never"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator = Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=False,
            )
            mock_tracker.is_last_connection.return_value = True

            result = coordinator.should_prompt_shutdown()

            assert result is False
            # Should not even check connections with 'never'
            mock_tracker.is_last_connection.assert_not_called()

    def test_should_prompt_shutdown_preference_always(self, mock_tracker, mock_manager):
        """Test should_prompt_shutdown with 'always' preference."""
        prefs_content = "neo4j_auto_shutdown: always"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator = Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=False,
            )
            mock_tracker.is_last_connection.return_value = True

            result = coordinator.should_prompt_shutdown()

            assert result is True
            mock_tracker.is_last_connection.assert_called_once()

    def test_prompt_user_shutdown_preference_always_auto_accept(self, mock_tracker, mock_manager):
        """Test prompt_user_shutdown with 'always' preference auto-accepts."""
        prefs_content = "neo4j_auto_shutdown: always"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator = Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=False,
            )

            # Should not prompt, should return True
            result = coordinator.prompt_user_shutdown()

            assert result is True

    def test_prompt_user_shutdown_response_always(self, coordinator):
        """Test user responding with 'always'."""
        prefs_content = """
### Neo4j Auto-Shutdown

Controls neo4j_auto_shutdown preference.

**Current setting:** ask

**Options:**
"""

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"

        with patch("builtins.input", return_value="always"), patch(
            "amplihack.neo4j.shutdown_coordinator.Path"
        ) as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            result = coordinator.prompt_user_shutdown()

            assert result is True
            mock_path.write_text.assert_called_once()

    def test_prompt_user_shutdown_response_a(self, coordinator):
        """Test user responding with 'a' (shortcut for always)."""
        prefs_content = """
### Neo4j Auto-Shutdown

Controls neo4j_auto_shutdown preference.

**Current setting:** ask

**Options:**
"""

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"

        with patch("builtins.input", return_value="a"), patch(
            "amplihack.neo4j.shutdown_coordinator.Path"
        ) as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            result = coordinator.prompt_user_shutdown()

            assert result is True
            mock_path.write_text.assert_called_once()

    def test_prompt_user_shutdown_response_never(self, coordinator):
        """Test user responding with 'never'."""
        prefs_content = """
### Neo4j Auto-Shutdown

Controls neo4j_auto_shutdown preference.

**Current setting:** ask

**Options:**
"""

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"

        with patch("builtins.input", return_value="never"), patch(
            "amplihack.neo4j.shutdown_coordinator.Path"
        ) as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            result = coordinator.prompt_user_shutdown()

            assert result is False
            mock_path.write_text.assert_called_once()

    def test_prompt_user_shutdown_response_v(self, coordinator):
        """Test user responding with 'v' (shortcut for never)."""
        prefs_content = """
### Neo4j Auto-Shutdown

Controls neo4j_auto_shutdown preference.

**Current setting:** ask

**Options:**
"""

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"

        with patch("builtins.input", return_value="v"), patch(
            "amplihack.neo4j.shutdown_coordinator.Path"
        ) as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            result = coordinator.prompt_user_shutdown()

            assert result is False
            mock_path.write_text.assert_called_once()

    def test_handle_session_exit_preference_never_no_prompt(self, mock_tracker, mock_manager):
        """Test complete flow: preference 'never' skips everything."""
        prefs_content = "neo4j_auto_shutdown: never"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator = Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=False,
            )
            mock_tracker.is_last_connection.return_value = True

            coordinator.handle_session_exit()

            # Should not check connections or shutdown
            mock_tracker.is_last_connection.assert_not_called()
            mock_manager.stop.assert_not_called()

    def test_handle_session_exit_preference_always_auto_shutdown(self, mock_tracker, mock_manager):
        """Test complete flow: preference 'always' auto-shuts down."""
        prefs_content = "neo4j_auto_shutdown: always"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator = Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=False,
            )
            mock_tracker.is_last_connection.return_value = True
            mock_manager.stop.return_value = True

            coordinator.handle_session_exit()

            # Should check connections and shutdown without prompting
            mock_tracker.is_last_connection.assert_called_once()
            mock_manager.stop.assert_called_once()

    def test_path_validation_rejects_traversal(self, coordinator):
        """Test path validation rejects path traversal attempts."""
        # Test case: file not named USER_PREFERENCES.md
        invalid_path = Path("/etc/passwd")
        with pytest.raises(ValueError, match="Invalid preferences file"):
            coordinator._validate_preferences_path(invalid_path)

        # Test case: path doesn't contain .claude/context
        invalid_path = Path("/tmp/USER_PREFERENCES.md")
        with pytest.raises(ValueError, match="must contain .claude/context"):
            coordinator._validate_preferences_path(invalid_path)

    def test_path_validation_accepts_valid_paths(self, coordinator):
        """Test path validation accepts valid preference paths."""
        # Test project-local path
        valid_path = Path.cwd() / ".claude" / "context" / "USER_PREFERENCES.md"
        resolved = coordinator._validate_preferences_path(valid_path)
        assert resolved.name == "USER_PREFERENCES.md"
        assert ".claude/context" in str(resolved)

        # Test home directory path
        valid_path = Path.home() / ".claude" / "context" / "USER_PREFERENCES.md"
        resolved = coordinator._validate_preferences_path(valid_path)
        assert resolved.name == "USER_PREFERENCES.md"
        assert ".claude/context" in str(resolved)

    def test_load_preference_with_path_validation(self, mock_tracker, mock_manager):
        """Test that _load_preference validates paths."""
        prefs_content = "neo4j_auto_shutdown: always"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"

        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            coordinator = Neo4jShutdownCoordinator(
                connection_tracker=mock_tracker,
                container_manager=mock_manager,
                auto_mode=False,
            )
            # Should succeed with valid path
            assert coordinator._preference == "always"

    def test_save_preference_with_path_validation(self, coordinator):
        """Test that _save_preference validates paths."""
        prefs_content = """
### Neo4j Auto-Shutdown

Controls neo4j_auto_shutdown preference.

**Current setting:** ask

**Options:**
"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = prefs_content
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"
        mock_path.name = "USER_PREFERENCES.md"
        mock_path.resolve.return_value = mock_path
        mock_path.__str__.return_value = "/path/.claude/context/USER_PREFERENCES.md"

        with patch("amplihack.neo4j.shutdown_coordinator.Path") as MockPath:
            MockPath.cwd.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = mock_path
            # Should validate path before saving
            coordinator._save_preference("always")
            mock_path.write_text.assert_called_once()
