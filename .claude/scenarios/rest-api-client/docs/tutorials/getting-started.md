# Getting Started with REST API Client

Learn how to use the REST API Client library in 10 minutes.

## What You'll Learn

By the end of this tutorial, you'll know how to:

- Initialize the API client
- Make basic HTTP requests (GET, POST, PUT, DELETE)
- Handle responses and errors
- Configure basic options

## Prerequisites

- Python 3.8 or higher
- Basic understanding of REST APIs
- Access to a test API (we'll use JSONPlaceholder)

## Step 1: Import and Initialize

First, import the APIClient and create an instance:

```python
from rest_api_client import APIClient

# Create a client for JSONPlaceholder (free test API)
client = APIClient(base_url="https://jsonplaceholder.typicode.com")
print("Client initialized!")
# Output: Client initialized!
```

The client is now ready to make requests to the JSONPlaceholder API.

## Step 2: Make Your First GET Request

Let's fetch a single post:

```python
# Get post with ID 1
response = client.get("/posts/1")

# Check the response
print(f"Status Code: {response.status_code}")
print(f"Title: {response.data['title']}")
print(f"Body: {response.data['body'][:50]}...")

# Output:
# Status Code: 200
# Title: sunt aut facere repellat provident occaecati excepturi optio reprehenderit
# Body: quia et suscipit\nsuscipit recusandae consequuntur...
```

## Step 3: Fetch Multiple Items

Get a list of posts with query parameters:

```python
# Get first 5 posts by user 1
response = client.get("/posts", params={"userId": 1, "_limit": 5})

print(f"Found {len(response.data)} posts")
for post in response.data:
    print(f"- Post {post['id']}: {post['title'][:30]}...")

# Output:
# Found 5 posts
# - Post 1: sunt aut facere repellat prov...
# - Post 2: qui est esse...
# - Post 3: ea molestias quasi exercitati...
# - Post 4: eum et est occaecati...
# - Post 5: nesciunt quas odio...
```

## Step 4: Create Data with POST

Create a new post:

```python
# Prepare new post data
new_post = {
    "title": "My Amazing Post",
    "body": "This is the content of my post. It's very informative!",
    "userId": 1
}

# Send POST request
response = client.post("/posts", json=new_post)

# Check the created post
print(f"Created post with ID: {response.data['id']}")
print(f"Title: {response.data['title']}")

# Output:
# Created post with ID: 101
# Title: My Amazing Post
```

## Step 5: Update Data with PUT

Update an existing post completely:

```python
# Complete replacement of post 1
updated_post = {
    "id": 1,
    "title": "Updated Title",
    "body": "Completely new content",
    "userId": 1
}

response = client.put("/posts/1", json=updated_post)

print(f"Updated post {response.data['id']}")
print(f"New title: {response.data['title']}")

# Output:
# Updated post 1
# New title: Updated Title
```

## Step 6: Partial Update with PATCH

Update only specific fields:

```python
# Update only the title
partial_update = {
    "title": "Partially Updated Title"
}

response = client.patch("/posts/1", json=partial_update)

print(f"Patched post {response.data['id']}")
print(f"Updated title: {response.data['title']}")

# Output:
# Patched post 1
# Updated title: Partially Updated Title
```

## Step 7: Delete Data

Remove a post:

```python
# Delete post 1
response = client.delete("/posts/1")

print(f"Delete status: {response.status_code}")
if response.status_code == 200:
    print("Post deleted successfully!")

# Output:
# Delete status: 200
# Post deleted successfully!
```

## Step 8: Handle Errors Gracefully

Learn to handle common errors:

```python
from rest_api_client import APIException

try:
    # Try to get a non-existent post
    response = client.get("/posts/99999")
    response.raise_for_status()
except APIException as e:
    print(f"Error occurred: {e.message}")
    print(f"Status code: {e.status_code}")

# Try with a completely invalid endpoint
try:
    response = client.get("/this-does-not-exist")
    response.raise_for_status()
except APIException as e:
    print(f"Invalid endpoint: {e.message}")

# Output:
# Error occurred: Not Found
# Status code: 404
# Invalid endpoint: Not Found
```

## Step 9: Work with Headers

Add custom headers for authentication or other purposes:

```python
# Create client with authentication header
auth_client = APIClient(
    base_url="https://jsonplaceholder.typicode.com",
    headers={
        "Authorization": "Bearer my-token-123",
        "X-Custom-Header": "CustomValue"
    }
)

# Make authenticated request
response = auth_client.get("/posts/1")
print(f"Authenticated request status: {response.status_code}")

# Output:
# Authenticated request status: 200
```

## Step 10: Configure Timeouts

Set appropriate timeouts for your requests:

```python
# Create client with custom timeout
fast_client = APIClient(
    base_url="https://jsonplaceholder.typicode.com",
    timeout=5  # 5 seconds timeout
)

# This will timeout if the server is slow
try:
    response = fast_client.get("/posts")
    print(f"Got {len(response.data)} posts quickly!")
except TimeoutException as e:
    print(f"Request timed out: {e.message}")

# Output:
# Got 100 posts quickly!
```

## Complete Example

Here's everything together in a working script:

```python
from rest_api_client import APIClient, APIException

def main():
    # Initialize client
    client = APIClient(base_url="https://jsonplaceholder.typicode.com")

    # Get all posts by a user
    response = client.get("/posts", params={"userId": 2})
    print(f"User 2 has {len(response.data)} posts")

    # Create a new post
    new_post = {
        "title": "Tutorial Complete!",
        "body": "I learned how to use the REST API Client",
        "userId": 2
    }

    response = client.post("/posts", json=new_post)
    post_id = response.data['id']
    print(f"Created post {post_id}")

    # Update it
    response = client.patch(f"/posts/{post_id}", json={"title": "Tutorial Mastered!"})
    print(f"Updated title: {response.data['title']}")

    # Clean up
    response = client.delete(f"/posts/{post_id}")
    print(f"Cleanup complete: {response.status_code}")

if __name__ == "__main__":
    main()

# Output:
# User 2 has 10 posts
# Created post 101
# Updated title: Tutorial Mastered!
# Cleanup complete: 200
```

## Next Steps

Congratulations! You've learned the basics of the REST API Client. Next, explore:

- [Advanced Features Tutorial](./advanced-features.md) - Learn about retry logic and rate limiting
- [Configuration Guide](../howto/configure-client.md) - Customize client behavior
- [Error Handling Guide](../howto/error-handling.md) - Build robust applications
- [API Reference](../reference/api.md) - Complete API documentation
