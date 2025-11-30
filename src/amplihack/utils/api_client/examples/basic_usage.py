#!/usr/bin/env python3
"""
Basic Usage Examples for REST API Client

This example demonstrates all key features of the REST API Client:
- GET/POST/PUT/DELETE requests
- Custom retry configuration
- Rate limiting configuration
- Error handling with custom exceptions
- Authentication setup
- Logging configuration

Run this example:
    python examples/basic_usage.py
"""

import logging
import os

from amplihack.utils.api_client import (
    APIClient,
    APIRequest,
    HTTPError,
    RateLimitConfig,
    RetryConfig,
)


def setup_logging():
    """Configure logging to see API client activity"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def example_basic_requests():
    """Demonstrate basic GET/POST/PUT/DELETE requests"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Basic HTTP Requests")
    print("=" * 60)

    # Create a client with default configuration
    client = APIClient(base_url="https://jsonplaceholder.typicode.com")

    # GET request
    print("\n1. GET Request:")
    response = client.get("/users/1")
    print(f"   Status: {response.status_code}")
    print(f"   User: {response.data.get('name')}")
    print(f"   Email: {response.data.get('email')}")

    # GET with query parameters
    print("\n2. GET with Query Parameters:")
    response = client.get("/posts", params={"userId": 1})
    print(f"   Status: {response.status_code}")
    print(f"   Posts found: {len(response.data)}")

    # POST request
    print("\n3. POST Request:")
    new_post = {
        "title": "Test Post",
        "body": "This is a test post created by the API client",
        "userId": 1,
    }
    response = client.post("/posts", json=new_post)
    print(f"   Status: {response.status_code}")
    print(f"   Created post ID: {response.data.get('id')}")

    # PUT request
    print("\n4. PUT Request:")
    updated_post = {
        "id": 1,
        "title": "Updated Post Title",
        "body": "Updated post body",
        "userId": 1,
    }
    response = client.put("/posts/1", json=updated_post)
    print(f"   Status: {response.status_code}")
    print(f"   Updated title: {response.data.get('title')}")

    # DELETE request
    print("\n5. DELETE Request:")
    response = client.delete("/posts/1")
    print(f"   Status: {response.status_code}")
    print("   Post deleted successfully")


def example_custom_retry_config():
    """Demonstrate custom retry configuration"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Custom Retry Configuration")
    print("=" * 60)

    # Create custom retry configuration
    retry_config = RetryConfig(
        max_retries=5,  # Retry up to 5 times
        base_delay=2.0,  # Start with 2-second delay
        max_delay=120.0,  # Cap delay at 2 minutes
        exponential_base=2.0,  # Double delay each time
    )
    # Delays will be: 2s, 4s, 8s, 16s, 32s

    client = APIClient(base_url="https://jsonplaceholder.typicode.com", retry_config=retry_config)

    print("\nRetry Configuration:")
    print(f"   Max Retries: {retry_config.max_retries}")
    print(f"   Base Delay: {retry_config.base_delay}s")
    print(f"   Max Delay: {retry_config.max_delay}s")
    print(f"   Exponential Base: {retry_config.exponential_base}")
    print("   Retry Sequence: 2s, 4s, 8s, 16s, 32s")

    # Make a request (will use retry config if failures occur)
    response = client.get("/users/1")
    print(f"\nRequest completed successfully: {response.status_code}")


def example_rate_limiting():
    """Demonstrate rate limiting configuration"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Rate Limiting Configuration")
    print("=" * 60)

    # Create custom rate limit configuration
    rate_limit_config = RateLimitConfig(
        max_wait_time=300.0,  # Wait up to 5 minutes
        respect_retry_after=True,  # Honor Retry-After header
        default_backoff=60.0,  # Default wait: 1 minute
    )

    client = APIClient(
        base_url="https://jsonplaceholder.typicode.com", rate_limit_config=rate_limit_config
    )

    print("\nRate Limit Configuration:")
    print(f"   Max Wait Time: {rate_limit_config.max_wait_time}s")
    print(f"   Respect Retry-After: {rate_limit_config.respect_retry_after}")
    print(f"   Default Backoff: {rate_limit_config.default_backoff}s")

    # Make a request (will handle rate limiting if it occurs)
    response = client.get("/users")
    print(f"\nRequest completed successfully: {response.status_code}")
    print(f"Users retrieved: {len(response.data)}")


