# Development Patterns & Solutions

This document captures proven patterns, solutions to common problems, and lessons learned from development. It serves as a quick reference for recurring challenges.

## Pattern: Claude Code SDK Integration

### Challenge

Integrating Claude Code SDK for AI-powered operations requires proper environment setup and timeout handling.

### Solution

```python
import asyncio
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

async def extract_with_claude_sdk(prompt: str, timeout_seconds: int = 120):
    """Extract using Claude Code SDK with proper timeout handling"""
    try:
        # Always use 120-second timeout for SDK operations
        async with asyncio.timeout(timeout_seconds):
            async with ClaudeSDKClient(
                options=ClaudeCodeOptions(
                    system_prompt="Extract information...",
                    max_turns=1,
                )
            ) as client:
                await client.query(prompt)

                response = ""
                async for message in client.receive_response():
                    if hasattr(message, "content"):
                        content = getattr(message, "content", [])
                        if isinstance(content, list):
                            for block in content:
                                if hasattr(block, "text"):
                                    response += getattr(block, "text", "")
                return response
    except asyncio.TimeoutError:
        print(f"Claude Code SDK timed out after {timeout_seconds} seconds")
        return ""
```

### Key Points

- **120-second timeout is optimal** - Gives SDK enough time without hanging forever
- **SDK only works in Claude Code environment** - Accept empty results outside
- **Handle markdown in responses** - Strip ```json blocks before parsing

## Pattern: Resilient Batch Processing

### Challenge

Processing large batches where individual items might fail, but we want to maximize successful processing.

### Solution

```python
class ResilientProcessor:
    async def process_batch(self, items):
        results = {"succeeded": [], "failed": []}

        for item in items:
            try:
                result = await self.process_item(item)
                results["succeeded"].append(result)
                # Save progress immediately
                self.save_results(results)
            except Exception as e:
                results["failed"].append({
                    "item": item,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                # Continue processing other items
                continue

        return results
```

### Key Points

- **Save after every item** - Never lose progress
- **Continue on failure** - Don't let one failure stop the batch
- **Track failure reasons** - Distinguish between types of failures
- **Support selective retry** - Only retry failed items

## Pattern: File I/O with Cloud Sync Resilience

### Challenge

File operations can fail mysteriously when directories are synced with cloud services (OneDrive, Dropbox).

### Solution

```python
import time
from pathlib import Path

def write_with_retry(filepath: Path, data: str, max_retries: int = 3):
    """Write file with exponential backoff for cloud sync issues"""
    retry_delay = 0.1

    for attempt in range(max_retries):
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(data)
            return
        except OSError as e:
            if e.errno == 5 and attempt < max_retries - 1:
                if attempt == 0:
                    print(f"File I/O error - retrying. May be cloud sync issue.")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise
```

### Key Points

- **Retry with exponential backoff** - Give cloud sync time to complete
- **Inform user about cloud sync** - Help them understand delays
- **Create parent directories** - Ensure path exists before writing

## Pattern: Async Context Management

### Challenge

Nested asyncio event loops cause hangs when integrating async SDKs.

### Solution

```python
# WRONG - Creates nested event loops
class Service:
    def process(self, data):
        return asyncio.run(self._async_process(data))  # Creates new loop

# Called from async context:
await loop.run_in_executor(None, service.process, data)  # Nested loops!

# RIGHT - Pure async throughout
class Service:
    async def process(self, data):
        return await self._async_process(data)  # No new loop

# Called from async context:
await service.process(data)  # Clean async chain
```

### Key Points

- **Never mix sync/async APIs** - Choose one approach
- **Avoid asyncio.run() in libraries** - Let caller manage the event loop
- **Design APIs to be fully async or fully sync** - Not both

## Pattern: Module Regeneration Structure

### Challenge

Creating modules that can be regenerated by AI without breaking system integration.

### Solution

```
module_name/
├── __init__.py         # Public interface ONLY via __all__
├── README.md           # Contract specification (required)
├── core.py             # Main implementation
├── models.py           # Data structures
├── tests/
│   ├── test_contract.py    # Verify public interface
│   └── test_core.py         # Unit tests
└── examples/
    └── basic_usage.py       # Working example
```

### Key Points

- **Contract in README.md** - AI can regenerate from this spec
- \***\*all** defines public interface\*\* - Clear boundary
- **Tests verify contract** - Not implementation details
- **Examples must work** - Validated by tests

## Pattern: Zero-BS Implementation

### Challenge

Avoiding stub code and placeholders that serve no purpose.

### Solution

```python
# BAD - Stub that does nothing
def process_payment(amount):
    # TODO: Implement Stripe integration
    raise NotImplementedError("Coming soon")

# GOOD - Working implementation
def process_payment(amount, payments_file="payments.json"):
    """Record payment locally - fully functional."""
    payment = {
        "amount": amount,
        "timestamp": datetime.now().isoformat(),
        "id": str(uuid.uuid4())
    }

    # Load and update
    payments = []
    if Path(payments_file).exists():
        payments = json.loads(Path(payments_file).read_text())

    payments.append(payment)
    Path(payments_file).write_text(json.dumps(payments, indent=2))

    return payment
```

### Key Points

- **Every function must work** - Or not exist
- **Use files instead of external services** - Start simple
- **No TODOs without code** - Implement or remove
- **Legitimate empty patterns are OK** - e.g., `pass` in Click groups

## Pattern: Incremental Processing

### Challenge

Supporting resumable, incremental processing of large datasets.

### Solution

```python
class IncrementalProcessor:
    def __init__(self, state_file="processing_state.json"):
        self.state_file = Path(state_file)
        self.state = self.load_state()

    def load_state(self):
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {"processed": [], "failed": [], "last_id": None}

    def save_state(self):
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def process_items(self, items):
        for item in items:
            if item.id in self.state["processed"]:
                continue  # Skip already processed

            try:
                self.process_item(item)
                self.state["processed"].append(item.id)
                self.state["last_id"] = item.id
                self.save_state()  # Save after each item
            except Exception as e:
                self.state["failed"].append({
                    "id": item.id,
                    "error": str(e)
                })
                self.save_state()
```

### Key Points

- **Save state after every item** - Resume from exact position
- **Track both success and failure** - Know what needs retry
- **Use fixed filenames** - Easy to find and resume
- **Support incremental updates** - Add new items without reprocessing

## Pattern: Configuration Single Source of Truth

### Challenge

Configuration scattered across multiple files causes drift and maintenance burden.

### Solution

```python
# Single source: pyproject.toml
[tool.myapp]
exclude = [".venv", "__pycache__", "node_modules"]
timeout = 30
batch_size = 100

# Read from single source
import tomllib

def load_config():
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)
    return config["tool"]["myapp"]

# Use everywhere
config = load_config()
excludes = config["exclude"]  # Don't hardcode these elsewhere
```

### Key Points

- **One authoritative location** - pyproject.toml for Python projects
- **Read, don't duplicate** - Load config at runtime
- **Document the source** - Make it clear where config lives
- **Accept minimal duplication** - Only for bootstrap/emergency

## Pattern: Parallel Task Execution

### Challenge

Executing multiple independent operations efficiently.

### Solution

```python
# WRONG - Sequential execution
results = []
for item in items:
    result = await process(item)
    results.append(result)

# RIGHT - Parallel execution
tasks = [process(item) for item in items]
results = await asyncio.gather(*tasks)

# With error handling
async def safe_process(item):
    try:
        return await process(item)
    except Exception as e:
        return {"error": str(e), "item": item}

tasks = [safe_process(item) for item in items]
results = await asyncio.gather(*tasks)
```

### Key Points

- **Use asyncio.gather() for parallel work** - Much faster
- **Wrap in error handlers** - Prevent one failure from stopping all
- **Consider semaphores for rate limiting** - Control concurrency
- **Return errors as values** - Don't let exceptions propagate

## Remember

These patterns represent hard-won knowledge from real development challenges. When facing similar problems:

1. **Check this document first** - Don't reinvent solutions
2. **Update when you learn something new** - Keep patterns current
3. **Include context** - Explain why, not just how
4. **Show working code** - Examples should be copy-pasteable
5. **Document the gotchas** - Save others from the same pain
