"""Neo4j configuration management.

Loads configuration from environment variables with sensible defaults.
Validates configuration and provides clear error messages.
Implements secure password generation and storage.
"""

import os
import secrets
import string
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Neo4jConfig:
    """Neo4j configuration (immutable).

    All configuration loaded from environment variables or defaults.
    Validation happens at initialization.
    """

    # Connection
    uri: str
    user: str
    password: str

    # Ports
    bolt_port: int
    http_port: int

    # Docker
    container_name: str
    image: str
    compose_file: Path
    compose_cmd: str  # "docker compose" or "docker-compose"

    # Resources
    heap_size: str
    page_cache_size: str

    # Behavior
    startup_timeout: int  # seconds to wait for container
    health_check_interval: int  # seconds between health checks

    @classmethod
    def from_environment(cls) -> "Neo4jConfig":
        """Load configuration from environment variables.

        Returns:
            Neo4jConfig instance with validated settings

        Raises:
            ValueError: If required configuration missing or invalid
        """
        # Get password from environment (REQUIRED)
        password = get_password_from_env()

        # Ports with defaults
        bolt_port = int(os.getenv("NEO4J_BOLT_PORT", "7687"))
        http_port = int(os.getenv("NEO4J_HTTP_PORT", "7474"))

        # Validate ports
        if not (1024 <= bolt_port <= 65535):
            raise ValueError(f"Invalid NEO4J_BOLT_PORT: {bolt_port}")
        if not (1024 <= http_port <= 65535):
            raise ValueError(f"Invalid NEO4J_HTTP_PORT: {http_port}")
        if bolt_port == http_port:
            raise ValueError("NEO4J_BOLT_PORT and NEO4J_HTTP_PORT must be different")

        # Docker Compose command detection
        compose_cmd = cls._detect_compose_command()

        # Find project root (where docker/ directory will be)
        project_root = cls._find_project_root()
        compose_file = project_root / "docker" / "docker-compose.neo4j.yml"

        return cls(
            uri=os.getenv("NEO4J_URI", f"bolt://localhost:{bolt_port}"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=password,
            bolt_port=bolt_port,
            http_port=http_port,
            container_name=os.getenv("NEO4J_CONTAINER_NAME", "amplihack-neo4j"),
            image=os.getenv("NEO4J_IMAGE", "neo4j:5.15-community"),
            compose_file=compose_file,
            compose_cmd=compose_cmd,
            heap_size=os.getenv("NEO4J_HEAP_SIZE", "2G"),
            page_cache_size=os.getenv("NEO4J_PAGE_CACHE_SIZE", "1G"),
            startup_timeout=int(os.getenv("NEO4J_STARTUP_TIMEOUT", "30")),
            health_check_interval=int(os.getenv("NEO4J_HEALTH_CHECK_INTERVAL", "2")),
        )

    @staticmethod
    def _detect_compose_command() -> str:
        """Detect which docker compose command is available.

        Returns:
            "docker compose" (V2), "docker-compose" (V1), or "docker" (fallback)

        Note:
            Falls back to "docker" if compose not available, allowing
            direct docker commands to be used instead.
        """
        # Check for env override first
        if override := os.getenv("NEO4J_COMPOSE_CMD"):
            return override

        # Try V2 first (preferred)
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return "docker compose"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Try V1 (fallback)
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return "docker-compose"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Fallback to direct docker (container might already be running)
        return "docker"

    @staticmethod
    def _find_project_root() -> Path:
        """Find project root (directory containing .git or pyproject.toml).

        Returns:
            Path to project root

        Raises:
            RuntimeError: If project root not found
        """
        current = Path.cwd()

        # Walk up directory tree looking for markers
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
                return parent

        # Fallback: use cwd
        return current


def get_password_from_env() -> str:
    """Get Neo4j password from environment variable.

    Returns:
        Neo4j password from NEO4J_PASSWORD environment variable

    Raises:
        ValueError: If NEO4J_PASSWORD not set in environment

    Note:
        Set NEO4J_PASSWORD in your .env file or shell environment.
        See .env.example for configuration template.
    """
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        raise ValueError(
            "NEO4J_PASSWORD environment variable not set.\n"
            "Set it in your .env file or shell environment:\n"
            "  export NEO4J_PASSWORD='your_secure_password'\n"
            "Or copy .env.example to .env and configure."
        )
    return password


def generate_neo4j_password() -> str:  # ggignore
    """Generate cryptographically secure password.

    Returns:
        32-character random password with ~190 bits of entropy
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # 32 characters = 190 bits of entropy
    return "".join(secrets.choice(alphabet) for _ in range(32))  # ggignore


def get_or_create_password() -> str:
    """Get existing password or create new one.

    Priority:
        1. NEO4J_PASSWORD environment variable
        2. Stored password file (~/.amplihack/.neo4j_password)
        3. Generate new password

    Returns:
        Neo4j password

    Side Effects:
        - Creates ~/.amplihack/.neo4j_password if it doesn't exist
        - Sets file permissions to 0o600 (owner read/write only)
    """
    # Priority 1: Environment variable
    if password := os.getenv("NEO4J_PASSWORD"):  # ggignore
        return password

    # Priority 2: Stored password file
    password_file = Path.home() / ".amplihack" / ".neo4j_password"
    if password_file.exists():
        try:
            password = password_file.read_text().strip()
            if password:  # Not empty
                # Verify permissions
                mode = password_file.stat().st_mode & 0o777
                if mode != 0o600:
                    print(
                        f"[WARN] Password file has insecure permissions: {mode:o}"
                    )
                    print("[INFO] Fixing permissions...")
                    password_file.chmod(0o600)
                return password
        except Exception as e:
            print(f"[WARN] Could not read password file: {e}")

    # Priority 3: Generate and store
    password = generate_neo4j_password()  # ggignore
    password_file.parent.mkdir(parents=True, exist_ok=True)
    password_file.write_text(password)  # ggignore
    password_file.chmod(0o600)  # Owner read/write only

    print(f"[INFO] Generated Neo4j password: {password_file}")
    print("[INFO] Password stored securely with 0o600 permissions")

    return password


# Singleton instance (lazy-loaded)
_config: Optional[Neo4jConfig] = None


def get_config() -> Neo4jConfig:
    """Get Neo4j configuration (singleton).

    Returns:
        Neo4jConfig instance

    Raises:
        ValueError: If configuration invalid
    """
    global _config
    if _config is None:
        _config = Neo4jConfig.from_environment()
    return _config


def reset_config():
    """Reset configuration (for testing)."""
    global _config
    _config = None
