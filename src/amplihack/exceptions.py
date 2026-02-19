"""
Core exception hierarchy for the amplihack CLI.

All amplihack-specific exceptions inherit from AmplihackError, enabling
callers to catch the full domain or specific subtypes as needed.

Usage:
    from amplihack.exceptions import ClaudeBinaryNotFoundError, LaunchError

    try:
        path = require_claude_cli()
    except ClaudeBinaryNotFoundError as e:
        print(f"Please install Claude CLI: {e}")
"""


class AmplihackError(Exception):
    """Base exception for all amplihack errors."""


# ── CLI / Launch ──────────────────────────────────────────────────────────────


class CLIError(AmplihackError):
    """Base exception for CLI-level errors."""


class ClaudeBinaryNotFoundError(CLIError):
    """Raised when the Claude CLI binary cannot be located or installed."""


class LaunchError(CLIError):
    """Raised when launching Claude CLI fails."""


class AppendInstructionError(CLIError):
    """Raised when appending an instruction to an active session fails."""


# ── Launcher / Process ────────────────────────────────────────────────────────


class LauncherError(AmplihackError):
    """Base exception for launcher-level errors."""


class AutoModeError(LauncherError):
    """Raised when auto-mode encounters a fatal error."""


class SessionNotFoundError(LauncherError):
    """Raised when a required active session cannot be found."""


# ── Configuration ─────────────────────────────────────────────────────────────


class ConfigurationError(AmplihackError):
    """Raised when configuration is missing or invalid."""


class PluginError(AmplihackError):
    """Raised when a plugin operation fails."""


# ── Recipe ────────────────────────────────────────────────────────────────────


class RecipeError(AmplihackError):
    """Base exception for recipe-related failures."""


class RecipeNotFoundError(RecipeError):
    """Raised when a requested recipe cannot be found."""


class RecipeValidationError(RecipeError):
    """Raised when a recipe file fails validation."""
