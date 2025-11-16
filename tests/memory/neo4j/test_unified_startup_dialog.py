"""Tests for unified Neo4j startup dialog.

Note: This file contains test fixtures with example passwords like "testpass".
These are NOT real credentials and should be ignored by security scanners.
"""

from unittest.mock import Mock, patch

import pytest

from amplihack.memory.neo4j.unified_startup_dialog import (
    ContainerOption,
    _check_env_sync_status,
    _format_env_sync_status,
    _format_ports,
    detect_container_options,
    display_unified_dialog,
    handle_credential_sync,
    unified_container_and_credential_dialog,
)


class TestContainerOption:
    """Test ContainerOption dataclass."""

    def test_container_option_creation(self):
        """ContainerOption can be created with all attributes."""
        option = ContainerOption(
            name="amplihack-test",
            status="Up 2 hours",
            ports=["7787->7687"],
            username="neo4j",
            password="FAKE_TEST_PASSWORD",  # Test fixture - not a real credential
            env_sync_status="match",
            is_running=True,
        )
        assert option.name == "amplihack-test"
        assert option.status == "Up 2 hours"
        assert option.ports == ["7787->7687"]
        assert option.username == "neo4j"
        assert option.password == "FAKE_TEST_PASSWORD"
        assert option.env_sync_status == "match"
        assert option.is_running is True


class TestEnvSyncStatus:
    """Test environment sync status checking."""

    def test_no_container_credentials(self):
        """Returns no_container_creds when container has no credentials."""
        mock_sync = Mock()
        status = _check_env_sync_status(mock_sync, None, None)
        assert status == "no_container_creds"

    def test_no_container_username(self):
        """Returns no_container_creds when username is missing."""
        mock_sync = Mock()
        status = _check_env_sync_status(mock_sync, None, "password")
        assert status == "no_container_creds"

    def test_no_container_password(self):
        """Returns no_container_creds when password is missing."""
        mock_sync = Mock()
        status = _check_env_sync_status(mock_sync, "username", None)
        assert status == "no_container_creds"

    def test_missing_env_credentials(self):
        """Returns missing when .env has no credentials."""
        mock_sync = Mock()
        mock_sync.get_existing_credentials.return_value = (None, None)
        status = _check_env_sync_status(mock_sync, "neo4j", "password")
        assert status == "missing"

    def test_credentials_match(self):
        """Returns match when credentials are identical."""
        mock_sync = Mock()
        mock_sync.get_existing_credentials.return_value = ("neo4j", "password")
        status = _check_env_sync_status(mock_sync, "neo4j", "password")
        assert status == "match"

    def test_credentials_different(self):
        """Returns different when credentials don't match."""
        mock_sync = Mock()
        mock_sync.get_existing_credentials.return_value = ("neo4j", "oldpass")
        status = _check_env_sync_status(mock_sync, "neo4j", "newpass")
        assert status == "different"


class TestFormatting:
    """Test formatting functions."""

    def test_format_env_sync_status_match(self):
        """Format match status correctly."""
        assert _format_env_sync_status("match") == "Credentials match ✓"

    def test_format_env_sync_status_different(self):
        """Format different status correctly."""
        assert _format_env_sync_status("different") == "Different credentials ⚠"

    def test_format_env_sync_status_missing(self):
        """Format missing status correctly."""
        assert _format_env_sync_status("missing") == "No .env credentials"

    def test_format_env_sync_status_no_container_creds(self):
        """Format no_container_creds status correctly."""
        assert _format_env_sync_status("no_container_creds") == "Could not detect credentials"

    def test_format_env_sync_status_unknown(self):
        """Format unknown status correctly."""
        assert _format_env_sync_status("unknown") == "Unknown"

    def test_format_ports_empty(self):
        """Format empty port list."""
        assert _format_ports([]) == "no ports"

    def test_format_ports_single(self):
        """Format single port."""
        assert _format_ports(["7787->7687"]) == "7787->7687"

    def test_format_ports_multiple(self):
        """Format multiple ports."""
        assert _format_ports(["7787->7687", "7774->7474"]) == "7787->7687, 7774->7474"


