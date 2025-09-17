#!/usr/bin/env python3
"""
Claude Code hook for session stop events.
Captures learnings and updates discoveries.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add project to path if needed
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Directories
LOG_DIR = project_root / ".claude" / "runtime" / "logs"
ANALYSIS_DIR = project_root / ".claude" / "runtime" / "analysis"
LOG_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str, level: str = "INFO"):
    """Simple logging to file"""
    timestamp = datetime.now().isoformat()
    log_file = LOG_DIR / "stop.log"

    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {level}: {message}\n")


def extract_learnings(messages: list) -> list:
    """Extract potential learnings from conversation"""
    learnings = []

    # Look for patterns indicating discoveries
    keywords = [
        "discovered",
        "learned",
        "found that",
        "turns out",
        "issue was",
        "solution was",
        "pattern",
    ]

    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            for keyword in keywords:
                if keyword.lower() in content.lower():
                    # Could use more sophisticated extraction here
                    learnings.append({"keyword": keyword, "preview": content[:200]})
                    break

    return learnings


def save_session_analysis(messages: list):
    """Save session analysis for later review"""
    analysis_file = ANALYSIS_DIR / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Extract stats
    stats = {
        "timestamp": datetime.now().isoformat(),
        "message_count": len(messages),
        "tool_uses": 0,
        "errors": 0,
    }

    # Count tool uses and errors
    for msg in messages:
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if "tool_use" in str(content):
                stats["tool_uses"] += 1
            if "error" in str(content).lower():
                stats["errors"] += 1

    # Extract learnings
    learnings = extract_learnings(messages)
    if learnings:
        stats["potential_learnings"] = len(learnings)

    # Save analysis
    analysis = {"stats": stats, "learnings": learnings}

    with open(analysis_file, "w") as f:
        json.dump(analysis, f, indent=2)

    log(f"Saved session analysis to {analysis_file.name}")


def main():
    """Process stop event"""
    try:
        log("Session stopping")

        # Read input
        raw_input = sys.stdin.read()
        input_data = json.loads(raw_input)

        # Extract messages
        messages = input_data.get("messages", [])
        log(f"Processing {len(messages)} messages")

        # Save session analysis
        if messages:
            save_session_analysis(messages)

        # Check for learnings
        learnings = extract_learnings(messages)

        # Build response
        output = {}
        if learnings:
            output = {
                "metadata": {
                    "learningsFound": len(learnings),
                    "source": "session_analysis",
                    "reminder": "Check .claude/runtime/analysis/ for session details",
                }
            }
            log(f"Found {len(learnings)} potential learnings")

        # Write output
        json.dump(output, sys.stdout)

    except Exception as e:
        log(f"Error: {e}", "ERROR")
        json.dump({}, sys.stdout)


if __name__ == "__main__":
    main()
