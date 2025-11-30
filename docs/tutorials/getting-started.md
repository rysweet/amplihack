# Tutorial: Your First API Client

Learn how to use the REST API Client library by building a simple application that interacts with a JSON placeholder API.

## What You'll Learn

By the end of this tutorial, you'll be able to:

- Create and configure an API client
- Make GET and POST requests
- Handle errors gracefully
- Implement retry logic
- Use rate limiting

## Prerequisites

- Python 3.8 or higher
- Basic understanding of HTTP and APIs
- pip package manager

## Step 1: Installation

First, install the REST API Client library:

```bash
pip install rest-api-client
```

## Step 2: Create Your First Client

Let's start by creating a simple client to interact with the JSONPlaceholder API:

```python
from rest_api_client import APIClient

# Create a client instance
client = APIClient(base_url="https://jsonplaceholder.typicode.com")

# Test the connection
response = client.get("/users/1")
print(f"User name: {response.data['name']}")
# Output: User name: Leanne Graham
```

## Step 3: Fetching Data

Now let's fetch a list of posts and filter them:

```python
# Get all posts
all_posts = client.get("/posts")
print(f"Total posts: {len(all_posts.data)}")
# Output: Total posts: 100

# Get posts by a specific user
user_posts = client.get("/posts", params={"userId": 1})
print(f"Posts by user 1: {len(user_posts.data)}")
# Output: Posts by user 1: 10

# Get a specific post
post = client.get("/posts/1")
print(f"Post title: {post.data['title']}")
# Output: Post title: sunt aut facere repellat provident occaecati excepturi optio reprehenderit
```

## Step 4: Creating Data

Let's create a new post:

```python
# Prepare post data
new_post = {
    "title": "My First Post",
    "body": "This is the content of my first post using the REST API Client.",
    "userId": 1
}

# Create the post
response = client.post("/posts", json=new_post)
print(f"Created post ID: {response.data['id']}")
# Output: Created post ID: 101

# Verify the created post
print(f"Title: {response.data['title']}")
print(f"Body: {response.data['body']}")
```

## Step 5: Updating and Deleting

Update an existing post:

```python
# Update a post
updated_data = {
    "id": 1,
    "title": "Updated Title",
    "body": "Updated content",
    "userId": 1
}

response = client.put("/posts/1", json=updated_data)
print(f"Updated: {response.data['title']}")
# Output: Updated: Updated Title

# Partial update using PATCH
partial_update = {"title": "Partially Updated"}
response = client.patch("/posts/1", json=partial_update)
print(f"Patched: {response.data['title']}")
# Output: Patched: Partially Updated

# Delete a post
client.delete("/posts/1")
print("Post deleted successfully")
# Output: Post deleted successfully
```

## Step 6: Error Handling

Let's add proper error handling:

```python
from rest_api_client.exceptions import APIError, NetworkError, ValidationError

def safe_get_user(user_id):
    """Safely fetch a user with error handling."""
    try:
        response = client.get(f"/users/{user_id}")
        return response.data
    except ValidationError as e:
        print(f"Invalid request: {e.message}")
        return None
    except NetworkError as e:
        print(f"Network error: {e.message}")
        return None
    except APIError as e:
        if e.status_code == 404:
            print(f"User {user_id} not found")
        else:
            print(f"API error: {e.status_code} - {e.message}")
        return None

# Test with valid and invalid IDs
user = safe_get_user(1)
if user:
    print(f"Found: {user['name']}")
# Output: Found: Leanne Graham

user = safe_get_user(999)
# Output: User 999 not found
```

## Step 7: Configuration

Configure the client for production use:

```python
from rest_api_client import APIClient
from rest_api_client.config import APIConfig, RetryConfig

# Configure retry behavior
retry_config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    exponential_base=2.0,
    retry_on_statuses=[429, 500, 502, 503, 504]
)

# Configure the API client
config = APIConfig(
    base_url="https://jsonplaceholder.typicode.com",
    timeout=30,
    max_retries=3,
    headers={"User-Agent": "MyApp/1.0"}
)

# Create configured client
client = APIClient(config=config, retry_config=retry_config)

# The client will now automatically retry on failures
response = client.get("/posts/1")
print(f"Fetched with retries: {response.data['title']}")
```

## Step 8: Rate Limiting

Implement rate limiting to be a good API citizen:

```python
# Create a rate-limited client
client = APIClient(
    base_url="https://jsonplaceholder.typicode.com",
    rate_limit_calls=10,  # 10 calls
    rate_limit_period=60   # per minute
)

# Make multiple requests
import time

print("Making rate-limited requests...")
for i in range(1, 21):
    start = time.time()
    response = client.get(f"/posts/{i}")
    elapsed = time.time() - start

    print(f"Request {i}: {response.data['id']} (took {elapsed:.2f}s)")

    # After 10 requests, the client will automatically pause
    if i == 10:
        print("Rate limit reached - client will pause...")
```

## Complete Example

Here's a complete example that puts it all together:

```python
from rest_api_client import APIClient
from rest_api_client.config import APIConfig, RetryConfig
from rest_api_client.exceptions import APIError, RateLimitError
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)

class BlogClient:
    """A simple blog API client."""

    def __init__(self):
        # Configure the client
        config = APIConfig(
            base_url="https://jsonplaceholder.typicode.com",
            timeout=30,
            rate_limit_calls=100,
            rate_limit_period=60
        )

        retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=1.0
        )

        self.client = APIClient(config=config, retry_config=retry_config)

    def get_user_posts(self, user_id):
        """Get all posts by a specific user."""
        try:
            response = self.client.get("/posts", params={"userId": user_id})
            return response.data
        except APIError as e:
            logging.error(f"Failed to get posts: {e}")
            return []

    def create_post(self, title, body, user_id=1):
        """Create a new blog post."""
        try:
            post_data = {
                "title": title,
                "body": body,
                "userId": user_id
            }
            response = self.client.post("/posts", json=post_data)
            return response.data
        except RateLimitError as e:
            logging.warning(f"Rate limited. Retry after {e.retry_after} seconds")
            return None
        except APIError as e:
            logging.error(f"Failed to create post: {e}")
            return None

# Use the blog client
blog = BlogClient()

# Get posts
posts = blog.get_user_posts(1)
print(f"User 1 has {len(posts)} posts")

# Create a post
new_post = blog.create_post(
    title="Learning REST API Client",
    body="This library makes API interactions so much easier!"
)

if new_post:
    print(f"Created post with ID: {new_post['id']}")
```

## Next Steps

Congratulations! You've learned the basics of using the REST API Client library. Here's what to explore next:

1. **Async Support**: Learn about [async clients](../howto/async-requests.md) for concurrent requests
2. **Advanced Configuration**: Deep dive into [configuration options](../reference/configuration.md)
3. **Custom Clients**: Build [specialized clients](../howto/custom-clients.md) for specific APIs
4. **Testing**: Learn to [test your API integrations](../howto/testing.md)

## Summary

In this tutorial, you learned how to:

- ✅ Install and configure the REST API Client
- ✅ Make various HTTP requests (GET, POST, PUT, PATCH, DELETE)
- ✅ Handle errors gracefully
- ✅ Configure retry logic and rate limiting
- ✅ Build a reusable client class

The REST API Client library provides a robust foundation for interacting with any REST API, handling the complexities of retries, rate limiting, and error handling so you can focus on your application logic.
