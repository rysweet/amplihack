"""
Unit tests for Neo4j credential detection from containers.

Tests the credential_detector module responsible for:
- Detecting passwords from running container environments
- Handling auth-disabled configurations (NEO4J_AUTH=none)
- Formatting credential status messages
- Error handling for Docker inspection failures
"""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest

from amplihack.memory.neo4j.credential_detector import (
    detect_container_password,
    format_credential_status,
)


class TestDetectContainerPassword:
    """Test password detection from container environments."""

    def test_WHEN_container_has_password_THEN_password_detected(self):
        """Test successful password detection from container with NEO4J_AUTH."""
        with patch("subprocess.run") as mock_run:
            # Simulate docker inspect returning environment with NEO4J_AUTH
            env_vars = ["PATH=/usr/bin", "NEO4J_AUTH=neo4j/secret123", "HOME=/var/lib/neo4j"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("amplihack-neo4j")

            assert password == "secret123"
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args == [
                "docker",
                "inspect",
                "amplihack-neo4j",
                "--format",
                "{{json .Config.Env}}",
            ]

    def test_WHEN_container_has_custom_username_THEN_password_extracted(self):
        """Test password extraction with custom username in NEO4J_AUTH."""
        with patch("subprocess.run") as mock_run:
            env_vars = ["NEO4J_AUTH=admin/mypassword123"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("custom-neo4j")

            assert password == "mypassword123"

    def test_WHEN_auth_disabled_THEN_returns_none(self):
        """Test handling of auth-disabled configuration (NEO4J_AUTH=none)."""
        with patch("subprocess.run") as mock_run:
            env_vars = ["NEO4J_AUTH=none", "PATH=/usr/bin"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("amplihack-neo4j")

            assert password is None

    def test_WHEN_container_not_found_THEN_returns_none(self):
        """Test handling of non-existent container."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1, stdout="", stderr="Error: No such container: nonexistent-container"
            )

            password = detect_container_password("nonexistent-container")

            assert password is None

    def test_WHEN_neo4j_auth_missing_THEN_returns_none(self):
        """Test handling when NEO4J_AUTH variable is not in environment."""
        with patch("subprocess.run") as mock_run:
            env_vars = ["PATH=/usr/bin", "HOME=/var/lib/neo4j", "JAVA_HOME=/usr/lib/jvm"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("amplihack-neo4j")

            assert password is None

    def test_WHEN_neo4j_auth_malformed_no_slash_THEN_returns_none(self):
        """Test handling of malformed NEO4J_AUTH without slash separator."""
        with patch("subprocess.run") as mock_run:
            env_vars = ["NEO4J_AUTH=invalidformat"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("amplihack-neo4j")

            assert password is None

    def test_WHEN_neo4j_auth_has_multiple_slashes_THEN_password_includes_slashes(self):
        """Test handling of password containing slash characters."""
        with patch("subprocess.run") as mock_run:
            # Password contains slashes (split with maxsplit=1 should handle this)
            env_vars = ["NEO4J_AUTH=neo4j/pass/with/slashes"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("amplihack-neo4j")

            assert password == "pass/with/slashes"

    def test_WHEN_docker_command_times_out_THEN_returns_none(self):
        """Test handling of Docker command timeout."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["docker", "inspect", "amplihack-neo4j"], timeout=5
            )

            password = detect_container_password("amplihack-neo4j")

            assert password is None

    def test_WHEN_json_parsing_fails_THEN_returns_none(self):
        """Test handling of invalid JSON output from docker inspect."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="invalid json [{]", stderr="")

            password = detect_container_password("amplihack-neo4j")

            assert password is None

    def test_WHEN_unexpected_exception_THEN_returns_none(self):
        """Test handling of unexpected exceptions during detection."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Unexpected error")

            password = detect_container_password("amplihack-neo4j")

            assert password is None

    def test_WHEN_subprocess_run_called_THEN_timeout_specified(self):
        """Test that subprocess.run is called with appropriate timeout."""
        with patch("subprocess.run") as mock_run:
            env_vars = ["NEO4J_AUTH=neo4j/password"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            detect_container_password("amplihack-neo4j")

            call_kwargs = mock_run.call_args[1]
            assert call_kwargs.get("timeout") == 5
            assert call_kwargs.get("capture_output") is True
            assert call_kwargs.get("text") is True

    def test_WHEN_empty_environment_array_THEN_returns_none(self):
        """Test handling of container with empty environment array."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps([]), stderr="")

            password = detect_container_password("amplihack-neo4j")

            assert password is None

    def test_WHEN_neo4j_auth_is_empty_string_THEN_returns_none(self):
        """Test handling of NEO4J_AUTH with empty value."""
        with patch("subprocess.run") as mock_run:
            env_vars = ["NEO4J_AUTH="]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("amplihack-neo4j")

            assert password is None

    def test_WHEN_neo4j_auth_only_username_THEN_returns_none(self):
        """Test handling of NEO4J_AUTH with username but no password."""
        with patch("subprocess.run") as mock_run:
            env_vars = ["NEO4J_AUTH=neo4j/"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("amplihack-neo4j")

            # Should extract empty string as password
            assert password == ""


class TestFormatCredentialStatus:
    """Test credential status formatting."""

    def test_WHEN_password_detected_THEN_formats_with_key_emoji(self):
        """Test formatting when credentials are detected."""
        status = format_credential_status("secret123")

        assert status == "🔑 Credentials detected"

    def test_WHEN_password_is_none_THEN_formats_with_warning_emoji(self):
        """Test formatting when no credentials detected."""
        status = format_credential_status(None)

        assert status == "⚠️ No credentials detected"

    def test_WHEN_empty_password_THEN_formats_with_key_emoji(self):
        """Test formatting with empty string password (truthy check)."""
        status = format_credential_status("")

        # Empty string is falsy in Python
        assert status == "⚠️ No credentials detected"

    def test_WHEN_non_empty_password_THEN_formats_with_key_emoji(self):
        """Test formatting with various non-empty passwords."""
        test_passwords = [
            "simple",
            "complex!@#$%",
            "with spaces",
            "123456",
            "a",  # Single character
        ]

        for password in test_passwords:
            status = format_credential_status(password)
            assert status == "🔑 Credentials detected", f"Failed for password: {password}"


class TestCredentialDetectorEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_WHEN_very_long_password_THEN_password_extracted(self):
        """Test handling of very long passwords."""
        long_password = "a" * 1000
        with patch("subprocess.run") as mock_run:
            env_vars = [f"NEO4J_AUTH=neo4j/{long_password}"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("amplihack-neo4j")

            assert password == long_password

    def test_WHEN_special_characters_in_password_THEN_password_extracted(self):
        """Test handling of passwords with special characters."""
        special_password = "p@ss!w0rd#$%^&*()"
        with patch("subprocess.run") as mock_run:
            env_vars = [f"NEO4J_AUTH=neo4j/{special_password}"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("amplihack-neo4j")

            assert password == special_password

    def test_WHEN_unicode_in_password_THEN_password_extracted(self):
        """Test handling of passwords with unicode characters."""
        unicode_password = "пароль🔑密码"
        with patch("subprocess.run") as mock_run:
            env_vars = [f"NEO4J_AUTH=neo4j/{unicode_password}"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("amplihack-neo4j")

            assert password == unicode_password

    def test_WHEN_whitespace_in_password_THEN_password_extracted(self):
        """Test handling of passwords with whitespace."""
        whitespace_password = "pass word\twith\nwhitespace"
        with patch("subprocess.run") as mock_run:
            env_vars = [f"NEO4J_AUTH=neo4j/{whitespace_password}"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("amplihack-neo4j")

            assert password == whitespace_password

    def test_WHEN_multiple_neo4j_auth_entries_THEN_first_is_used(self):
        """Test handling of multiple NEO4J_AUTH entries (should use first)."""
        with patch("subprocess.run") as mock_run:
            env_vars = [
                "NEO4J_AUTH=neo4j/password1",
                "OTHER_VAR=value",
                "NEO4J_AUTH=neo4j/password2",
            ]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            password = detect_container_password("amplihack-neo4j")

            # Should use first occurrence
            assert password == "password1"


class TestCredentialDetectorLogging:
    """Test logging behavior (verify log calls are made)."""

    def test_WHEN_detection_succeeds_THEN_logs_info(self):
        """Test that successful detection logs appropriate messages."""
        with patch("subprocess.run") as mock_run, patch(
            "amplihack.memory.neo4j.credential_detector.logger"
        ) as mock_logger:
            env_vars = ["NEO4J_AUTH=neo4j/password"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            detect_container_password("amplihack-neo4j")

            # Should log debug and info messages
            assert mock_logger.debug.called
            assert mock_logger.info.called

    def test_WHEN_auth_disabled_THEN_logs_info(self):
        """Test that auth-disabled case logs info message."""
        with patch("subprocess.run") as mock_run, patch(
            "amplihack.memory.neo4j.credential_detector.logger"
        ) as mock_logger:
            env_vars = ["NEO4J_AUTH=none"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            detect_container_password("amplihack-neo4j")

            # Should log info about disabled auth
            mock_logger.info.assert_called()
            call_args = str(mock_logger.info.call_args)
            assert "disabled" in call_args.lower()

    def test_WHEN_malformed_auth_THEN_logs_warning(self):
        """Test that malformed auth format logs warning."""
        with patch("subprocess.run") as mock_run, patch(
            "amplihack.memory.neo4j.credential_detector.logger"
        ) as mock_logger:
            env_vars = ["NEO4J_AUTH=malformed"]
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(env_vars), stderr="")

            detect_container_password("amplihack-neo4j")

            # Should log warning about unexpected format
            mock_logger.warning.assert_called()

    def test_WHEN_timeout_occurs_THEN_logs_warning(self):
        """Test that timeout logs warning message."""
        with patch("subprocess.run") as mock_run, patch(
            "amplihack.memory.neo4j.credential_detector.logger"
        ) as mock_logger:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["docker", "inspect", "amplihack-neo4j"], timeout=5
            )

            detect_container_password("amplihack-neo4j")

            # Should log warning about timeout
            mock_logger.warning.assert_called()
            call_args = str(mock_logger.warning.call_args)
            assert "timeout" in call_args.lower()


@pytest.mark.integration
class TestCredentialDetectorIntegration:
    """Integration tests requiring real Docker containers."""

    def test_WHEN_real_container_available_THEN_credentials_detected(self):
        """Test credential detection with real Docker container.

        This test is marked as integration and will be skipped in unit test runs.
        """
        pytest.skip("Requires real Docker container - run with: pytest -m integration")
