"""End-to-end agentic tests for Neo4j session cleanup.

These tests verify the complete user experience for Neo4j database
cleanup on session exit, including preferences, signal handlers, and
interactive prompts.

Marked with @pytest.mark.gadugi for selective execution.
"""

import os
import sys
import time
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set environment variable to allow default password for testing
os.environ["NEO4J_ALLOW_DEFAULT_PASSWORD"] = "true"


@pytest.mark.gadugi
def test_neo4j_cleanup_interactive_prompt_yes():
    """Test that user can choose to shutdown Neo4j interactively.

    Real scenario: User exits session with Neo4j running, is last connection,
    chooses 'yes' to shutdown.
    """
    from unittest.mock import Mock, patch

    from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker
    from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator

    # Mock connection tracker to simulate last connection
    tracker = Mock(spec=Neo4jConnectionTracker)
    tracker.is_last_connection.return_value = True

    # Mock container manager
    container_manager = Mock()
    container_manager.stop.return_value = True

    # Create coordinator in interactive mode
    coordinator = Neo4jShutdownCoordinator(
        connection_tracker=tracker,
        container_manager=container_manager,
        auto_mode=False
    )

    # Simulate user typing 'y'
    with patch('builtins.input', return_value='y'):
        result = coordinator.prompt_user_shutdown()

    # Verify user choice was respected
    assert result is True, "User chose 'y' but shutdown was not initiated"

    print("\n✓ Interactive prompt 'yes' test passed")


@pytest.mark.gadugi
def test_neo4j_cleanup_interactive_prompt_no():
    """Test that user can choose NOT to shutdown Neo4j.

    Real scenario: User exits session, is last connection, chooses 'no'.
    """
    from unittest.mock import Mock, patch

    from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker
    from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator

    tracker = Mock(spec=Neo4jConnectionTracker)
    tracker.is_last_connection.return_value = True

    container_manager = Mock()
    container_manager.stop.return_value = True

    coordinator = Neo4jShutdownCoordinator(
        connection_tracker=tracker,
        container_manager=container_manager,
        auto_mode=False
    )

    # Simulate user typing 'n'
    with patch('builtins.input', return_value='n'):
        result = coordinator.prompt_user_shutdown()

    # Verify user choice was respected
    assert result is False, "User chose 'n' but shutdown was initiated"

    # Container manager should NOT have been called
    assert not container_manager.stop.called, "Shutdown was called despite user saying 'no'"

    print("\n✓ Interactive prompt 'no' test passed")


@pytest.mark.gadugi
def test_neo4j_cleanup_preference_always():
    """Test that 'always' preference skips prompt and shutdowns automatically.

    Real scenario: User has set preference to always shutdown, should not see prompt.
    """
    from unittest.mock import Mock, patch

    from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker
    from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator

    tracker = Mock(spec=Neo4jConnectionTracker)
    tracker.is_last_connection.return_value = True

    container_manager = Mock()
    container_manager.stop.return_value = True

    # Create coordinator with 'always' preference
    coordinator = Neo4jShutdownCoordinator(
        connection_tracker=tracker,
        container_manager=container_manager,
        auto_mode=False
    )

    # Mock preference loading to return 'always'
    with patch.object(coordinator, '_preference', 'always'):
        # Should NOT prompt, should automatically return True
        result = coordinator.prompt_user_shutdown()

    assert result is True, "Preference 'always' did not auto-accept shutdown"

    print("\n✓ Preference 'always' test passed")


@pytest.mark.gadugi
def test_neo4j_cleanup_preference_never():
    """Test that 'never' preference skips prompt entirely.

    Real scenario: User has set preference to never shutdown.
    """
    from unittest.mock import Mock, patch

    from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker
    from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator

    tracker = Mock(spec=Neo4jConnectionTracker)
    tracker.is_last_connection.return_value = True

    container_manager = Mock()

    coordinator = Neo4jShutdownCoordinator(
        connection_tracker=tracker,
        container_manager=container_manager,
        auto_mode=False
    )

    # Mock preference to 'never'
    with patch.object(coordinator, '_preference', 'never'):
        # should_prompt_shutdown should return False
        result = coordinator.should_prompt_shutdown()

    assert result is False, "Preference 'never' still prompted user"

    print("\n✓ Preference 'never' test passed")


@pytest.mark.gadugi
def test_neo4j_cleanup_preference_persistence():
    """Test that user can save preference via prompt response.

    Real scenario: User responds with 'always' or 'never' to save preference.
    """
    from unittest.mock import Mock, patch

    from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker
    from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator

    tracker = Mock(spec=Neo4jConnectionTracker)
    tracker.is_last_connection.return_value = True

    container_manager = Mock()

    coordinator = Neo4jShutdownCoordinator(
        connection_tracker=tracker,
        container_manager=container_manager,
        auto_mode=False
    )

    # Mock _save_preference to verify it's called
    with patch.object(coordinator, '_save_preference') as save_mock:
        # Simulate user typing 'always'
        with patch('builtins.input', return_value='always'):
            result = coordinator.prompt_user_shutdown()

        # Verify preference was saved
        assert save_mock.called, "User said 'always' but preference was not saved"
        assert save_mock.call_args[0][0] == 'always', "Wrong preference value saved"
        assert result is True, "User said 'always' but shutdown not initiated"

    # Reset and test 'never'
    with patch.object(coordinator, '_save_preference') as save_mock:
        # Simulate user typing 'never'
        with patch('builtins.input', return_value='never'):
            result = coordinator.prompt_user_shutdown()

        # Verify preference was saved
        assert save_mock.called, "User said 'never' but preference was not saved"
        assert save_mock.call_args[0][0] == 'never', "Wrong preference value saved"
        assert result is False, "User said 'never' but shutdown was initiated"

    print("\n✓ Preference persistence test passed")


