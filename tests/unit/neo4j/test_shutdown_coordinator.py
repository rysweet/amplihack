"""Unit tests for Neo4jShutdownCoordinator.

Tests shutdown decision logic, user prompting, and execution.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

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
        return Neo4jShutdownCoordinator(
            connection_tracker=mock_tracker,
            container_manager=mock_manager,
            auto_mode=False,
        )

    @pytest.fixture
    def auto_coordinator(self, mock_tracker, mock_manager):
        """Create coordinator instance in auto mode."""
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

    def test_handle_session_exit_multiple_connections(self, coordinator, mock_tracker, mock_manager):
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
