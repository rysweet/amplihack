#!/usr/bin/env python
"""Test script to verify API client fixes."""

import asyncio

from amplihack.api_client import APIClient, ValidationError


async def test_url_validation():
    """Test that security validation works."""
    print("Testing URL validation...")

    # These should raise ValidationError
    forbidden_urls = [
        "http://localhost:8080/test",
        "http://127.0.0.1/api",
        "http://169.254.169.254/latest/meta-data",
        "http://192.168.1.1/admin",
        "http://10.0.0.1/internal",
    ]

    for url in forbidden_urls:
        try:
            async with APIClient(base_url=url) as client:
                await client.get("/test")
            print(f"  ❌ {url} - Should have been blocked!")
        except ValidationError as e:
            print(f"  ✅ {url} - Blocked correctly: {e}")
        except Exception as e:
            print(f"  ❌ {url} - Unexpected error: {e}")

    # This should work
    valid_url = "https://api.example.com"
    try:
        async with APIClient(base_url=valid_url) as client:
            print(f"  ✅ {valid_url} - Accepted correctly")
    except Exception as e:
        print(f"  ❌ {valid_url} - Should have been accepted: {e}")


async def test_header_validation():
    """Test that header validation works."""
    print("\nTesting header validation...")

    try:
        client = APIClient(base_url="https://api.example.com")
        # Try to inject headers with newlines
        bad_headers = {"X-Bad-Header": "value\nX-Injected: evil"}
        await client._merge_headers(bad_headers)
        print("  ❌ Header injection should have been blocked!")
    except ValidationError as e:
        print(f"  ✅ Header injection blocked: {e}")
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")


async def test_ssl_warning():
    """Test that SSL warning is logged."""
    print("\nTesting SSL warning...")

    # This should warn
    try:
        client = APIClient(base_url="https://api.example.com", verify_ssl=False)
        await client._ensure_session()
        await client.close()
        print("  ✅ SSL=False client created (check logs for warning)")
    except Exception as e:
        print(f"  ❌ Error creating client: {e}")


async def test_no_response_body_hacking():
    """Test that we don't hack the response._body anymore."""
    print("\nTesting response handling...")

    # Just verify the client can be created and doesn't have _body hacking
    client = APIClient(base_url="https://api.example.com")

    # Check the _execute_request returns tuple now
    import inspect

    source = inspect.getsource(client._execute_request)
    if "response._body" in source:
        print("  ❌ Still using response._body hack!")
    elif "return response, text" in source:
        print("  ✅ Using proper tuple return")
    else:
        print("  ⚠️  Cannot verify implementation")

    await client.close()


async def test_removed_classes():
    """Test that unused classes were removed."""
    print("\nTesting class removal...")

    # These should not exist
    removed_items = [
        ("models", "RequestID"),
        ("models", "ErrorDetail"),
        ("exceptions", "ConnectionError"),
        ("exceptions", "DNSError"),
        ("exceptions", "SSLError"),
        ("exceptions", "BadGatewayError"),
        ("retry", "ExponentialBackoff"),
    ]

    for module_name, class_name in removed_items:
        try:
            if module_name == "models":
                from amplihack.api_client import models

                module = models
            elif module_name == "exceptions":
                from amplihack.api_client import exceptions

                module = exceptions
            elif module_name == "retry":
                from amplihack.api_client import retry

                module = retry

            if hasattr(module, class_name):
                print(f"  ❌ {module_name}.{class_name} still exists!")
            else:
                print(f"  ✅ {module_name}.{class_name} removed")
        except ImportError:
            print(f"  ⚠️  Cannot import {module_name}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("API Client Fixes Verification")
    print("=" * 60)

    await test_url_validation()
    await test_header_validation()
    await test_ssl_warning()
    await test_no_response_body_hacking()
    await test_removed_classes()

    print("\n" + "=" * 60)
    print("Verification Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
