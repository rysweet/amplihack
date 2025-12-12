"""Example usage of the API Client module.

This example demonstrates:
- Basic GET requests
- POST with JSON body
- Bearer token authentication
- API key authentication
- Error handling
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api_client import APIClient, APIError, AuthType


def example_basic_get():
    """Example: Basic GET request to public API."""
    print("=== Basic GET Request ===")

    # Using postman-echo.com for testing (more reliable than httpbin.org)
    client = APIClient(base_url="https://postman-echo.com")

    try:
        result = client.get("/get", params={"name": "test", "value": "123"})
        print(f"Response args: {result.get('args')}")
    except APIError as e:
        print(f"Error: {e.status_code} - {e.message}")


def example_post_json():
    """Example: POST request with JSON body."""
    print("\n=== POST with JSON ===")

    client = APIClient(base_url="https://postman-echo.com")

    try:
        result = client.post("/post", data={"name": "Alice", "age": 30})
        print(f"Sent JSON: {result.get('data')}")
    except APIError as e:
        print(f"Error: {e.status_code} - {e.message}")


def example_bearer_auth():
    """Example: Bearer token authentication."""
    print("\n=== Bearer Token Auth ===")

    client = APIClient(
        base_url="https://postman-echo.com", auth_type=AuthType.BEARER, auth_token="my-secret-token"
    )

    try:
        result = client.get("/headers")
        auth_header = result.get("headers", {}).get("authorization")
        print(f"Authorization header: {auth_header}")
    except APIError as e:
        print(f"Error: {e.status_code} - {e.message}")


def example_api_key_auth():
    """Example: API key authentication."""
    print("\n=== API Key Auth ===")

    client = APIClient(
        base_url="https://postman-echo.com",
        auth_type=AuthType.API_KEY,
        auth_token="my-api-key",
        api_key_header="X-API-Key",  # pragma: allowlist secret
    )

    try:
        result = client.get("/headers")
        api_key = result.get("headers", {}).get("x-api-key")
        print(f"X-API-Key header: {api_key}")
    except APIError as e:
        print(f"Error: {e.status_code} - {e.message}")


def example_error_handling():
    """Example: Error handling for 4xx responses."""
    print("\n=== Error Handling ===")

    client = APIClient(base_url="https://postman-echo.com")

    try:
        # This will return a 404
        result = client.get("/status/404")
        print(f"Result: {result}")
    except APIError as e:
        print(f"Caught error: HTTP {e.status_code}")
        print(f"Message: {e.message}")


def main():
    """Run all examples."""
    print("API Client Usage Examples")
    print("=" * 50)

    example_basic_get()
    example_post_json()
    example_bearer_auth()
    example_api_key_auth()
    example_error_handling()

    print("\n" + "=" * 50)
    print("Examples complete!")


if __name__ == "__main__":
    main()