def example_error_handling():
    """Demonstrate comprehensive error handling"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Error Handling")
    print("=" * 60)

    client = APIClient(base_url="https://jsonplaceholder.typicode.com")

    # 1. Handle 404 Not Found
    print("\n1. Handling 404 Not Found:")
    try:
        response = client.get("/users/999999")  # Non-existent user
    except HTTPError as e:
        print("   ✓ Caught HTTPError")
        print(f"   Status Code: {e.status_code}")
        print(f"   Message: {e.message}")

    # 2. Handle invalid endpoint
    print("\n2. Handling Invalid Endpoint:")
    try:
        response = client.get("/invalid/endpoint/that/does/not/exist")
    except HTTPError as e:
        print("   ✓ Caught HTTPError")
        print(f"   Status Code: {e.status_code}")

    # 3. Demonstrate rate limit error (simulated)
    print("\n3. Rate Limit Error Handling (conceptual):")
    print("   When API returns 429:")
    print("   - RateLimitError is raised if wait time > max_wait_time")
    print("   - Otherwise, client automatically waits and retries")
    print("   - wait_time and retry_after are available in exception")

    # 4. Demonstrate retry exhausted (simulated)
    print("\n4. Retry Exhausted Error (conceptual):")
    print("   When all retries fail:")
    print("   - RetryExhaustedError is raised")
    print("   - Contains number of attempts")
    print("   - Contains last error encountered")


def example_authentication():
    """Demonstrate authentication setup"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Authentication")
    print("=" * 60)

    # 1. API Key in Header
    print("\n1. API Key Authentication:")
    client_api_key = APIClient(
        base_url="https://api.example.com", default_headers={"X-API-Key": "your-api-key-here"}
    )
    print("   ✓ Client configured with API key in header")

    # 2. Bearer Token
    print("\n2. Bearer Token Authentication:")
    client_bearer = APIClient(
        base_url="https://api.example.com",
        default_headers={"Authorization": "Bearer your-token-here"},
    )
    print("   ✓ Client configured with Bearer token")

    # 3. From Environment Variable
    print("\n3. Environment Variable Authentication:")
    api_key = os.getenv("API_KEY", "default-key-for-demo")
    client_env = APIClient(
        base_url="https://api.example.com", default_headers={"X-API-Key": api_key}
    )
    print("   ✓ Client configured with API key from environment")
    print(
        f"   (Using: {'actual environment variable' if 'API_KEY' in os.environ else 'default demo key'})"
    )


def example_structured_requests():
    """Demonstrate using APIRequest dataclass"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Structured Requests with APIRequest")
    print("=" * 60)

    client = APIClient(base_url="https://jsonplaceholder.typicode.com")

    # Create a structured request
    request = APIRequest(
        method="POST",
        url="/posts",
        headers={"Content-Type": "application/json"},
        params={"notify": "true"},
        json={
            "title": "Structured Request Example",
            "body": "This request was created using APIRequest dataclass",
            "userId": 1,
        },
    )

    print("\nAPIRequest Details:")
    print(f"   Method: {request.method}")
    print(f"   URL: {request.url}")
    print(f"   Headers: {request.headers}")
    print(f"   Params: {request.params}")
    print(f"   JSON Body: {request.json}")

    # Execute the structured request
    response = client.execute(request)
    print("\nResponse:")
    print(f"   Status: {response.status_code}")
    print(f"   Created ID: {response.data.get('id')}")
    print(f"   Elapsed Time: {response.elapsed_time:.3f}s")


def example_advanced_configuration():
    """Demonstrate advanced client configuration"""
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Advanced Configuration")
    print("=" * 60)

    # Create a fully configured client
    client = APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        timeout=60.0,  # 60-second timeout
        verify_ssl=True,  # Verify SSL certificates (default)
        default_headers={"User-Agent": "MyApp/1.0", "Accept": "application/json"},
        retry_config=RetryConfig(
            max_retries=3, base_delay=1.0, max_delay=30.0, exponential_base=2.0
        ),
        rate_limit_config=RateLimitConfig(
            max_wait_time=180.0, respect_retry_after=True, default_backoff=30.0
        ),
    )

    print("\nClient Configuration:")
    print("   Base URL: https://jsonplaceholder.typicode.com")
    print("   Timeout: 60.0s")
    print("   SSL Verification: Enabled")
    print("   Default Headers: User-Agent, Accept")
    print("   Retry: Max 3 attempts with exponential backoff")
    print("   Rate Limit: Max wait 180s, respect Retry-After")

    # Make a request with the fully configured client
    response = client.get("/users/1")
    print(f"\nRequest completed successfully: {response.status_code}")


def example_response_details():
    """Demonstrate accessing response details"""
    print("\n" + "=" * 60)
    print("EXAMPLE 8: Response Details")
    print("=" * 60)

    client = APIClient(base_url="https://jsonplaceholder.typicode.com")
    response = client.get("/users/1")

    print("\nAPIResponse Details:")
    print(f"   Status Code: {response.status_code}")
    print(f"   Elapsed Time: {response.elapsed_time:.3f}s")
    print(f"   Content-Type: {response.headers.get('content-type')}")

    print("\n   Data (parsed JSON):")
    for key, value in response.data.items():
        if isinstance(value, dict):
            print(f"      {key}: {type(value).__name__} with {len(value)} fields")
        else:
            print(f"      {key}: {value}")

    print("\n   Raw Text (first 100 chars):")
    print(f"      {response.text[:100]}...")


def main():
    """Run all examples"""
    setup_logging()

    print("\n" + "=" * 60)
    print("REST API CLIENT - COMPREHENSIVE USAGE EXAMPLES")
    print("=" * 60)

    try:
        example_basic_requests()
        example_custom_retry_config()
        example_rate_limiting()
        example_error_handling()
        example_authentication()
        example_structured_requests()
        example_advanced_configuration()
        example_response_details()

        print("\n" + "=" * 60)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        raise


if __name__ == "__main__":
    main()
