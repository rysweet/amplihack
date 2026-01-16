#!/usr/bin/env python3
"""Manual testing script for Copilot CLI integration.

Run this script to manually verify core functionality without pytest.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def test_formatters():
    """Test output formatters."""
    print("\n=== Testing Formatters ===")

    from amplihack.copilot.formatters import (
        FormattingConfig,
        OutputFormatter,
        StatusType,
    )

    # Create formatter
    config = FormattingConfig(use_color=True, use_emoji=True)
    formatter = OutputFormatter(config)

    # Test status messages
    print(formatter.success("Test successful"))
    print(formatter.error("Test error"))
    print(formatter.warning("Test warning"))
    print(formatter.info("Test info"))

    # Test table
    headers = ["Name", "Status"]
    rows = [["Agent A", "Success"], ["Agent B", "Failed"]]
    print("\n" + formatter.table(headers, rows))

    print("\n✓ Formatters working")


def test_errors():
    """Test error handling."""
    print("\n=== Testing Errors ===")

    from amplihack.copilot.errors import (
        CopilotError,
        InstallationError,
        InvocationError,
    )

    # Test base error
    error = CopilotError("Test error")
    print(f"Base error: {error}")

    # Test installation error
    install_error = InstallationError("npm not found")
    print(f"Installation error: {install_error}")

    # Test invocation error
    invoke_error = InvocationError("Copilot failed")
    print(f"Invocation error: {invoke_error}")

    print("\n✓ Errors working")


def test_config():
    """Test configuration."""
    print("\n=== Testing Configuration ===")

    from amplihack.copilot.config import CopilotConfig

    # Create config
    config = CopilotConfig(
        auto_sync_agents="always",
        use_color=True,
        max_turns=20,
    )

    print(f"Auto sync: {config.auto_sync_agents}")
    print(f"Use color: {config.use_color}")
    print(f"Max turns: {config.max_turns}")

    # Test serialization
    config_dict = config.to_dict()
    print(f"Serialized keys: {list(config_dict.keys())}")

    print("\n✓ Configuration working")


def test_session_manager():
    """Test session management."""
    print("\n=== Testing Session Manager ===")

    from amplihack.copilot.session_manager import CopilotSessionManager

    test_dir = Path("/tmp/test_copilot_sessions")
    test_dir.mkdir(exist_ok=True)

    try:
        # Create session
        manager = CopilotSessionManager(test_dir, "test_session_001")
        print(f"Created session: {manager.session_id}")

        # Update phase
        manager.update_phase("planning")
        print(f"Updated phase to: {manager.state.phase}")

        # Update context
        manager.update_context("test_key", "test_value")
        value = manager.get_context("test_key")
        print(f"Context value: {value}")

        print("\n✓ Session manager working")
    finally:
        # Cleanup
        import shutil

        if test_dir.exists():
            shutil.rmtree(test_dir)


def main():
    """Run all manual tests."""
    print("=" * 70)
    print("Copilot CLI Integration - Manual Testing")
    print("=" * 70)

    try:
        test_formatters()
        test_errors()
        test_config()
        test_session_manager()

        print("\n" + "=" * 70)
        print("✓ All manual tests passed!")
        print("=" * 70)
        return 0
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
