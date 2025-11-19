"""Secure secrets loading and container environment preparation."""

import json
import os
import re
import yaml
from pathlib import Path
from typing import Dict, Optional


class SecretsManager:
    """Secure secrets loading and container environment preparation."""

    @staticmethod
    def load(secrets_file: Optional[Path] = None) -> Dict[str, str]:
        """
        Load secrets with standard priority:
        1. Environment variables (highest priority)
        2. .env file in current directory
        3. Custom secrets file (if provided)

        Args:
            secrets_file: Optional custom secrets file path

        Returns:
            dict: All secrets loaded from the highest priority source.
                  Returns empty dict if no sources available.

        Raises:
            PermissionError: If custom secrets file has insecure permissions
            ValueError: If custom secrets file contains malformed YAML/JSON
        """
        secrets = {}

        # Priority 1: Check environment variable
        if 'ANTHROPIC_API_KEY' in os.environ:
            secrets['ANTHROPIC_API_KEY'] = os.environ['ANTHROPIC_API_KEY']
            return secrets

        # Priority 2: Check .env file
        env_file = Path.cwd() / '.env'
        if env_file.exists():
            # Parse .env file (KEY=value format)
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    secrets[key.strip()] = value.strip()

            if secrets:
                return secrets

        # Priority 3: Custom file (if provided)
        if secrets_file:
            return SecretsManager._load_from_file(secrets_file)

        # No secrets found - return empty dict
        return {}

    @staticmethod
    def _load_from_file(file_path: Path) -> Dict[str, str]:
        """
        Load secrets from a custom file (YAML or JSON format).

        Args:
            file_path: Path to secrets file

        Returns:
            dict: Secrets loaded from file

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file has insecure permissions
            ValueError: If file contains malformed YAML/JSON
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Secrets file not found: {file_path}")

        # Validate permissions before loading
        SecretsManager._validate_file_permissions(file_path)

        content = file_path.read_text()

        # Try YAML first (most common)
        try:
            secrets = yaml.safe_load(content)
            if secrets is None:
                return {}
            return secrets if isinstance(secrets, dict) else {}
        except yaml.YAMLError:
            # Fallback to JSON
            try:
                secrets = json.loads(content)
                return secrets if isinstance(secrets, dict) else {}
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Failed to parse secrets file as YAML or JSON: {e}"
                )

    @staticmethod
    def _validate_file_permissions(file_path: Path) -> bool:
        """
        Ensure secrets file has restrictive permissions (0o600).

        Args:
            file_path: Path to secrets file

        Returns:
            True if permissions are secure

        Raises:
            PermissionError: If permissions are insecure (not 0o600)
        """
        # Get file permissions
        file_stat = file_path.stat()
        file_mode = file_stat.st_mode & 0o777

        # Check if permissions are exactly 0o600
        if file_mode != 0o600:
            raise PermissionError(
                f"Secrets file has insecure permissions: {oct(file_mode)}. "
                f"Run: chmod 600 {file_path}"
            )

        return True

    @staticmethod
    def get_container_env(required_vars: list[str]) -> Dict[str, str]:
        """
        Prepare environment variables for container injection.
        Minimal principle: only pass required variables.

        Priority order:
        1. Explicit system environment variables (highest)
        2. ~/.claude-msec-key values (overlay, don't override)

        Args:
            required_vars: List of environment variable names needed

        Returns:
            dict: Environment variables ready for container injection

        Raises:
            ValueError: If any required variables are missing
        """
        env = {}

        # First, check system environment (highest priority)
        for var in required_vars:
            if var in os.environ:
                env[var] = os.environ[var]

        # Load file secrets and overlay (don't override system vars)
        file_secrets = SecretsManager.load()
        for var in required_vars:
            if var not in env and var in file_secrets:
                env[var] = file_secrets[var]

        # Validate all required vars are present
        missing = [var for var in required_vars if var not in env]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        # Sanitize all values
        for key, value in env.items():
            env[key] = SecretsManager.sanitize_value(value)

        return env

    @staticmethod
    def sanitize_value(value: str) -> str:
        """
        Validate secret value doesn't contain shell injection patterns.

        Args:
            value: Secret value to validate

        Returns:
            str: Original value if safe

        Raises:
            ValueError: If value contains suspicious patterns
        """
        # Check for shell injection patterns
        suspicious_patterns = [
            r'\$\(',  # Command substitution $(...)
            r'`',     # Backtick command substitution
            r';\s*\w',  # Command chaining with semicolon
            r'\|\s*\w',  # Pipe to another command
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, value):
                raise ValueError(
                    f"Suspicious pattern detected in secret value: {pattern}"
                )

        return value
