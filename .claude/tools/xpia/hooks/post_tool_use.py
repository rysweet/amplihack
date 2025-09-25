#!/usr/bin/env python3
"""
XPIA Security Post-Tool-Use Hook

Monitors command execution results and logs security events.
Analyzes tool output for potential security indicators.
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
        # Don't fail post-processing if logging fails
        pass


def analyze_command_output(command: str, output: str, error: str) -> Dict[str, Any]:
    """
    Analyze command output for security indicators

    Returns analysis result with any security concerns
    """
    try:
        analysis = {"security_indicators": [], "risk_level": "none", "recommendations": []}

        # Check for common error patterns that might indicate malicious activity
        security_error_patterns = [
            ("permission denied", "Potential privilege escalation attempt"),
            ("command not found", "Possible malicious command injection"),
            ("connection refused", "Network-based attack attempt"),
            ("access denied", "Unauthorized access attempt"),
            ("sudo:", "Privilege escalation detected"),
        ]

        output_lower = output.lower() + " " + error.lower()

        for pattern, description in security_error_patterns:
            if pattern in output_lower:
                analysis["security_indicators"].append(
                    {"pattern": pattern, "description": description, "type": "error_pattern"}
                )

        # Check for suspicious output patterns
        suspicious_output_patterns = [
            ("password:", "Password prompt detected"),
            ("login:", "Login prompt detected"),
            ("token", "Authentication token in output"),
            ("key:", "Potential key material in output"),
            ("secret", "Potential secret in output"),
        ]

        for pattern, description in suspicious_output_patterns:
            if pattern in output_lower:
                analysis["security_indicators"].append(
                    {"pattern": pattern, "description": description, "type": "output_pattern"}
                )

        # Determine risk level based on indicators
        if analysis["security_indicators"]:
            if any(
                "privilege" in ind["description"].lower() for ind in analysis["security_indicators"]
            ):
                analysis["risk_level"] = "high"
                analysis["recommendations"].append(
                    "Review command for privilege escalation attempts"
                )
            elif any(
                "password" in ind["description"].lower() or "secret" in ind["description"].lower()
                for ind in analysis["security_indicators"]
            ):
                analysis["risk_level"] = "medium"
                analysis["recommendations"].append("Check for sensitive data exposure")
            else:
                analysis["risk_level"] = "low"
                analysis["recommendations"].append("Monitor for unusual patterns")
        else:
            analysis["risk_level"] = "none"
            analysis["recommendations"].append("Command execution appears normal")

        return analysis

    except Exception as e:
        return {
            "security_indicators": [],
            "risk_level": "unknown",
            "recommendations": [f"Analysis error: {e}"],
            "error": str(e),
        }


def process_tool_result(
    tool_name: str, parameters: Dict[str, Any], result: Dict[str, Any]
) -> Dict[str, Any]:
    """Process post-tool-use monitoring"""
    try:
        # Only analyze Bash tool results for now
        if tool_name != "Bash":
            return {
                "status": "success",
                "message": f"No XPIA monitoring needed for tool: {tool_name}",
            }

        command = parameters.get("command", "")
        output = result.get("output", "")
        error = result.get("error", "")
        exit_code = result.get("exit_code", 0)

        # Analyze the command output
        analysis = analyze_command_output(command, output, error)

        # Log the execution and analysis
        log_data = {
            "tool": tool_name,
            "command": command[:100] + "..." if len(command) > 100 else command,
            "exit_code": exit_code,
            "output_length": len(output),
            "error_length": len(error),
            "analysis": analysis,
            "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
        }

        # Don't log sensitive output content, just metadata
        if analysis["risk_level"] in ["medium", "high"]:
            log_data["security_alert"] = True
            # Log more details for security events
            log_data["output_sample"] = output[:200] if output else ""
            log_data["error_sample"] = error[:200] if error else ""

        log_security_event("post_tool_analysis", log_data)

        return {
            "status": "success",
            "message": f"Command monitored (risk: {analysis['risk_level']})",
            "analysis": analysis,
        }

    except Exception as e:
        # Log error but don't fail post-processing
        log_security_event(
            "post_tool_error",
            {
                "error": str(e),
                "tool": tool_name,
                "parameters_keys": list(parameters.keys()) if parameters else [],
            },
        )

        return {"status": "error", "message": f"XPIA monitoring error: {e}", "error": str(e)}


def main():
    """Main hook execution"""
    try:
        # Parse input from Claude Code
        # Input format: JSON with tool name, parameters, and result
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
        result = input_data.get("result", {})

        # Process the monitoring
        monitoring_result = process_tool_result(tool_name, parameters, result)

        # Output result
        print(json.dumps(monitoring_result))

        # Always exit successfully for post-processing
        sys.exit(0)

    except Exception as e:
        # Output error but don't fail post-processing
        error_result = {
            "status": "error",
            "message": f"XPIA post-tool hook failed: {e}",
            "error": str(e),
        }
        print(json.dumps(error_result))
        sys.exit(0)


if __name__ == "__main__":
    main()
