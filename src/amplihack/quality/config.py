"""Configuration management for quality checks."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python
    except ImportError:
        tomllib = None  # Will gracefully handle missing TOML support


@dataclass
class QualityConfig:
    """Configuration for quality checks."""

    enabled: bool = True
    fast_mode: bool = True
    fast_mode_timeout: int = 5
    full_mode_timeout: int = 30
    validators: List[str] = field(
        default_factory=lambda: ["python", "shell", "markdown", "yaml", "json"]
    )
    exclude: List[str] = field(
        default_factory=lambda: ["**/__pycache__/**", "**/.venv/**", "**/venv/**", "**/.git/**"]
    )
    severity: List[str] = field(default_factory=lambda: ["error", "warning"])

    @classmethod
    def from_pyproject(cls, pyproject_path: Optional[Path] = None) -> "QualityConfig":
        """Load configuration from pyproject.toml.

        Args:
            pyproject_path: Path to pyproject.toml (default: search from cwd)

        Returns:
            QualityConfig instance
        """
        config = cls()

        # Find pyproject.toml
        if pyproject_path is None:
            pyproject_path = cls._find_pyproject()

        if pyproject_path and pyproject_path.exists() and tomllib:
            try:
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                # Extract amplihack.quality config
                quality_config = (
                    data.get("tool", {}).get("amplihack", {}).get("quality", {})
                )

                if quality_config:
                    config.enabled = quality_config.get("enabled", config.enabled)
                    config.fast_mode = quality_config.get("fast_mode", config.fast_mode)
                    config.fast_mode_timeout = quality_config.get(
                        "fast_mode_timeout", config.fast_mode_timeout
                    )
                    config.full_mode_timeout = quality_config.get(
                        "full_mode_timeout", config.full_mode_timeout
                    )
                    config.validators = quality_config.get("validators", config.validators)
                    config.exclude = quality_config.get("exclude", config.exclude)
                    config.severity = quality_config.get("severity", config.severity)

            except Exception:
                # If loading fails, use defaults
                pass

        # Apply environment variable overrides
        config._apply_env_overrides()

        return config

    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        # AMPLIHACK_QUALITY_ENABLED
        if "AMPLIHACK_QUALITY_ENABLED" in os.environ:
            self.enabled = os.environ["AMPLIHACK_QUALITY_ENABLED"].lower() in (
                "true",
                "1",
                "yes",
            )

        # AMPLIHACK_QUALITY_FAST_MODE
        if "AMPLIHACK_QUALITY_FAST_MODE" in os.environ:
            self.fast_mode = os.environ["AMPLIHACK_QUALITY_FAST_MODE"].lower() in (
                "true",
                "1",
                "yes",
            )

        # AMPLIHACK_QUALITY_FAST_TIMEOUT
        if "AMPLIHACK_QUALITY_FAST_TIMEOUT" in os.environ:
            try:
                self.fast_mode_timeout = int(os.environ["AMPLIHACK_QUALITY_FAST_TIMEOUT"])
            except ValueError:
                pass

        # AMPLIHACK_QUALITY_FULL_TIMEOUT
        if "AMPLIHACK_QUALITY_FULL_TIMEOUT" in os.environ:
            try:
                self.full_mode_timeout = int(os.environ["AMPLIHACK_QUALITY_FULL_TIMEOUT"])
            except ValueError:
                pass

        # AMPLIHACK_QUALITY_VALIDATORS
        if "AMPLIHACK_QUALITY_VALIDATORS" in os.environ:
            validators = os.environ["AMPLIHACK_QUALITY_VALIDATORS"]
            self.validators = [v.strip() for v in validators.split(",")]

    @staticmethod
    def _find_pyproject() -> Optional[Path]:
        """Find pyproject.toml by walking up from current directory.

        Returns:
            Path to pyproject.toml or None if not found
        """
        current = Path.cwd()

        # Walk up to root
        for parent in [current] + list(current.parents):
            pyproject = parent / "pyproject.toml"
            if pyproject.exists():
                return pyproject

        return None

    @property
    def timeout(self) -> int:
        """Get timeout based on fast_mode setting.

        Returns:
            Timeout in seconds
        """
        return self.fast_mode_timeout if self.fast_mode else self.full_mode_timeout
