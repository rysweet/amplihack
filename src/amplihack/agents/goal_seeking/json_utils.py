"""Shared JSON parsing utilities for LLM responses.

Handles common LLM response patterns:
- Raw JSON objects
- JSON wrapped in markdown code blocks (```json ... ```)
- JSON arrays
- Graceful fallback on parse failure

Philosophy: Single source of truth for JSON extraction from LLM output.
"""

from __future__ import annotations

import json
import re
from typing import Any


def parse_llm_json(response_text: str) -> dict[str, Any] | None:
    """Parse JSON from an LLM response, handling markdown code blocks.

    Tries multiple extraction strategies:
    1. Direct JSON parse
    2. Extract from ```json ... ``` blocks
    3. Extract from generic ``` ... ``` blocks
    4. Find first { ... } block

    Args:
        response_text: Raw LLM response text

    Returns:
        Parsed dict or None if parsing fails
    """
    if not response_text:
        return None

    text = response_text.strip()

    # Strategy 1: Direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from ```json ... ``` blocks
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fenced:
        try:
            result = json.loads(fenced.group(1).strip())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find first { ... } block
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            result = json.loads(brace_match.group(0))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None


def parse_llm_json_list(response_text: str) -> list[dict[str, Any]]:
    """Parse a JSON list from an LLM response.

    Args:
        response_text: Raw LLM response text

    Returns:
        Parsed list of dicts, or empty list if parsing fails
    """
    if not response_text:
        return []

    text = response_text.strip()

    # Direct parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Extract from code block
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fenced:
        try:
            result = json.loads(fenced.group(1).strip())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    return []


__all__ = ["parse_llm_json", "parse_llm_json_list"]
