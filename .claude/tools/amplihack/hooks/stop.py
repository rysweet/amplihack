#!/usr/bin/env python3
"""
Claude Code hook for stop events.
Checks lock flag and blocks stop if continuous work mode is enabled.
"""

import json
import sys
from pathlib import Path

# Flag file location
LOCK_FLAG = Path(__file__).parent.parent / ".lock_active"


def run():
    """Check lock flag and block stop if active.

    Returns:
        Dict with decision to block or allow stop
    """
    if LOCK_FLAG.exists():
        # Lock is active - block stop and continue working
        return {
            "decision": "block",
            "reason": "we must keep pursuing the user's objective and must not stop the turn - look for any additional TODOs, next steps, or unfinished work and pursue it diligently in as many parallel tasks as you can",
            "continue": True
        }

    # Not locked - allow stop
    return {
        "decision": "allow",
        "continue": False
    }


def main():
    """Entry point for the stop hook."""
    try:
        result = run()
        print(json.dumps(result))
        return 0
    except Exception as e:
        # On error, allow stop (fail-safe)
        error_result = {
            "decision": "allow",
            "continue": False,
            "error": str(e)
        }
        print(json.dumps(error_result), file=sys.stderr)
        return 0  # Don't fail the hook - just allow stop


if __name__ == "__main__":
    sys.exit(main())