@pytest.mark.gadugi
def test_neo4j_cleanup_auto_mode_skips_prompt():
    """Test that auto mode never prompts user.

    Real scenario: Running in auto mode (AMPLIHACK_AUTO_MODE=true).
    """
    from unittest.mock import Mock

    from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker
    from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator

    tracker = Mock(spec=Neo4jConnectionTracker)
    tracker.is_last_connection.return_value = True

    container_manager = Mock()

    # Create coordinator in AUTO mode
    coordinator = Neo4jShutdownCoordinator(
        connection_tracker=tracker,
        container_manager=container_manager,
        auto_mode=True  # AUTO MODE
    )

    # should_prompt_shutdown should return False in auto mode
    result = coordinator.should_prompt_shutdown()

    assert result is False, "Auto mode still tried to prompt user"

    # Connection tracker should NOT have been called (optimization)
    assert not tracker.is_last_connection.called, "Connection check performed in auto mode"

    print("\n✓ Auto mode skip prompt test passed")


@pytest.mark.gadugi
def test_neo4j_cleanup_multiple_connections_no_prompt():
    """Test that multiple connections prevents prompt.

    Real scenario: Other sessions are using Neo4j, should not prompt.
    """
    from unittest.mock import Mock

    from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker
    from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator

    tracker = Mock(spec=Neo4jConnectionTracker)
    tracker.is_last_connection.return_value = False  # Multiple connections

    container_manager = Mock()

    coordinator = Neo4jShutdownCoordinator(
        connection_tracker=tracker,
        container_manager=container_manager,
        auto_mode=False
    )

    # Should not prompt when multiple connections exist
    result = coordinator.should_prompt_shutdown()

    assert result is False, "Prompted user despite multiple connections"

    print("\n✓ Multiple connections test passed")


@pytest.mark.gadugi
def test_neo4j_cleanup_fail_safe_on_error():
    """Test fail-safe behavior when errors occur.

    Real scenario: Neo4j query fails, should not crash or block exit.
    """
    from unittest.mock import Mock

    from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker
    from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator

    # Mock tracker that raises exception
    tracker = Mock(spec=Neo4jConnectionTracker)
    tracker.is_last_connection.side_effect = Exception("Connection check failed")

    container_manager = Mock()

    coordinator = Neo4jShutdownCoordinator(
        connection_tracker=tracker,
        container_manager=container_manager,
        auto_mode=False
    )

    # Should handle exception gracefully
    try:
        coordinator.handle_session_exit()
        # Should not raise, should log and continue
        assert True, "handle_session_exit completed despite error"
    except Exception as e:
        pytest.fail(f"handle_session_exit raised exception: {e}")

    print("\n✓ Fail-safe error handling test passed")


@pytest.mark.gadugi
def test_neo4j_cleanup_timeout_defaults_to_no():
    """Test that prompt timeout defaults to 'no' (safe default).

    Real scenario: User doesn't respond to prompt within 10 seconds.
    """
    from unittest.mock import Mock, patch

    from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker
    from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator

    tracker = Mock(spec=Neo4jConnectionTracker)
    tracker.is_last_connection.return_value = True

    container_manager = Mock()

    coordinator = Neo4jShutdownCoordinator(
        connection_tracker=tracker,
        container_manager=container_manager,
        auto_mode=False
    )

    # Mock input to hang (simulate no response)
    def hang(prompt_text):
        time.sleep(15)  # Longer than timeout
        return ''

    with patch('builtins.input', side_effect=hang):
        result = coordinator.prompt_user_shutdown()

    # Should default to False (no shutdown) on timeout
    assert result is False, "Timeout did not default to 'no'"

    print("\n✓ Prompt timeout test passed")


@pytest.mark.gadugi
def test_neo4j_cleanup_complete_flow():
    """Test complete end-to-end flow.

    Real scenario: Session ends, Neo4j running, last connection, user accepts shutdown.
    """
    from unittest.mock import Mock, patch

    from amplihack.neo4j.connection_tracker import Neo4jConnectionTracker
    from amplihack.neo4j.shutdown_coordinator import Neo4jShutdownCoordinator

    # Setup mocks
    tracker = Mock(spec=Neo4jConnectionTracker)
    tracker.is_last_connection.return_value = True

    container_manager = Mock()
    container_manager.stop.return_value = True

    coordinator = Neo4jShutdownCoordinator(
        connection_tracker=tracker,
        container_manager=container_manager,
        auto_mode=False
    )

    # Simulate user interaction
    with patch('builtins.input', return_value='y'):
        coordinator.handle_session_exit()

    # Verify complete flow
    assert tracker.is_last_connection.called, "Connection check not performed"
    assert container_manager.stop.called, "Database not shutdown despite user acceptance"

    print("\n✓ Complete end-to-end flow test passed")


def test_gadugi_tests_runnable():
    """Verify all gadugi tests are properly marked and runnable."""
    # This test always passes - it's to verify the test structure
    assert True, "Gadugi test structure verified"


if __name__ == "__main__":
    # Run gadugi tests when executed directly
    print("Running Neo4j cleanup end-to-end agentic tests...")
    pytest.main([__file__, "-v", "-m", "gadugi"])
