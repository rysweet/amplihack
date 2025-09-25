#!/usr/bin/env python3
"""
Example demonstrating claude-trace integration usage.

This example shows how to use the simple claude-trace integration
for debugging and monitoring Claude Code interactions.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.utils.claude_trace import get_claude_command, should_use_trace


def main():
    """Demonstrate claude-trace integration."""
    print("🔍 Claude-Trace Integration Example")
    print("=" * 50)

    # 1. Basic Usage - Check Current State
    print("\n📋 Current Configuration:")
    print("-" * 30)

    print(f"AMPLIHACK_USE_TRACE: {os.getenv('AMPLIHACK_USE_TRACE', 'not set')}")
    print(f"Should use trace: {should_use_trace()}")
    print(f"Claude command: {get_claude_command()}")

    # 2. Enable Trace Mode
    print("\n🔧 Enabling Trace Mode:")
    print("-" * 30)

    # Set environment variable
    os.environ["AMPLIHACK_USE_TRACE"] = "1"
    print("Set AMPLIHACK_USE_TRACE=1")
    print(f"Should use trace: {should_use_trace()}")
    print(f"Claude command: {get_claude_command()}")

    # 3. Disable Trace Mode
    print("\n🔧 Disabling Trace Mode:")
    print("-" * 30)

    # Unset environment variable
    if "AMPLIHACK_USE_TRACE" in os.environ:
        del os.environ["AMPLIHACK_USE_TRACE"]
    print("Unset AMPLIHACK_USE_TRACE")
    print(f"Should use trace: {should_use_trace()}")
    print(f"Claude command: {get_claude_command()}")

    # 4. Usage Instructions
    print("\n📖 Usage Instructions:")
    print("-" * 30)
    print("To enable claude-trace:")
    print("  export AMPLIHACK_USE_TRACE=1")
    print("  # OR")
    print("  AMPLIHACK_USE_TRACE=1 amplihack")
    print()
    print("To disable (default):")
    print("  unset AMPLIHACK_USE_TRACE")
    print("  # OR")
    print("  export AMPLIHACK_USE_TRACE=0")

    print("\n" + "=" * 50)
    print("🎉 Claude-Trace Example Complete!")
    print()
    print("Key Features:")
    print("  ✅ Simple environment variable control")
    print("  ✅ Automatic claude-trace installation")
    print("  ✅ Graceful fallback to regular claude")
    print("  ✅ No configuration files needed")


if __name__ == "__main__":
    main()
