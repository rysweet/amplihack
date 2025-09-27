"""Docker container manager for amplihack."""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from .detector import DockerDetector


class DockerManager:
    """Manages Docker containers for amplihack execution."""

    IMAGE_NAME = "amplihack:latest"

    def __init__(self):
        """Initialize DockerManager."""
        self.detector = DockerDetector()

    def build_image(self) -> bool:
        """Build the Docker image if it doesn't exist."""
        if not self.detector.is_running():
            print("Docker is not running.", file=sys.stderr)
            return False

        # Check if image already exists
        if self.detector.check_image_exists(self.IMAGE_NAME):
            return True

        print(f"Building Docker image: {self.IMAGE_NAME}")

        # Find Dockerfile at project root
        project_root = Path(__file__).parent.parent.parent.parent
        dockerfile = project_root / "Dockerfile"

        if not dockerfile.exists():
            print(f"Dockerfile not found at {dockerfile}", file=sys.stderr)
            return False

        try:
            result = subprocess.run(
                [
                    "docker",
                    "build",
                    "-t",
                    self.IMAGE_NAME,
                    "-f",
                    str(dockerfile),
                    str(project_root),
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"Docker build failed: {result.stderr}", file=sys.stderr)
                return False

            print(f"Successfully built Docker image: {self.IMAGE_NAME}")
            return True

        except subprocess.SubprocessError as e:
            print(f"Error building Docker image: {e}", file=sys.stderr)
            return False

    def run_command(self, args: List[str], cwd: Optional[str] = None) -> int:
        """Run amplihack command in Docker container."""
        if not self.detector.is_running():
            print("Docker is not running.", file=sys.stderr)
            return 1

        # Ensure image exists
        if not self.build_image():
            print("Failed to build Docker image.", file=sys.stderr)
            return 1

        # Mount working directory
        work_dir = Path(cwd or os.getcwd()).resolve()

        # Build Docker command with security options
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--interactive",
            "--tty" if sys.stdin.isatty() else "--no-TTY",
            # Security options
            "--security-opt",
            "no-new-privileges",
            # Resource limits
            "--memory",
            "4g",  # Limit memory to 4GB
            "--cpus",
            "2",  # Limit CPU to 2 cores
            # Run as non-root user (UID 1000)
            "--user",
            "1000:1000",
            # Mount workspace
            "-v",
            f"{work_dir}:/workspace",
            "-w",
            "/workspace",
        ]

        # Forward important environment variables
        env_vars = self._get_env_vars()
        for key, value in env_vars.items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        # Add image and amplihack arguments
        docker_cmd.append(self.IMAGE_NAME)
        docker_cmd.extend(args)

        # Run the container
        try:
            return subprocess.run(docker_cmd).returncode
        except subprocess.SubprocessError as e:
            print(f"Error running Docker container: {e}", file=sys.stderr)
            return 1

    def _sanitize_env_value(self, value: str) -> str:
        """Sanitize environment variable value by removing control characters."""
        # Remove control characters (except newlines/tabs which are sometimes legitimate)
        sanitized = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", value)
        return sanitized

    def _validate_api_key(self, key_name: str, value: str) -> bool:
        """Validate API key format for known providers."""
        # Basic validation - ensure it looks like a legitimate key
        if not value or len(value) < 10:
            return False

        # Provider-specific validation
        if key_name == "ANTHROPIC_API_KEY":
            # Anthropic keys typically start with sk- and have alphanumeric chars
            return bool(re.match(r"^sk-[a-zA-Z0-9\-_]+$", value))
        elif key_name in ["OPENAI_API_KEY"]:
            # OpenAI keys typically start with sk- and have alphanumeric chars
            return bool(re.match(r"^sk-[a-zA-Z0-9\-_]+$", value))
        elif key_name in ["GITHUB_TOKEN", "GH_TOKEN"]:
            # GitHub tokens have various formats (ghp_, ghs_, github_pat_, etc.)
            return bool(
                re.match(r"^(ghp_|ghs_|github_pat_|gho_|ghu_)[a-zA-Z0-9_]+$", value)
            ) or bool(re.match(r"^[a-f0-9]{40}$", value))  # Classic tokens

        # For unknown keys, just ensure they're not obviously malicious
        return bool(re.match(r"^[a-zA-Z0-9\-_./+=]+$", value))

    def _get_env_vars(self) -> dict:
        """Get environment variables to forward to container with validation."""
        env_vars = {}

        # API keys and credentials with validation
        for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GITHUB_TOKEN", "GH_TOKEN"]:
            if value := os.getenv(key):
                sanitized = self._sanitize_env_value(value)
                if self._validate_api_key(key, sanitized):
                    env_vars[key] = sanitized
                else:
                    print(f"Warning: Invalid format for {key}, skipping", file=sys.stderr)

        # Amplihack vars (except Docker trigger)
        for key, value in os.environ.items():
            if key.startswith("AMPLIHACK_") and key != "AMPLIHACK_USE_DOCKER":
                env_vars[key] = self._sanitize_env_value(value)

        # Terminal settings
        if term := os.getenv("TERM"):
            env_vars["TERM"] = self._sanitize_env_value(term)

        return env_vars

    @classmethod
    def should_use_docker(cls) -> bool:
        """Check if Docker should be used."""
        return DockerDetector().should_use_docker()
