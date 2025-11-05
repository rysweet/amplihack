"""
Unit tests for Neo4j dependency checking and goal-seeking agent.

Tests the DependencyAgent class responsible for:
- Checking Docker daemon availability
- Checking Python package dependencies
- Checking port availability
- Providing remediation guidance
- Validating full prerequisite chain

All tests should FAIL initially (TDD approach).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestDockerDaemonCheck:
    """Test Docker daemon detection."""

    def test_WHEN_docker_installed_and_running_THEN_check_passes(self):
        """Test successful Docker daemon check."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Docker version 24.0.0")

            result = agent.check_docker_daemon()

            assert result.success is True
            assert result.message or result.details

    def test_WHEN_docker_not_installed_THEN_check_fails_with_guidance(self):
        """Test Docker not installed scenario."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("docker: command not found")

            result = agent.check_docker_daemon()

            assert result.success is False
            assert "install" in result.remediation.lower()
            assert "docker" in result.remediation.lower()

    def test_WHEN_docker_daemon_not_running_THEN_check_fails_with_start_guidance(self):
        """Test Docker installed but daemon not running."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stderr="Cannot connect to the Docker daemon"
            )

            result = agent.check_docker_daemon()

            assert result.success is False
            assert "start" in result.remediation.lower() or "running" in result.remediation.lower()

    def test_WHEN_docker_permission_denied_THEN_check_fails_with_permission_guidance(self):
        """Test Docker permission issues."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=1,
                stderr="permission denied"
            )

            result = agent.check_docker_daemon()

            assert result.success is False
            assert "permission" in result.remediation.lower()
            assert "usermod" in result.remediation or "docker group" in result.remediation.lower()


class TestDockerComposeCheck:
    """Test Docker Compose detection."""

    def test_WHEN_docker_compose_v2_available_THEN_check_passes(self):
        """Test Docker Compose V2 detection."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Docker Compose version v2.20.0"
            )

            result = agent.check_docker_compose()

            assert result.success is True
            assert result.version == "v2" or "v2" in str(result.details)

    def test_WHEN_docker_compose_v1_available_THEN_check_passes_with_fallback(self):
        """Test Docker Compose V1 detection as fallback."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('subprocess.run') as mock_run:
            # First call (docker compose) fails, second call (docker-compose) succeeds
            mock_run.side_effect = [
                Mock(returncode=1, stderr="unknown command"),
                Mock(returncode=0, stdout="docker-compose version 1.29.0")
            ]

            result = agent.check_docker_compose()

            assert result.success is True
            assert result.version == "v1" or "v1" in str(result.details)

    def test_WHEN_neither_compose_version_available_THEN_check_fails_with_guidance(self):
        """Test when neither Docker Compose version is available."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                Mock(returncode=1, stderr="unknown command"),  # V2 check
                FileNotFoundError("docker-compose not found")  # V1 check
            ]

            result = agent.check_docker_compose()

            assert result.success is False
            assert "install" in result.remediation.lower()
            assert "compose" in result.remediation.lower()


class TestPythonPackageCheck:
    """Test Python package dependency checks."""

    def test_WHEN_neo4j_package_installed_THEN_check_passes(self):
        """Test neo4j package is installed."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('importlib.metadata.version') as mock_version:
            mock_version.return_value = "5.15.0"

            result = agent.check_python_packages()

            assert result.success is True
            assert "5.15" in str(result.details) or result.version == "5.15.0"

    def test_WHEN_neo4j_package_missing_THEN_check_fails_with_install_command(self):
        """Test neo4j package not installed."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('importlib.metadata.version') as mock_version:
            mock_version.side_effect = ModuleNotFoundError("No module named 'neo4j'")

            result = agent.check_python_packages()

            assert result.success is False
            assert "pip install" in result.remediation
            assert "neo4j" in result.remediation

    def test_WHEN_neo4j_package_wrong_version_THEN_check_fails_with_upgrade_command(self):
        """Test neo4j package has incorrect version."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('importlib.metadata.version') as mock_version:
            mock_version.return_value = "4.0.0"  # Too old

            result = agent.check_python_packages()

            assert result.success is False
            assert "upgrade" in result.remediation.lower() or "install" in result.remediation
            assert "5.15" in result.remediation or ">=5.15" in result.remediation

    def test_WHEN_check_packages_auto_install_enabled_THEN_attempts_install(self):
        """Test auto-installation of missing packages."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('importlib.metadata.version') as mock_version:
            mock_version.side_effect = ModuleNotFoundError("No module named 'neo4j'")

            with patch('subprocess.run') as mock_run:
                mock_run.return_value = Mock(returncode=0)

                result = agent.check_python_packages(auto_install=True)

                # Should have attempted pip install
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                assert 'pip' in call_args
                assert 'install' in call_args


