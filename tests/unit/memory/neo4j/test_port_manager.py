"""
Unit tests for Neo4j port management with container port detection.

Tests the port_manager module responsible for:
- get_container_ports() - querying actual container ports via docker
- resolve_port_conflicts() - detecting conflicts and updating .env
- Port availability checking
- Neo4j instance detection

Focus on the new container port detection functionality.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from amplihack.memory.neo4j.port_manager import (
    find_available_port,
    get_container_ports,
    is_port_in_use,
    resolve_port_conflicts,
)


class TestGetContainerPorts:
    """Test get_container_ports() function for Docker port detection."""

    def test_WHEN_container_running_with_standard_output_THEN_ports_extracted(self):
        """Test successful port extraction with standard Docker output format."""
        mock_output = """7474/tcp -> 0.0.0.0:7774
7687/tcp -> 0.0.0.0:7787
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )

            result = get_container_ports("amplihack-neo4j")

            assert result == (7787, 7774)  # (bolt, http)
            mock_run.assert_called_once_with(
                ["docker", "port", "amplihack-neo4j"],
                capture_output=True,
                timeout=5,
                text=True,
                check=False,
            )

    def test_WHEN_container_running_with_ipv6_format_THEN_ports_extracted(self):
        """Test port extraction with IPv6 format output."""
        mock_output = """7474/tcp -> [::]:7774
7687/tcp -> [::]:7787
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )

            result = get_container_ports("amplihack-neo4j")

            assert result == (7787, 7774)

    def test_WHEN_container_running_with_mixed_formats_THEN_ports_extracted(self):
        """Test port extraction with mixed IPv4/IPv6 output."""
        mock_output = """7474/tcp -> 0.0.0.0:7774
7474/tcp -> [::]:7774
7687/tcp -> 0.0.0.0:7787
7687/tcp -> [::]:7787
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )

            result = get_container_ports("amplihack-neo4j")

            # Should find both ports from first occurrence
            assert result == (7787, 7774)

    def test_WHEN_container_running_with_non_standard_ports_THEN_actual_ports_extracted(self):
        """Test port extraction when container uses non-standard host ports."""
        mock_output = """7474/tcp -> 0.0.0.0:8888
7687/tcp -> 0.0.0.0:9999
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )

            result = get_container_ports("amplihack-neo4j")

            assert result == (9999, 8888)  # bolt=9999, http=8888

    def test_WHEN_container_not_found_THEN_returns_none(self):
        """Test container not found (non-zero exit code)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stdout="",
                stderr="Error: No such container: amplihack-neo4j"
            )

            result = get_container_ports("amplihack-neo4j")

            assert result is None

    def test_WHEN_output_malformed_with_only_one_port_THEN_returns_none(self):
        """Test parsing error when only one port is present."""
        mock_output = """7687/tcp -> 0.0.0.0:7787
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )

            result = get_container_ports("amplihack-neo4j")

            # Missing HTTP port - should return None
            assert result is None

    def test_WHEN_output_malformed_with_invalid_format_THEN_returns_none(self):
        """Test parsing error with completely malformed output."""
        mock_output = """invalid output format
