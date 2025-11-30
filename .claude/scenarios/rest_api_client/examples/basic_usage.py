#!/usr/bin/env python3
"""Basic usage example for REST API Client.

This example demonstrates the core functionality of the REST API client.
"""

import os
import sys

# Add scenarios directory to path for proper package imports
scenarios_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if scenarios_dir not in sys.path:
    sys.path.insert(0, scenarios_dir)

from rest_api_client import APIClient, APIConfig


def main():
    """Run basic usage examples."""
    print("REST API Client - Basic Usage Example\n")
    print("=" * 50)

    # Example 1: Simple client creation
    print("\n1. Creating a simple client:")
    client = APIClient(base_url="https://jsonplaceholder.typicode.com")
    print(f"   Client created with base URL: {client.base_url}")

    # Example 2: Making a GET request
    print("\n2. Making a GET request:")
    try:
        response = client.get("/posts/1")
        print(f"   Status: {response.status_code}")
        print(f"   Success: {response.is_success}")
        if response.json:
            print(f"   Title: {response.json.get('title', 'N/A')}")
    except Exception as e:
        print(f"   Error: {e}")

    # Example 3: Client with configuration
    print("\n3. Creating client with configuration:")
    config = APIConfig(
        base_url="https://jsonplaceholder.typicode.com",
        timeout=60,
        max_retries=5,
        headers={"User-Agent": "REST-API-Client/1.0"},
    )
    configured_client = APIClient(config=config)
    print(f"   Timeout: {configured_client.timeout}s")
    print(f"   Max retries: {configured_client.max_retries}")

    # Example 4: Using context manager
    print("\n4. Using client as context manager:")
    with APIClient(base_url="https://jsonplaceholder.typicode.com") as api:
        response = api.get("/users")
        print(f"   Retrieved {len(response.json) if response.json else 0} users")

    # Example 5: Error handling
    print("\n5. Error handling example:")
    try:
        response = client.get("/posts/999999")  # Non-existent post
        print(f"   Found post: {response.json}")
    except Exception as e:
        print(f"   Handled error: {type(e).__name__}")

    print("\n" + "=" * 50)
    print("Examples completed successfully!")


if __name__ == "__main__":
    main()
