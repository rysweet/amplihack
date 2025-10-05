#!/usr/bin/env python3
"""Simple reflection system that delegates to UltraThink."""

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

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


def check_for_duplicates(title: str) -> List[str]:
    """Check for existing similar issues."""
    try:
        keywords = title.lower().replace("improve ", "").split()[:3]
        result = subprocess.run(
            ["gh", "issue", "list", "--search", " ".join(keywords), "--json", "number,title,state"],
            capture_output=True,
            text=True,
            check=True,
        )
        issues = json.loads(result.stdout)
        return [
            f"https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/{issue['number']}"
            for issue in issues
            if issue["state"] == "open" and any(k in issue["title"].lower() for k in keywords)
        ]
    except Exception:
        return []


def create_github_issue(patterns: Dict[str, int], context: Dict[str, str] = None) -> Optional[str]:
    """Create GitHub issue for top pattern with enhanced context."""
    if not patterns:
        return None

    top_pattern = max(patterns.items(), key=lambda x: x[1])
    pattern_name, count = top_pattern
    title = f"Improve {pattern_name.replace('_', ' ')}"

    # Check for duplicates before creating
    duplicates = check_for_duplicates(title)
    if duplicates:
        log_decision(f"Skipped creating issue '{title}' - {len(duplicates)} similar issues exist")
        return duplicates[0]

    # Enhanced body with context
    ctx = context or {}
    body = f"""## Pattern: {pattern_name} ({count} occurrences)
**Session**: {ctx.get("session_id", "unknown")} | **Time**: {ctx.get("timestamp", "unknown")}

## Examples
{ctx.get("examples", f"Found {count} occurrences")}

## Fix
Refactor {pattern_name.replace("_", " ")} issues.

## Steps
1. Review locations 2. Prioritize 3. Apply tools

*Auto-generated*"""

    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.splitlines():
            if "github.com" in line:
                return line.strip()
    except (subprocess.CalledProcessError, Exception):
        return None
    return None


def cleanup_duplicate_issues() -> int:
    """Clean up obvious duplicate issues."""
    try:
        result = subprocess.run(
            ["gh", "issue", "list", "--state", "open", "--json", "number,title"],
            capture_output=True,
            text=True,
            check=True,
        )
        issues = json.loads(result.stdout)
        seen_titles = {}
        closed = 0

        for issue in issues:
            title = issue["title"]
            if title in seen_titles and issue["number"] > seen_titles[title]:
                subprocess.run(
                    [
                        "gh",
                        "issue",
                        "close",
                        str(issue["number"]),
                        "--comment",
                        f"Duplicate of #{seen_titles[title]}",
                    ],
                    capture_output=True,
                )
                closed += 1
                log_decision(f"Closed #{issue['number']} as duplicate")
            else:
                seen_titles[title] = issue["number"]
        return closed
    except Exception:
        return 0


def invoke_ultrathink(issue_url: str) -> None:
    """Invoke UltraThink to handle the issue."""
    task = f"Fix the issue at {issue_url}"
    log_decision(f"Delegating to UltraThink: {task}")
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
    with (log_dir / "DECISIONS.md").open("a") as f:
        f.write(f"\n## {message}\n**Why**: Pattern detection | **Alt**: Manual review\n")


def main(transcript_path: Optional[str] = None) -> Optional[str]:
    """Main reflection pipeline."""
    content = read_transcript(transcript_path)
    if not content:
        return None

    patterns = detect_patterns(content)
    if not patterns:
        return None

    # Clean up duplicates and prepare context
    duplicates_closed = cleanup_duplicate_issues()
    if duplicates_closed > 0:
        log_decision(f"Cleaned up {duplicates_closed} duplicates")

    context = {
        "session_id": str(os.getpid()),
        "timestamp": datetime.now().isoformat(),
        "examples": f"Found {sum(patterns.values())} occurrences across {len(patterns)} types",
    }
    issue_url = create_github_issue(patterns, context)
    if not issue_url:
        return None
    if should_autofix():
        invoke_ultrathink(issue_url)
    return issue_url


if __name__ == "__main__":
    import sys

    result = main(sys.argv[1] if len(sys.argv) > 1 else None)
    if result:
        print(f"Created issue: {result}")
