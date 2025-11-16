"""Tests for container naming and selection system."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

from amplihack.memory.neo4j.container_selection import (
    ContainerInfo,
    NameResolutionContext,
    discover_amplihack_containers,
    format_ports,
    get_default_container_name,
    resolve_container_name,
    sanitize_directory_name,
)


class TestSanitization:
    """Test directory name sanitization."""

    def test_simple_name(self):
        """Simple alphanumeric name passes through."""
        assert sanitize_directory_name("myproject") == "myproject"

    def test_special_chars_replaced(self):
        """Special characters are replaced with dashes."""
        assert sanitize_directory_name("my_project.v2") == "my-project-v2"
        assert sanitize_directory_name("my@project#123") == "my-project-123"

    def test_consecutive_dashes_removed(self):
        """Consecutive dashes are collapsed to single dash."""
        assert sanitize_directory_name("my---project") == "my-project"

    def test_leading_trailing_dashes_removed(self):
        """Leading and trailing dashes are removed."""
        assert sanitize_directory_name("-myproject-") == "myproject"

    def test_truncation(self):
        """Long names are truncated at 40 characters."""
        long_name = "a" * 50
        result = sanitize_directory_name(long_name)
        assert len(result) == 40
        assert result == "a" * 40


class TestDefaultContainerName:
    """Test default container name generation."""

    def test_default_name_format(self):
        """Default name has amplihack- prefix."""
        name = get_default_container_name(Path("/home/user/myproject"))
        assert name == "amplihack-myproject"

    def test_special_chars_sanitized(self):
        """Special characters in directory name are sanitized."""
        name = get_default_container_name(Path("/home/user/my_project.v2"))
        assert name == "amplihack-my-project-v2"

    def test_long_directory_name(self):
        """Long directory names are truncated."""
        long_dir = "a" * 50
        name = get_default_container_name(Path(f"/home/user/{long_dir}"))
        assert name.startswith("amplihack-")
        assert len(name) <= 51  # amplihack- (10) + 40 chars + dash (1)


class TestFormatPorts:
    """Test port formatting."""

    def test_empty_ports(self):
        """Empty port list returns 'no ports'."""
        assert format_ports([]) == "no ports"

    def test_single_port(self):
        """Single port is formatted correctly."""
        assert format_ports(["7787->7687"]) == "7787->7687"

    def test_multiple_ports(self):
        """Multiple ports are comma-separated."""
        ports = ["7787->7687", "7774->7474"]
        assert format_ports(ports) == "7787->7687, 7774->7474"


class TestNameResolution:
    """Test container name resolution logic."""

    def test_cli_arg_takes_priority(self):
        """CLI argument has highest priority."""
        context = NameResolutionContext(
            cli_arg="custom-container",
            env_var="env-container",
            current_dir=Path("/home/user/project"),
            auto_mode=False,
        )
        result = resolve_container_name(context=context)
        assert result == "custom-container"

    def test_env_var_second_priority(self):
        """Environment variable is used if no CLI arg."""
        context = NameResolutionContext(
            cli_arg=None,
            env_var="env-container",
            current_dir=Path("/home/user/project"),
            auto_mode=False,
        )
        # Mock discover to return empty list
        with patch(
            "amplihack.memory.neo4j.container_selection.discover_amplihack_containers",
            return_value=[],
        ):
            result = resolve_container_name(context=context)
            assert result == "env-container"

    def test_auto_mode_uses_default(self):
        """Auto mode uses default without prompting."""
        context = NameResolutionContext(
            cli_arg=None,
            env_var=None,
            current_dir=Path("/home/user/myproject"),
            auto_mode=True,
        )
        result = resolve_container_name(context=context)
        assert result == "amplihack-myproject"

    @patch("amplihack.memory.neo4j.container_selection.discover_amplihack_containers")
    @patch("builtins.input")
    def test_interactive_selection_create_new(self, mock_input, mock_discover):
        """Interactive mode can create new container."""
        mock_discover.return_value = [
            ContainerInfo("amplihack-project1", "Up 2 hours", ["7787->7687"])
        ]
        # Select option 2 (create new)
        mock_input.return_value = "2"

        context = NameResolutionContext(
            cli_arg=None,
            env_var=None,
            current_dir=Path("/home/user/myproject"),
            auto_mode=False,
        )
        result = resolve_container_name(context=context)
        assert result == "amplihack-myproject"

    @patch("amplihack.memory.neo4j.container_selection.discover_amplihack_containers")
    @patch("builtins.input")
    def test_interactive_selection_existing(self, mock_input, mock_discover):
        """Interactive mode can select existing container."""
        mock_discover.return_value = [
            ContainerInfo("amplihack-project1", "Up 2 hours", ["7787->7687"])
        ]
        # Select option 1 (existing container)
        mock_input.return_value = "1"

        context = NameResolutionContext(
            cli_arg=None,
            env_var=None,
            current_dir=Path("/home/user/myproject"),
            auto_mode=False,
        )
        result = resolve_container_name(context=context)
        assert result == "amplihack-project1"


class TestDiscovery:
    """Test container discovery."""

    @patch("subprocess.run")
    def test_discover_no_containers(self, mock_run):
        """Discovery returns empty list when no containers found."""
        # Mock docker ps returning empty
        mock_run.return_value = Mock(returncode=0, stdout="")
        result = discover_amplihack_containers()
        assert result == []

    @patch("subprocess.run")
    def test_discover_with_containers(self, mock_run):
        """Discovery returns container list."""
        # Mock docker ps returning container names
        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            if "{{.Names}}" in cmd:
                return Mock(returncode=0, stdout="amplihack-project1\namplihack-project2\n")
            if "{{.Status}}" in cmd:
                return Mock(returncode=0, stdout="Up 2 hours")
            if "inspect" in cmd:
                return Mock(returncode=0, stdout='{"7687/tcp":[{"HostPort":"7787"}]}')
            return Mock(returncode=1, stdout="")

        mock_run.side_effect = run_side_effect
        result = discover_amplihack_containers()
        assert len(result) == 2
        assert result[0].name == "amplihack-project1"
        assert result[1].name == "amplihack-project2"

    @patch("subprocess.run")
    def test_discover_docker_not_available(self, mock_run):
        """Discovery handles Docker not being available."""
        mock_run.return_value = Mock(returncode=1, stdout="")
        result = discover_amplihack_containers()
        assert result == []


class TestEnvironmentVariableIntegration:
    """Test integration with environment variables."""

    def test_reads_cli_from_env(self):
        """Reads CLI arg from NEO4J_CONTAINER_NAME_CLI env var."""
        with patch.dict(os.environ, {"NEO4J_CONTAINER_NAME_CLI": "test-container"}):
            result = resolve_container_name(
                cli_arg=None,
                env_var=None,
                current_dir=Path("/home/user/project"),
                auto_mode=True,
            )
            assert result == "test-container"

    def test_cli_arg_overrides_env(self):
        """Direct CLI arg overrides environment variable."""
        with patch.dict(os.environ, {"NEO4J_CONTAINER_NAME_CLI": "env-container"}):
            result = resolve_container_name(
                cli_arg="direct-container",
                env_var=None,
                current_dir=Path("/home/user/project"),
                auto_mode=True,
            )
            assert result == "direct-container"
