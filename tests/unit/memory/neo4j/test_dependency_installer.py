"""Tests for dependency installer.

Tests the goal-seeking autonomous installation system with mocked
system operations (no actual sudo commands executed).
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from src.amplihack.memory.neo4j.dependency_installer import (
    AptInstaller,
    BrewInstaller,
    Dependency,
    DependencyInstaller,
    DependencyType,
    InstallStatus,
    OSDetector,
    check_dependencies,
    install_neo4j_dependencies,
)


class TestOSDetector:
    """Tests for OS detection."""

    @patch("platform.system")
    def test_detect_macos(self, mock_system):
        """Should detect macOS."""
        mock_system.return_value = "Darwin"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="14.0\n", returncode=0)
            result = OSDetector.detect()

        assert result["type"] == "macos"
        assert result["version"] == "14.0"
        assert result["name"] == "macOS"

    @patch("platform.system")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_detect_ubuntu(self, mock_file, mock_exists, mock_system):
        """Should detect Ubuntu from /etc/os-release."""
        mock_system.return_value = "Linux"
        mock_exists.return_value = True
        mock_file.return_value.readlines.return_value = [
            'ID="ubuntu"\n',
            'VERSION_ID="22.04"\n',
            'NAME="Ubuntu"\n',
        ]

        result = OSDetector.detect()

        assert result["type"] == "ubuntu"
        assert result["version"] == "22.04"
        assert result["name"] == "Ubuntu"


class TestAptInstaller:
    """Tests for apt-based installer (Ubuntu/Debian)."""

    def setup_method(self):
        """Setup test instance."""
        self.installer = AptInstaller()

    def test_docker_dependency_definition(self):
        """Should return correct Docker dependency for apt."""
        dep = self.installer.install_docker()

        assert dep.name == "docker"
        assert dep.type == DependencyType.DOCKER
        assert dep.requires_sudo is True
        assert "apt install" in dep.commands[1]
        assert "docker.io" in dep.commands[1]
        assert dep.verify_cmd == "docker --version"

    def test_docker_compose_dependency_definition(self):
        """Should return correct Docker Compose dependency for apt."""
        dep = self.installer.install_docker_compose()

        assert dep.name == "docker-compose-plugin"
        assert dep.type == DependencyType.DOCKER_COMPOSE
        assert dep.requires_sudo is True
        assert "docker-compose-plugin" in dep.commands[0]

    def test_python_package_dependency(self):
        """Should return Python package dependency (OS-independent)."""
        dep = self.installer.install_python_package("neo4j")

        assert dep.name == "python-neo4j"
        assert dep.type == DependencyType.PYTHON_PACKAGE
        assert dep.requires_sudo is False
        assert "neo4j" in dep.commands[0]


class TestBrewInstaller:
    """Tests for Homebrew-based installer (macOS)."""

    def setup_method(self):
        """Setup test instance."""
        self.installer = BrewInstaller()

    def test_docker_dependency_definition(self):
        """Should return correct Docker dependency for Homebrew."""
        dep = self.installer.install_docker()

        assert dep.name == "docker"
        assert dep.requires_sudo is False  # Homebrew doesn't need sudo
        assert "brew install" in dep.commands[0]
        assert "--cask" in dep.commands[0]

    def test_docker_compose_no_install_needed(self):
        """Should indicate Docker Compose is included with Docker Desktop."""
        dep = self.installer.install_docker_compose()

        assert dep.name == "docker-compose"
        assert len(dep.commands) == 0  # No installation needed
        assert dep.verify_cmd == "docker compose version"


class TestDependencyInstaller:
    """Tests for main installer orchestrator."""

    @patch.object(OSDetector, "detect")
    def test_init_ubuntu(self, mock_detect):
        """Should initialize with apt strategy for Ubuntu."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}

        installer = DependencyInstaller()

        assert isinstance(installer.strategy, AptInstaller)
        assert installer.os_info["type"] == "ubuntu"

    @patch.object(OSDetector, "detect")
    def test_init_macos(self, mock_detect):
        """Should initialize with Homebrew strategy for macOS."""
        mock_detect.return_value = {"type": "macos", "version": "14.0", "name": "macOS"}

        installer = DependencyInstaller()

        assert isinstance(installer.strategy, BrewInstaller)

    @patch.object(OSDetector, "detect")
    def test_init_unsupported_os(self, mock_detect):
        """Should raise error for unsupported OS."""
        mock_detect.return_value = {"type": "windows", "version": "11", "name": "Windows"}

        with pytest.raises(RuntimeError, match="Unsupported OS"):
            DependencyInstaller()

    @patch.object(OSDetector, "detect")
    @patch("subprocess.run")
    def test_check_missing_docker(self, mock_run, mock_detect):
        """Should detect missing Docker."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}
        mock_run.side_effect = [
            # docker --version check fails
            Mock(returncode=1),
        ]

        installer = DependencyInstaller()
        missing = installer.check_missing_dependencies()

        # Should have Docker in missing list
        assert any(dep.name == "docker" for dep in missing)

    @patch.object(OSDetector, "detect")
    @patch("src.amplihack.memory.neo4j.dependency_installer.subprocess.run")
    def test_check_missing_docker_compose(self, mock_run, mock_detect):
        """Should detect missing Docker Compose."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}

        def run_side_effect(cmd, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            if "docker --version" in cmd_str:
                return Mock(returncode=0)
            elif "docker ps" in cmd_str:
                return Mock(returncode=0, stdout="", stderr="")
            elif "docker compose version" in cmd_str:
                return Mock(returncode=1)
            return Mock(returncode=0)

        mock_run.side_effect = run_side_effect

        with patch.dict("sys.modules", {"neo4j": MagicMock()}):
            installer = DependencyInstaller()
            missing = installer.check_missing_dependencies()

        # Should have Docker Compose in missing list
        assert any(dep.name == "docker-compose-plugin" for dep in missing)

    @patch.object(OSDetector, "detect")
    @patch("src.amplihack.memory.neo4j.dependency_installer.subprocess.run")
    def test_check_missing_docker_permission(self, mock_run, mock_detect):
        """Should detect Docker permission issues."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}

        def run_side_effect(cmd, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
            if "docker --version" in cmd_str:
                return Mock(returncode=0)
            elif "docker ps" in cmd_str:
                return Mock(returncode=1, stdout="", stderr="permission denied")
            return Mock(returncode=0)

        mock_run.side_effect = run_side_effect

        installer = DependencyInstaller()
        missing = installer.check_missing_dependencies()

        # Should suggest adding user to docker group
        assert any(dep.type == DependencyType.USER_GROUP for dep in missing)

    @patch.object(OSDetector, "detect")
    @patch("src.amplihack.memory.neo4j.dependency_installer.subprocess.run")
    def test_check_all_satisfied(self, mock_run, mock_detect):
        """Should return empty list when all dependencies satisfied."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}

        def run_side_effect(cmd, **kwargs):
            # All checks succeed
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = run_side_effect

        # Mock neo4j import success
        with patch.dict("sys.modules", {"neo4j": MagicMock()}):
            installer = DependencyInstaller()
            missing = installer.check_missing_dependencies()

        assert len(missing) == 0

    @patch.object(OSDetector, "detect")
    @patch("subprocess.run")
    def test_install_dependency_success(self, mock_run, mock_detect):
        """Should successfully install dependency."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}
        # Mock successful command execution and verification
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        installer = DependencyInstaller(auto_confirm=True)
        dep = Dependency(
            name="test-package",
            type=DependencyType.SYSTEM_PACKAGE,
            why="Test package",
            commands=["sudo apt install -y test-package"],
            verify_cmd="dpkg -l | grep test-package",
            requires_sudo=True,
            risk_level="low",
        )

        result = installer.install_dependency(dep)

        assert result.status == InstallStatus.SUCCESS
        assert result.message == "Installed successfully"

    @patch.object(OSDetector, "detect")
    @patch("subprocess.run")
    def test_install_dependency_failure(self, mock_run, mock_detect):
        """Should handle installation failure gracefully."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}
        # Mock failed command execution
        mock_run.return_value = Mock(
            returncode=1, stdout="", stderr="Package not found"
        )

        installer = DependencyInstaller(auto_confirm=True)
        dep = Dependency(
            name="nonexistent-package",
            type=DependencyType.SYSTEM_PACKAGE,
            why="Test package",
            commands=["sudo apt install -y nonexistent-package"],
            verify_cmd="dpkg -l | grep nonexistent-package",
            requires_sudo=True,
            risk_level="low",
        )

        result = installer.install_dependency(dep)

        assert result.status == InstallStatus.FAILED
        assert "Package not found" in result.message

    @patch.object(OSDetector, "detect")
    def test_install_dependency_user_group(self, mock_detect):
        """Should mark as requires relogin for user group changes."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}

        installer = DependencyInstaller(auto_confirm=True)
        dep = Dependency(
            name="docker-group",
            type=DependencyType.USER_GROUP,
            why="Docker group membership",
            commands=["sudo usermod -aG docker user"],
            verify_cmd='groups | grep "docker"',
            requires_sudo=True,
            risk_level="low",
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            result = installer.install_dependency(dep)

        assert result.status == InstallStatus.REQUIRES_RELOGIN

    @patch.object(OSDetector, "detect")
    @patch("builtins.input")
    def test_confirm_installation_yes(self, mock_input, mock_detect):
        """Should return True when user confirms."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}
        mock_input.return_value = "y"

        installer = DependencyInstaller(auto_confirm=False)
        result = installer.confirm_installation()

        assert result is True

    @patch.object(OSDetector, "detect")
    @patch("builtins.input")
    def test_confirm_installation_no(self, mock_input, mock_detect):
        """Should return False when user declines."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}
        mock_input.return_value = "n"

        installer = DependencyInstaller(auto_confirm=False)
        result = installer.confirm_installation()

        assert result is False

    @patch.object(OSDetector, "detect")
    def test_auto_confirm_skips_prompt(self, mock_detect):
        """Should skip confirmation when auto_confirm=True."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}

        installer = DependencyInstaller(auto_confirm=True)
        result = installer.confirm_installation()

        assert result is True  # Should auto-confirm without prompting


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @patch.object(DependencyInstaller, "install_missing")
    @patch.object(OSDetector, "detect")
    def test_install_neo4j_dependencies_success(self, mock_detect, mock_install):
        """Should install dependencies successfully."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}
        mock_install.return_value = {"success": True, "installed": 2, "failed": 0}

        result = install_neo4j_dependencies(auto_confirm=True)

        assert result is True
        mock_install.assert_called_once()

    @patch.object(DependencyInstaller, "install_missing")
    @patch.object(OSDetector, "detect")
    def test_install_neo4j_dependencies_failure(self, mock_detect, mock_install):
        """Should return False when installation fails."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}
        mock_install.return_value = {"success": False, "installed": 1, "failed": 1}

        result = install_neo4j_dependencies(auto_confirm=True)

        assert result is False

    @patch.object(DependencyInstaller, "check_missing_dependencies")
    @patch.object(OSDetector, "detect")
    def test_check_dependencies(self, mock_detect, mock_check):
        """Should return list of missing dependency names."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}
        mock_check.return_value = [
            Dependency(
                name="docker",
                type=DependencyType.DOCKER,
                why="Test",
                commands=[],
                verify_cmd="",
                requires_sudo=True,
                risk_level="low",
            ),
            Dependency(
                name="docker-compose-plugin",
                type=DependencyType.DOCKER_COMPOSE,
                why="Test",
                commands=[],
                verify_cmd="",
                requires_sudo=True,
                risk_level="low",
            ),
        ]

        result = check_dependencies()

        assert result == ["docker", "docker-compose-plugin"]


class TestIntegration:
    """Integration-style tests (still mocked, but testing full flow)."""

    @patch.object(OSDetector, "detect")
    @patch("src.amplihack.memory.neo4j.dependency_installer.subprocess.run")
    @patch("builtins.input")
    def test_full_installation_flow(self, mock_input, mock_run, mock_detect):
        """Should complete full installation flow successfully."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}

        # Mock user confirms installation
        mock_input.return_value = "y"

        # Create a counter to track calls
        call_count = [0]

        def run_side_effect(cmd, **kwargs):
            call_count[0] += 1
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd

            # First few calls are checks
            if call_count[0] <= 3:
                if "docker --version" in cmd_str:
                    return Mock(returncode=1)  # Docker missing
                elif "docker ps" in cmd_str:
                    return Mock(returncode=1, stdout="", stderr="")
                elif "docker compose" in cmd_str:
                    return Mock(returncode=0, stdout="", stderr="")

            # All installation commands and verifications succeed
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = run_side_effect

        with patch.dict("sys.modules", {"neo4j": MagicMock()}):
            installer = DependencyInstaller(auto_confirm=False)
            result = installer.install_missing(confirm=True)

        assert result["success"] is True
        assert result["installed"] >= 1

    @patch.object(OSDetector, "detect")
    @patch("src.amplihack.memory.neo4j.dependency_installer.subprocess.run")
    def test_no_dependencies_missing(self, mock_run, mock_detect):
        """Should handle case where no dependencies are missing."""
        mock_detect.return_value = {"type": "ubuntu", "version": "22.04", "name": "Ubuntu"}

        # Mock all checks succeed
        def run_side_effect(cmd, **kwargs):
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = run_side_effect

        with patch.dict("sys.modules", {"neo4j": MagicMock()}):
            installer = DependencyInstaller(auto_confirm=True)
            result = installer.install_missing(confirm=False)

        assert result["success"] is True
        assert result["installed"] == 0
        assert len(result["results"]) == 0
