#!/usr/bin/env python3
"""Analyze claude-trace logs and identify improvement opportunities."""

import subprocess
from pathlib import Path
from typing import List


def find_unprocessed_logs(trace_dir: str) -> List[str]:
    trace_path = Path(trace_dir)
    if not trace_path.exists():
        return []
    return [str(f) for f in trace_path.glob("*.jsonl") if f.parent.name != "already_processed"]


def build_analysis_prompt(log_files: List[str]) -> str:
    logs_list = "\n".join(log_files)
    return f"""/ultrathink: Please very carefully analyze all of these logs:
{logs_list}

Look for patterns or problems in these 5 categories:

1. **Agent Opportunities**: Patterns suggesting new special-purpose agents
2. **Frustration Points**: User frustration indicating instruction/prompt improvements
3. **Failing Patterns**: Tools or patterns that repeatedly failed (need instruction updates)
4. **Simplification**: Opportunities to build new CLI tools to simplify workflows
5. **New Commands**: New claude code commands that could shortcut common tasks

For each improvement you identify:
- Open a detailed GitHub issue with evidence from logs
- Follow the full default workflow to create a PR addressing the issue
"""


def process_log(log_file: str) -> None:
    log_path = Path(log_file)
    if not log_path.exists():
        return
    processed_dir = log_path.parent / "already_processed"
    processed_dir.mkdir(exist_ok=True)
    log_path.rename(processed_dir / log_path.name)


def main() -> None:
    log_files = find_unprocessed_logs(".claude-trace")
    if not log_files:
        print("No unprocessed trace logs found.")
        return
    try:
        result = subprocess.run(["amplihack", build_analysis_prompt(log_files)], check=False)
        if result.returncode == 0:
            for log_file in log_files:
                process_log(log_file)
            print(f"Successfully processed {len(log_files)} log file(s).")
        else:
            print(
                f"Analysis failed with exit code {result.returncode}. Logs not marked as processed."
            )
    except Exception as e:
        print(f"Error during analysis: {e}")


if __name__ == "__main__":
    main()
