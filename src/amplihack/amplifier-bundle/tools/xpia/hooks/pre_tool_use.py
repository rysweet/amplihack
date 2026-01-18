#!/usr/bin/env python3
"""
XPIA Security Pre-Tool-Use Hook

Validates commands before execution to prevent prompt injection attacks.
Specifically focuses on Bash tool security validation.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project src to path for imports - find project root by .claude marker
current = Path(__file__).resolve()
project_root = None
for parent in current.parents:
    if (parent / ".claude").exists() and (parent / "CLAUDE.md").exists():
        project_root = parent
        break
if project_root is None:
    raise ImportError("Could not locate project root - missing .claude directory")
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "Specs"))

try:
    from xpia_defense_interface import (  # type: ignore
        ContentType,
        RiskLevel,
    )
except ImportError:
    # Mock classes for graceful degradation
    class ContentType:
        COMMAND = "command"

    class RiskLevel:
        NONE = "none"
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"


def log_security_event(event_type: str, data: dict) -> None:
    """Log security event to XPIA security log"""
    log_dir = Path.home() / ".claude" / "logs" / "xpia"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"security_{datetime.now().strftime('%Y%m%d')}.log"

    log_entry = {"timestamp": datetime.now().isoformat(), "event_type": event_type, "data": data}

    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        # Don't fail tool execution if logging fails
        pass


def validate_bash_command(command: str, context: dict[str, Any]) -> dict[str, Any]:
    """
    Validate bash command for security threats

    Returns validation result with risk assessment
    """
    try:
        # Basic threat patterns (simplified for initial implementation)
        high_risk_patterns = [
            r"rm\s+-rf\s+/[^a-zA-Z]",  # rm -rf / but not /path
            r"rm\s+-rf\s+/$",  # rm -rf / at end of line
            r"chmod\s+777",
            r"sudo\s+rm",
            r"curl.*\|\s*bash",
            r"wget.*\|\s*sh",
            r"eval\s*\(",
            r"exec\s*\(",
        ]

        medium_risk_patterns = [
            r"rm\s+-rf",
            r"chmod\s+\+x",
            r"sudo",
            r"curl.*download",
            r"wget.*download",
        ]

        # Check for high-risk patterns
        import re

        for pattern in high_risk_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return {
                    "risk_level": RiskLevel.HIGH,
                    "should_block": True,
                    "threats": [
                        {
                            "type": "command_injection",
                            "description": f"High-risk command pattern detected: {pattern}",
                            "severity": RiskLevel.HIGH,
                        }
                    ],
                    "recommendations": [
                        "Review command for security implications",
                        "Consider safer alternatives",
                    ],
                }

        # Check for medium-risk patterns
        for pattern in medium_risk_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return {
                    "risk_level": RiskLevel.MEDIUM,
                    "should_block": False,
                    "threats": [
                        {
                            "type": "elevated_privileges",
                            "description": f"Medium-risk command pattern detected: {pattern}",
                            "severity": RiskLevel.MEDIUM,
                        }
                    ],
                    "recommendations": ["Verify command necessity", "Monitor execution results"],
                }

        # Command appears safe
        return {
            "risk_level": RiskLevel.NONE,
            "should_block": False,
            "threats": [],
            "recommendations": ["Command appears safe"],
        }

    except Exception as e:
        # On validation error, allow command but log the issue
        return {
            "risk_level": RiskLevel.LOW,
            "should_block": False,
            "threats": [],
            "recommendations": [f"Validation error: {e}"],
            "error": str(e),
        }


def process_tool_use_request(tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """Process pre-tool-use validation.

    Returns Claude Code hook protocol format:
    - {} for allow (default behavior)
    - {"permissionDecision": "deny", "message": "..."} for block
    """
    try:
        # Only validate Bash tool usage
        if tool_name != "Bash":
            # Return empty dict to allow - this is the correct Claude Code protocol
            return {}

        # Extract command from parameters
        command = parameters.get("command", "")
        if not command:
            return {}  # Allow - no command to validate

        # Validate the command
        validation_result = validate_bash_command(command, parameters)

        # Log the validation
        log_data = {
            "tool": tool_name,
            "command": command[:100] + "..." if len(command) > 100 else command,
            "validation_result": validation_result,
            "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
        }
        log_security_event("pre_tool_validation", log_data)

        # Determine action using correct Claude Code hook protocol
        if validation_result["should_block"]:
            # CORRECT FORMAT: Use permissionDecision for PreToolUse hooks
            return {
                "permissionDecision": "deny",
                "message": f"🚫 XPIA Security Block: Command blocked due to security risk ({validation_result['risk_level']})\n"
                f"Threats detected: {validation_result.get('threats', [])}\n"
                f"Recommendations: {validation_result.get('recommendations', [])}",
            }

        # Allow - return empty dict (correct Claude Code protocol)
        return {}

    except Exception as e:
        # Log error but allow command execution
        log_security_event(
            "pre_tool_error",
            {"error": str(e), "tool": tool_name, "parameters": str(parameters)[:200]},
        )
        # Return empty dict to allow on error (fail-open)
        return {}


def main():
    """Main hook execution.

    Claude Code PreToolUse hook protocol:
    - Input: JSON with toolUse.name and toolUse.input
    - Output: {} to allow, {"permissionDecision": "deny", "message": "..."} to block
    - Exit 0 always (hook doesn't control exit code, output controls behavior)
    """
    try:
        # Parse input from Claude Code
        # Input format: JSON with toolUse object containing name and input
        input_data = {}
        if len(sys.argv) > 1:
            # Command line argument
            input_data = json.loads(sys.argv[1])
        else:
            # Read from stdin
            input_line = sys.stdin.read().strip()
            if input_line:
                input_data = json.loads(input_line)

        # Extract tool information using correct Claude Code protocol
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "unknown")
        parameters = tool_use.get("input", {})

        # Process the validation
        result = process_tool_use_request(tool_name, parameters)

        # Output result using correct protocol
        print(json.dumps(result))

        # Always exit 0 - the output JSON controls behavior, not exit code
        sys.exit(0)

    except Exception:
        # Output empty dict to allow on error (fail-open)
        # This follows Claude Code protocol for graceful degradation
        print(json.dumps({}))
        sys.exit(0)


if __name__ == "__main__":
    main()
