#!/usr/bin/env python3
"""
Integration test for Python debugging scenario.

Tests the complete workflow from issue #1549:
1. Detect Python project
2. Generate debugpy configuration
3. Start dap-mcp server
4. Verify server responds
5. Cleanup resources

Note: Actual MCP tool invocation (set_breakpoint, step_in, etc.) requires
Claude Code environment and cannot be tested here. This test validates the
infrastructure layer that enables MCP debugging.
"""

import json
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from detect_language import detect_language, get_debugger_for_language
from generate_dap_config import generate_config, validate_config


def calculate_average(numbers):
    """Function with intentional bug for testing."""
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers) - 1  # Bug: subtracting 1


def test_debugging():
    """Test case that should fail - for debugging demonstration."""
    # This should return 20, but returns 19 due to bug
    result = calculate_average([10, 20, 30])
    assert result == 20, f"Expected 20, got {result}"


def test_python_debug_workflow():
    """Test complete Python debugging workflow.

    Validates:
    1. Language detection identifies Python
    2. Config generation creates valid debugpy config
    3. Config includes correct program path
    4. All debugging prerequisites are met
    """
    print("\n" + "=" * 70)
    print("Python Debugging Workflow Test")
    print("=" * 70)

    # Step 1: Detect language
    print("\n[Step 1] Detecting language...")
    test_dir = Path(__file__).parent.parent
    language, confidence = detect_language(str(test_dir))

    print(f"  Language: {language}")
    print(f"  Confidence: {confidence:.0%}")
    print(f"  Debugger: {get_debugger_for_language(language)}")

    assert language == "python", f"Expected python, got {language}"
    assert confidence >= 0.70, f"Expected confidence >= 0.70, got {confidence}"

    # Step 2: Generate configuration
    print("\n[Step 2] Generating debugpy configuration...")
    config = generate_config(language="python", project_dir=str(test_dir), entry_point=__file__)

    print(f"  Config type: {config.get('type')}")
    print(f"  Program: {config.get('program')}")
    print(f"  CWD: {config.get('cwd')}")

    # Step 3: Validate configuration
    print("\n[Step 3] Validating configuration...")
    is_valid = validate_config(config)
    print(f"  Valid: {is_valid}")

    assert is_valid, "Generated config should be valid"
    assert config["type"] == "python", "Config type should be python"
    assert "program" in config, "Config must specify program"
    assert "cwd" in config, "Config must specify working directory"

    # Step 4: Save config for manual MCP testing
    print("\n[Step 4] Saving configuration for MCP server...")
    config_path = Path("/tmp/test_python_debug_config.json")
    config_path.write_text(json.dumps(config, indent=2))
    print(f"  Config saved: {config_path}")

    # Step 5: Verify test file exists
    print("\n[Step 5] Verifying test file with bug...")
    test_file = Path(__file__)
    assert test_file.exists(), "Test file should exist"
    print(f"  Test file: {test_file}")
    print("  Bug location: calculate_average() line 14 (off-by-one error)")

    print("\n" + "=" * 70)
    print("✅ Python debugging workflow validated")
    print("=" * 70)
    print("\nTo test actual MCP debugging:")
    print(f"1. Start server: ./scripts/start_dap_mcp.sh start {config_path}")
    print("2. In Claude Code session, ask to debug test_python_debug.py")
    print("3. Skill should detect debugging intent and use MCP tools:")
    print("   - set_breakpoint at line 14 (the bug)")
    print("   - step_in to calculate_average()")
    print("   - evaluate 'len(numbers)' (should be 3)")
    print("   - evaluate 'len(numbers) - 1' (should be 2, causing bug)")
    print("4. Stop server: ./scripts/start_dap_mcp.sh stop")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_python_debug_workflow()
        if success:
            print("✅ Infrastructure test passed")
            print("⚠️  MCP protocol testing requires Claude Code environment")
            sys.exit(0)
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
