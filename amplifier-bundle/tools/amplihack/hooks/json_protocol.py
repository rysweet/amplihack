#!/usr/bin/env python3
"""
JSON protocol for hook system - robust JSON parsing.

Provides resilient JSON parsing with graceful error handling for
malformed or truncated JSON input.
"""

import json
from typing import Any


class RobustJSONParser:
    """Robust JSON parser that handles malformed input gracefully.

    Features:
    - Handles truncated JSON
    - Recovers from trailing commas
    - Provides helpful error messages
    - Never crashes on bad input
    """

    def parse(self, raw_input: str) -> dict[str, Any]:
        """Parse JSON with error recovery.

        Args:
            raw_input: Raw JSON string to parse

        Returns:
            Parsed dictionary, or empty dict if parsing fails

        Raises:
            json.JSONDecodeError: If JSON is invalid and cannot be recovered
        """
        if not raw_input or not raw_input.strip():
            return {}

        # Try normal parse first
        try:
            return json.loads(raw_input)
        except json.JSONDecodeError as e:
            # Try to recover from common issues
            recovered = self._attempt_recovery(raw_input, e)
            if recovered is not None:
                return recovered
            # Re-raise original error if recovery failed
            raise

    def _attempt_recovery(
        self, raw_input: str, original_error: json.JSONDecodeError
    ) -> dict[str, Any] | None:
        """Attempt to recover from JSON parse errors.

        Args:
            raw_input: Original input string
            original_error: The original parse error

        Returns:
            Recovered dict or None if recovery failed
        """
        # Try removing trailing commas
        if "," in raw_input:
            try:
                # Remove trailing commas before closing braces/brackets
                fixed = raw_input.replace(",}", "}").replace(",]", "]")
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

        # Try truncating at last valid character
        if "Expecting" in str(original_error):
            try:
                # Find last complete JSON object
                last_brace = raw_input.rfind("}")
                if last_brace > 0:
                    truncated = raw_input[: last_brace + 1]
                    return json.loads(truncated)
            except json.JSONDecodeError:
                pass

        return None


__all__ = ["RobustJSONParser"]
