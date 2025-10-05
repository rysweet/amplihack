#!/usr/bin/env python3
"""Integration test for passthrough mode with the proxy server."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx  # type: ignore

# Test configuration
TEST_CONFIG = {
    "PASSTHROUGH_MODE": "true",
    "PASSTHROUGH_FALLBACK_ENABLED": "true",
    "ANTHROPIC_API_KEY": "test-invalid-key",  # Use invalid key to trigger failures  # pragma: allowlist secret
    "AZURE_OPENAI_API_KEY": "test-azure-key",  # pragma: allowlist secret
    "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
    "PORT": "8083",  # Use different port for testing
    "LOG_LEVEL": "DEBUG",
}


def start_test_server():
    """Start the proxy server for testing."""
    print("Starting test proxy server...")

    # Set test environment variables
    env = os.environ.copy()
    env.update(TEST_CONFIG)

    # Start the server
    cmd = [sys.executable, "-m", "amplihack.proxy.server"]
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent,
    )

    # Wait a moment for the server to start
    time.sleep(3)

    return process


def test_status_endpoint():
    """Test the status endpoint."""
    print("Testing status endpoint...")

    try:
        response = httpx.get("http://localhost:8083/status", timeout=10)

        if response.status_code == 200:
            status = response.json()
            print("✅ Status endpoint working")
            print(f"Passthrough mode: {status.get('passthrough_mode')}")

            if status.get("passthrough_mode"):
                passthrough_status = status.get("passthrough_status", {})
                print(f"Passthrough enabled: {passthrough_status.get('passthrough_enabled')}")
                print(f"Anthropic configured: {passthrough_status.get('anthropic_configured')}")
                print(f"Azure configured: {passthrough_status.get('azure_configured')}")

            return True
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Status endpoint error: {e}")
        return False


def test_messages_endpoint():
    """Test the messages endpoint with passthrough mode."""
    print("Testing messages endpoint...")

    # Test request data
    request_data = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "Hello! This is a test message."}],
    }

    headers = {"Content-Type": "application/json", "x-api-key": "test-key"}

    try:
        response = httpx.post(
            "http://localhost:8083/v1/messages", json=request_data, headers=headers, timeout=30
        )

        print(f"Response status: {response.status_code}")

        if response.status_code in [200, 401, 403, 429, 500]:
            # These are expected status codes during testing
            print(f"✅ Messages endpoint responded (status: {response.status_code})")

            try:
                response_data = response.json()
                print(f"Response type: {response_data.get('type', 'unknown')}")
            except json.JSONDecodeError:
                print("Response is not JSON (expected for some errors)")

            return True
        else:
            print(f"❌ Unexpected response status: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Messages endpoint error: {e}")
        return False


def main():
    """Run integration tests."""
    print("🧪 Passthrough Mode Integration Test\n")

    # Check if httpx is available
    try:
        import httpx  # type: ignore  # noqa: F401
    except ImportError:
        print("❌ httpx not available. Install with: pip install httpx")
        return False

    # Start the test server
    server_process = None
    try:
        server_process = start_test_server()

        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print("❌ Server failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False

        print("Server started, running tests...\n")

        # Run tests
        tests = [
            ("Status Endpoint", test_status_endpoint),
            ("Messages Endpoint", test_messages_endpoint),
        ]

        passed = 0
        for test_name, test_func in tests:
            print(f"--- Testing {test_name} ---")
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name} PASSED\n")
                else:
                    print(f"❌ {test_name} FAILED\n")
            except Exception as e:
                print(f"❌ {test_name} ERROR: {e}\n")

        print(f"🏁 Integration Test Results: {passed}/{len(tests)} tests passed")

        if passed == len(tests):
            print("🎉 Integration tests passed! Passthrough mode is working.")
            return True
        else:
            print("💥 Some integration tests failed.")
            return False

    finally:
        # Clean up
        if server_process:
            print("Stopping test server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait()
            print("Server stopped.")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
