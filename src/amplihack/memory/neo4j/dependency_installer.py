"""Autonomous dependency installer for Neo4j prerequisites.

Goal-seeking agent that detects, plans, and installs missing dependencies
with user confirmation and comprehensive logging.
"""

import logging
import os
import platform
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of dependencies that can be installed."""

    DOCKER = "docker"
    DOCKER_COMPOSE = "docker_compose"
    PYTHON_PACKAGE = "python_package"
    SYSTEM_PACKAGE = "system_package"
    USER_GROUP = "user_group"


class InstallStatus(Enum):
    """Status of installation attempt."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    REQUIRES_REBOOT = "requires_reboot"
    REQUIRES_RELOGIN = "requires_relogin"


@dataclass
class Dependency:
    """Represents a dependency to be installed."""

    name: str
    type: DependencyType
    why: str  # Why is this needed
    commands: list[str]  # Commands to install
    verify_cmd: str  # Command to verify installation
    requires_sudo: bool
    risk_level: str  # "none", "low", "medium", "high"
    rollback_cmd: str | None = None


@dataclass
class InstallResult:
    """Result of an installation attempt."""

    dependency: Dependency
    status: InstallStatus
    message: str
    duration_seconds: float = 0.0


class OSDetector:
    """Detect operating system and version."""

    @staticmethod
    def detect() -> dict[str, str]:
        """Detect OS type and version.

        Returns:
            Dictionary with 'type', 'version', 'name' keys
        """
        system = platform.system().lower()

        if system == "linux":
            return OSDetector._detect_linux()
        if system == "darwin":
            return OSDetector._detect_macos()
        return {"type": "unknown", "version": "", "name": system}

    @staticmethod
    def _detect_linux() -> dict[str, str]:
        """Detect Linux distribution."""
        try:
            # Read /etc/os-release
            if Path("/etc/os-release").exists():
                with open("/etc/os-release") as f:
                    lines = f.readlines()
                    info = {}
                    for line in lines:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            info[key] = value.strip('"')

                    return {
                        "type": info.get("ID", "linux").lower(),
                        "version": info.get("VERSION_ID", ""),
                        "name": info.get("NAME", "Linux"),
                    }
        except Exception as e:
            logger.debug(f"Failed to detect Linux distro: {e}")

        return {"type": "linux", "version": "", "name": "Linux"}

    @staticmethod
    def _detect_macos() -> dict[str, str]:
        """Detect macOS version."""
        try:
            result = subprocess.run(["sw_vers", "-productVersion"], capture_output=True, text=True)
            version = result.stdout.strip()
            return {"type": "macos", "version": version, "name": "macOS"}
        except Exception as e:
            logger.debug(f"Failed to detect macOS version: {e}")

        return {"type": "macos", "version": "", "name": "macOS"}


class InstallStrategy(ABC):
    """Abstract base class for OS-specific installation strategies."""

    @abstractmethod
    def install_docker(self) -> Dependency:
        """Return dependency definition for Docker installation."""

    @abstractmethod
    def install_docker_compose(self) -> Dependency:
        """Return dependency definition for Docker Compose installation."""

    @abstractmethod
    def install_system_package(self, package: str) -> Dependency:
        """Return dependency definition for system package installation."""

    def install_python_package(self, package: str) -> Dependency:
        """Return dependency definition for Python package installation.

        This is OS-independent, so implemented in base class.
        """
        # Prefer uv if available, fallback to pip
        use_uv = self._check_command_exists("uv")

        if use_uv:
            cmd = f"uv pip install {package}"
        else:
            cmd = f"pip install {package}"

        return Dependency(
            name=f"python-{package}",
            type=DependencyType.PYTHON_PACKAGE,
            why=f"Required Python package: {package}",
            commands=[cmd],
            verify_cmd=f'python -c "import {package.split("[")[0]}"',
            requires_sudo=False,
            risk_level="none",
            rollback_cmd=f"pip uninstall -y {package}",
        )

    def add_user_to_docker_group(self) -> Dependency:
        """Return dependency definition for adding user to docker group."""
        username = os.getenv("USER", os.getenv("USERNAME", "user"))

        return Dependency(
            name="docker-group-membership",
            type=DependencyType.USER_GROUP,
            why="Allow running Docker without sudo",
            commands=[f"sudo usermod -aG docker {username}"],
            verify_cmd='groups | grep -q "docker"',
            requires_sudo=True,
            risk_level="low",
            rollback_cmd=f"sudo gpasswd -d {username} docker",
        )

    @staticmethod
    def _check_command_exists(command: str) -> bool:
        """Check if command exists in PATH."""
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                timeout=2,
            )
            return True
        except Exception:
            return False


