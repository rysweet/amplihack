#!/usr/bin/env python3
"""Monitor debugging session resource usage.

Public API:
    get_process_info(pid) -> Optional[dict]
    monitor_session(pid_file, interval) -> None
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import sys

# Public API
__all__ = ['get_process_info', 'monitor_session']

# Require psutil - fail fast if not available
try:
    import psutil
except ImportError:
    print("ERROR: psutil is required for session monitoring", file=sys.stderr)
    print("Install with: pip install psutil", file=sys.stderr)
    sys.exit(1)

# Resource limits
MAX_MEMORY_MB = 4096
SESSION_TIMEOUT_MIN = 30
CHECK_INTERVAL_SEC = 5

def get_process_info(pid: int) -> Optional[Dict[str, Any]]:
    """Get process information.

    Only tracks essential metrics: memory, status, and creation time.
    CPU monitoring removed (was blocking for 1 second).
    """
    try:
        proc = psutil.Process(pid)
        return {
            'memory_mb': proc.memory_info().rss / (1024 * 1024),
            'status': proc.status(),
            'create_time': datetime.fromtimestamp(proc.create_time()),
        }
    except psutil.NoSuchProcess:
        return None
    except Exception as e:
        print(json.dumps({"error": f"Failed to get process info: {e}"}), file=sys.stderr)
        return None

def monitor_session(pid_file: str, interval: int = CHECK_INTERVAL_SEC) -> None:
    """Monitor debugging session resources.

    Args:
        pid_file: Path to PID file
        interval: Check interval in seconds
    """
    pid_path = Path(pid_file)

    if not pid_path.exists():
        print(json.dumps({"error": "Session not running", "pid_file": str(pid_path)}))
        return

    try:
        pid = int(pid_path.read_text().strip())
    except (ValueError, OSError) as e:
        print(json.dumps({"error": f"Failed to read PID file: {e}"}))
        return

    # Get process information using psutil
    info = get_process_info(pid)
    if info is None:
        print(json.dumps({"error": "Process not found", "pid": pid}))
        return

    start_time = info['create_time']

    print(json.dumps({
        "status": "monitoring_started",
        "pid": pid,
        "start_time": start_time.isoformat(),
        "limits": {
            "max_memory_mb": MAX_MEMORY_MB,
            "session_timeout_min": SESSION_TIMEOUT_MIN
        }
    }))

    while True:
        time.sleep(interval)

        info = get_process_info(pid)

        if info is None:
            print(json.dumps({"status": "completed", "pid": pid}))
            return

        # Calculate session duration
        duration_min = (datetime.now() - start_time).total_seconds() / 60
        mem_mb = info['memory_mb']

        # Check limits and collect warnings
        warnings = []

        if mem_mb > MAX_MEMORY_MB:
            warnings.append(f"Memory limit exceeded: {mem_mb:.1f}MB > {MAX_MEMORY_MB}MB")

        if duration_min > SESSION_TIMEOUT_MIN:
            warnings.append(f"Session timeout exceeded: {duration_min:.1f}min > {SESSION_TIMEOUT_MIN}min")

        # Output status (simplified - removed CPU and idle tracking)
        status = {
            "pid": pid,
            "memory_mb": round(mem_mb, 1),
            "duration_min": round(duration_min, 1),
            "status": info['status'],
            "warnings": warnings
        }

        print(json.dumps(status))

        # Exit if critical warnings
        if warnings:
            print(json.dumps({
                "status": "terminated",
                "reason": "resource_limits_exceeded",
                "warnings": warnings
            }))
            return

def main():
    """Main entry point."""
    import argparse

    global MAX_MEMORY_MB, SESSION_TIMEOUT_MIN

    parser = argparse.ArgumentParser(description='Monitor debugging session')
    parser.add_argument('--pid-file', default='.dap_mcp.pid',
                       help='Path to PID file (default: .dap_mcp.pid)')
    parser.add_argument('--interval', type=int, default=CHECK_INTERVAL_SEC,
                       help=f'Check interval in seconds (default: {CHECK_INTERVAL_SEC})')
    parser.add_argument('--max-memory', type=int, default=MAX_MEMORY_MB,
                       help=f'Max memory in MB (default: {MAX_MEMORY_MB})')
    parser.add_argument('--timeout', type=int, default=SESSION_TIMEOUT_MIN,
                       help=f'Session timeout in minutes (default: {SESSION_TIMEOUT_MIN})')
    args = parser.parse_args()

    # Update global limits
    MAX_MEMORY_MB = args.max_memory
    SESSION_TIMEOUT_MIN = args.timeout

    try:
        monitor_session(args.pid_file, args.interval)
    except KeyboardInterrupt:
        print(json.dumps({"status": "interrupted"}))
    except Exception as e:
        print(json.dumps({"error": f"Monitoring failed: {e}"}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
