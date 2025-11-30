# REST API Client

A robust, type-safe HTTP client library with automatic retry logic, rate
limiting, and comprehensive error handling.

## Installation

```bash
pip install rest-api-client
```

## Quick Start

```python
from rest_api_client import APIClient

# Create a client instance
client = APIClient(base_url="https://api.example.com")

# Make a simple GET request
response = client.get("/users/123")
print(response.data)
# Output: {"id": 123, "name": "Alice", "email": "alice@example.com"}

# POST with JSON data
user_data = {"name": "Bob", "email": "bob@example.com"}
response = client.post("/users", json=user_data)
print(f"Created user: {response.data['id']}")
# Output: Created user: 124
```

## Features

- **All HTTP Methods**: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- **Automatic Retries**: Exponential backoff with configurable attempts
- **Rate Limiting**: Built-in token bucket algorithm for API limits
- **Type Safety**: Full type hints with dataclass models
- **Error Handling**: Comprehensive exception hierarchy
- **Logging**: Structured logging for debugging
- **Async Support**: Both sync and async clients available

## Basic Usage

### Creating a Client

```python
from rest_api_client import APIClient
from rest_api_client.config import APIConfig

# Simple initialization
client = APIClient(base_url="https://api.example.com")

# With configuration
config = APIConfig(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=3,
    rate_limit_calls=100,
    rate_limit_period=60
)
client = APIClient(config=config)

# With authentication
client = APIClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)
```

### Making Requests

```python
# GET request
users = client.get("/users")

# GET with query parameters
filtered_users = client.get("/users", params={"active": True, "limit": 10})

# POST with JSON
new_user = client.post("/users", json={"name": "Charlie"})

# PUT with data
updated = client.put("/users/123", json={"name": "Charles"})

# DELETE request
client.delete("/users/456")

# Custom headers for a single request
response = client.get(
    "/users/me",
    headers={"X-Custom-Header": "value"}
)
```

### Error Handling

```python
from rest_api_client.exceptions import (
    APIError,
    RateLimitError,
    NetworkError,
    ValidationError
)

try:
    response = client.get("/protected-resource")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except ValidationError as e:
    print(f"Invalid request: {e.message}")
except NetworkError as e:
    print(f"Network issue: {e.message}")
except APIError as e:
    print(f"API error: {e.status_code} - {e.message}")
```

### Rate Limiting

The client automatically handles rate limiting:

```python
# Configure rate limits
client = APIClient(
    base_url="https://api.example.com",
    rate_limit_calls=100,  # 100 calls
    rate_limit_period=60    # per 60 seconds
)

# The client will automatically throttle requests
for i in range(200):
    # This will pause when rate limit is reached
    response = client.get(f"/items/{i}")
```

---

# Amplihack Agentic Coding Framework

## Remote Execution (Beta)

Distribute agentic work across Azure VMs:

```sh
amplihack remote auto "implement feature" --region westus3 --vm-size s
```

Documentation:
[.claude/tools/amplihack/remote/README.md](.claude/tools/amplihack/remote/README.md)

### Profile Management

**Reduce token usage by 72% with profile-based component filtering:**

# Install with filtering

amplihack install

# Result: Only 9/32 agents staged (72% reduction)

# Launch with filtering

amplihack launch

# Result: Focused environment for coding tasks

| Agent            | Purpose                                  |
| ---------------- | ---------------------------------------- |
| **api-designer** | API design and endpoint structure        |
| **architect**    | System design and architecture decisions |
| **builder**      | Code generation and implementation       |
| **optimizer**    | Performance optimization and efficiency  |
| **reviewer**     | Code quality and best practices review   |
| **tester**       | Test generation and validation           |

### Commands

