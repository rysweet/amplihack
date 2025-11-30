# API Client Quick Start Tutorial

Learn how to use the api_client module to integrate with REST APIs in 10 minutes.

## What You'll Learn

By the end of this tutorial, you'll be able to:

- Set up the API client
- Make your first API request
- Handle responses and errors
- Use authentication
- Implement a complete workflow

## Prerequisites

- Python 3.8 or higher
- Basic understanding of REST APIs
- The api_client module in your project

## Step 1: Import and Configure

First, import the necessary classes and create a client:

```python
from api_client import APIClient, ClientConfig

# Create configuration for a test API
config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")

# Initialize the client
client = APIClient(config)

print("Client configured and ready!")
```

Run this code. You should see:

```
Client configured and ready!
```

## Step 2: Make Your First Request

Let's fetch some data from the API:

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

# Fetch a user
response = client.get("/users/1")

# Convert response to JSON
user = response.json()

print(f"Name: {user['name']}")
print(f"Email: {user['email']}")
print(f"Company: {user['company']['name']}")
```

Output:

```
Name: Leanne Graham
Email: Sincere@april.biz
Company: Romaguera-Crona
```

## Step 3: Send Data with POST

Now let's create a new resource:

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

# Data for new post
new_post = {
    "title": "My First API Post",
    "body": "This is the content of my post created via the API client.",
    "userId": 1
}

# Create the post
response = client.post("/posts", json=new_post)

# Check the result
if response.status_code == 201:
    created = response.json()
    print(f"Success! Created post with ID: {created['id']}")
    print(f"Title: {created['title']}")
else:
    print(f"Failed with status: {response.status_code}")
```

Output:

```
Success! Created post with ID: 101
Title: My First API Post
```

## Step 4: Handle Errors Gracefully

APIs can fail. Let's handle errors properly:

```python
from api_client import APIClient, ClientConfig, HTTPError, APIError

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

def fetch_user_safely(user_id):
    """Fetch a user with proper error handling"""
    try:
        response = client.get(f"/users/{user_id}")
        return response.json()

    except HTTPError as e:
        if e.status_code == 404:
            print(f"User {user_id} not found")
        else:
            print(f"HTTP error {e.status_code}: {e.message}")
        return None

    except APIError as e:
        print(f"API error: {e}")
        return None

# Test with valid and invalid IDs
user = fetch_user_safely(1)
if user:
    print(f"Found: {user['name']}")

user = fetch_user_safely(999)  # Doesn't exist
```

Output:

```
Found: Leanne Graham
User 999 not found
```

## Step 5: Use Query Parameters

Many APIs accept query parameters for filtering:

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

# Fetch posts by a specific user
response = client.get("/posts", params={"userId": 1})
posts = response.json()

print(f"User 1 has {len(posts)} posts:")
for post in posts[:3]:  # Show first 3
    print(f"- {post['title']}")
```

Output:

```
User 1 has 10 posts:
- sunt aut facere repellat provident occaecati excepturi optio reprehenderit
- qui est esse
- ea molestias quasi exercitationem repellat qui ipsa sit aut
```

## Step 6: Add Authentication

For APIs that require authentication:

```python
from api_client import APIClient, ClientConfig

# Example with GitHub API (replace with your token)
config = ClientConfig(
    base_url="https://api.github.com",
    api_key="ghp_your_personal_access_token_here"
)
client = APIClient(config)

try:
    # This will work with a valid token
    response = client.get("/user")
    user = response.json()
    print(f"Authenticated as: {user['login']}")

except HTTPError as e:
    if e.status_code == 401:
        print("Invalid token. Please check your API key.")
```

## Step 7: Complete Workflow Example

Let's build a complete workflow that fetches data, processes it, and creates new resources:

```python
from api_client import APIClient, ClientConfig, HTTPError

def user_post_workflow():
    """Complete workflow: fetch user, get their posts, create summary"""

    config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
    client = APIClient(config)

    print("Starting workflow...")

    # Step 1: Fetch a user
    print("\n1. Fetching user...")
    user = client.get("/users/1").json()
    print(f"   User: {user['name']}")

    # Step 2: Get user's posts
    print("\n2. Fetching user's posts...")
    posts = client.get("/posts", params={"userId": user['id']}).json()
    print(f"   Found {len(posts)} posts")

    # Step 3: Get comments for first post
    print("\n3. Fetching comments for first post...")
    if posts:
        first_post = posts[0]
        comments = client.get(f"/posts/{first_post['id']}/comments").json()
        print(f"   Post '{first_post['title'][:30]}...' has {len(comments)} comments")

    # Step 4: Create a summary post
    print("\n4. Creating summary post...")
    summary = {
        "title": f"Summary for {user['name']}",
        "body": f"User has {len(posts)} posts with various comments",
        "userId": user['id']
    }

    try:
        response = client.post("/posts", json=summary)
        if response.status_code == 201:
            created = response.json()
            print(f"   Created summary post with ID: {created['id']}")
    except HTTPError as e:
        print(f"   Failed to create post: {e}")

    print("\nWorkflow complete!")

# Run the workflow
user_post_workflow()
```

Output:

```
Starting workflow...

1. Fetching user...
   User: Leanne Graham

2. Fetching user's posts...
   Found 10 posts

3. Fetching comments for first post...
   Post 'sunt aut facere repellat prov...' has 5 comments

4. Creating summary post...
   Created summary post with ID: 101

Workflow complete!
```

## Step 8: Configure for Your Needs

Customize the client for your specific requirements:

```python
from api_client import APIClient, ClientConfig

# Custom configuration
config = ClientConfig(
    base_url="https://api.example.com",
    timeout=60.0,        # Longer timeout for slow endpoints
    max_retries=5,       # More retries for unreliable network
    api_key="your_key"   # Authentication
)

client = APIClient(config)

# The client will now:
# - Wait up to 60 seconds for responses
# - Retry failed requests up to 5 times
# - Include your API key in all requests
# - Rate limit to 10 requests per second automatically
```

## What You've Learned

Congratulations! You now know how to:

✅ Configure the API client
✅ Make GET and POST requests
✅ Handle responses and convert to JSON
✅ Deal with errors gracefully
✅ Use query parameters
✅ Add authentication
✅ Build complete workflows

## Next Steps

Explore more advanced features:

1. **Concurrent Requests**: See [parallel requests example](../howto/api_client_examples.md#concurrent-requests)
2. **Pagination**: Learn about [handling paginated APIs](../howto/api_client_examples.md#pagination-patterns)
3. **Caching**: Implement [response caching](../howto/api_client_examples.md#caching-responses)
4. **Custom Retry Logic**: Build [advanced retry strategies](../howto/api_client_examples.md#retry-with-custom-logic)

## Quick Reference

```python
# Import
from api_client import APIClient, ClientConfig, HTTPError, APIError

# Configure
config = ClientConfig(base_url="https://api.example.com")
client = APIClient(config)

# Request methods
response = client.get(endpoint, params={}, headers={})
response = client.post(endpoint, json={}, headers={})
response = client.put(endpoint, json={}, headers={})
response = client.delete(endpoint, headers={})

# Response handling
data = response.json()      # Parse as JSON
text = response.text()       # Get as string
bytes = response.content     # Get raw bytes
status = response.status_code # HTTP status code

# Error handling
try:
    response = client.get(endpoint)
except HTTPError as e:
    print(f"HTTP {e.status_code}: {e.message}")
except APIError as e:
    print(f"API Error: {e}")
```

Happy coding with the API client!