class TestPortAvailability:
    """Test port availability checks."""

    def test_WHEN_ports_available_THEN_check_passes(self):
        """Test that required ports are available."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('socket.socket') as mock_socket:
            # Simulate ports being available (bind succeeds)
            mock_sock = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock
            mock_sock.bind.return_value = None

            result = agent.check_port_availability()

            assert result.success is True

    def test_WHEN_bolt_port_in_use_THEN_check_fails_with_port_info(self):
        """Test Bolt port (7687) already in use."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock
            # Simulate port 7687 in use
            mock_sock.bind.side_effect = OSError("Address already in use")

            result = agent.check_port_availability()

            assert result.success is False
            assert "7687" in str(result.details) or "7687" in result.remediation
            assert "port" in result.remediation.lower()

    def test_WHEN_http_port_in_use_THEN_check_fails_with_alternative_suggestion(self):
        """Test HTTP port (7474) already in use."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock
            # HTTP port in use, Bolt port available
            mock_sock.bind.side_effect = [None, OSError("Address already in use")]

            result = agent.check_port_availability()

            assert result.success is False
            assert "7474" in str(result.details) or "7474" in result.remediation
            assert "NEO4J_HTTP_PORT" in result.remediation or "environment" in result.remediation.lower()

    def test_WHEN_custom_ports_specified_THEN_those_ports_checked(self):
        """Test checking custom port configuration."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock

            result = agent.check_port_availability(bolt_port=7688, http_port=7475)

            # Should check custom ports
            bind_calls = mock_sock.bind.call_args_list
            assert any(7688 in str(c) for c in bind_calls)
            assert any(7475 in str(c) for c in bind_calls)


class TestFullPrerequisiteCheck:
    """Test comprehensive prerequisite validation."""

    def test_WHEN_all_prerequisites_met_THEN_report_success(self):
        """Test when all checks pass."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch.object(agent, 'check_docker_daemon') as mock_docker:
            with patch.object(agent, 'check_docker_compose') as mock_compose:
                with patch.object(agent, 'check_python_packages') as mock_packages:
                    with patch.object(agent, 'check_port_availability') as mock_ports:
                        # All checks pass
                        mock_docker.return_value = Mock(success=True)
                        mock_compose.return_value = Mock(success=True)
                        mock_packages.return_value = Mock(success=True)
                        mock_ports.return_value = Mock(success=True)

                        report = agent.check_all_prerequisites()

                        assert report.all_passed is True
                        assert len(report.failures) == 0

    def test_WHEN_docker_missing_THEN_report_shows_docker_failure(self):
        """Test reporting when Docker is missing."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch.object(agent, 'check_docker_daemon') as mock_docker:
            with patch.object(agent, 'check_docker_compose') as mock_compose:
                with patch.object(agent, 'check_python_packages') as mock_packages:
                    with patch.object(agent, 'check_port_availability') as mock_ports:
                        mock_docker.return_value = Mock(success=False, remediation="Install Docker")
                        mock_compose.return_value = Mock(success=True)
                        mock_packages.return_value = Mock(success=True)
                        mock_ports.return_value = Mock(success=True)

                        report = agent.check_all_prerequisites()

                        assert report.all_passed is False
                        assert len(report.failures) == 1
                        assert "docker" in report.failures[0].lower()

    def test_WHEN_multiple_failures_THEN_report_shows_all_issues(self):
        """Test reporting multiple failed checks."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch.object(agent, 'check_docker_daemon') as mock_docker:
            with patch.object(agent, 'check_docker_compose') as mock_compose:
                with patch.object(agent, 'check_python_packages') as mock_packages:
                    with patch.object(agent, 'check_port_availability') as mock_ports:
                        mock_docker.return_value = Mock(success=False, remediation="Fix Docker")
                        mock_compose.return_value = Mock(success=False, remediation="Install Compose")
                        mock_packages.return_value = Mock(success=True)
                        mock_ports.return_value = Mock(success=True)

                        report = agent.check_all_prerequisites()

                        assert report.all_passed is False
                        assert len(report.failures) >= 2

    def test_WHEN_check_all_with_auto_fix_THEN_attempts_remediation(self):
        """Test auto-fix mode attempts to resolve issues."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        with patch.object(agent, 'check_python_packages') as mock_packages:
            # First call: fails, second call after auto-fix: passes
            mock_packages.side_effect = [
                Mock(success=False, remediation="pip install neo4j"),
                Mock(success=True)
            ]

            report = agent.check_all_prerequisites(auto_fix=True)

            # Should have attempted fix
            assert mock_packages.call_count == 2


