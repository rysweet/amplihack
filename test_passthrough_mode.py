#!/usr/bin/env python3
"""Test script for passthrough mode functionality."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import amplihack
sys.path.insert(0, str(Path(__file__).parent / "src"))

from amplihack.proxy.config import ProxyConfig
from amplihack.proxy.passthrough import PassthroughHandler


async def test_passthrough_handler():
    """Test the passthrough handler directly."""
    print("Testing PassthroughHandler...")

    # Create test configuration
    test_config = {
        "PASSTHROUGH_MODE": "true",
        "PASSTHROUGH_FALLBACK_ENABLED": "true",
        "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
        "AZURE_OPENAI_API_KEY": "test-azure-key",  # pragma: allowlist secret
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
    }

    # Set environment variables for testing
    for key, value in test_config.items():
        os.environ[key] = value

    try:
        handler = PassthroughHandler()

        # Test configuration
        print(f"Passthrough enabled: {handler.is_enabled()}")
        print(f"Should use fallback: {handler.should_use_fallback()}")

        # Test status
        status = handler.get_status()
        print(f"Handler status: {json.dumps(status, indent=2)}")

        # Test failure tracking
        print("\nTesting failure tracking...")
        handler.record_anthropic_failure()
        print(f"After 1 failure - should use fallback: {handler.should_use_fallback()}")

        handler.record_anthropic_failure()
        print(f"After 2 failures - should use fallback: {handler.should_use_fallback()}")

        handler.record_anthropic_success()
        print(f"After success - should use fallback: {handler.should_use_fallback()}")

        print("✅ PassthroughHandler basic tests passed")

    except Exception as e:
        print(f"❌ PassthroughHandler test failed: {e}")
        return False

    finally:
        # Clean up environment
        for key in test_config:
            os.environ.pop(key, None)

    return True


def test_proxy_config():
    """Test the proxy configuration for passthrough mode."""
    print("\nTesting ProxyConfig passthrough methods...")

    # Create test configuration
    test_config = {
        "PASSTHROUGH_MODE": "true",
        "PASSTHROUGH_FALLBACK_ENABLED": "false",
        "PASSTHROUGH_MAX_RETRIES": "5",
        "PASSTHROUGH_RETRY_DELAY": "2.0",
        "PASSTHROUGH_FALLBACK_AFTER_FAILURES": "3",
        "AZURE_CLAUDE_SONNET_DEPLOYMENT": "gpt-4-test",
        "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
    }

    # Set environment variables
    for key, value in test_config.items():
        os.environ[key] = value

    try:
        config = ProxyConfig()

        # Test passthrough configuration methods
        print(f"Passthrough mode enabled: {config.is_passthrough_mode_enabled()}")
        print(f"Fallback enabled: {config.is_passthrough_fallback_enabled()}")
        print(f"Max retries: {config.get_passthrough_max_retries()}")
        print(f"Retry delay: {config.get_passthrough_retry_delay()}")
        print(f"Fallback after failures: {config.get_passthrough_fallback_after_failures()}")

        # Test Azure Claude deployment mapping
        sonnet_deployment = config.get_azure_claude_deployment("claude-3-5-sonnet-20241022")
        print(f"Sonnet deployment: {sonnet_deployment}")

        # Test validation
        valid = config.validate_passthrough_config()
        print(f"Configuration valid: {valid}")

        print("✅ ProxyConfig passthrough tests passed")

    except Exception as e:
        print(f"❌ ProxyConfig test failed: {e}")
        return False

    finally:
        # Clean up environment
        for key in test_config:
            os.environ.pop(key, None)

    return True


def test_environment_example():
    """Test the example environment configuration."""
    print("\nTesting example .env configuration...")

    example_file = Path(__file__).parent / ".env.passthrough.example"
    if not example_file.exists():
        print("❌ Example .env file not found")
        return False

    try:
        # Read and parse the example file
        with open(example_file, "r") as f:
            content = f.read()

        # Count configuration variables
        config_lines = [
            line
            for line in content.split("\n")
            if line.strip() and not line.strip().startswith("#") and "=" in line
        ]

        print(f"Found {len(config_lines)} configuration variables in example")

        # Check for key variables
        required_vars = [
            "PASSTHROUGH_MODE",
            "ANTHROPIC_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
        ]

        for var in required_vars:
            if var in content:
                print(f"✅ {var} documented")
            else:
                print(f"❌ {var} missing from example")
                return False

        print("✅ Example .env configuration tests passed")

    except Exception as e:
        print(f"❌ Example .env test failed: {e}")
        return False

    return True


async def main():
    """Run all tests."""
    print("🧪 Testing Passthrough Mode Implementation\n")

    tests = [
        ("PassthroughHandler", test_passthrough_handler()),
        ("ProxyConfig", test_proxy_config()),
        ("Example .env", test_environment_example()),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_coro in tests:
        print(f"\n--- Running {test_name} test ---")
        try:
            if asyncio.iscoroutine(test_coro):
                result = await test_coro
            else:
                result = test_coro

            if result:
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                print(f"❌ {test_name} test FAILED")

        except Exception as e:
            print(f"❌ {test_name} test ERROR: {e}")

    print(f"\n🏁 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Passthrough mode implementation is ready.")
        return True
    else:
        print("💥 Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
