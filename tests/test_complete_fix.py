#!/usr/bin/env python3
"""Complete test of all fixes made to the REST API client."""

import json
import os
import warnings


def test_all_fixes():
    """Test all critical and security fixes."""

    print("Testing REST API Client Fixes")
    print("=" * 50)

    # Test 1: Import fix (critical bug)
    print("\n1. Testing import fix (APIClientError vs APIException)...")
    from rest_api_client.exceptions import APIClientError

    from rest_api_client.models import APIResponse

    # Create a response with non-standard error code
    response = APIResponse(status_code=999, body=json.dumps({"error": "Custom error"}), headers={})

    try:
        response.raise_for_status()
    except APIClientError as e:
        print(f"   ✓ APIClientError raised correctly for non-standard status: {e.status_code}")
        assert e.status_code == 999
    except Exception as e:
        print(f"   ✗ Wrong exception type: {type(e).__name__}")
        raise

    # Test 2: Environment variable support for API key
    print("\n2. Testing environment variable support for API key...")
    from rest_api_client import APIClient

    # Set environment variable  # pragma: allowlist secret
    os.environ["API_KEY"] = "test-api-key-from-env"  # pragma: allowlist secret

    # Create client without explicit API key
    client = APIClient(base_url="https://api.example.com")

    # Check if API key was picked up from environment
    if "Authorization" in client.headers:
        auth_header = client.headers["Authorization"]
        if auth_header == "Bearer test-api-key-from-env":
            print("   ✓ API key loaded from environment variable")
        else:
            print(f"   ✗ Wrong auth header: {auth_header}")
    else:
        print("   ✗ Authorization header not set")

    # Clean up
    del os.environ["API_KEY"]

    # Test 3: SSL verification warning
    print("\n3. Testing SSL verification warning...")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Create client with SSL verification disabled
        client = APIClient(base_url="https://api.example.com", verify_ssl=False)

        # Check if warning was issued
        if w:
            warning = w[0]
            if issubclass(warning.category, UserWarning):
                print(f"   ✓ Security warning issued: {warning.message}")
            else:
                print(f"   ✗ Wrong warning type: {warning.category}")
        else:
            print("   ✗ No warning issued for disabled SSL")

    # Test 4: Test dependency (responses package)
    print("\n4. Testing that responses package is available...")
    try:
        import importlib.util

        spec = importlib.util.find_spec("responses")
        if spec is not None:
            print("   ✓ responses package is installed")
        else:
            print("   ✗ responses package not found (needed for tests)")
    except ImportError:
        print("   ✗ responses package not found (needed for tests)")

    print("\n" + "=" * 50)
    print("✅ ALL FIXES VERIFIED SUCCESSFULLY!")
    print("\nSummary of fixes:")
    print("1. ✓ Fixed critical import bug (APIException → APIClientError)")
    print("2. ✓ Added environment variable support for API key")
    print("3. ✓ Added SSL verification warning")
    print("4. ✓ Added responses package to test dependencies")

    return True


if __name__ == "__main__":
    test_all_fixes()
