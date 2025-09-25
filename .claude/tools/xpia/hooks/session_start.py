#!/usr/bin/env python3
"""
XPIA Security Session Start Hook

Initializes XPIA security monitoring at session start.
Validates XPIA system health and logs session initialization.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project src to path for imports
project_root = Path(__file__).parents[4]
sys.path.insert(0, str(project_root / "src"))

try:
    from amplihack.security.xpia_health import check_xpia_health
except ImportError:
    # Graceful degradation if XPIA modules not available
    def check_xpia_health():
        return {"status": "not_available", "message": "XPIA modules not found"}


def log_security_event(event_type: str, data: dict) -> None:
    """Log security event to XPIA security log"""
    log_dir = Path.home() / ".claude" / "logs" / "xpia"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"security_{datetime.now().strftime('%Y%m%d')}.log"

    log_entry = {"timestamp": datetime.now().isoformat(), "event_type": event_type, "data": data}

    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        # Don't fail session start if logging fails
        print(f"Warning: Failed to log security event: {e}", file=sys.stderr)


def initialize_xpia_security() -> dict:
    """Initialize XPIA security system for session"""
    try:
        # Check XPIA system health
        health_status = check_xpia_health()

        # Log session start
        session_data = {
            "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
            "working_directory": os.getcwd(),
            "health_status": health_status,
        }

        log_security_event("session_start", session_data)

        return {
            "status": "success",
            "xpia_health": health_status,
            "message": "XPIA security monitoring initialized",
        }

    except Exception as e:
        error_data = {"error": str(e), "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown")}
        log_security_event("session_start_error", error_data)

        return {
            "status": "error",
            "error": str(e),
            "message": "XPIA security initialization failed",
        }


def main():
    """Main hook execution"""
    try:
        result = initialize_xpia_security()

        # Output result for Claude Code to process
        print(json.dumps(result))

        # Exit with success status
        sys.exit(0)

    except Exception as e:
        # Output error for debugging
        error_result = {
            "status": "error",
            "error": str(e),
            "message": "XPIA session start hook failed",
        }
        print(json.dumps(error_result))

        # Don't fail session start for XPIA issues
        sys.exit(0)


if __name__ == "__main__":
    main()
