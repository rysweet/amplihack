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
import sys
from pathlib import Path

repo_src = Path(__file__).resolve().parents[2] / "src"
if repo_src.exists():
    if str(repo_src) in sys.path:
        sys.path.remove(str(repo_src))
    sys.path.insert(0, str(repo_src))
for module_name in list(sys.modules):
    if module_name == "amplihack" or module_name.startswith("amplihack."):
        sys.modules.pop(module_name, None)

from amplihack.recipes.execution_root_policy import (
    extract_gh_account as _shared_extract_gh_account,
)
from amplihack.recipes.execution_root_policy import (
    require_expected_gh_account as _shared_require_expected_gh_account,
)
from amplihack.recipes.execution_root_policy import (
    require_resolved_value as _shared_require_resolved_value,
)
from amplihack.recipes.execution_root_policy import (
    resolve_github_repo_slug as _shared_resolve_github_repo_slug,
)
from amplihack.recipes.execution_root_policy import (
    validate_execution_root as _shared_validate_execution_root,
)
from amplihack.recipes.execution_root_policy import (
    validate_gh_auth_status as _shared_validate_gh_auth_status,
)


def extract_json(text: str) -> dict:
    """Extract and parse the FIRST complete JSON object from LLM output.

    Handles:
    - Markdown code blocks (```json ... ``` or ``` ... ```)
    - Raw JSON embedded in prose (tries each candidate in document order)
    - Multiple code blocks (tries each independently)
    - Prose with non-JSON braces before actual JSON

    Priority order (fix #3075):
    1. ``json``-tagged code blocks (most explicit signal)
    2. Untagged code blocks
    3. Raw JSON in prose (balanced-brace scanner)
    """
    # 1. Prefer explicitly ```json-tagged code blocks first.
    for m in re.finditer(r"```json\s*(\{[^`]*\})\s*```", text, re.DOTALL):
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            continue  # malformed block, try next

    # 2. Try untagged code blocks (``` without a language tag).
    for m in re.finditer(r"```\s*(\{[^`]*\})\s*```", text, re.DOTALL):
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            continue

    # 3. Fallback: scan for first valid JSON object in document order.
    # json.JSONDecoder.raw_decode() correctly handles } inside string values,
    # unlike a manual depth counter which treats all } as structural.
    _decoder = json.JSONDecoder()
    pos = 0
    while True:
        start = text.find("{", pos)
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


extract_gh_account = _shared_extract_gh_account
require_expected_gh_account = _shared_require_expected_gh_account
require_resolved_value = _shared_require_resolved_value
resolve_github_repo_slug = _shared_resolve_github_repo_slug
validate_gh_auth_status = _shared_validate_gh_auth_status
validate_execution_root = _shared_validate_execution_root


if __name__ == "__main__":
    # CLI for manual testing and debugging.
    # Usage:
    #   echo '{"task_type": "dev", "workstreams": []}' | python3 orch_helper.py extract
    #   echo "dev" | python3 orch_helper.py normalise
    cmd = sys.argv[1] if len(sys.argv) > 1 else "extract"
    text = sys.stdin.read()
    if cmd == "extract":
        print(json.dumps(extract_json(text)))
    elif cmd == "normalise":
        print(normalise_type(text.strip()))
    elif cmd == "gh-account":
        print(extract_gh_account(text) or "")
    elif cmd == "repo-slug":
        if len(sys.argv) != 3:
            print("Usage: orch_helper.py repo-slug REMOTE_URL", file=sys.stderr)
            sys.exit(2)
        print(resolve_github_repo_slug(sys.argv[2]))
    elif cmd == "require-bound":
        if len(sys.argv) != 4:
            print("Usage: orch_helper.py require-bound FIELD_NAME VALUE", file=sys.stderr)
            sys.exit(2)
        print(require_resolved_value(sys.argv[3], field_name=sys.argv[2]))
    else:
        print(
            "Unknown command: "
            f"{cmd}. Use: extract | normalise | gh-account | repo-slug | require-bound",
            file=sys.stderr,
        )
        sys.exit(1)
