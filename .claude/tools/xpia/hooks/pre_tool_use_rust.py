#!/usr/bin/env python3
"""
XPIA PreToolUse Hook — Rust-backed.

Calls the xpia-defend Rust binary via subprocess to validate bash commands
before execution. This replaces the Python regex-based validation with
guaranteed-linear Rust regex matching.

Protocol (Claude Code PreToolUse):
  Input:  JSON on stdin with top-level keys:
          tool_name, tool_input, session_id, cwd, hook_event_name, etc.
  Output: {} to allow, {"permissionDecision": "deny", "message": "..."} to block
  Exit:   Always 0 (output controls behavior, not exit code)
"""

import json
import sys
from pathlib import Path


# Find project root: Claude Code provides CWD in the hook input,
# and also sets the process CWD to the project directory.
# Walk up from CWD first, then fall back to __file__ parent chain.
def _find_project_root(cwd_override: str | None = None) -> Path | None:
    starts = []
    if cwd_override:
        starts.append(Path(cwd_override))
    starts.append(Path.cwd())
    starts.append(Path(__file__).resolve())
    for start in starts:
        for candidate in [start] + list(start.parents):
            if (candidate / "pyproject.toml").exists() and (candidate / "src").is_dir():
                return candidate
    return None


def _log_event(event_type: str, data: dict) -> None:
    """Log to XPIA security log."""
    log_dir = Path.home() / ".claude" / "logs" / "xpia"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = (
        log_dir / f"rust_security_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.log"
    )
    entry = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "event_type": event_type,
        "backend": "rust",
        "data": data,
    }
    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Never fail tool execution over logging


def _allow() -> None:
    print(json.dumps({}))
    sys.exit(0)


def _deny(message: str) -> None:
    print(json.dumps({"permissionDecision": "deny", "message": message}))
    sys.exit(0)


def main():
    try:
        # Parse input from Claude Code
        input_data = {}
        if len(sys.argv) > 1:
            input_data = json.loads(sys.argv[1])
        else:
            stdin_text = sys.stdin.read().strip()
            if stdin_text:
                input_data = json.loads(stdin_text)

        # Claude Code sends top-level tool_name and tool_input
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # Only validate Bash tool
        if tool_name != "Bash":
            _allow()

        command = tool_input.get("command", "")
        if not command:
            _allow()

        # Resolve project root using CWD from hook input
        cwd_override = input_data.get("cwd")
        project_root = _find_project_root(cwd_override)
        if project_root is None:
            _deny("🚫 XPIA: Cannot find project root — blocking (fail-closed).")

        sys.path.insert(0, str(project_root / "src"))
        try:
            from amplihack.security.rust_xpia import is_available, validate_bash_command
        except ImportError:
            _deny("🚫 XPIA: Cannot import rust_xpia bridge — blocking (fail-closed).")
            return  # unreachable, _deny calls sys.exit

        if not is_available():
            _log_event("rust_unavailable", {"command": command[:100]})
            _deny(
                "🚫 XPIA Security: Rust defense binary (xpia-defend) not found. "
                "All bash commands blocked until binary is installed."
            )

        # Call Rust binary via subprocess bridge
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
            threat_descs = [t.get("description", "unknown") for t in result.threats[:3]]
            _deny(
                f"🚫 XPIA Security Block (Rust): Command blocked — {result.risk_level} risk\n"
                f"Threats: {', '.join(threat_descs)}\n"
                f"Recommendations: {', '.join(result.recommendations[:2])}"
            )
        else:
            _allow()

    except Exception as e:
        # Fail-closed: block on ANY error
        _log_event("hook_error", {"error": str(e)})
        _deny(f"🚫 XPIA Security: Hook error (fail-closed): {e}")


if __name__ == "__main__":
    main()