class TestRemediationGuidance:
    """Test remediation guidance generation."""

    def test_WHEN_get_remediation_for_docker_THEN_returns_install_steps(self):
        """Test Docker installation guidance."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        guidance = agent.get_remediation_guidance("docker_not_installed")

        assert isinstance(guidance, str)
        assert "docker" in guidance.lower()
        assert "install" in guidance.lower()
        assert "https://" in guidance  # Should include documentation link

    def test_WHEN_get_remediation_for_permissions_THEN_returns_usermod_command(self):
        """Test Docker permission fix guidance."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        guidance = agent.get_remediation_guidance("docker_permission_denied")

        assert "usermod" in guidance or "docker group" in guidance.lower()
        assert "log out" in guidance.lower() or "re-login" in guidance.lower()

    def test_WHEN_get_remediation_for_port_conflict_THEN_returns_config_options(self):
        """Test port conflict resolution guidance."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        guidance = agent.get_remediation_guidance("port_conflict", port=7687)

        assert "7687" in guidance
        assert "NEO4J_BOLT_PORT" in guidance or "environment" in guidance.lower()

    def test_WHEN_get_remediation_for_unknown_issue_THEN_returns_general_help(self):
        """Test generic guidance for unknown issues."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        guidance = agent.get_remediation_guidance("unknown_issue")

        assert isinstance(guidance, str)
        assert len(guidance) > 0


class TestWorkflowGuidance:
    """Test step-by-step workflow guidance."""

    def test_WHEN_generate_workflow_THEN_returns_ordered_steps(self):
        """Test generating step-by-step fix workflow."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        workflow = agent.generate_fix_workflow()

        assert isinstance(workflow, list)
        assert len(workflow) > 0
        # Should be ordered steps
        for i, step in enumerate(workflow, 1):
            assert "step" in step.lower() or str(i) in step

    def test_WHEN_generate_workflow_with_failures_THEN_prioritizes_blockers(self):
        """Test that workflow prioritizes blocking issues."""
        from amplihack.memory.neo4j.dependency_agent import DependencyAgent

        agent = DependencyAgent()
        failures = [
            {"check": "docker", "blocker": True},
            {"check": "ports", "blocker": False}
        ]

        workflow = agent.generate_fix_workflow(failures)

        # Docker (blocker) should come before ports
        workflow_str = " ".join(workflow).lower()
        docker_pos = workflow_str.find("docker")
        ports_pos = workflow_str.find("port")

        assert docker_pos < ports_pos


class TestCheckResult:
    """Test CheckResult data structure."""

    def test_WHEN_create_check_result_THEN_has_required_fields(self):
        """Test CheckResult structure."""
        from amplihack.memory.neo4j.dependency_agent import CheckResult

        result = CheckResult(
            check_name="test_check",
            success=True,
            message="Check passed",
            remediation="No action needed"
        )

        assert result.check_name == "test_check"
        assert result.success is True
        assert result.message == "Check passed"
        assert result.remediation == "No action needed"

    def test_WHEN_check_result_failed_THEN_has_remediation(self):
        """Test failed CheckResult includes remediation."""
        from amplihack.memory.neo4j.dependency_agent import CheckResult

        result = CheckResult(
            check_name="docker_check",
            success=False,
            message="Docker not found",
            remediation="Install Docker from https://docker.com"
        )

        assert result.success is False
        assert len(result.remediation) > 0


@pytest.mark.integration
class TestDependencyAgentIntegration:
    """Integration tests requiring real system checks."""

    def test_WHEN_real_system_checked_THEN_provides_accurate_report(self):
        """Test with real system dependencies.

        This test is marked as integration and will be skipped in unit test runs.
        """
        pytest.skip("Requires real system - run with: pytest -m integration")