| Command                        | Description                                             |
| ------------------------------ | ------------------------------------------------------- |
| `amplihack new`                | **NEW!** Generate goal-seeking agents from prompts      |
| `/amplihack:ultrathink`        | Deep multi-agent analysis (now DEFAULT for all prompts) |
| `/amplihack:analyze`           | Code analysis and philosophy compliance review          |
| `/amplihack:auto`              | Autonomous agentic loop (clarify → plan → execute)      |
| `/amplihack:cascade`           | Fallback cascade for resilient operations               |
| `/amplihack:debate`            | Multi-agent debate for complex decisions                |
| `/amplihack:expert-panel`      | Multi-expert review with voting                         |
| `/amplihack:n-version`         | N-version programming for critical code                 |
| `/amplihack:socratic`          | Generate Socratic questions to challenge claims         |
| `/amplihack:reflect`           | Session reflection and improvement analysis             |
| `/amplihack:improve`           | Capture learnings and implement improvements            |
| `/amplihack:fix`               | Fix common errors and code issues                       |
| `/amplihack:modular-build`     | Build self-contained modules with clear contracts       |
| `/amplihack:knowledge-builder` | Build comprehensive knowledge base                      |
| `/amplihack:transcripts`       | Conversation transcript management                      |
| `/amplihack:xpia`              | Security analysis and threat detection                  |
| `/amplihack:customize`         | Manage user-specific preferences                        |
| `/amplihack:ddd:0-help`        | Document-Driven Development help and guidance           |
| `/amplihack:ddd:1-plan`        | Phase 0: Planning & Alignment                           |
| `/amplihack:ddd:2-docs`        | Phase 1: Documentation Retcon                           |
| `/amplihack:ddd:3-code-plan`   | Phase 3: Implementation Planning                        |
| `/amplihack:ddd:4-code`        | Phase 4: Code Implementation                            |
| `/amplihack:ddd:5-finish`      | Phase 5: Testing & Phase 6: Cleanup                     |
| `/amplihack:ddd:prime`         | Prime context with DDD overview                         |
| `/amplihack:ddd:status`        | Check current DDD phase and progress                    |
| `/amplihack:lock`              | Enable continuous work mode                             |
| `/amplihack:unlock`            | Disable continuous work mode                            |
| `/amplihack:install`           | Install amplihack tools                                 |
| `/amplihack:uninstall`         | Uninstall amplihack tools                               |

### Specialized Agents (23)

| Agent                       | Purpose                                         |
| --------------------------- | ----------------------------------------------- |
| **ambiguity**               | Clarify ambiguous requirements                  |
| **amplifier-cli-architect** | CLI tool design and architecture                |
| **analyzer**                | Deep code analysis                              |
| **azure-kubernetes-expert** | Azure Kubernetes Service expertise              |
| **ci-diagnostic-workflow**  | CI/CD pipeline diagnostics                      |
| **cleanup**                 | Remove artifacts and enforce philosophy         |
| **database**                | Database design and optimization                |
| **fallback-cascade**        | Resilient fallback strategies                   |
| **fix-agent**               | Automated error fixing                          |
| **integration**             | System integration patterns                     |
| **knowledge-archaeologist** | Extract and preserve knowledge                  |
| **memory-manager**          | Context and state management                    |
| **multi-agent-debate**      | Facilitate multi-perspective debates            |
| **n-version-validator**     | Validate N-version implementations              |
| **patterns**                | Design pattern recommendations                  |
| **pre-commit-diagnostic**   | Pre-commit hook diagnostics                     |
| **preference-reviewer**     | User preference validation                      |
| **prompt-writer**           | Effective prompt engineering                    |
| **rust-programming-expert** | Rust language expertise                         |
| **security**                | Security analysis and vulnerability detection   |
| **visualization-architect** | Data visualization design                       |
| **xpia-defense**            | Advanced threat detection                       |
| **philosophy-guardian**     | Philosophy compliance and simplicity validation |

## Core Concepts

### Workflow

Iterative multi-step development process (customizeable via DEFAULT_WORKFLOW.md)

1. Clarify requirements
2. Create issue
3. Setup branch
4. Design tests
5. Implement
6. Simplify
7. Test
8. Commit
9. Create PR
10. Review
11. Integrate feedback
12. Check philosophy
13. Prepare merge
