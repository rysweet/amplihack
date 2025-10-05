#!/usr/bin/env python3
"""Simple reflection system that delegates to UltraThink."""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional

# Pattern definitions
PATTERNS = {
    "error_handling": r"(try:|except:|raise |Error\()",
    "type_hints": r"(def \w+\([^)]*\)\s*:(?!\s*->))",
    "docstrings": r'(def \w+.*:\n(?!\s*"""|\s*\'\'\'|\s*#))',
    "code_duplication": r"(# TODO: refactor|duplicate|copy-paste)",
    "complexity": r"(if.*if.*if|for.*for.*for)",
}


def read_transcript(path: Optional[str]) -> str:
    """Read session transcript."""
    if not path or not Path(path).exists():
        return ""
    return Path(path).read_text()


def detect_patterns(content: str) -> Dict[str, int]:
    """Detect improvement patterns."""
    results = {}
    for name, pattern in PATTERNS.items():
        matches = len(re.findall(pattern, content, re.MULTILINE))
        if matches > 0:
            results[name] = matches
    return results


def should_autofix() -> bool:
    """Check if auto-fix is enabled."""
    return os.getenv("ENABLE_AUTOFIX", "").lower() == "true"


def create_github_issue(patterns: Dict[str, int]) -> Optional[str]:
    """Create GitHub issue for top pattern."""
    if not patterns:
        return None

    # Simple priority: most occurrences wins
    top_pattern = max(patterns.items(), key=lambda x: x[1])
    pattern_name, count = top_pattern

    title = f"Improve {pattern_name.replace('_', ' ')}"
    body = f"""## Pattern Detected
- **Type**: {pattern_name}
- **Occurrences**: {count}

## Suggested Improvement
Refactor code to address {pattern_name.replace("_", " ")} issues.

## Context
Detected during session reflection analysis.
"""

    # Create issue via gh CLI
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            capture_output=True,
            text=True,
            check=True,
        )
        # Extract issue URL from output
        for line in result.stdout.splitlines():
            if "github.com" in line:
                return line.strip()
    except (subprocess.CalledProcessError, Exception):
        return None
    return None


def invoke_ultrathink(issue_url: str) -> None:
    """Invoke UltraThink to handle the issue."""
    task = f"Fix the issue at {issue_url}"

    # Log the delegation
    log_decision(f"Delegating to UltraThink: {task}")

    # Create a marker file for UltraThink to pick up
    # (UltraThink monitors this directory for tasks)
    task_file = Path(".claude/runtime/tasks") / f"auto_{os.getpid()}.json"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(
        json.dumps(
            {"command": "ultrathink", "task": task, "source": "reflection", "issue_url": issue_url}
        )
    )


def log_decision(message: str) -> None:
    """Log decisions to session log."""
    log_dir = Path(".claude/runtime/logs/current")
    log_dir.mkdir(parents=True, exist_ok=True)

    decisions_file = log_dir / "DECISIONS.md"
    with decisions_file.open("a") as f:
        f.write("\n## Reflection Decision\n")
        f.write(f"**What**: {message}\n")
        f.write("**Why**: Pattern detection triggered automation\n")
        f.write("**Alternatives**: Manual review, ignore pattern\n")


def main(transcript_path: Optional[str] = None) -> Optional[str]:
    """Main reflection pipeline."""
    # Read transcript
    content = read_transcript(transcript_path)
    if not content:
        return None

    # Detect patterns
    patterns = detect_patterns(content)
    if not patterns:
        return None

    # Create issue
    issue_url = create_github_issue(patterns)
    if not issue_url:
        return None

    # Auto-fix if enabled
    if should_autofix():
        invoke_ultrathink(issue_url)

    return issue_url


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else None
    result = main(path)
    if result:
        print(f"Created issue: {result}")
