#!/usr/bin/env python3
"""Complete CRUD operations example using REST API Client.

This example demonstrates:
- Creating resources (POST)
- Reading resources (GET)
- Updating resources (PUT/PATCH)
- Deleting resources (DELETE)
- Working with collections
- Handling responses
"""

import json
from typing import Any

from rest_api_client import APIClient


def pretty_print(label: str, data: Any) -> None:
    """Pretty print JSON data with a label."""
    print(f"\n{label}:")
    print("-" * 40)
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2))
    else:
        print(data)


class UserManager:
    """Manage users via REST API."""

    def __init__(self, base_url: str):
        self.client = APIClient(base_url=base_url)

    def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new user."""
        response = self.client.post("/users", json=user_data)
        response.raise_for_status()
        return response.data

    def get_user(self, user_id: int) -> dict[str, Any]:
        """Retrieve a single user by ID."""
        response = self.client.get(f"/users/{user_id}")
        response.raise_for_status()
        return response.data

    def list_users(self, page: int = 1, limit: int = 10) -> list[dict[str, Any]]:
        """List users with pagination."""
        response = self.client.get("/users", params={"page": page, "limit": limit})
        response.raise_for_status()
        return response.data

    def update_user(self, user_id: int, user_data: dict[str, Any]) -> dict[str, Any]:
        """Update a user (full update)."""
        response = self.client.put(f"/users/{user_id}", json=user_data)
        response.raise_for_status()
        return response.data

    def patch_user(self, user_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        """Partially update a user."""
        response = self.client.patch(f"/users/{user_id}", json=updates)
        response.raise_for_status()
        return response.data

    def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        response = self.client.delete(f"/users/{user_id}")
        response.raise_for_status()
        return response.status_code == 204

    def search_users(self, query: str, filters: dict[str, Any] = None) -> list[dict[str, Any]]:
        """Search users with query and filters."""
        params = {"q": query}
        if filters:
            params.update(filters)
        response = self.client.get("/users/search", params=params)
        response.raise_for_status()
        return response.data

    def bulk_create_users(self, users: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create multiple users in a single request."""
        response = self.client.post("/users/bulk", json={"users": users})
        response.raise_for_status()
        return response.data

    def get_user_stats(self) -> dict[str, Any]:
        """Get user statistics."""
        response = self.client.get("/users/stats")
        response.raise_for_status()
        return response.data


def main():
    """Demonstrate CRUD operations."""
    # Use JSONPlaceholder as a free test API
    manager = UserManager("https://jsonplaceholder.typicode.com")

    # 1. CREATE - Add a new user
    new_user = {
        "name": "Jane Smith",
        "username": "jsmith",
        "email": "jane.smith@example.com",
        "address": {
            "street": "123 Main St",
            "suite": "Apt 4B",
            "city": "New York",
            "zipcode": "10001",
        },
        "phone": "555-1234",
        "website": "janesmith.com",
        "company": {
            "name": "Tech Corp",
            "catchPhrase": "Innovation first",
            "bs": "synergize scalable solutions",
        },
    }

    created_user = manager.create_user(new_user)
    pretty_print("Created User", created_user)
    user_id = created_user.get("id", 1)

    # 2. READ - Get the created user
    retrieved_user = manager.get_user(user_id)
    pretty_print("Retrieved User", retrieved_user)

    # 3. READ - List all users
    users = manager.list_users(page=1, limit=5)
    pretty_print("User List (First 5)", users)

    # 4. UPDATE - Full update
    updated_user = {**new_user, "name": "Jane Doe", "email": "jane.doe@example.com"}
    result = manager.update_user(user_id, updated_user)
    pretty_print("Updated User (PUT)", result)

    # 5. UPDATE - Partial update
    patches = {"phone": "555-9999", "website": "janedoe.io"}
    result = manager.patch_user(user_id, patches)
    pretty_print("Patched User (PATCH)", result)

    # 6. Advanced Operations

    # Search users (if API supports it)
    try:
        search_results = manager.search_users("Jane", filters={"city": "New York"})
        pretty_print("Search Results", search_results)
    except Exception as e:
        print(f"Search not supported: {e}")

    # Bulk operations (if API supports it)
    bulk_users = [
        {"name": "User 1", "email": "user1@example.com"},
        {"name": "User 2", "email": "user2@example.com"},
        {"name": "User 3", "email": "user3@example.com"},
    ]
    try:
        bulk_results = manager.bulk_create_users(bulk_users)
        pretty_print("Bulk Created Users", bulk_results)
    except Exception as e:
        print(f"Bulk create not supported: {e}")

    # Get statistics (if API supports it)
    try:
        stats = manager.get_user_stats()
        pretty_print("User Statistics", stats)
    except Exception as e:
        print(f"Stats not supported: {e}")

    # 7. DELETE - Remove the user
    deleted = manager.delete_user(user_id)
    print(f"\nUser deleted successfully: {deleted}")

    # 8. Working with nested resources
    print("\n" + "=" * 50)
    print("Working with Nested Resources")
    print("=" * 50)

    # Example: User's posts
    posts_client = APIClient(base_url="https://jsonplaceholder.typicode.com")

    # Get all posts for a user
    response = posts_client.get(f"/users/{user_id}/posts")
    user_posts = response.data
    pretty_print(f"Posts for User {user_id}", user_posts[:2] if user_posts else [])

    # Create a post for a user
    new_post = {
        "userId": user_id,
        "title": "My First Post",
        "body": "This is the content of my first post.",
    }
    response = posts_client.post("/posts", json=new_post)
    created_post = response.data
    pretty_print("Created Post", created_post)

    # 9. Batch operations with error handling
    print("\n" + "=" * 50)
    print("Batch Operations with Error Handling")
    print("=" * 50)

    def process_users_batch(users_data: list[dict[str, Any]]) -> dict[str, list]:
        """Process a batch of users, handling errors gracefully."""
        results = {"successful": [], "failed": []}

        for user_data in users_data:
            try:
                created = manager.create_user(user_data)
                results["successful"].append(created)
                print(f"✓ Created user: {user_data.get('name')}")
            except Exception as e:
                results["failed"].append({"user": user_data, "error": str(e)})
                print(f"✗ Failed to create user {user_data.get('name')}: {e}")

        return results

    batch_data = [
        {"name": "Alice", "email": "alice@example.com", "username": "alice"},
        {"name": "Bob", "email": "bob@example.com", "username": "bob"},
        {"name": "Charlie", "email": "charlie@example.com", "username": "charlie"},
    ]

    batch_results = process_users_batch(batch_data)
    print("\nBatch Results:")
    print(f"  Successful: {len(batch_results['successful'])}")
    print(f"  Failed: {len(batch_results['failed'])}")


if __name__ == "__main__":
    main()
