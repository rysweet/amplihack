#!/usr/bin/env python3
"""
Ruthlessly Simple Shell Command Hook

Executes safe shell commands when prompts start with '!'.
Blocks prompt submission and shows command output.
"""

import json
import subprocess
import sys

# Safe read-only commands only
SAFE_COMMANDS = {"ls", "pwd", "date", "whoami", "cat", "head", "tail", "echo", "wc"}


def main():
    try:
        # Read hook input
        data = json.load(sys.stdin)
        prompt = data.get("prompt", "").strip()

        # Pass through normal prompts
        if not prompt.startswith("!"):
            sys.exit(0)

        # Extract command
        command = prompt[1:].strip()
        if not command:
            output = {
                "decision": "block",
                "reason": "Empty shell command. Usage: !<command>\nExample: !ls -la",
            }
            print(json.dumps(output))
            sys.exit(0)

        # Basic safety: whitelist check
        base_cmd = command.split()[0]
        if base_cmd not in SAFE_COMMANDS:
            safe_list = ", ".join(sorted(SAFE_COMMANDS))
            reason = f"🚫 Command '{base_cmd}' not allowed.\n\nAllowed commands: {safe_list}"
            output = {"decision": "block", "reason": reason}
            print(json.dumps(output))
            sys.exit(0)

        # Execute with basic safety
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=5, cwd="/tmp"
        )

        # Format output
        output_text = f"$ {command}\n\n"
        if result.stdout:
            output_text += result.stdout
        if result.stderr:
            output_text += f"\nError: {result.stderr}"
        if result.returncode != 0:
            output_text += f"\nExit code: {result.returncode}"

        output = {"decision": "block", "reason": output_text}
        print(json.dumps(output))

    except subprocess.TimeoutExpired:
        output = {"decision": "block", "reason": "Command timed out (5 second limit)"}
        print(json.dumps(output))
    except Exception as e:
        output = {"decision": "block", "reason": f"Error: {str(e)}"}
        print(json.dumps(output))


if __name__ == "__main__":
    main()
