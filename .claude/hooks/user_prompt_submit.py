#!/usr/bin/env python3
"""
Ruthlessly Simple Shell Command Hook

Executes safe shell commands when prompts start with '!'.
Blocks prompt submission and shows command output.
"""

import json
import shlex
import subprocess
import sys
import tempfile

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

        # Parse command safely
        try:
            cmd_args = shlex.split(command)
        except ValueError:
            output = {"decision": "block", "reason": "🚫 Invalid command format"}
            print(json.dumps(output))
            sys.exit(0)

        # Basic safety: whitelist check
        base_cmd = cmd_args[0]
        if base_cmd not in SAFE_COMMANDS:
            safe_list = ", ".join(sorted(SAFE_COMMANDS))
            reason = f"🚫 Command '{base_cmd}' not allowed.\n\nAllowed commands: {safe_list}"
            output = {"decision": "block", "reason": reason}
            print(json.dumps(output))
            sys.exit(0)

        # Execute safely without shell
        result = subprocess.run(
            cmd_args,
            shell=False,
            capture_output=True,
            text=True,
            timeout=5,
            cwd=tempfile.gettempdir(),
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
        output = {"decision": "block", "reason": f"Error: {e!s}"}
        print(json.dumps(output))


if __name__ == "__main__":
    main()
