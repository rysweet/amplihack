"""Utility functions for amplihack."""

from .defensive import (
    DefensiveError,
    FileOperationError,
    JSONExtractionError,
    RetryExhaustedError,
    isolate_prompt,
    parse_llm_json,
    read_file_with_retry,
    retry_with_feedback,
    validate_json_schema,
    write_file_with_retry,
)
from .hello_world import hello_world
from .paths import FrameworkPathResolver
from .process import ProcessManager
from .uvx_staging import stage_uvx_framework


def is_uvx_deployment() -> bool:
    """Simple UVX detection based on sys.executable location."""
    import sys

    # Check if running from UV cache (primary indicator)
    return ".cache/uv/" in sys.executable or "\\cache\\uv\\" in sys.executable


__all__ = [
    # Path utilities
    "FrameworkPathResolver",
    # Process utilities
    "ProcessManager",
    # Hello world
    "hello_world",
    # UVX utilities
    "is_uvx_deployment",
    "stage_uvx_framework",
    # Defensive utilities
    "DefensiveError",
    "JSONExtractionError",
    "RetryExhaustedError",
    "FileOperationError",
    "parse_llm_json",
    "retry_with_feedback",
    "isolate_prompt",
    "read_file_with_retry",
    "write_file_with_retry",
    "validate_json_schema",
]
