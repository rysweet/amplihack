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
from typing import Any, Dict

# Add project src to path for imports
project_root = Path(__file__).parents[4]
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


def validate_bash_command(command: str, context: Dict[str, Any]) -> Dict[str, Any]:
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


def process_tool_use_request(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Process pre-tool-use validation"""
    try:
        # Only validate Bash tool usage
        if tool_name != "Bash":
            return {
                "status": "success",
                "action": "allow",
                "message": f"No XPIA validation needed for tool: {tool_name}",
            }

        # Extract command from parameters
        command = parameters.get("command", "")
        if not command:
            return {"status": "success", "action": "allow", "message": "No command to validate"}

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

        # Determine action
        if validation_result["should_block"]:
            return {
                "status": "blocked",
                "action": "deny",
                "message": f"Command blocked due to security risk: {validation_result['risk_level']}",
                "validation": validation_result,
            }
        return {
            "status": "success",
            "action": "allow",
            "message": f"Command validated (risk: {validation_result['risk_level']})",
            "validation": validation_result,
        }

    except Exception as e:
        # Log error but allow command execution
        log_security_event(
            "pre_tool_error",
            {"error": str(e), "tool": tool_name, "parameters": str(parameters)[:200]},
        )

        return {
            "status": "error",
            "action": "allow",
            "message": f"XPIA validation error: {e}",
            "error": str(e),
        }


def main():
    """Main hook execution"""
    try:
        # Parse input from Claude Code
        # Input format: JSON with tool name and parameters
        input_data = {}
        if len(sys.argv) > 1:
            # Command line argument
            input_data = json.loads(sys.argv[1])
        else:
            # Read from stdin
            input_line = sys.stdin.read().strip()
            if input_line:
                input_data = json.loads(input_line)

        tool_name = input_data.get("tool", "unknown")
        parameters = input_data.get("parameters", {})

        # Process the validation
        result = process_tool_use_request(tool_name, parameters)

        # Output result
        print(json.dumps(result))

        # Exit based on result
        if result.get("action") == "deny":
            sys.exit(1)  # Block execution
        else:
            sys.exit(0)  # Allow execution

    except Exception as e:
        # Output error but don't block tool execution
        error_result = {
            "status": "error",
            "action": "allow",
            "message": f"XPIA pre-tool hook failed: {e}",
            "error": str(e),
        }
        print(json.dumps(error_result))
        sys.exit(0)


if __name__ == "__main__":
    main()
