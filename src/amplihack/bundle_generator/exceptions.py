"""
Exception hierarchy for the Agent Bundle Generator.

Provides comprehensive error handling with error codes, recovery suggestions,
and detailed context for troubleshooting.
"""

import datetime
from typing import Any


class BundleGeneratorError(Exception):
    """Base exception for all bundle generator operations."""

    def __init__(
        self,
        message: str,
        error_code: str = "GENERAL_ERROR",
        details: dict[str, Any] | None = None,
        recovery_suggestion: str | None = None,
    ):
        """
        Initialize bundle generator error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error context
            recovery_suggestion: Suggested recovery action
        """
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        self.recovery_suggestion = recovery_suggestion
        self.timestamp = datetime.datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/API responses."""
        return {
            "error": self.__class__.__name__,
            "message": str(self),
            "error_code": self.error_code,
            "details": self.details,
            "recovery_suggestion": self.recovery_suggestion,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        """Enhanced string representation including error code."""
        base_message = super().__str__()
        return f"[{self.error_code}] {base_message}"


class ParsingError(BundleGeneratorError):
    """Exception raised when prompt parsing fails."""

    def __init__(
        self,
        message: str,
        prompt_fragment: str | None = None,
        position: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Initialize parsing error.

        Args:
            message: Error description
            prompt_fragment: Problematic part of the prompt
            position: Character position where error occurred
            details: Additional context
        """
        super().__init__(
            message,
            error_code="PARSING_FAILED",
            details=details or {},
            recovery_suggestion="Check prompt syntax and structure. Ensure clear agent descriptions.",
        )
        if prompt_fragment:
            self.details["prompt_fragment"] = prompt_fragment
        if position is not None:
            self.details["position"] = position


class ExtractionError(BundleGeneratorError):
    """Exception raised when intent extraction fails."""

    def __init__(
        self,
        message: str,
        ambiguous_terms: list | None = None,
        confidence_score: float | None = None,
    ):
        """
        Initialize extraction error.

        Args:
            message: Error description
            ambiguous_terms: Terms that couldn't be interpreted
            confidence_score: Extraction confidence (0-1)
        """
        details = {}
        if ambiguous_terms:
            details["ambiguous_terms"] = ambiguous_terms
        if confidence_score is not None:
            details["confidence_score"] = confidence_score

        super().__init__(
            message,
            error_code="EXTRACTION_FAILED",
            details=details,
            recovery_suggestion="Provide clearer agent requirements. Use specific action verbs and clear role definitions.",
        )


class GenerationError(BundleGeneratorError):
    """Exception raised when agent generation fails."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        generation_stage: str | None = None,
        partial_content: str | None = None,
    ):
        """
        Initialize generation error.

        Args:
            message: Error description
            agent_name: Name of agent being generated
            generation_stage: Stage where generation failed
            partial_content: Any partial content generated
        """
        details = {}
        if agent_name:
            details["agent_name"] = agent_name
        if generation_stage:
            details["generation_stage"] = generation_stage
        if partial_content:
            details["partial_content"] = partial_content[:500]  # Limit size

        super().__init__(
            message,
            error_code="GENERATION_FAILED",
            details=details,
            recovery_suggestion="Try simplifying agent requirements or generating agents individually.",
        )


class ValidationError(BundleGeneratorError):
    """Exception raised when validation fails."""

    def __init__(
        self,
        message: str,
        validation_type: str,
        failures: list | None = None,
    ):
        """
        Initialize validation error.

        Args:
            message: Error description
            validation_type: Type of validation that failed
            failures: List of specific validation failures
        """
        super().__init__(
            message,
            error_code="VALIDATION_FAILED",
            details={
                "validation_type": validation_type,
                "failures": failures or [],
            },
            recovery_suggestion="Review validation failures and correct the identified issues.",
        )


class PackagingError(BundleGeneratorError):
    """Exception raised when bundle packaging fails."""

    def __init__(
        self,
        message: str,
        package_format: str | None = None,
        file_path: str | None = None,
    ):
        """
        Initialize packaging error.

        Args:
            message: Error description
            package_format: Format being packaged to
            file_path: Path where packaging failed
        """
        details = {}
        if package_format:
            details["package_format"] = package_format
        if file_path:
            details["file_path"] = file_path

        super().__init__(
            message,
            error_code="PACKAGING_FAILED",
            details=details,
            recovery_suggestion="Check file permissions and available disk space. Ensure package format is supported.",
        )


class DistributionError(BundleGeneratorError):
    """Exception raised when bundle distribution fails."""

    def __init__(
        self,
        message: str,
        platform: str | None = None,
        repository: str | None = None,
        http_status: int | None = None,
    ):
        """
        Initialize distribution error.

        Args:
            message: Error description
            platform: Distribution platform (e.g., "github")
            repository: Target repository
            http_status: HTTP status code if applicable
        """
        details = {}
        if platform:
            details["platform"] = platform
        if repository:
            details["repository"] = repository
        if http_status:
            details["http_status"] = http_status

        super().__init__(
            message,
            error_code="DISTRIBUTION_FAILED",
            details=details,
            recovery_suggestion="Check network connectivity and authentication. Verify repository permissions.",
        )


class RateLimitError(BundleGeneratorError):
    """Exception raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        retry_after_seconds: int,
        endpoint: str | None = None,
    ):
        """
        Initialize rate limit error.

        Args:
            message: Error description
            retry_after_seconds: Seconds until retry allowed
            endpoint: API endpoint that was rate limited
        """
        super().__init__(
            message,
            error_code="RATE_LIMIT_EXCEEDED",
            details={
                "retry_after_seconds": retry_after_seconds,
                "endpoint": endpoint,
            },
            recovery_suggestion=f"Wait {retry_after_seconds} seconds before retrying.",
        )
        self.retry_after_seconds = retry_after_seconds


class TimeoutError(BundleGeneratorError):
    """Exception raised when operations timeout."""

    def __init__(
        self,
        message: str,
        operation: str,
        timeout_seconds: int,
    ):
        """
        Initialize timeout error.

        Args:
            message: Error description
            operation: Operation that timed out
            timeout_seconds: Configured timeout value
        """
        super().__init__(
            message,
            error_code="TIMEOUT",
            details={
                "operation": operation,
                "timeout_seconds": timeout_seconds,
            },
            recovery_suggestion="Try with simpler requirements or increase timeout value.",
        )
