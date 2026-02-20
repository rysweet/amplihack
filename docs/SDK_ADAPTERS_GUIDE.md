# SDK Adapters Guide

Deep dive into the four SDK backends for goal-seeking agents. This guide covers installation, configuration, API mapping, and troubleshooting for each SDK.

---

## Overview

The `GoalSeekingAgent` abstraction allows you to write agent logic once and run it on any of four SDK backends. Each SDK provides different native tools, state management, and LLM models, but the seven learning tools and memory system work identically across all of them.

```python
from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

# Same interface, different backends:
agent = create_agent(name="learner", sdk="copilot")
agent = create_agent(name="learner", sdk="claude")
agent = create_agent(name="learner", sdk="microsoft")
agent = create_agent(name="learner", sdk="mini")
```

---

## Copilot SDK (Default)

**Package:** `github-copilot-sdk`
**Default model:** `gpt-4.1`
**Env var override:** `COPILOT_MODEL`

### Installation

```bash
pip install github-copilot-sdk
```

Also requires the GitHub Copilot CLI to be installed and authenticated:

```bash
# Authenticate with GitHub
gh auth login
gh extension install github/gh-copilot
```

### When to Use

- General development tasks involving file system, git, and web operations
- When you need streaming support
- When working within the GitHub ecosystem
- When you want session-based conversation state

### Native Tools

| Tool           | Description                                 |
| -------------- | ------------------------------------------- |
| `file_system`  | Read, write, edit files                     |
| `git`          | Git operations (status, commit, push, etc.) |
| `web_requests` | HTTP requests to external APIs              |

### API Mapping

| GoalSeekingAgent Method         | Copilot SDK Equivalent                       |
| ------------------------------- | -------------------------------------------- |
| `_create_sdk_agent()`           | `CopilotClient()` + `create_session(config)` |
| `_run_sdk_agent(task)`          | `session.send_and_wait({"prompt": task})`    |
| `_register_tool_with_sdk(tool)` | Add to session config `tools` list           |

### Configuration

The Copilot SDK uses a session configuration dict:

```python
session_config = {
    "model": "gpt-4.1",
    "streaming": False,
    "tools": [...],           # Custom learning tools
    "systemMessage": {"content": "..."},
    "customAgents": [{
        "name": "my-agent",
        "displayName": "My Agent",
        "description": "...",
        "prompt": "...",
    }],
}
```

### Lifecycle

The Copilot client is initialized lazily (on first `run()` call) because it requires async start:

```
create_agent("x", sdk="copilot")
    --> stores session_config (sync)
agent.run("task")
    --> _ensure_client() initializes CopilotClient (async)
    --> creates session with config
    --> sends task to session
agent.close()
    --> stops CopilotClient
```

### Troubleshooting

**"github-copilot-sdk not installed"**

- Install: `pip install github-copilot-sdk`
- Verify: `python -c "from copilot import CopilotClient; print('OK')"`

**"Authentication failed"**

- Run `gh auth login` and ensure your token has Copilot access.

**Session resets after tool registration**

- This is expected. Registering a new tool rebuilds the session config and resets the session. Tools should be registered before the first `run()` call.

---

## Claude SDK

**Package:** `claude-agents`
**Default model:** `claude-sonnet-4-5-20250929`
**Env var override:** `CLAUDE_AGENT_MODEL`

### Installation

```bash
pip install claude-agents
```

Requires `ANTHROPIC_API_KEY` environment variable.

### When to Use

- Subagent delegation (Claude SDK has native support for spawning sub-agents)
- MCP (Model Context Protocol) integration for external tool servers
- When you need bash, file read/write, and grep as native tools
- When you want hooks for logging and validation

### Native Tools

| Tool         | Description              |
| ------------ | ------------------------ |
| `bash`       | Execute shell commands   |
| `read_file`  | Read file contents       |
| `write_file` | Write/create files       |
| `edit_file`  | Edit existing files      |
| `glob`       | Pattern-match file paths |
| `grep`       | Search file contents     |

### API Mapping

| GoalSeekingAgent Method         | Claude SDK Equivalent                              |
| ------------------------------- | -------------------------------------------------- |
| `_create_sdk_agent()`           | `ClaudeAgent(model, system, tools, allowed_tools)` |
| `_run_sdk_agent(task)`          | `agent.run(task)`                                  |
| `_register_tool_with_sdk(tool)` | Recreate agent with updated tools                  |