class TestDetectContainerOptions:
    """Test container option detection."""

    @patch("amplihack.memory.neo4j.container_selection.discover_amplihack_containers")
    @patch("amplihack.neo4j.detector.Neo4jContainerDetector")
    @patch("amplihack.neo4j.credential_sync.CredentialSync")
    def test_detect_no_containers(self, mock_cred_sync_class, mock_detector_class, mock_discover):
        """Detect returns empty list when no containers exist."""
        mock_discover.return_value = []
        options = detect_container_options("amplihack-test")
        assert options == []

    @patch("amplihack.memory.neo4j.container_selection.discover_amplihack_containers")
    @patch("amplihack.neo4j.detector.Neo4jContainerDetector")
    @patch("amplihack.neo4j.credential_sync.CredentialSync")
    def test_detect_with_running_container(self, mock_cred_sync_class, mock_detector_class, mock_discover):
        """Detect returns options for running container."""
        # Mock container info
        mock_container = Mock()
        mock_container.name = "amplihack-test"
        mock_container.status = "Up 2 hours"
        mock_container.ports = ["7787->7687"]
        mock_discover.return_value = [mock_container]

        # Mock credential detection
        mock_detector = Mock()
        mock_detected = Mock()
        mock_detected.username = "neo4j"
        mock_detected.password = "FAKE_PASSWORD_FOR_TESTS"
        mock_detector.detect_container.return_value = mock_detected
        mock_detector_class.return_value = mock_detector

        # Mock credential sync
        mock_cred_sync = Mock()
        mock_cred_sync.get_existing_credentials.return_value = ("neo4j", "testpass")
        mock_cred_sync_class.return_value = mock_cred_sync

        options = detect_container_options("amplihack-test")
        assert len(options) == 1
        assert options[0].name == "amplihack-test"
        assert options[0].is_running is True
        assert options[0].username == "neo4j"
        assert options[0].env_sync_status == "match"

    @patch("amplihack.memory.neo4j.container_selection.discover_amplihack_containers")
    @patch("amplihack.neo4j.detector.Neo4jContainerDetector")
    @patch("amplihack.neo4j.credential_sync.CredentialSync")
    def test_detect_handles_credential_detection_failure(
        self, mock_cred_sync_class, mock_detector_class, mock_discover
    ):
        """Detect handles credential detection failures gracefully."""
        # Mock container info
        mock_container = Mock()
        mock_container.name = "amplihack-test"
        mock_container.status = "Up 2 hours"
        mock_container.ports = ["7787->7687"]
        mock_discover.return_value = [mock_container]

        # Mock credential detection to raise exception
        mock_detector = Mock()
        mock_detector.detect_container.side_effect = Exception("Connection failed")
        mock_detector_class.return_value = mock_detector

        # Mock credential sync
        mock_cred_sync = Mock()
        mock_cred_sync.get_existing_credentials.return_value = (None, None)
        mock_cred_sync_class.return_value = mock_cred_sync

        options = detect_container_options("amplihack-test")
        assert len(options) == 1
        assert options[0].name == "amplihack-test"
        assert options[0].username is None
        assert options[0].password is None
        assert options[0].env_sync_status == "no_container_creds"