class AptInstaller(InstallStrategy):
    """Installation strategy for Debian/Ubuntu (apt)."""

    def install_docker(self) -> Dependency:
        return Dependency(
            name="docker",
            type=DependencyType.DOCKER,
            why="Required for Neo4j container management",
            commands=[
                "sudo apt update",
                "sudo apt install -y docker.io",
                "sudo systemctl start docker",
                "sudo systemctl enable docker",
            ],
            verify_cmd="docker --version",
            requires_sudo=True,
            risk_level="low",
            rollback_cmd="sudo apt remove -y docker.io",
        )

    def install_docker_compose(self) -> Dependency:
        return Dependency(
            name="docker-compose-plugin",
            type=DependencyType.DOCKER_COMPOSE,
            why="Required for Neo4j container orchestration",
            commands=["sudo apt install -y docker-compose-plugin"],
            verify_cmd="docker compose version",
            requires_sudo=True,
            risk_level="low",
            rollback_cmd="sudo apt remove -y docker-compose-plugin",
        )

    def install_system_package(self, package: str) -> Dependency:
        return Dependency(
            name=package,
            type=DependencyType.SYSTEM_PACKAGE,
            why=f"System package: {package}",
            commands=[f"sudo apt install -y {package}"],
            verify_cmd=f"dpkg -l | grep -q {package}",
            requires_sudo=True,
            risk_level="low",
            rollback_cmd=f"sudo apt remove -y {package}",
        )


class BrewInstaller(InstallStrategy):
    """Installation strategy for macOS (Homebrew)."""

    def install_docker(self) -> Dependency:
        return Dependency(
            name="docker",
            type=DependencyType.DOCKER,
            why="Required for Neo4j container management",
            commands=[
                "brew install --cask docker",
                "open -a Docker",  # Start Docker Desktop
            ],
            verify_cmd="docker --version",
            requires_sudo=False,
            risk_level="low",
            rollback_cmd="brew uninstall --cask docker",
        )

    def install_docker_compose(self) -> Dependency:
        # Docker Compose is included with Docker Desktop on macOS
        return Dependency(
            name="docker-compose",
            type=DependencyType.DOCKER_COMPOSE,
            why="Included with Docker Desktop",
            commands=[],  # No additional installation needed
            verify_cmd="docker compose version",
            requires_sudo=False,
            risk_level="none",
        )

    def install_system_package(self, package: str) -> Dependency:
        return Dependency(
            name=package,
            type=DependencyType.SYSTEM_PACKAGE,
            why=f"System package: {package}",
            commands=[f"brew install {package}"],
            verify_cmd=f"brew list {package}",
            requires_sudo=False,
            risk_level="low",
            rollback_cmd=f"brew uninstall {package}",
        )


