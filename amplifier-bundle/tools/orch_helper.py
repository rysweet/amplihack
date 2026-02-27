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
    - Raw JSON embedded in prose (tries each candidate in document order)
    - Multiple code blocks (tries each independently)
    - Prose with non-JSON braces before actual JSON
    """
    # Try each code block in order (non-greedy within block = one block at a time)
    for m in re.finditer(r'```(?:json)?\s*(\{[^`]*\})\s*```', text, re.DOTALL):
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            continue  # malformed block, try next

    # Fallback: scan for first valid JSON object in document order.
    # json.JSONDecoder.raw_decode() correctly handles } inside string values,
    # unlike a manual depth counter which treats all } as structural.
    _decoder = json.JSONDecoder()
    pos = 0
    while True:
        start = text.find('{', pos)
        if start == -1:
            break
        try:
            return _decoder.raw_decode(text, start)[0]
        except json.JSONDecodeError:
            pos = start + 1
            continue
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
    # CLI for manual testing and debugging.
    # Usage:
    #   echo '{"task_type": "dev", "workstreams": []}' | python3 orch_helper.py extract
    #   echo "dev" | python3 orch_helper.py normalise
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "extract"
    text = sys.stdin.read()
    if cmd == "extract":
        print(json.dumps(extract_json(text)))
    elif cmd == "normalise":
        print(normalise_type(text.strip()))
    else:
        print(f"Unknown command: {cmd}. Use: extract | normalise", file=sys.stderr)
        sys.exit(1)
