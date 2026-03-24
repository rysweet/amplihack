#!/usr/bin/env python3
"""Rust-backed XPIA PreToolUse hook.

Validates Bash commands by calling the Rust-backed ``amplihack.security.rust_xpia``
bridge, which shells out to the ``xpia-defend`` binary. The Claude Code hook
contract is:

- Input on stdin as JSON with top-level ``tool_name`` / ``tool_input`` fields
- Output ``{}`` to allow
- Output ``{"permissionDecision": "deny", "message": "..."}`` to block
- Exit code always ``0``; the JSON payload controls behavior
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


def _is_amplihack_root(candidate: Path) -> bool:
    return (candidate / "pyproject.toml").exists() and (
        candidate / "src" / "amplihack" / "__init__.py"
    ).is_file()


def _find_project_root(cwd_override: str | None = None) -> Path | None:
    """Find the amplihack repo root from hook cwd or file location."""
    starts = []
    if cwd_override:
        starts.append(Path(cwd_override))
    starts.append(Path.cwd())
    starts.append(Path(__file__).resolve())

    for start in starts:
        for candidate in [start, *start.parents]:
            if _is_amplihack_root(candidate):
                return candidate
    return None


def _import_rust_xpia(project_root: Path | None):
    """Import the Rust XPIA bridge from source or installed package."""
    if project_root is not None:
        sys.path.insert(0, str(project_root / "src"))

    try:
        from amplihack.security.rust_xpia import is_available, validate_bash_command
    except ImportError as exc:
        raise ImportError(
            "Cannot import amplihack.security.rust_xpia from the repo source tree "
            "or the active Python environment."
        ) from exc

    return is_available, validate_bash_command


def _log_event(event_type: str, data: dict) -> None:
    """Write an XPIA audit log entry without breaking tool execution."""
    log_dir = Path.home() / ".claude" / "logs" / "xpia"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"rust_security_{datetime.now().strftime('%Y%m%d')}.log"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "backend": "rust",
        "data": data,
    }
    try:
        with open(log_file, "a") as handle:
            handle.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def _allow() -> None:
    print(json.dumps({}))
    sys.exit(0)


def _deny(message: str) -> None:
    print(json.dumps({"permissionDecision": "deny", "message": message}))
    sys.exit(0)


def main() -> None:
    try:
        if len(sys.argv) > 1:
            input_data = json.loads(sys.argv[1])
        else:
            stdin_text = sys.stdin.read().strip()
            input_data = json.loads(stdin_text) if stdin_text else {}

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if tool_name != "Bash":
            _allow()

        command = tool_input.get("command", "")
        if not command:
            _allow()

        project_root = _find_project_root(input_data.get("cwd"))
        is_available, validate_bash_command = _import_rust_xpia(project_root)

        if not is_available():
            _log_event("rust_unavailable", {"command": command[:100]})
            _deny(
                "🚫 XPIA Security: Rust defense binary (xpia-defend) not found. "
                "All bash commands blocked until binary is installed."
            )

        result = validate_bash_command(command)

        _log_event(
            "pre_tool_validation",
            {
                "command": command[:100],
                "is_valid": result.is_valid,
                "risk_level": result.risk_level,
                "threats": len(result.threats),
                "session_id": input_data.get("session_id", "unknown"),
            },
        )

        if result.should_block or not result.is_valid:
            threat_descriptions = [
                threat.get("description", "unknown") for threat in result.threats[:3]
            ]
            _deny(
                f"🚫 XPIA Security Block (Rust): Command blocked — {result.risk_level} risk\n"
                f"Threats: {', '.join(threat_descriptions)}\n"
                f"Recommendations: {', '.join(result.recommendations[:2])}"
            )

        _allow()
    except Exception as exc:
        _log_event("hook_error", {"error": str(exc)})
        _deny(f"🚫 XPIA Security: Hook error (fail-closed): {exc}")


if __name__ == "__main__":
    main()
