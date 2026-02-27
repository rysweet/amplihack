#!/usr/bin/env python3
"""
Shared orchestration helper functions for smart-orchestrator recipe.

Provides extract_json() and normalise_type() used by the parse-decomposition
and create-workstreams-config bash steps. Having them here (not inline in YAML
heredocs) enables linting, unit testing, and import by other tools.
"""
from __future__ import annotations
import json
import re


def extract_json(text: str) -> dict:
    """Extract and parse the FIRST complete JSON object from LLM output.

    Handles:
    - Markdown code blocks (```json ... ``` or ``` ... ```)
    - Raw JSON embedded in prose
    - Multiple code blocks (returns only the first valid one)
    """
    # Try each code block in order — use non-greedy within each block
    # to avoid merging multiple blocks.
    # [^`]* stops at the next backtick, ensuring one code block is parsed at a time.
    for m in re.finditer(r'```(?:json)?\s*(\{[^`]*\})\s*```', text, re.DOTALL):
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            continue  # malformed block, try next

    # Fallback: find the first complete balanced-brace JSON object
    start = text.find('{')
    if start == -1:
        return {}

    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    break
    return {}


def normalise_type(raw: str) -> str:
    """Normalise LLM task_type to one of: Q&A, Operations, Investigation, Development."""
    t = raw.lower()
    if any(k in t for k in ("q&a", "qa", "question", "answer")):
        return "Q&A"
    if any(k in t for k in ("ops", "operation", "admin", "command")):
        return "Operations"
    if any(k in t for k in ("invest", "research", "explor", "analys", "understand")):
        return "Investigation"
    return "Development"


if __name__ == "__main__":
    # CLI: echo '{"task_type": "Development"}' | python3 orch_helper.py
    import sys
    print(json.dumps(extract_json(sys.stdin.read())))
