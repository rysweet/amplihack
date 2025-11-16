# Context Providers & Middleware

## Context Providers

Context providers inject additional information into agent conversations. They enable agents to access:

- Conversation history from databases
- User profiles and preferences
- Relevant documents (RAG)
- Real-time data
- Session state

### Built-in Context Provider

```python
from agents_framework import Thread, Agent, ModelClient

# Thread automatically provides conversation history
thread = Thread()

agent = Agent(model=ModelClient(model="gpt-4"))

await agent.run(thread=thread, message="My name is Alice")
await agent.run(thread=thread, message="What's my name?")
# Agent remembers: "Your name is Alice"
```

### Custom Context Provider

```python
from agents_framework import ContextProvider

class DatabaseContextProvider(ContextProvider):
    """Load conversation history from database."""

    async def get_context(self, thread_id: str) -> list[dict]:
        """Retrieve messages for thread."""
        messages = await db.fetch_messages(thread_id)
        return [{"role": m.role, "content": m.content} for m in messages]

    async def save_context(self, thread_id: str, messages: list[dict]):
        """Persist new messages."""
        await db.save_messages(thread_id, messages)

# Use custom provider
agent = Agent(
    model=model,
    context_provider=DatabaseContextProvider()
)
```

### RAG Context Provider

```python
class RAGContextProvider(ContextProvider):
    """Inject relevant documents based on query."""

    def __init__(self, vector_store):
        self.vector_store = vector_store

    async def get_context(self, thread_id: str, current_message: str) -> list[dict]:
        # Get conversation history
        history = await db.fetch_messages(thread_id)

        # Retrieve relevant documents
        query_embedding = get_embedding(current_message)
        docs = self.vector_store.search(query_embedding, top_k=3)

        # Inject as system message
        context_message = {
            "role": "system",
            "content": f"Relevant documents:\n{format_docs(docs)}"
        }

        return [context_message] + history

# Usage
agent = Agent(
    model=model,
    context_provider=RAGContextProvider(vector_store)
)
```

### User Profile Context

```python
class UserProfileProvider(ContextProvider):
    """Include user preferences and history."""

    async def get_context(self, thread_id: str) -> list[dict]:
        user_id = await get_user_from_thread(thread_id)
        profile = await db.get_user_profile(user_id)

        profile_context = {
            "role": "system",
            "content": f"""User Profile:
            - Name: {profile.name}
            - Preferences: {profile.preferences}
            - Language: {profile.language}
            - Previous interactions: {profile.interaction_count}
            """
        }

        history = await db.fetch_messages(thread_id)
        return [profile_context] + history
```

## Middleware

Middleware intercepts and processes messages before/after agent execution. Use cases:

- Logging and monitoring
- Authentication and authorization
- Rate limiting
- Content filtering
- Response transformation

### Middleware Interface

```python
from agents_framework import Middleware

class CustomMiddleware(Middleware):
    async def process_request(self, message: dict, context: dict):
        """Called before agent processes message."""
        # Modify message or context
        return message, context

    async def process_response(self, response: dict, context: dict):
        """Called after agent generates response."""
        # Modify or log response
        return response
```

### Logging Middleware

```python
class LoggingMiddleware(Middleware):
    async def process_request(self, message: dict, context: dict):
        print(f"[REQUEST] {message['content']}")
        return message, context

    async def process_response(self, response: dict, context: dict):
        print(f"[RESPONSE] {response['content']}")
        print(f"[TOKENS] {response.get('usage', {})}")
        return response

# Add to agent
agent = Agent(
    model=model,
    middleware=[LoggingMiddleware()]
)
```

### Authentication Middleware

```python
class AuthMiddleware(Middleware):
    async def process_request(self, message: dict, context: dict):
        user_id = context.get("user_id")
        if not user_id:
            raise PermissionError("User not authenticated")

        # Check permissions
        permissions = await get_user_permissions(user_id)
        context["permissions"] = permissions

        return message, context
```

### Rate Limiting Middleware

