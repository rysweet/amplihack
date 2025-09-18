#!/usr/bin/env python3
"""
Claude Code hook for post tool use events.
Tracks tool usage and performance metrics.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add project to path if needed
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Directories
LOG_DIR = project_root / ".claude" / "runtime" / "logs"
METRICS_DIR = project_root / ".claude" / "runtime" / "metrics"
LOG_DIR.mkdir(parents=True, exist_ok=True)
METRICS_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str, level: str = "INFO"):
    """Simple logging to file"""
    timestamp = datetime.now().isoformat()
    log_file = LOG_DIR / "post_tool_use.log"

    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {level}: {message}\n")


def save_metric(tool_name: str, duration_ms: int = None):
    """Save tool usage metrics"""
    metrics_file = METRICS_DIR / "tool_usage.jsonl"

    metric = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "duration_ms": duration_ms
    }

    with open(metrics_file, "a") as f:
        f.write(json.dumps(metric) + "\n")


def main():
    """Process post tool use event"""
    try:
        log("Processing post tool use")

        # Read input
        raw_input = sys.stdin.read()
        input_data = json.loads(raw_input)

        # Extract tool information
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "unknown")

        # Extract result if available
        result = input_data.get("result", {})

        log(f"Tool used: {tool_name}")

        # Save metrics
        save_metric(tool_name)

        # Simple decision reminders for specific tools
        output = {}
        
        # Decision triggers - gentle reminders only
        DECISION_TRIGGERS = {
            "TodoWrite": "Consider recording your task breakdown reasoning",
            "Task": "Consider documenting why you're using this agent",
            "MultiEdit": "If making significant refactoring, consider noting the approach"
        }
        
        if tool_name in DECISION_TRIGGERS:
            # Add gentle reminder as additional context
            output["additionalContext"] = DECISION_TRIGGERS[tool_name]
            log(f"Added decision reminder for {tool_name}")

        # Return output
        json.dump(output, sys.stdout)

    except Exception as e:
        log(f"Error: {e}", "ERROR")
        json.dump({}, sys.stdout)


if __name__ == "__main__":
    main()