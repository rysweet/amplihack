"""Docker availability detection for amplihack."""

import os
import shutil

from amplihack.utils.subprocess_runner import SubprocessRunner


class DockerDetector:
    """Detects Docker availability and configuration."""

    def __init__(self):
        """Initialize DockerDetector with subprocess runner."""
        self._runner = SubprocessRunner(default_timeout=5, log_commands=False)

    def is_available(self) -> bool:
        """Check if Docker is installed."""
        return shutil.which("docker") is not None

    def is_running(self) -> bool:
        """Check if Docker daemon is running."""
        if not self.is_available():
            return False

        result = self._runner.run_safe(
            ["docker", "info"],
            timeout=5,
            capture=False,
            context="checking docker daemon status",
        )
        return result.success

    def should_use_docker(self) -> bool:
        """Determine if Docker should be used."""
        # Check environment variable
        if os.getenv("AMPLIHACK_USE_DOCKER", "").lower() not in ("1", "true", "yes"):
            return False

        # Don't use Docker if already in Docker
        if self.is_in_docker():
            return False

        # Check Docker availability
        return self.is_running()

    def is_in_docker(self) -> bool:
        """Check if running inside a Docker container."""
        # Check environment variable we set
        if os.getenv("AMPLIHACK_IN_DOCKER") == "1":
            return True

        # Check for Docker-specific files
        if os.path.exists("/.dockerenv"):
            return True

        # Check cgroup for docker
        try:
            with open("/proc/1/cgroup") as f:
                if "docker" in f.read():
                    return True
        except (FileNotFoundError, PermissionError):
            pass

        return False

    def check_image_exists(self, image_name: str) -> bool:
        """Check if a Docker image exists locally."""
        if not self.is_running():
            return False

        result = self._runner.run_safe(
            ["docker", "images", "-q", image_name],
            timeout=5,
            capture=True,
            context=f"checking if docker image {image_name} exists",
        )
        return bool(result.stdout.strip()) if result.success else False
