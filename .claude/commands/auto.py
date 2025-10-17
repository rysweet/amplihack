#!/usr/bin/env python3
"""
/auto command - Autonomous Agentic Loop

Invokes the auto mode CLI workflow with the user's prompt and current context.
"""

import json
import sys
from pathlib import Path

# Set up path to import amplihack modules
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "src"))

from amplihack.launcher.auto_mode import AutoMode


def main():
    """Execute auto mode with the user's prompt."""
    # Read input from Claude Code (JSON format)
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract prompt from input
    prompt = input_data.get("prompt", "").strip()

    if not prompt:
        print("Error: No prompt provided. Usage: /auto <your prompt>", file=sys.stderr)
        print("\nExample: /auto implement user authentication with tests")
        sys.exit(1)

    # Get working directory from context
    working_dir = Path(input_data.get("workingDirectory", Path.cwd()))

    # Get max turns (default 10)
    max_turns = 10

    # Print startup message
    print(f"🤖 Starting autonomous mode with prompt: {prompt[:80]}...")
    print(f"📁 Working directory: {working_dir}")
    print(f"🔄 Max turns: {max_turns}")
    print()

    # Initialize and run auto mode
    # Use "claude" as the SDK since this is being called from Claude Code
    auto = AutoMode(sdk="claude", prompt=prompt, max_turns=max_turns, working_dir=working_dir)

    # Run the agentic loop
    exit_code = auto.run()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
