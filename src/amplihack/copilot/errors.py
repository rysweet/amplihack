"""Error types for Copilot CLI integration.

Philosophy:
- Clear error hierarchy
- Actionable error messages
- Zero-BS - all errors work

Public API:
    CopilotError: Base error for Copilot operations
    InstallationError: Copilot CLI not installed or installation failed
    InvocationError: Agent invocation failed
"""


class CopilotError(Exception):
    """Base error for Copilot CLI operations."""

    pass


class InstallationError(CopilotError):
    """Error installing or detecting Copilot CLI."""

    pass


class InvocationError(CopilotError):
    """Error invoking Copilot agent."""

    pass


__all__ = ["CopilotError", "InstallationError", "InvocationError"]