no port mappings here
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )

            result = get_container_ports("amplihack-neo4j")

            assert result is None

    def test_WHEN_output_has_non_numeric_ports_THEN_returns_none(self):
        """Test parsing error when port numbers are not valid integers."""
        mock_output = """7474/tcp -> 0.0.0.0:invalid
7687/tcp -> 0.0.0.0:notaport
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )

            result = get_container_ports("amplihack-neo4j")

            assert result is None

    def test_WHEN_command_times_out_THEN_returns_none(self):
        """Test timeout handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["docker", "port", "amplihack-neo4j"],
                timeout=5
            )

            result = get_container_ports("amplihack-neo4j")

            assert result is None

    def test_WHEN_unexpected_exception_THEN_returns_none(self):
        """Test graceful handling of unexpected exceptions."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Unexpected error")

            result = get_container_ports("amplihack-neo4j")

            assert result is None

    def test_WHEN_empty_output_THEN_returns_none(self):
        """Test handling of empty output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="",
                stderr=""
            )

            result = get_container_ports("amplihack-neo4j")

            assert result is None

    def test_WHEN_output_has_extra_whitespace_THEN_ports_extracted(self):
        """Test robustness to extra whitespace in output."""
        mock_output = """  7474/tcp -> 0.0.0.0:7774
  7687/tcp -> 0.0.0.0:7787
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )

            result = get_container_ports("amplihack-neo4j")

            assert result == (7787, 7774)


class TestResolvePortConflictsWithContainer:
    """Test resolve_port_conflicts() integration with get_container_ports()."""

    def test_WHEN_container_ports_match_env_THEN_no_update_needed(self):
        """Test matching ports - no .env update needed."""
        with patch("amplihack.memory.neo4j.port_manager.get_container_ports") as mock_get_ports:
            mock_get_ports.return_value = (7787, 7774)  # Matches bolt/http args

            bolt, http, messages = resolve_port_conflicts(
                bolt_port=7787,
                http_port=7774,
                password="test_pass",
                project_root=None
            )

            assert bolt == 7787
            assert http == 7774
            assert any("Our Neo4j container found" in msg for msg in messages)
            assert any("7787/7774" in msg for msg in messages)

    def test_WHEN_container_ports_mismatch_env_THEN_env_updated(self):
        """Test mismatched ports - .env should be updated to match container."""
        # Container is running on 8888/9999 but .env says 7787/7774
        with patch("amplihack.memory.neo4j.port_manager.get_container_ports") as mock_get_ports, \
             patch("amplihack.memory.neo4j.port_manager._update_env_ports") as mock_update_env:

            mock_get_ports.return_value = (8888, 9999)  # Container actual ports

            project_root = Path("/fake/project")
            bolt, http, messages = resolve_port_conflicts(
                bolt_port=7787,  # What .env thinks
                http_port=7774,
                password="test_pass",
                project_root=project_root
            )

            # Should return container's actual ports
            assert bolt == 8888
            assert http == 9999

            # Should update .env to match
            mock_update_env.assert_called_once_with(project_root, 8888, 9999)

            # Check messages
            assert any("Container running on ports 8888/9999" in msg for msg in messages)
            assert any("but .env specifies 7787/7774" in msg for msg in messages)
            assert any("Updated .env with actual container ports" in msg for msg in messages)

    def test_WHEN_container_ports_mismatch_and_env_update_fails_THEN_warning_shown(self):
        """Test graceful handling when .env update fails."""
        with patch("amplihack.memory.neo4j.port_manager.get_container_ports") as mock_get_ports, \
             patch("amplihack.memory.neo4j.port_manager._update_env_ports") as mock_update_env:

            mock_get_ports.return_value = (8888, 9999)
            mock_update_env.side_effect = IOError("Permission denied")

            bolt, http, messages = resolve_port_conflicts(
                bolt_port=7787,
                http_port=7774,
                password="test_pass",
                project_root=Path("/fake/project")
            )

            # Should still return correct ports
            assert bolt == 8888
            assert http == 9999

            # Should warn about update failure
            assert any("Could not update .env" in msg for msg in messages)
            assert any("Permission denied" in msg for msg in messages)

    def test_WHEN_no_container_running_THEN_falls_through_to_existing_logic(self):
        """Test that when no container is found, existing port conflict logic runs."""
        with patch("amplihack.memory.neo4j.port_manager.get_container_ports") as mock_get_ports, \
             patch("amplihack.memory.neo4j.port_manager.is_port_in_use") as mock_port_in_use:

            mock_get_ports.return_value = None  # No container
            mock_port_in_use.return_value = False  # Ports available

            bolt, http, messages = resolve_port_conflicts(
                bolt_port=7787,
                http_port=7774,
                password="test_pass",
                project_root=None
            )

            # Should use requested ports
            assert bolt == 7787
            assert http == 7774

            # Should check port availability (existing behavior)
            mock_port_in_use.assert_called()
            assert any("available" in msg.lower() for msg in messages)

    def test_WHEN_no_container_and_ports_in_use_THEN_finds_alternatives(self):
        """Test fallback to finding alternative ports when no container and ports busy."""
        with patch("amplihack.memory.neo4j.port_manager.get_container_ports") as mock_get_ports, \
             patch("amplihack.memory.neo4j.port_manager.is_port_in_use") as mock_port_in_use, \
             patch("amplihack.memory.neo4j.port_manager.find_available_port") as mock_find_port, \
             patch("amplihack.memory.neo4j.port_manager.detect_neo4j_on_port") as mock_detect:

            mock_get_ports.return_value = None  # No container
            mock_port_in_use.return_value = True  # Ports busy
            mock_detect.return_value = (False, False)  # Not Neo4j
            mock_find_port.side_effect = [7888, 7874]  # Alternative ports

            bolt, http, messages = resolve_port_conflicts(
                bolt_port=7787,
                http_port=7774,
                password="test_pass",
                project_root=None
            )

            # Should find alternatives
            assert bolt == 7888
            assert http == 7874

            # Should report conflict and alternatives
            assert any("in use" in msg.lower() for msg in messages)
            assert any("alternative" in msg.lower() for msg in messages)


class TestPortAvailability:
    """Test basic port availability checking functions."""

    def test_WHEN_port_available_THEN_is_port_in_use_returns_false(self):
        """Test that available ports are correctly detected."""
        # Mock socket to simulate available port
        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.return_value = 1  # Non-zero = not in use
            mock_socket_class.return_value.__enter__.return_value = mock_socket

            result = is_port_in_use(9999)

            assert result is False

    def test_WHEN_port_in_use_THEN_is_port_in_use_returns_true(self):
        """Test that busy ports are correctly detected."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket = Mock()
            mock_socket.connect_ex.return_value = 0  # Zero = in use
            mock_socket_class.return_value.__enter__.return_value = mock_socket

            result = is_port_in_use(9999)

            assert result is True

    def test_WHEN_finding_available_port_THEN_returns_first_free(self):
        """Test find_available_port returns first available port."""
        with patch("amplihack.memory.neo4j.port_manager.is_port_in_use") as mock_in_use:
            # First 3 ports busy, 4th free
            mock_in_use.side_effect = [True, True, True, False]

            result = find_available_port(8000)

            assert result == 8003  # 8000, 8001, 8002 busy -> 8003 free

    def test_WHEN_no_ports_available_in_range_THEN_returns_none(self):
        """Test find_available_port returns None when range exhausted."""
        with patch("amplihack.memory.neo4j.port_manager.is_port_in_use") as mock_in_use:
            mock_in_use.return_value = True  # All ports busy

            result = find_available_port(8000, max_attempts=10)

            assert result is None
            assert mock_in_use.call_count == 10


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_WHEN_container_output_has_blank_lines_THEN_handled_gracefully(self):
        """Test that blank lines in docker output don't cause issues."""
        mock_output = """

7474/tcp -> 0.0.0.0:7774


7687/tcp -> 0.0.0.0:7787

"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=mock_output, stderr="")

            result = get_container_ports()

            assert result == (7787, 7774)

    def test_WHEN_container_name_is_custom_THEN_correct_container_queried(self):
        """Test that custom container names are passed correctly."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Not found")

            result = get_container_ports("my-custom-neo4j")

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "my-custom-neo4j" in call_args

    def test_WHEN_project_root_is_none_THEN_no_env_update_attempted(self):
        """Test that .env update is skipped when project_root is None."""
        with patch("amplihack.memory.neo4j.port_manager.get_container_ports") as mock_get_ports, \
             patch("amplihack.memory.neo4j.port_manager._update_env_ports") as mock_update_env:

            mock_get_ports.return_value = (8888, 9999)

            bolt, http, messages = resolve_port_conflicts(
                bolt_port=7787,
                http_port=7774,
                password="test_pass",
                project_root=None  # No project root
            )

            # Should not attempt .env update
            mock_update_env.assert_not_called()

            # But should still return correct ports
            assert bolt == 8888
            assert http == 9999

    def test_WHEN_ports_are_zero_THEN_returns_none(self):
        """Test edge case of port 0 - should be treated as invalid."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="7474/tcp -> 0.0.0.0:0\n7687/tcp -> 0.0.0.0:0",
                stderr=""
            )

            result = get_container_ports()

            # Port 0 parsed but treated as invalid (falsy check in line 153)
            # This is correct - Neo4j can't actually listen on port 0
            assert result is None

    def test_WHEN_high_port_numbers_THEN_handled_correctly(self):
        """Test handling of high port numbers (near 65535)."""
        mock_output = """7474/tcp -> 0.0.0.0:65534
