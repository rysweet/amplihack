#!/usr/bin/env python3
"""Manual test script to verify auto mode log formatting fix.

This script creates a simple AutoMode instance and generates log messages
to verify that they have proper spacing (double newlines) for readability.

Run this script and visually inspect the output to confirm:
1. Log messages have blank lines between them
2. Output is readable and well-spaced
3. No regression in basic logging functionality
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from amplihack.launcher.auto_mode import AutoMode

def test_log_formatting():
    """Test that log messages have proper spacing."""
    print("=" * 60)
    print("MANUAL TEST: Auto Mode Log Formatting")
    print("=" * 60)
    print("\nThis test will output several log messages.")
    print("Verify that there is a BLANK LINE between each log entry.")
    print("-" * 60)
    print()

    # Create AutoMode instance with temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        auto_mode = AutoMode(
            sdk="claude",
            prompt="Test prompt for log formatting",
            max_turns=5,
            working_dir=Path(temp_dir)
        )

        print("EXPECTED OUTPUT: Three log messages with blank lines between them")
        print("=" * 60)
        print()

        # Generate test log messages
        auto_mode.log("First log message - testing spacing", level="INFO")
        auto_mode.log("Second log message - should have blank line above", level="INFO")
        auto_mode.log("Third log message - should have blank line above", level="INFO")

        print()
        print("=" * 60)
        print()

        # Test different log levels
        print("TESTING LOG LEVELS:")
        print("=" * 60)
        print()

        auto_mode.log("INFO level message", level="INFO")
        auto_mode.log("WARNING level message", level="WARNING")
        auto_mode.log("ERROR level message", level="ERROR")
        auto_mode.log("DEBUG level message (should NOT appear in stdout)", level="DEBUG")

        print()
        print("=" * 60)
        print()

        # Verify file logging
        log_file = auto_mode.log_dir / "auto.log"
        print(f"VERIFYING FILE LOGGING at: {log_file}")
        print()

        if log_file.exists():
            with open(log_file) as f:
                file_content = f.read()
                print("File log content:")
                print("-" * 60)
                print(file_content)
                print("-" * 60)
                print()

                # Count lines - file should use single newlines
                file_lines = file_content.strip().split('\n')
                print(f"File has {len(file_lines)} log entries")

                # Verify DEBUG is in file
                if "DEBUG" in file_content:
                    print("✓ DEBUG messages correctly written to file")
                else:
                    print("✗ DEBUG messages missing from file")
        else:
            print("✗ Log file not created")

        print()
        print("=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        print()
        print("VERIFICATION CHECKLIST:")
        print("  [ ] Stdout log messages have blank lines between them")
        print("  [ ] All messages start with [AUTO CLAUDE] prefix")
        print("  [ ] INFO, WARNING, ERROR appear in stdout")
        print("  [ ] DEBUG does NOT appear in stdout")
        print("  [ ] DEBUG DOES appear in log file")
        print("  [ ] File log uses single newlines (no blank lines)")
        print()

if __name__ == "__main__":
    test_log_formatting()