### Tool Registration

The Claude SDK agent is immutable after creation. Registering a new tool requires recreating the entire agent:

```python
def _register_tool_with_sdk(self, tool):
    self._tools.append(tool)
    self._create_sdk_agent()  # Recreates the agent
```

This means you should register all custom tools before calling `run()`.

### System Prompt Structure

The Claude implementation builds a structured system prompt that covers all four agent capabilities:

```
GOAL SEEKING:
1. Determine the user's intent from their message
2. Form a specific, evaluable goal
3. Make a plan to achieve the goal
4. Execute the plan iteratively
5. Evaluate whether the goal was achieved

LEARNING:
- Use learn_from_content to extract and store facts
- Use search_memory to retrieve relevant stored knowledge
- Use verify_fact to check claims against your knowledge
- Use find_knowledge_gaps to identify what you don't know

TEACHING:
- Use explain_knowledge to generate explanations
- Adapt your explanations to the learner's level
- Ask probing questions to verify understanding

APPLYING:
- Use stored knowledge to solve new problems
- Use native tools (bash, file operations) to take real actions
- Verify your work using verify_fact and search_memory

ADDITIONAL INSTRUCTIONS:
[User-provided instructions appended here]
```

### Troubleshooting

**"claude-agents not installed"**

- Install: `pip install claude-agents`
- Verify: `python -c "from claude_agents import Agent; print('OK')"`

**"ANTHROPIC_API_KEY not set"**

- Set: `export ANTHROPIC_API_KEY=sk-ant-...`

**Agent seems to ignore new tools**

- Tools added after `_create_sdk_agent()` require recreating the agent. Call `_register_tool_with_sdk()` which handles this automatically.

---

## Microsoft Agent Framework

**Package:** `agent-framework`
**Default model:** `gpt-4`
**Env var override:** (none; set in code)

### Installation

```bash
pip install agent-framework --pre
```

### When to Use

- Structured multi-agent workflows using GraphWorkflow
- When you need middleware for logging, authentication, or validation
- When you want OpenTelemetry integration for observability
- When you need structured output via Pydantic models
- When thread-based multi-turn state management is important

### Native Tools

| Tool           | Description                           |
| -------------- | ------------------------------------- |
| `model_client` | Depends on model client configuration |

The Microsoft Agent Framework is more flexible about tools -- they are defined via the `@function_tool` decorator pattern, so native tools depend on your model client setup.

### API Mapping

| GoalSeekingAgent Method         | MS Agent Framework Equivalent                                             |
| ------------------------------- | ------------------------------------------------------------------------- |
| `_create_sdk_agent()`           | `MSAgent(name, model=ModelClient(...), instructions, tools)` + `Thread()` |
| `_run_sdk_agent(task)`          | `agent.run(thread=thread, message=task)`                                  |
| `_register_tool_with_sdk(tool)` | Recreate agent with updated tools                                         |

### Thread-Based State

Unlike other SDKs, the Microsoft framework uses a `Thread` object for multi-turn conversation state:

```python
self._thread = Thread()  # Created once during init

# Each run adds to the same thread
response = await self._sdk_agent.run(
    thread=self._thread,
    message=task,
)
```

This gives you automatic conversation history without manually managing message arrays.

### Tool Registration

Tools are registered by wrapping Python functions with the appropriate metadata:

```python
for tool in self._tools:
    fn = tool.function
    fn.__name__ = tool.name
    fn.__doc__ = tool.description
    ms_tools.append(fn)
```

### Troubleshooting

**"agent-framework not installed"**

- Install: `pip install agent-framework --pre` (note the `--pre` flag for pre-release)
- Verify: `python -c "from agents_framework import Agent; print('OK')"`

**"Thread state lost"**

- The `close()` method sets `self._thread = None`. Create a new agent instance for a fresh conversation.

---

## Mini Framework

**Package:** None (uses `litellm` which is already an amplihack dependency)
**Default model:** Any model supported by litellm
**Env var override:** (none)

### Installation

No additional installation needed. The mini framework wraps the existing `LearningAgent` class.

### When to Use

- Quick testing and prototyping without installing external SDKs
- Benchmarking against other SDKs (same interface, minimal overhead)
- When you only need the learning/memory capabilities without native file/git/web tools
- In CI/CD environments where installing SDK packages is impractical

