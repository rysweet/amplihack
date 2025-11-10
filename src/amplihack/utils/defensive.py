"""Defensive programming utilities for robust LLM interactions and I/O operations.

This module provides utilities for:
- Extracting JSON from LLM responses (parse_llm_json)
- Intelligent retry with error correction (retry_with_feedback)
- Context contamination prevention (isolate_prompt)
- Cloud sync aware file I/O with exponential backoff (read_file_with_retry, write_file_with_retry)

Philosophy: Zero-BS, ruthlessly simple defensive patterns.
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

T = TypeVar("T")


class DefensiveError(Exception):
    """Base exception for defensive utility errors."""


class JSONExtractionError(DefensiveError):
    """Failed to extract valid JSON from LLM response."""


class RetryExhaustedError(DefensiveError):
    """Retry attempts exhausted without success."""


class FileOperationError(DefensiveError):
    """File operation failed after retries."""

def parse_llm_json(response: str, strict: bool = False) -> Dict[str, Any]:
    """Extract and parse JSON from LLM response text.

    LLMs often return JSON wrapped in markdown code blocks, explanatory text,
    or with minor formatting issues. This function handles common patterns:
    - JSON in markdown code blocks (```json ... ```)
    - JSON with surrounding text
    - Minor whitespace issues
    - Trailing commas (if not strict)

    Args:
        response: Raw text response from LLM that may contain JSON
        strict: If True, enforce strict JSON parsing (no trailing commas)

    Returns:
        Parsed JSON as dictionary

    Raises:
        JSONExtractionError: If no valid JSON found or parsing fails

    Examples:
        >>> parse_llm_json('```json\\n{"key": "value"}\\n```')
        {'key': 'value'}

        >>> parse_llm_json('Here is the data: {"key": "value"}')
        {'key': 'value'}

        >>> parse_llm_json('{"key": "value",}')  # Trailing comma
        {'key': 'value'}
    """
    if not response or not response.strip():
        raise JSONExtractionError("Empty response")

    # Strategy 1: Try direct parsing first (fastest)
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks
    # Pattern: ```json ... ``` or ```\n...\n```
    code_block_pattern = r"```(?:json)?\s*\n(.*?)\n```"
    matches = re.findall(code_block_pattern, response, re.DOTALL)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # Strategy 3: Find JSON object or array in text
    # Look for balanced braces/brackets (greedy to capture full structure)
    # Start by finding opening brace/bracket and count to find matching closing
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start_idx = response.find(start_char)
        if start_idx == -1:
            continue

        # Find matching closing bracket/brace
        depth = 0
        for i in range(start_idx, len(response)):
            if response[i] == start_char:
                depth += 1
            elif response[i] == end_char:
                depth -= 1
                if depth == 0:
                    # Found complete JSON structure
                    candidate = response[start_idx : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    # Strategy 4: Fix common issues and retry
    if not strict:
        # Remove trailing commas before closing braces/brackets
        cleaned = re.sub(r",(\s*[}\]])", r"\1", response)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # All strategies failed
    raise JSONExtractionError(
        f"Could not extract valid JSON from response. First 200 chars: {response[:200]}"
    )


def retry_with_feedback(
    func: Callable[..., T],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    error_handler: Optional[Callable[[Exception, int], Optional[str]]] = None,
) -> T:
    """Execute function with intelligent retry and error feedback.

    Implements exponential backoff with optional error handling callback
    that can provide feedback for next attempt (useful for LLM corrections).

    Args:
        func: Function to execute (should accept feedback kwarg if error_handler used)
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds between retries (default: 1.0)
        backoff_factor: Multiplier for delay after each attempt (default: 2.0)
        error_handler: Optional callback(exception, attempt_num) -> feedback_string
                      Return None to use default retry, return string for feedback

    Returns:
        Result of successful function execution

    Raises:
        RetryExhaustedError: If all attempts fail
        Original exception: If error_handler re-raises

    Examples:
        >>> def flaky_api_call():
        ...     # Simulated flaky operation
        ...     import random
        ...     if random.random() < 0.5:
        ...         raise ConnectionError("Network issue")
        ...     return "success"

        >>> result = retry_with_feedback(flaky_api_call, max_attempts=3)

        >>> def llm_call_with_feedback(feedback=None):
        ...     # LLM call that can use feedback to correct errors
        ...     prompt = "Generate JSON" + (f" (Note: {feedback})" if feedback else "")
        ...     # ... actual LLM call ...
        ...     return {"result": "data"}

        >>> def json_error_handler(exc, attempt):
        ...     if isinstance(exc, JSONExtractionError):
        ...         return "Previous attempt failed JSON parsing. Ensure valid JSON."
        ...     return None

        >>> result = retry_with_feedback(
        ...     llm_call_with_feedback,
        ...     max_attempts=3,
        ...     error_handler=json_error_handler
        ... )
    """
    last_exception: Optional[Exception] = None
    delay = initial_delay
    feedback: Optional[str] = None

    for attempt in range(1, max_attempts + 1):
        try:
            # Try calling with feedback if available
            if feedback is not None and error_handler is not None:
                # Function should accept feedback kwarg
                return func(feedback=feedback)
            return func()

        except Exception as exc:
            last_exception = exc

            # Last attempt - don't retry
            if attempt == max_attempts:
                break

            # Get feedback from error handler if provided
            if error_handler:
                try:
                    feedback = error_handler(exc, attempt)
                except (TypeError, ValueError, AttributeError) as e:
                    # Error handler invalid or failed - log and continue with default retry
                    logger.debug(f"Error handler failed: {e}")
                    feedback = None
                except Exception as e:
                    # Unexpected error in handler - log warning and continue
                    logger.warning(f"Unexpected error in error handler: {e}")
                    feedback = None

            # Wait before next attempt (exponential backoff)
            time.sleep(delay)
            delay *= backoff_factor

    # All attempts exhausted
    raise RetryExhaustedError(
        f"Operation failed after {max_attempts} attempts. "
        f"Last error: {type(last_exception).__name__}: {last_exception}"
    ) from last_exception


def isolate_prompt(
    user_prompt: str,
    system_context: Optional[str] = None,
    prevent_injection: bool = True,
) -> Dict[str, str]:
    """Isolate user prompt to prevent context contamination.

    Protects against:
    - Prompt injection attempts
    - Context leakage between prompts
    - Instruction override attempts

    Args:
        user_prompt: User's input prompt
        system_context: Optional system context to include
        prevent_injection: If True, sanitize user input for common injection patterns

    Returns:
        Dictionary with isolated 'system' and 'user' prompts

    Examples:
        >>> result = isolate_prompt("What is 2+2?")
        >>> result['user']
        'What is 2+2?'

        >>> result = isolate_prompt(
        ...     "What is 2+2?",
        ...     system_context="You are a helpful math tutor."
        ... )
        >>> result['system']
        'You are a helpful math tutor.'
    """
    # Sanitize user prompt if injection prevention enabled
    if prevent_injection:
        sanitized = _sanitize_prompt_injection(user_prompt)
    else:
        sanitized = user_prompt

    # Build isolated prompt structure
    result: Dict[str, str] = {}

    if system_context:
        result["system"] = system_context.strip()

    # Wrap user content with clear delimiters
    result["user"] = f"<user_input>\n{sanitized.strip()}\n</user_input>"

    return result


def _sanitize_prompt_injection(prompt: str) -> str:
    """Sanitize prompt for common injection patterns.

    Args:
        prompt: Raw user prompt

    Returns:
        Sanitized prompt
    """
    # Remove common injection patterns - match whole phrases
    dangerous_patterns = [
        (r"ignore\s+(?:all\s+)?(?:previous|above|prior)\s+instructions?", "ignore instructions"),
        (
            r"disregard\s+(?:all\s+)?(?:previous|above|prior)\s+instructions?",
            "disregard instructions",
        ),
        (r"forget\s+(?:all\s+)?(?:previous|above|prior)\s+instructions?", "forget instructions"),
        (r"new\s+instructions?\s*:", "new instructions"),
        (r"(?:^|\s)system\s*:", "system:"),
        (r"<\s*system\s*>", "<system>"),
        (r"</\s*system\s*>", "</system>"),
    ]

    sanitized = prompt
    for pattern, name in dangerous_patterns:
        if re.search(pattern, sanitized, flags=re.IGNORECASE):
            sanitized = re.sub(pattern, "[FILTERED]", sanitized, flags=re.IGNORECASE)

    return sanitized


def read_file_with_retry(
    file_path: Union[str, Path],
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    encoding: str = "utf-8",
) -> str:
    """Read file with retry logic for cloud sync conflicts.

    Cloud storage services (Dropbox, OneDrive, iCloud) can cause temporary
    file locking or sync conflicts. This function implements exponential
    backoff to handle transient issues.

    Args:
        file_path: Path to file to read
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds between retries (default: 0.5)
        backoff_factor: Multiplier for delay after each attempt (default: 2.0)
        encoding: File encoding (default: utf-8)

    Returns:
        File contents as string

    Raises:
        FileOperationError: If all attempts fail

    Examples:
        >>> content = read_file_with_retry("config.json")
        >>> data = json.loads(content)
    """
    path = Path(file_path)
    last_exception: Optional[Exception] = None
    delay = initial_delay

    for attempt in range(1, max_attempts + 1):
        try:
            return path.read_text(encoding=encoding)

        except (OSError, PermissionError) as exc:
            last_exception = exc

            # Last attempt - don't retry
            if attempt == max_attempts:
                break

            # Wait before next attempt (exponential backoff)
            time.sleep(delay)
            delay *= backoff_factor

    # All attempts exhausted
    raise FileOperationError(
        f"Failed to read file '{path}' after {max_attempts} attempts. "
        f"Last error: {type(last_exception).__name__}: {last_exception}"
    ) from last_exception


def write_file_with_retry(
    file_path: Union[str, Path],
    content: str,
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    encoding: str = "utf-8",
    create_dirs: bool = True,
) -> None:
    """Write file with retry logic for cloud sync conflicts.

    Cloud storage services (Dropbox, OneDrive, iCloud) can cause temporary
    file locking or sync conflicts. This function implements exponential
    backoff to handle transient issues.

    Args:
        file_path: Path to file to write
        content: Content to write to file
        max_attempts: Maximum number of attempts (default: 3)
        initial_delay: Initial delay in seconds between retries (default: 0.5)
        backoff_factor: Multiplier for delay after each attempt (default: 2.0)
        encoding: File encoding (default: utf-8)
        create_dirs: Create parent directories if they don't exist (default: True)

    Raises:
        FileOperationError: If all attempts fail

    Examples:
        >>> write_file_with_retry("output.json", json.dumps(data, indent=2))
    """
    path = Path(file_path)
    last_exception: Optional[Exception] = None
    delay = initial_delay

    # Create parent directories if requested
    if create_dirs and not path.parent.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise FileOperationError(
                f"Failed to create parent directories for '{path}': {exc}"
            ) from exc

    for attempt in range(1, max_attempts + 1):
        try:
            path.write_text(content, encoding=encoding)
            return  # Success

        except (OSError, PermissionError) as exc:
            last_exception = exc

            # Last attempt - don't retry
            if attempt == max_attempts:
                break

            # Wait before next attempt (exponential backoff)
            time.sleep(delay)
            delay *= backoff_factor

    # All attempts exhausted
    raise FileOperationError(
        f"Failed to write file '{path}' after {max_attempts} attempts. "
        f"Last error: {type(last_exception).__name__}: {last_exception}"
    ) from last_exception


def validate_json_schema(
    data: Dict[str, Any],
    required_keys: List[str],
    optional_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Validate JSON data against expected schema.

    Simple schema validation for defensive JSON parsing. Ensures required
    keys are present and no unexpected keys exist.

    Args:
        data: JSON data to validate
        required_keys: List of required key names
        optional_keys: List of optional key names (default: None)

    Returns:
        Validated data (same as input)

    Raises:
        ValueError: If schema validation fails

    Examples:
        >>> data = {"name": "test", "value": 42}
        >>> validate_json_schema(data, required_keys=["name", "value"])
        {'name': 'test', 'value': 42}

        >>> validate_json_schema(data, required_keys=["name"], optional_keys=["value"])
        {'name': 'test', 'value': 42}

        >>> validate_json_schema(data, required_keys=["missing"])
        Traceback (most recent call last):
        ...
        ValueError: Missing required keys: missing
    """
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data).__name__}")

    # Check required keys
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise ValueError(f"Missing required keys: {', '.join(missing_keys)}")

    # Check for unexpected keys
    allowed_keys = set(required_keys)
    if optional_keys:
        allowed_keys.update(optional_keys)

    unexpected_keys = [key for key in data if key not in allowed_keys]
    if unexpected_keys:
        raise ValueError(f"Unexpected keys: {', '.join(unexpected_keys)}")

    return data


__all__ = [
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