```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimitMiddleware(Middleware):
    def __init__(self, max_requests_per_minute: int = 10):
        self.max_requests = max_requests_per_minute
        self.requests = defaultdict(list)

    async def process_request(self, message: dict, context: dict):
        user_id = context.get("user_id", "anonymous")
        now = datetime.now()

        # Remove old requests
        cutoff = now - timedelta(minutes=1)
        self.requests[user_id] = [
            t for t in self.requests[user_id] if t > cutoff
        ]

        # Check limit
        if len(self.requests[user_id]) >= self.max_requests:
            raise Exception("Rate limit exceeded")

        self.requests[user_id].append(now)
        return message, context
```

### Content Filtering Middleware

```python
class ContentFilterMiddleware(Middleware):
    def __init__(self, blocked_words: list[str]):
        self.blocked_words = blocked_words

    async def process_request(self, message: dict, context: dict):
        content = message["content"].lower()
        for word in self.blocked_words:
            if word in content:
                raise ValueError(f"Inappropriate content detected")
        return message, context

    async def process_response(self, response: dict, context: dict):
        # Filter response too
        content = response["content"]
        for word in self.blocked_words:
            content = content.replace(word, "***")
        response["content"] = content
        return response
```

### Response Transformation Middleware

```python
class FormattingMiddleware(Middleware):
    async def process_response(self, response: dict, context: dict):
        # Add markdown formatting
        content = response["content"]
        content = f"**Agent Response:**\n\n{content}"
        response["content"] = content
        return response
```

### Middleware Chain

```python
agent = Agent(
    model=model,
    middleware=[
        AuthMiddleware(),
        RateLimitMiddleware(max_requests_per_minute=20),
        LoggingMiddleware(),
        ContentFilterMiddleware(["spam", "abuse"]),
        FormattingMiddleware()
    ]
)
# Middleware executes in order for requests, reverse order for responses
```

## C# Middleware Example

```csharp
using Microsoft.Agents.AI;

public class LoggingMiddleware : IMiddleware
{
    public async Task<Message> ProcessRequestAsync(Message message, Context context)
    {
        Console.WriteLine($"[REQUEST] {message.Content}");
        return message;
    }

    public async Task<Message> ProcessResponseAsync(Message response, Context context)
    {
        Console.WriteLine($"[RESPONSE] {response.Content}");
        return response;
    }
}

var agent = new Agent(
    model: model,
    middleware: new[] { new LoggingMiddleware() }
);
```

## Advanced Patterns

### Conditional Middleware

```python
class ConditionalMiddleware(Middleware):
    async def process_request(self, message: dict, context: dict):
        # Only apply to certain users
        if context.get("user_type") == "premium":
            context["priority"] = "high"
        return message, context
```

### Caching Middleware

```python
class CachingMiddleware(Middleware):
    def __init__(self):
        self.cache = {}

    async def process_request(self, message: dict, context: dict):
        cache_key = hash(message["content"])
        if cache_key in self.cache:
            context["cached_response"] = self.cache[cache_key]
        return message, context

    async def process_response(self, response: dict, context: dict):
        if "cached_response" not in context:
            cache_key = hash(context["original_message"])
            self.cache[cache_key] = response
        return response
```

### Metrics Middleware

```python
from prometheus_client import Counter, Histogram

class MetricsMiddleware(Middleware):
    def __init__(self):
        self.request_count = Counter("agent_requests", "Total requests")
        self.response_time = Histogram("agent_response_time", "Response time")

    async def process_request(self, message: dict, context: dict):
        self.request_count.inc()
        context["start_time"] = time.time()
        return message, context

    async def process_response(self, response: dict, context: dict):
        duration = time.time() - context["start_time"]
        self.response_time.observe(duration)
        return response
```

## Best Practices

1. **Keep middleware focused**: One responsibility per middleware
2. **Order matters**: Place auth before logging, logging before filtering
3. **Error handling**: Catch and handle exceptions gracefully
4. **Performance**: Minimize overhead in hot path
5. **Testing**: Test middleware independently and in chains
6. **Documentation**: Document what each middleware does and its dependencies