7687/tcp -> 0.0.0.0:65535
"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=mock_output, stderr="")

            result = get_container_ports()

            assert result == (65535, 65534)


class TestIntegrationScenarios:
    """Integration-style tests simulating real-world scenarios."""

    def test_SCENARIO_container_restarted_on_different_ports(self):
        """
        Scenario: Container was restarted by Docker on different ports.
        .env still has old ports. Should detect and update.
        """
        with patch("amplihack.memory.neo4j.port_manager.get_container_ports") as mock_get_ports, \
             patch("amplihack.memory.neo4j.port_manager._update_env_ports") as mock_update_env:

            # Container now on 7888/7874 instead of 7787/7774
            mock_get_ports.return_value = (7888, 7874)

            project_root = Path("/project")
            bolt, http, messages = resolve_port_conflicts(
                bolt_port=7787,  # Old port from .env
                http_port=7774,
                password="test_pass",
                project_root=project_root
            )

            # Should update to container's actual ports
            assert bolt == 7888
            assert http == 7874
            mock_update_env.assert_called_once_with(project_root, 7888, 7874)

    def test_SCENARIO_first_startup_no_container(self):
        """
        Scenario: First time starting - no container exists yet.
        Should fall through to normal port selection.
        """
        with patch("amplihack.memory.neo4j.port_manager.get_container_ports") as mock_get_ports, \
             patch("amplihack.memory.neo4j.port_manager.is_port_in_use") as mock_port_in_use:

            mock_get_ports.return_value = None  # No container
            mock_port_in_use.return_value = False  # Ports free

            bolt, http, messages = resolve_port_conflicts(
                bolt_port=7787,
                http_port=7774,
                password="test_pass",
                project_root=None
            )

            assert bolt == 7787
            assert http == 7774
            assert any("available" in msg.lower() for msg in messages)

    def test_SCENARIO_container_exists_ports_match(self):
        """
        Scenario: Container running on expected ports. Happy path.
        Should just return confirmation.
        """
        with patch("amplihack.memory.neo4j.port_manager.get_container_ports") as mock_get_ports:
            mock_get_ports.return_value = (7787, 7774)

            bolt, http, messages = resolve_port_conflicts(
                bolt_port=7787,
                http_port=7774,
                password="test_pass",
                project_root=None
            )

            assert bolt == 7787
            assert http == 7774
            assert any("✅" in msg for msg in messages)
            assert any("found" in msg.lower() for msg in messages)