class DependencyInstaller:
    """Main orchestrator for autonomous dependency installation.

    Goal-seeking agent that detects missing dependencies, plans
    installation, requests confirmation, and executes safely.
    """

    def __init__(self, auto_confirm: bool = False):
        """Initialize installer.

        Args:
            auto_confirm: If True, skip confirmation prompts (for testing)
        """
        self.auto_confirm = auto_confirm
        self.os_info = OSDetector.detect()
        self.strategy = self._select_strategy()
        self.log_file = Path.home() / ".amplihack" / "logs" / "dependency_installer.log"
        self._ensure_log_dir()

    def _select_strategy(self) -> InstallStrategy:
        """Select appropriate installation strategy based on OS."""
        os_type = self.os_info["type"]

        strategies = {
            "ubuntu": AptInstaller(),
            "debian": AptInstaller(),
            "macos": BrewInstaller(),
        }

        strategy = strategies.get(os_type)
        if strategy is None:
            raise RuntimeError(
                f"Unsupported OS: {os_type}. Supported: {', '.join(strategies.keys())}"
            )

        return strategy

    def _ensure_log_dir(self):
        """Ensure log directory exists."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def check_missing_dependencies(self) -> list[Dependency]:
        """Detect missing dependencies for Neo4j.

        Returns:
            List of missing dependencies that need installation
        """
        missing = []

        # Check Docker
        if not self._check_command("docker --version"):
            missing.append(self.strategy.install_docker())

        # Check Docker daemon running
        if self._check_command("docker --version") and not self._check_command("docker ps"):
            # Docker installed but daemon not running
            # Check if it's a permission issue
            result = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=5)
            if "permission denied" in result.stderr.lower():
                missing.append(self.strategy.add_user_to_docker_group())

        # Check Docker Compose
        if not self._check_command("docker compose version"):
            missing.append(self.strategy.install_docker_compose())

        # Check Python neo4j package
        try:
            import neo4j  # noqa: F401
        except ImportError:
            missing.append(self.strategy.install_python_package("neo4j"))

        return missing

    def _check_command(self, cmd: str) -> bool:
        """Check if command executes successfully."""
        try:
            result = subprocess.run(cmd.split(), capture_output=True, timeout=5, text=True)
            return result.returncode == 0
        except Exception as e:
            self.logger.debug("Command execution failed (%s): %s", cmd, e)
            return False

    def show_installation_plan(self, dependencies: list[Dependency]) -> None:
        """Display installation plan to user.

        Args:
            dependencies: List of dependencies to install
        """
        print("\n" + "=" * 60)
        print("Installation Plan")
        print("=" * 60)

        requires_sudo = any(dep.requires_sudo for dep in dependencies)
        total_time = len(dependencies) * 30  # Rough estimate: 30s per dependency

        for i, dep in enumerate(dependencies, 1):
            print(f"\n[{i}] {dep.name}")
            print(f"    Why: {dep.why}")
            print(f"    Risk: {dep.risk_level}")
            if dep.commands:
                print("    Commands:")
                for cmd in dep.commands:
                    sudo_marker = "🔒 " if "sudo" in cmd else "   "
                    print(f"      {sudo_marker}{cmd}")
            if dep.requires_sudo:
                print("    ⚠️  Requires sudo (will prompt for password)")

        print(f"\nEstimated time: {total_time // 60} minutes")
        print(f"Requires sudo: {'Yes' if requires_sudo else 'No'}")
        print("=" * 60)

    def confirm_installation(self) -> bool:
        """Request user confirmation to proceed.

        Returns:
            True if user confirms, False otherwise
        """
        if self.auto_confirm:
            return True

        response = input("\nProceed with installation? (y/n): ").strip().lower()
        return response in ["y", "yes"]

    def install_dependency(self, dependency: Dependency) -> InstallResult:
        """Install a single dependency.

        Args:
            dependency: Dependency to install

        Returns:
            InstallResult with status and message
        """
        import time

        start_time = time.time()

        self._log(f"Installing {dependency.name}")
        print(f"\n[Installing] {dependency.name}...")

        # If no commands, it means dependency is already satisfied
        if not dependency.commands:
            duration = time.time() - start_time
            self._log(f"Skipped {dependency.name} (already satisfied)")
            return InstallResult(
                dependency=dependency,
                status=InstallStatus.SKIPPED,
                message="Already satisfied",
                duration_seconds=duration,
            )

        # Execute installation commands
        for cmd in dependency.commands:
            self._log(f"Executing: {cmd}")

            try:
                # Show command being run
                if dependency.requires_sudo and "sudo" in cmd:
                    print(f"  Running (requires password): {cmd}")
                else:
                    print(f"  Running: {cmd}")

                # Execute command
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )

                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout
                    self._log(f"Failed to execute {cmd}: {error_msg}")
                    return InstallResult(
                        dependency=dependency,
                        status=InstallStatus.FAILED,
                        message=f"Command failed: {error_msg}",
                        duration_seconds=time.time() - start_time,
                    )

            except subprocess.TimeoutExpired:
                self._log(f"Timeout executing {cmd}")
                return InstallResult(
                    dependency=dependency,
                    status=InstallStatus.FAILED,
                    message="Command timeout",
                    duration_seconds=time.time() - start_time,
                )
            except Exception as e:
                self._log(f"Error executing {cmd}: {e}")
                return InstallResult(
                    dependency=dependency,
                    status=InstallStatus.FAILED,
                    message=str(e),
                    duration_seconds=time.time() - start_time,
                )

        # Verify installation
        if dependency.verify_cmd:
            self._log(f"Verifying: {dependency.verify_cmd}")
            try:
                result = subprocess.run(
                    dependency.verify_cmd,
                    shell=True,
                    capture_output=True,
                    timeout=5,
                )

                if result.returncode != 0:
                    self._log(f"Verification failed for {dependency.name}")
                    return InstallResult(
                        dependency=dependency,
                        status=InstallStatus.FAILED,
                        message="Installation succeeded but verification failed",
                        duration_seconds=time.time() - start_time,
                    )
            except Exception as e:
                self._log(f"Verification error for {dependency.name}: {e}")

        duration = time.time() - start_time

        # Check if requires relogin
        if dependency.type == DependencyType.USER_GROUP:
            status = InstallStatus.REQUIRES_RELOGIN
            message = "Installed (log out and log back in for changes to take effect)"
        else:
            status = InstallStatus.SUCCESS
            message = "Installed successfully"

        self._log(f"Successfully installed {dependency.name}")
        print(f"  ✓ {message}")

        return InstallResult(
            dependency=dependency,
            status=status,
            message=message,
            duration_seconds=duration,
        )

    def install_missing(self, confirm: bool = True) -> dict[str, any]:
        """Main entry point: Check, plan, confirm, install.

        Args:
            confirm: Whether to request user confirmation

        Returns:
            Dictionary with installation results:
            {
                'success': bool,
                'installed': int,
                'failed': int,
                'skipped': int,
                'results': List[InstallResult],
            }
        """
        self._log("=" * 60)
        self._log("Starting dependency installation check")
        self._log(f"OS: {self.os_info['name']} {self.os_info['version']}")

        # Phase 1: Detection
        print("\nChecking for missing dependencies...")
        missing = self.check_missing_dependencies()

        if not missing:
            print("✓ All dependencies satisfied")
            self._log("All dependencies satisfied")
            return {
                "success": True,
                "installed": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
            }

        print(f"Found {len(missing)} missing dependencies")

        # Phase 2: Planning
        self.show_installation_plan(missing)

        # Phase 3: Confirmation
        if confirm and not self.confirm_installation():
            print("\nInstallation cancelled by user")
            self._log("Installation cancelled by user")
            return {
                "success": False,
                "installed": 0,
                "failed": 0,
                "skipped": len(missing),
                "results": [],
            }

        # Phase 4: Execution
        print("\n" + "=" * 60)
        print("Installing dependencies...")
        print("=" * 60)

        results = []
        for i, dep in enumerate(missing, 1):
            print(f"\n[{i}/{len(missing)}]")
            result = self.install_dependency(dep)
            results.append(result)

            # Stop on failure for critical dependencies
            if result.status == InstallStatus.FAILED:
                print(f"\n⚠️  Installation of {dep.name} failed")
                print(f"Error: {result.message}")
                if dep.rollback_cmd:
                    print(f"\nTo rollback: {dep.rollback_cmd}")

        # Phase 5: Summary
        self._show_summary(results)

        # Compile statistics
        installed = sum(1 for r in results if r.status == InstallStatus.SUCCESS)
        failed = sum(1 for r in results if r.status == InstallStatus.FAILED)
        skipped = sum(1 for r in results if r.status == InstallStatus.SKIPPED)

        return {
            "success": failed == 0,
            "installed": installed,
            "failed": failed,
            "skipped": skipped,
            "results": results,
        }

    def _show_summary(self, results: list[InstallResult]) -> None:
        """Show installation summary.

        Args:
            results: List of installation results
        """
        print("\n" + "=" * 60)
        print("Installation Summary")
        print("=" * 60)

        success = [r for r in results if r.status == InstallStatus.SUCCESS]
        failed = [r for r in results if r.status == InstallStatus.FAILED]
        skipped = [r for r in results if r.status == InstallStatus.SKIPPED]
        relogin = [r for r in results if r.status == InstallStatus.REQUIRES_RELOGIN]

        print(f"\n✓ Installed: {len(success)}")
        print(f"✗ Failed: {len(failed)}")
        print(f"○ Skipped: {len(skipped)}")

        if relogin:
            print("\n⚠️  Action Required:")
            print("  Log out and log back in for changes to take effect:")
            for r in relogin:
                print(f"    - {r.dependency.name}")

        if failed:
            print("\n❌ Failed Installations:")
            for r in failed:
                print(f"\n  {r.dependency.name}:")
                print(f"    Error: {r.message}")
                if r.dependency.rollback_cmd:
                    print(f"    Rollback: {r.dependency.rollback_cmd}")

        total_time = sum(r.duration_seconds for r in results)
        print(f"\nTotal time: {total_time:.1f} seconds")
        print("=" * 60)

    def _log(self, message: str) -> None:
        """Log message to file.

        Args:
            message: Message to log
        """
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} {message}\n"

        try:
            with open(self.log_file, "a") as f:
                f.write(log_entry)
        except Exception as e:
            # Don't fail if logging fails
            logger.debug(f"Failed to write to log file: {e}")


# Convenience functions


def install_neo4j_dependencies(auto_confirm: bool = False) -> bool:
    """Install all dependencies needed for Neo4j.

    Args:
        auto_confirm: If True, skip confirmation prompts

    Returns:
        True if all dependencies installed successfully
    """
    installer = DependencyInstaller(auto_confirm=auto_confirm)
    result = installer.install_missing(confirm=not auto_confirm)
    return result["success"]


def check_dependencies() -> list[str]:
    """Check for missing dependencies (non-interactive).

    Returns:
        List of missing dependency names
    """
    installer = DependencyInstaller()
    missing = installer.check_missing_dependencies()
    return [dep.name for dep in missing]