class TestDisplayUnifiedDialog:
    """Test unified dialog display and interaction."""

    def test_display_no_containers(self, capsys):
        """Display returns new container option when no containers exist."""
        result = display_unified_dialog([], "amplihack-test")
        assert result is not None
        assert result.name == "amplihack-test"
        assert result.status == "new"
        assert result.is_running is False

        captured = capsys.readouterr()
        assert "No existing containers found" in captured.err
        assert "Creating new container: amplihack-test" in captured.err

    @patch("builtins.input")
    def test_display_select_existing_container(self, mock_input, capsys):
        """Display allows selecting existing container."""
        mock_input.return_value = "1"

        option = ContainerOption(
            name="amplihack-existing",
            status="Up 2 hours",
            ports=["7787->7687"],
            username="neo4j",
            password="FAKE_PASSWORD_FOR_TESTS",
            env_sync_status="match",
            is_running=True,
        )

        result = display_unified_dialog([option], "amplihack-test")
        assert result == option
        assert result.name == "amplihack-existing"

        captured = capsys.readouterr()
        assert "Existing containers:" in captured.err
        assert "amplihack-existing" in captured.err
        assert "✓ Selected: amplihack-existing" in captured.err

    @patch("builtins.input")
    def test_display_select_create_new(self, mock_input, capsys):
        """Display allows creating new container."""
        mock_input.return_value = "2"

        option = ContainerOption(
            name="amplihack-existing",
            status="Up 2 hours",
            ports=["7787->7687"],
            username="neo4j",
            password="FAKE_PASSWORD_FOR_TESTS",
            env_sync_status="match",
            is_running=True,
        )

        result = display_unified_dialog([option], "amplihack-new")
        assert result is not None
        assert result.name == "amplihack-new"
        assert result.status == "new"

        captured = capsys.readouterr()
        assert "Create new container: amplihack-new" in captured.err
        assert "✓ Creating new: amplihack-new" in captured.err

    @patch("builtins.input")
    def test_display_handles_invalid_input(self, mock_input, capsys):
        """Display handles invalid input gracefully."""
        # First invalid, then valid
        mock_input.side_effect = ["invalid", "1"]

        option = ContainerOption(
            name="amplihack-test",
            status="Up 2 hours",
            ports=["7787->7687"],
            username="neo4j",
            password="FAKE_PASSWORD_FOR_TESTS",
            env_sync_status="match",
            is_running=True,
        )

        result = display_unified_dialog([option], "amplihack-new")
        assert result == option

        captured = capsys.readouterr()
        assert "Please enter a valid number" in captured.err

    @patch("builtins.input")
    def test_display_handles_keyboard_interrupt(self, mock_input):
        """Display raises KeyboardInterrupt when user cancels."""
        mock_input.side_effect = KeyboardInterrupt()

        option = ContainerOption(
            name="amplihack-test",
            status="Up 2 hours",
            ports=["7787->7687"],
            username="neo4j",
            password="FAKE_PASSWORD_FOR_TESTS",
            env_sync_status="match",
            is_running=True,
        )

        with pytest.raises(KeyboardInterrupt):
            display_unified_dialog([option], "amplihack-new")


class TestHandleCredentialSync:
    """Test credential synchronization handling."""

    def test_new_container_no_credentials(self, capsys):
        """Handle new container with no .env credentials."""
        selected = ContainerOption(
            name="amplihack-test",
            status="new",
            ports=[],
            username=None,
            password=None,
            env_sync_status="missing",
            is_running=False,
        )

        with patch("amplihack.neo4j.credential_sync.CredentialSync") as mock_cred_sync_class:
            mock_cred_sync = Mock()
            mock_cred_sync.has_credentials.return_value = False
            mock_cred_sync_class.return_value = mock_cred_sync

            result = handle_credential_sync(selected)
            assert result is True

            captured = capsys.readouterr()
            assert "No .env credentials found" in captured.err

    def test_credentials_already_match(self, capsys):
        """Handle container with matching credentials."""
        selected = ContainerOption(
            name="amplihack-test",
            status="Up 2 hours",
            ports=["7787->7687"],
            username="neo4j",
            password="FAKE_PASSWORD_FOR_TESTS",
            env_sync_status="match",
            is_running=True,
        )

        result = handle_credential_sync(selected)
        assert result is True

        captured = capsys.readouterr()
        assert "credentials already match container" in captured.err

    def test_no_container_credentials(self, capsys):
        """Handle container with no detectable credentials."""
        selected = ContainerOption(
            name="amplihack-test",
            status="Up 2 hours",
            ports=["7787->7687"],
            username=None,
            password=None,
            env_sync_status="no_container_creds",
            is_running=True,
        )

        result = handle_credential_sync(selected)
        assert result is False

        captured = capsys.readouterr()
        assert "Could not detect container credentials" in captured.err

    @patch("builtins.input")
    def test_sync_credentials_user_accepts(self, mock_input, capsys):
        """Handle credential sync when user accepts."""
        mock_input.return_value = "y"

        selected = ContainerOption(
            name="amplihack-test",
            status="Up 2 hours",
            ports=["7787->7687"],
            username="neo4j",
            password="FAKE_PASSWORD_FOR_TESTS",
            env_sync_status="different",
            is_running=True,
        )

        with patch("amplihack.neo4j.credential_sync.CredentialSync") as mock_cred_sync_class:
            mock_cred_sync = Mock()
            mock_cred_sync.sync_credentials.return_value = True
            mock_cred_sync_class.return_value = mock_cred_sync

            result = handle_credential_sync(selected)
            assert result is True

            captured = capsys.readouterr()
            assert "Credentials synchronized to .env" in captured.err

    @patch("builtins.input")
    def test_sync_credentials_user_declines(self, mock_input, capsys):
        """Handle credential sync when user declines."""
        mock_input.return_value = "n"

        selected = ContainerOption(
            name="amplihack-test",
            status="Up 2 hours",
            ports=["7787->7687"],
            username="neo4j",
            password="FAKE_PASSWORD_FOR_TESTS",
            env_sync_status="different",
            is_running=True,
        )

        result = handle_credential_sync(selected)
        assert result is True

        captured = capsys.readouterr()
        assert "Using existing .env credentials" in captured.err

    @patch("builtins.input")
    def test_sync_credentials_fails(self, mock_input, capsys):
        """Handle credential sync failure."""
        mock_input.return_value = "y"

        selected = ContainerOption(
            name="amplihack-test",
            status="Up 2 hours",
            ports=["7787->7687"],
            username="neo4j",
            password="FAKE_PASSWORD_FOR_TESTS",
            env_sync_status="different",
            is_running=True,
        )

        with patch("amplihack.neo4j.credential_sync.CredentialSync") as mock_cred_sync_class:
            mock_cred_sync = Mock()
            mock_cred_sync.sync_credentials.return_value = False
            mock_cred_sync_class.return_value = mock_cred_sync

            result = handle_credential_sync(selected)
            assert result is False

            captured = capsys.readouterr()
            assert "Failed to sync credentials" in captured.err


