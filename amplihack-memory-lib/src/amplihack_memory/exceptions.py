"""Custom exceptions for amplihack-memory-lib."""


class MemoryError(Exception):
    """Base exception for memory operations."""


class ExperienceNotFoundError(MemoryError):
    """Raised when an experience cannot be found."""


class InvalidExperienceError(MemoryError):
    """Raised when an experience fails validation."""


class MemoryQuotaExceededError(MemoryError):
    """Raised when memory quota is exceeded."""
