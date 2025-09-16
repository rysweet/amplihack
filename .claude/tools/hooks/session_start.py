#!/usr/bin/env python3
"""
Claude Code hook for session start.
Reads JSON from stdin, processes, writes JSON to stdout.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add project to path if needed
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Logs directory
LOG_DIR = project_root / ".claude" / "runtime" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str, level: str = "INFO"):
    """Simple logging to file"""
    timestamp = datetime.now().isoformat()
    log_file = LOG_DIR / "session_start.log"

    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {level}: {message}\n")


def main():
    """Process session start event"""
    try:
        log("Session starting")

        # Read input
        raw_input = sys.stdin.read()
        input_data = json.loads(raw_input)

        # Extract prompt
        prompt = input_data.get("prompt", "")
        log(f"Prompt length: {len(prompt)}")

        # Build context if needed
        context_parts = []

        # Add project context
        context_parts.append("## Project Context")
        context_parts.append("This is the Microsoft Hackathon 2025 Agentic Coding project.")
        context_parts.append("Focus on building AI-powered development tools.")

        # Check for recent discoveries
        discoveries_file = project_root / "DISCOVERIES.md"
        if discoveries_file.exists():
            context_parts.append("\n## Recent Learnings")
            context_parts.append("Check DISCOVERIES.md for recent insights.")

        # Build response
        output = {}
        if context_parts:
            context = "\n".join(context_parts)
            output = {
                "additionalContext": context,
                "metadata": {
                    "source": "project_context",
                    "timestamp": datetime.now().isoformat()
                }
            }

        # Write output
        json.dump(output, sys.stdout)
        log(f"Returned context with {len(context_parts)} parts")

    except Exception as e:
        log(f"Error: {e}", "ERROR")
        # Return empty on error to not break the chain
        json.dump({}, sys.stdout)


if __name__ == "__main__":
    main()