class TestUnifiedDialog:
    """Test unified dialog entry point."""

    @patch("amplihack.memory.neo4j.container_selection.get_default_container_name")
    def test_auto_mode_uses_default(self, mock_get_default):
        """Auto mode returns default name without dialog."""
        mock_get_default.return_value = "amplihack-auto"

        result = unified_container_and_credential_dialog(auto_mode=True)
        assert result == "amplihack-auto"

    @patch("amplihack.memory.neo4j.container_selection.get_default_container_name")
    def test_uses_provided_default_name(self, mock_get_default):
        """Uses provided default name instead of auto-detected."""
        result = unified_container_and_credential_dialog(
            default_name="amplihack-custom",
            auto_mode=True
        )
        assert result == "amplihack-custom"
        mock_get_default.assert_not_called()

    @patch("amplihack.memory.neo4j.unified_startup_dialog.detect_container_options")
    @patch("amplihack.memory.neo4j.unified_startup_dialog.display_unified_dialog")
    @patch("amplihack.memory.neo4j.unified_startup_dialog.handle_credential_sync")
    def test_interactive_mode_full_flow(
        self, mock_handle_sync, mock_display, mock_detect
    ):
        """Interactive mode executes full dialog flow."""
        # Mock detection
        option = ContainerOption(
            name="amplihack-test",
            status="Up 2 hours",
            ports=["7787->7687"],
            username="neo4j",
            password="FAKE_PASSWORD_FOR_TESTS",
            env_sync_status="match",
            is_running=True,
        )
        mock_detect.return_value = [option]

        # Mock display returning selection
        mock_display.return_value = option

        # Mock credential sync
        mock_handle_sync.return_value = True

        result = unified_container_and_credential_dialog(
            default_name="amplihack-test",
            auto_mode=False
        )

        assert result == "amplihack-test"
        mock_detect.assert_called_once()
        mock_display.assert_called_once()
        mock_handle_sync.assert_called_once()

    @patch("amplihack.memory.neo4j.unified_startup_dialog.detect_container_options")
    @patch("amplihack.memory.neo4j.unified_startup_dialog.display_unified_dialog")
    def test_handles_keyboard_interrupt(self, mock_display, mock_detect):
        """Propagates KeyboardInterrupt from dialog."""
        mock_detect.return_value = []
        mock_display.side_effect = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            unified_container_and_credential_dialog(
                default_name="amplihack-test",
                auto_mode=False
            )

    @patch("amplihack.memory.neo4j.unified_startup_dialog.detect_container_options")
    def test_handles_exception_gracefully(self, mock_detect):
        """Handles exceptions by returning default name."""
        mock_detect.side_effect = Exception("Unexpected error")

        result = unified_container_and_credential_dialog(
            default_name="amplihack-fallback",
            auto_mode=False
        )

        assert result == "amplihack-fallback"

    @patch("amplihack.memory.neo4j.unified_startup_dialog.detect_container_options")
    @patch("amplihack.memory.neo4j.unified_startup_dialog.display_unified_dialog")
    def test_handles_user_cancellation(self, mock_display, mock_detect):
        """Returns None when user cancels dialog."""
        mock_detect.return_value = []
        mock_display.return_value = None

        result = unified_container_and_credential_dialog(
            default_name="amplihack-test",
            auto_mode=False
        )

        assert result is None
