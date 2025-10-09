"""Docker availability detection for amplihack."""

import os
import shutil
import subprocess


class DockerDetector:
    """Detects Docker availability and configuration."""

    def is_available(self) -> bool:
        """Check if Docker is installed."""
        return shutil.which("docker") is not None

    def is_running(self) -> bool:
        """Check if Docker daemon is running."""
        if not self.is_available():
            return False

        try:
            result = subprocess.run(
                ["docker", "info"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False

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

        try:
            result = subprocess.run(
                ["docker", "images", "-q", image_name],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return bool(result.stdout.strip())
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False
