"""Error definitions for Serena MCP integration.

This module defines all error types used by the Serena integration,
with structured error messages and suggested fixes.
"""


class SerenaIntegrationError(Exception):
    """Base exception for all Serena integration errors.

    Attributes:
        message: Human-readable error description
        suggested_fix: Actionable suggestion for resolving the error
    """

    def __init__(self, message: str, suggested_fix: str = ""):
        self.message = message
        self.suggested_fix = suggested_fix
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.suggested_fix:
            return f"{self.message}\n\nSuggested fix: {self.suggested_fix}"
        return self.message


class UvNotFoundError(SerenaIntegrationError):
    """Raised when uv is not installed or not found in PATH."""

    def __init__(self):
        super().__init__(
            message="uv is not installed or not found in PATH",
            suggested_fix=(
                "Install uv using one of these methods:\n"
                "  - curl -LsSf https://astral.sh/uv/install.sh | sh\n"
                "  - pip install uv\n"
                "Then restart your terminal and try again."
            ),
        )


class SerenaNotFoundError(SerenaIntegrationError):
    """Raised when Serena cannot be accessed via uvx."""

    def __init__(self, details: str = ""):
        message = "Serena is not accessible via uvx"
        if details:
            message += f": {details}"
        super().__init__(
            message=message,
            suggested_fix=(
                "Ensure you have:\n"
                "  1. uv installed and in PATH\n"
                "  2. Git installed (required for git+ URLs)\n"
                "  3. Network access to github.com\n"
                "Test manually: uvx --from git+https://github.com/oraios/serena serena --help"
            ),
        )


class ConfigurationError(SerenaIntegrationError):
    """Raised when MCP configuration operations fail."""

    def __init__(self, message: str, suggested_fix: str = ""):
        if not suggested_fix:
            suggested_fix = (
                "Check that:\n"
                "  1. The configuration file is valid JSON\n"
                "  2. You have write permissions to the config directory\n"
                "  3. Claude Desktop is not currently running"
            )
        super().__init__(message=message, suggested_fix=suggested_fix)


class PlatformNotSupportedError(SerenaIntegrationError):
    """Raised when the current platform is not supported."""

    def __init__(self, platform: str):
        super().__init__(
            message=f"Platform '{platform}' is not supported",
            suggested_fix=(
                "Supported platforms:\n"
                "  - Linux (including WSL)\n"
                "  - macOS\n"
                "  - Windows\n"
                "If you're on a supported platform, please file a bug report."
            ),
        )
