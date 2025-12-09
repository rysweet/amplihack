"""Demo usage of simple-api-client.

Run with: python -m simple_api_client
"""

from simple_api_client import APIError, get, post


def main():
    """Demonstrate the simple-api-client module."""
    print("Simple API Client Demo")
    print("=" * 50)

    # Demo GET request
    print("\n1. GET request - Fetching a post:")
    try:
        post_data = get("https://jsonplaceholder.typicode.com/posts/1")
        print(f"   Title: {post_data['title'][:50]}...")
        print(f"   User ID: {post_data['userId']}")
    except APIError as e:
        print(f"   Error: {e.message}")

    # Demo GET list
    print("\n2. GET request - Fetching multiple posts:")
    try:
        posts = get("https://jsonplaceholder.typicode.com/posts?_limit=3")
        print(f"   Fetched {len(posts)} posts")
        for p in posts:
            print(f"   - Post {p['id']}: {p['title'][:40]}...")
    except APIError as e:
        print(f"   Error: {e.message}")

    # Demo POST request
    print("\n3. POST request - Creating a new post:")
    try:
        new_post = {
            "title": "My Test Post",
            "body": "This is a test post created by simple-api-client",
            "userId": 1,
        }
        result = post("https://jsonplaceholder.typicode.com/posts", new_post)
        print(f"   Created post with ID: {result['id']}")
        print(f"   Title: {result['title']}")
    except APIError as e:
        print(f"   Error: {e.message}")

    # Demo error handling
    print("\n4. Error handling - Requesting non-existent resource:")
    try:
        get("https://jsonplaceholder.typicode.com/posts/99999")
        print("   Unexpected success!")
    except APIError as e:
        print(f"   Caught APIError: {e.message}")
        print(f"   Status code: {e.status_code}")

    print("\n" + "=" * 50)
    print("Demo complete!")


if __name__ == "__main__":
    main()
