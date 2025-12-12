"""Error classes for remote execution.

This module defines the error hierarchy for remote execution operations,
providing clear error categories with context and actionable messages.
"""


class RemoteExecutionError(Exception):
    """Base exception for all remote execution errors.

    All remote execution errors inherit from this base class,
    allowing for catch-all error handling while maintaining
    specific error types for detailed handling.
    """

    def __init__(self, message: str, context: dict | None = None):
        """Initialize remote execution error.

        Args:
            message: Human-readable error description
            context: Optional dict with error context (vm_name, file_path, etc.)
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        """Return formatted error message with context."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (context: {context_str})"
        return self.message


class PackagingError(RemoteExecutionError):
    """Error during context packaging phase.

    Raised when:
    - Secrets detected in files
    - Archive size exceeds limit
    - Git bundle creation fails
    - Required files missing
    """


class ProvisioningError(RemoteExecutionError):
    """Error during VM provisioning phase.

    Raised when:
    - Azlin command fails
    - VM creation timeout
    - SSH connection fails
    - Azlin not installed/configured
    """


class TransferError(RemoteExecutionError):
    """Error during file transfer phase.

    Raised when:
    - Upload/download fails
    - Checksum verification fails
    - Network connection lost
    - Insufficient disk space
    """


class ExecutionError(RemoteExecutionError):
    """Error during remote command execution phase.

    Raised when:
    - Remote command fails
    - Timeout exceeded
    - Process terminated unexpectedly
    - Environment setup fails
    """


class IntegrationError(RemoteExecutionError):
    """Error during result integration phase.

    Raised when:
    - Merge conflicts detected
    - Branch import fails
    - Log copying fails
    - Git state corruption
    """


class CleanupError(RemoteExecutionError):
    """Error during VM cleanup phase.

    Raised when:
    - VM deletion fails
    - Resource cleanup fails
    - Azlin kill command fails

    Note: Cleanup errors are typically non-fatal and logged as warnings.
    """
