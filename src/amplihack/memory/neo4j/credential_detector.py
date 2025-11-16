"""Credential detection for existing Neo4j containers.

Detects credentials from running containers by inspecting environment variables.
Handles both password-based and auth-disabled configurations.
"""

import json
import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def detect_container_password(container_name: str) -> Optional[str]:
    """Detect password from existing container's environment variables.

    Args:
        container_name: Name of the container to inspect

    Returns:
        Password string if detected, None if auth disabled or detection failed

    Behavior:
        - Inspects container environment using docker inspect
        - Extracts NEO4J_AUTH environment variable
        - Parses format: "neo4j/PASSWORD" or "none"
        - Returns None if auth is disabled (NEO4J_AUTH=none)
        - Returns None if container not found or inspection fails

    Example:
        >>> password = detect_container_password("amplihack-test")
        >>> if password:
        ...     print(f"Detected password: {password}")
        ... else:
        ...     print("Auth disabled or detection failed")
    """
    try:
        logger.debug("Detecting credentials for container: %s", container_name)

        # Use docker inspect to get environment variables
        cmd = ["docker", "inspect", container_name, "--format", "{{json .Config.Env}}"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

        if result.returncode != 0:
            logger.debug("Failed to inspect container: %s", result.stderr)
            return None

        # Parse JSON array of environment variables
        env_vars = json.loads(result.stdout.strip())

        # Find NEO4J_AUTH variable
        for env_var in env_vars:
            if env_var.startswith("NEO4J_AUTH="):
                auth_value = env_var.split("=", 1)[1]
                logger.debug("Found NEO4J_AUTH in container environment")

                # Handle auth disabled case
                if auth_value == "none":
                    logger.info("Container has auth disabled (NEO4J_AUTH=none)")
                    return None

                # Parse "neo4j/PASSWORD" format
                if "/" in auth_value:
                    username, password = auth_value.split("/", 1)
                    logger.info("Detected credentials from container (user: %s)", username)
                    return password

                logger.warning(
                    "Unexpected NEO4J_AUTH format (contains %d characters)", len(auth_value)
                )
                return None

        # NEO4J_AUTH not found in environment
        logger.debug("NEO4J_AUTH not found in container environment")
        return None

    except subprocess.TimeoutExpired:
        logger.warning("Timeout inspecting container: %s", container_name)
        return None
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse container environment: %s", e)
        return None
    except Exception as e:
        logger.warning("Error detecting credentials: %s", e)
        return None


def format_credential_status(password: Optional[str]) -> str:
    """Format credential detection status for display.

    Args:
        password: Detected password or None

    Returns:
        User-friendly status string with icon

    Example:
        >>> format_credential_status("secret123")
        '🔑 Credentials detected'
        >>> format_credential_status(None)
        '⚠️ No credentials detected'
    """
    if password:
        return "🔑 Credentials detected"
    return "⚠️ No credentials detected"
