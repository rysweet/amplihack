#!/usr/bin/env python3
"""
Error protocol for hook system - structured error handling.

Provides consistent error reporting across all hooks with severity levels
and structured error information.
"""

from dataclasses import dataclass
from enum import Enum


class HookErrorSeverity(Enum):
    """Severity levels for hook errors."""

    WARNING = "warning"  # Non-critical, operation can continue
    ERROR = "error"  # Error occurred but hook can fail-open
    FATAL = "fatal"  # Critical error, but still fail-open


@dataclass
class HookError:
    """Structured error information for hooks.

    Attributes:
        severity: Error severity level
        message: Human-readable error message
        context: Additional context about where/why error occurred
        suggestion: Suggested action to resolve the error
    """

    severity: HookErrorSeverity
    message: str
    context: str | None = None
    suggestion: str | None = None


class HookException(Exception):
    """Exception raised by hooks with structured error information.

    This exception carries a HookError object that provides detailed,
    structured information about the error for logging and user feedback.
    """

    def __init__(self, error: HookError):
        self.error = error
        super().__init__(error.message)


class HookImportError(HookException):
    """Specialized exception for import failures in hooks."""


class HookConfigError(HookException):
    """Specialized exception for configuration errors in hooks."""


class HookValidationError(HookException):
    """Specialized exception for validation errors in hooks."""


__all__ = [
    "HookError",
    "HookErrorSeverity",
    "HookException",
    "HookImportError",
    "HookConfigError",
    "HookValidationError",
]