### Native Tools

| Tool                | Description                  |
| ------------------- | ---------------------------- |
| `read_content`      | Read text content            |
| `search_memory`     | Search stored knowledge      |
| `synthesize_answer` | LLM-powered answer synthesis |
| `calculate`         | Basic arithmetic             |

### API Mapping

| GoalSeekingAgent Method         | Mini Framework Equivalent                                   |
| ------------------------------- | ----------------------------------------------------------- |
| `_create_sdk_agent()`           | `LearningAgent(agent_name, model, storage_path)`            |
| `_run_sdk_agent(task)`          | `learning_agent.answer_question(task, question_level="L2")` |
| `_register_tool_with_sdk(tool)` | No-op (fixed tool set)                                      |

### How It Works

The mini framework adapter wraps the existing `LearningAgent` class to make it conform to the `GoalSeekingAgent` interface:

```python
class _MiniFrameworkAdapter(GoalSeekingAgent):
    def _create_sdk_agent(self):
        self._learning_agent = LearningAgent(
            agent_name=self.name,
            model=self._mini_model,
            storage_path=self.storage_path,
            use_hierarchical=True,
        )
        # Share the memory reference
        self.memory = self._learning_agent.memory
```

This means the mini framework shares its memory instance with the GoalSeekingAgent base class, so both `self.memory` and `self._learning_agent.memory` point to the same database.

### Limitations

- **Fixed tool set** -- You cannot register additional custom tools.
- **No native file/git/web tools** -- Only learning-focused tools are available.
- **Synchronous under the hood** -- The `_run_sdk_agent()` is async in signature but calls synchronous `answer_question()`.
- **Single-turn** -- Each `run()` call is independent; there is no multi-turn conversation state.

### Troubleshooting

**"litellm not installed"**

- Install: `pip install litellm`
- This should already be available as an amplihack dependency.

**"Memory not shared"**

- The adapter explicitly shares memory: `self.memory = self._learning_agent.memory`. If you see different memory states, check that you are using the same agent instance.

---

## Choosing an SDK

| Scenario                  | Recommended SDK       | Why                                                      |
| ------------------------- | --------------------- | -------------------------------------------------------- |
| Quick prototype           | `mini`                | No extra deps, fast setup                                |
| File/git/web tasks        | `copilot`             | Best native tool coverage                                |
| Subagent delegation       | `claude`              | Native subagent support                                  |
| Multi-agent orchestration | `microsoft`           | GraphWorkflow, middleware                                |
| CI/CD testing             | `mini`                | No SDK installation needed                               |
| Production deployment     | `copilot` or `claude` | Mature SDKs with full tool access                        |
| Benchmarking              | `mini`                | Minimal overhead, fair comparison                        |
| Teaching sessions         | Any                   | Teaching uses separate LLM calls, not the SDK agent loop |

---

## Adding a New SDK

To add support for a new SDK:

1. **Create** `src/amplihack/agents/goal_seeking/sdk_adapters/new_sdk.py`

2. **Implement** the four abstract methods:

```python
from .base import GoalSeekingAgent, AgentTool, AgentResult, SDKType

class NewSDKGoalSeekingAgent(GoalSeekingAgent):
    def _create_sdk_agent(self) -> None:
        # Initialize your SDK client/agent
        pass

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        # Run the task through your SDK's agent loop
        # Return AgentResult with response, goal_achieved, tools_used, etc.
        pass

    def _get_native_tools(self) -> list[str]:
        # Return list of tool names your SDK provides natively
        return ["tool1", "tool2"]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        # Register a custom AgentTool with your SDK
        pass
```

3. **Add** to `SDKType` enum in `base.py`:

```python
class SDKType(str, Enum):
    COPILOT = "copilot"
    CLAUDE = "claude"
    MICROSOFT = "microsoft"
    MINI = "mini"
    NEW_SDK = "new_sdk"  # Add your SDK
```

4. **Register** in `factory.py`:

```python
if sdk == SDKType.NEW_SDK:
    from .new_sdk import NewSDKGoalSeekingAgent
    return NewSDKGoalSeekingAgent(
        name=name,
        instructions=instructions,
        model=model or "default-model",
        ...
    )
```

5. **Test** using the progressive test suite to verify equivalent behavior:

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval_new_sdk \
    --agent-name new-sdk-test
```
