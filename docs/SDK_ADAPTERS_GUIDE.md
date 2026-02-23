# SDK Adapters Guide

Deep dive into the four SDK backends for goal-seeking agents. This guide covers installation, configuration, API mapping, and troubleshooting for each SDK.

---

## Overview

The `GoalSeekingAgent` abstraction allows you to write agent logic once and run it on any of four SDK backends. Each SDK provides different native tools, state management, and LLM models, but the learning/answering core and memory system work identically across all of them.

**Key design point**: All four SDK adapters delegate `learn_from_content()` and `answer_question()` to a shared `LearningAgent` instance (lazily created via `_get_learning_agent()` in `base.py`). This means:

- The eval harness calls `learn_from_content()` / `answer_question()` directly on the SDK agent, which routes to `LearningAgent` internally.
- All SDKs get identical fact extraction, intent detection, retrieval strategies, and synthesis prompts.
- The SDK-specific `_run_sdk_agent()` is used only for general task execution through the SDK's native agent loop (not for eval).
- There is no mock mode. All SDK adapters require their respective SDK packages to be installed.

```python
from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

# Same interface, different backends:
agent = create_agent(name="learner", sdk="copilot")
agent = create_agent(name="learner", sdk="claude")
agent = create_agent(name="learner", sdk="microsoft")
agent = create_agent(name="learner", sdk="mini")

# All agents share the same public API:
agent.learn_from_content("Some content to learn.")
answer = agent.answer_question("What did you learn?")
agent.close()
```

### Import Paths

| Class / Function            | Import Path                                                |
| --------------------------- | ---------------------------------------------------------- |
| `create_agent()`            | `amplihack.agents.goal_seeking.sdk_adapters.factory`       |
| `GoalSeekingAgent` (ABC)    | `amplihack.agents.goal_seeking.sdk_adapters.base`          |
| `CopilotGoalSeekingAgent`   | `amplihack.agents.goal_seeking.sdk_adapters.copilot_sdk`   |
| `ClaudeGoalSeekingAgent`    | `amplihack.agents.goal_seeking.sdk_adapters.claude_sdk`    |
| `MicrosoftGoalSeekingAgent` | `amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk` |
| `AgentTool`, `AgentResult`  | `amplihack.agents.goal_seeking.sdk_adapters.base`          |
| `SDKType`                   | `amplihack.agents.goal_seeking.sdk_adapters.base`          |
| `LearningAgent`             | `amplihack.agents.goal_seeking.learning_agent`             |
| `MultiAgentLearningAgent`   | `amplihack.agents.goal_seeking.sub_agents.multi_agent`     |

### How the Base Class Delegates to LearningAgent

The `GoalSeekingAgent` ABC in `base.py` provides `learn_from_content()` and `answer_question()` as public methods. Both delegate to an internal `LearningAgent` instance:

```python
class GoalSeekingAgent(ABC):
    def _get_learning_agent(self):
        """Lazily create a LearningAgent sharing this agent's storage path."""
        if not hasattr(self, "_learning_agent_cache"):
            from amplihack.agents.goal_seeking.learning_agent import LearningAgent
            eval_model = os.environ.get("EVAL_MODEL", "claude-sonnet-4-5-20250929")
            self._learning_agent_cache = LearningAgent(
                agent_name=f"{self.name}_learning",
                model=eval_model,
                storage_path=self.storage_path,
                use_hierarchical=True,
            )
        return self._learning_agent_cache

    def learn_from_content(self, content: str) -> dict:
        """Delegates to LearningAgent._extract_facts_with_llm()."""
        return self._tool_learn(content)  # _tool_learn calls _get_learning_agent()

    def answer_question(self, question: str) -> str:
        """Delegates to LearningAgent.answer_question()."""
        la = self._get_learning_agent()
        return la.answer_question(question)
```

The `_tool_learn` method (which backs the `learn_from_content` tool) also delegates to the LearningAgent for proper LLM-based fact extraction with temporal detection, entity extraction, and structured fact storage.

### API Surface

All `GoalSeekingAgent` instances expose:

| Method / Property      | Description                                               |
| ---------------------- | --------------------------------------------------------- |
| `learn_from_content()` | Learn facts from text (delegates to LearningAgent)        |
| `answer_question()`    | Answer questions from memory (delegates to LearningAgent) |
| `run(task, max_turns)` | Execute task via SDK's native agent loop (async)          |
| `form_goal(intent)`    | Create a structured Goal from user intent                 |
| `get_memory_stats()`   | Get memory statistics                                     |
| `close()`              | Clean up resources                                        |
| `name`                 | Agent name                                                |
| `model`                | LLM model being used                                      |
| `memory`               | Memory instance (MemoryRetriever)                         |
| `storage_path`         | Path to memory database                                   |

---

## Copilot SDK

**Package:** `github-copilot-sdk`
**Default model:** `gpt-4.1`
**Env var override:** `COPILOT_MODEL`
**Source:** `src/amplihack/agents/goal_seeking/sdk_adapters/copilot_sdk.py`

### Installation

```bash
pip install github-copilot-sdk
```

Also requires the GitHub Copilot CLI to be installed and authenticated:

```bash
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

| GoalSeekingAgent Method         | Copilot SDK Equivalent                                  |
| ------------------------------- | ------------------------------------------------------- |
| `_create_sdk_agent()`           | Build `SessionConfig` with tools and system prompt      |
| `_run_sdk_agent(task)`          | `_ensure_client()` then `session.send_and_wait(task)`   |
| `_register_tool_with_sdk(tool)` | Append to Copilot tools list, invalidate session config |

### Lifecycle

The Copilot client is initialized lazily (on first `_run_sdk_agent()` call) and creates a fresh client+session each time to avoid stale event loop issues:

```
create_agent("x", sdk="copilot")
    --> builds SessionConfig (sync, no client started)
agent.run("task")
    --> _ensure_client() creates CopilotClient + session
    --> sends task via send_and_wait
    --> cleans up client+session in finally block
agent.close()
    --> clears references
```

Supports async context manager: `async with CopilotGoalSeekingAgent(...) as agent:`.

### Troubleshooting

**"github-copilot-sdk not installed"**

- Install: `pip install github-copilot-sdk`
- Verify: `python -c "from copilot import CopilotClient; print('OK')"`

**"Authentication failed"**

- Run `gh auth login` and ensure your token has Copilot access.

---

## Claude Agent SDK

**Package:** `claude-agent-sdk`
**Default model:** `claude-sonnet-4-5-20250929`
**Env var override:** `CLAUDE_AGENT_MODEL`
**Source:** `src/amplihack/agents/goal_seeking/sdk_adapters/claude_sdk.py`

### Installation

```bash
pip install claude-agent-sdk
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

| GoalSeekingAgent Method         | Claude SDK Equivalent                                               |
| ------------------------------- | ------------------------------------------------------------------- |
| `_create_sdk_agent()`           | Store config dict with model and system prompt                      |
| `_run_sdk_agent(task)`          | `ClaudeSDKClient(options)` -> `query(task)` -> `receive_response()` |
| `_register_tool_with_sdk(tool)` | Append to tools, call `_create_sdk_agent()` to rebuild config       |

### Architecture

The Claude SDK uses `ClaudeSDKClient` with an async context manager pattern. Each `_run_sdk_agent()` call creates a fresh client with `ClaudeAgentOptions`:

```python
options = ClaudeAgentOptions(
    model=self._sdk_agent["model"],
    system_prompt=self._sdk_agent["system"],
    max_turns=max_turns,
    permission_mode="bypassPermissions",
)
client = ClaudeSDKClient(options=options)

async with client:
    await client.query(task)
    async for msg in client.receive_response():
        # Process AssistantMessage and ResultMessage
```

### Troubleshooting

**"claude-agent-sdk not installed"**

- Install: `pip install claude-agent-sdk`
- Verify: `python -c "from claude_agent_sdk import ClaudeSDKClient; print('OK')"`

**"ANTHROPIC_API_KEY not set"**

- Set: `export ANTHROPIC_API_KEY=sk-ant-...`

---

## Microsoft Agent Framework

**Package:** `agent-framework`
**Default model:** `gpt-4o`
**Env var override:** `MICROSOFT_AGENT_MODEL`
**Source:** `src/amplihack/agents/goal_seeking/sdk_adapters/microsoft_sdk.py`

### Installation

```bash
pip install agent-framework
```

### When to Use

- Structured multi-agent workflows
- When you need middleware for logging, authentication, or validation
- When you want OpenTelemetry integration for observability
- When thread-based multi-turn state management is important

### Native Tools

Tools are registered via the `FunctionTool` wrapper pattern. The 7 learning tools from `GoalSeekingAgent` are wrapped as `FunctionTool` objects:

```python
from agent_framework import FunctionTool
tool = FunctionTool(name="learn_from_content", description="...", func=wrapper_fn)
```

### API Mapping

| GoalSeekingAgent Method         | MS Agent Framework Equivalent                                                  |
| ------------------------------- | ------------------------------------------------------------------------------ |
| `_create_sdk_agent()`           | `Agent(OpenAIChatClient(...), instructions, name, tools)` + `create_session()` |
| `_run_sdk_agent(task)`          | `agent.run(messages=task, session=session)`                                    |
| `_register_tool_with_sdk(tool)` | Append to tools, call `_create_sdk_agent()` to rebuild                         |

### Session-Based State

Unlike other SDKs, the Microsoft framework uses a session for multi-turn conversation state:

```python
self._sdk_agent = AFAgent(chat_client, instructions=system_prompt, name=self.name, tools=tools)
self._session = self._sdk_agent.create_session()

# Each run adds to the same session
response = await self._sdk_agent.run(messages=task, session=self._session)
```

Use `agent.reset_session()` to start a fresh conversation.

### Troubleshooting

**"agent-framework not installed"**

- Install: `pip install agent-framework`
- Verify: `python -c "from agent_framework import Agent; print('OK')"`

**"OPENAI_API_KEY not set"**

- The SDK agent is created lazily if OPENAI_API_KEY is not set at init time. It will be created when `_run_sdk_agent` is called.
- Note: `learn_from_content()` / `answer_question()` do NOT need OPENAI_API_KEY since they use the LearningAgent with the EVAL_MODEL (typically Anthropic).

---

## Mini Framework

**Package:** None (uses `litellm` which is already an amplihack dependency)
**Default model:** Any model supported by litellm
**Source:** `src/amplihack/agents/goal_seeking/sdk_adapters/factory.py` (`_MiniFrameworkAdapter`)

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

| GoalSeekingAgent Method         | Mini Framework Equivalent                                 |
| ------------------------------- | --------------------------------------------------------- |
| `_create_sdk_agent()`           | `WikipediaLearningAgent(agent_name, model, storage_path)` |
| `_run_sdk_agent(task)`          | `learning_agent.answer_question(task)`                    |
| `_register_tool_with_sdk(tool)` | No-op (fixed tool set)                                    |

### Limitations

- **Fixed tool set** -- You cannot register additional custom tools.
- **No native file/git/web tools** -- Only learning-focused tools are available.
- **Single-turn** -- Each `run()` call is independent; there is no multi-turn conversation state.

---

## Choosing an SDK

| Scenario                  | Recommended SDK       | Why                                                      |
| ------------------------- | --------------------- | -------------------------------------------------------- |
| Quick prototype           | `mini`                | No extra deps, fast setup                                |
| File/git/web tasks        | `copilot`             | Best native tool coverage                                |
| Subagent delegation       | `claude`              | Native subagent support                                  |
| Multi-agent orchestration | `microsoft`           | Session-based, middleware                                |
| CI/CD testing             | `mini`                | No SDK installation needed                               |
| Production deployment     | `copilot` or `claude` | Mature SDKs with full tool access                        |
| Benchmarking              | `mini`                | Minimal overhead, fair comparison                        |
| Teaching sessions         | Any                   | Teaching uses separate LLM calls, not the SDK agent loop |

---

## Per-SDK Eval Prompts

Each SDK has dedicated eval prompt templates in `src/amplihack/agents/goal_seeking/prompts/sdk/`:

| File                     | Purpose                                          |
| ------------------------ | ------------------------------------------------ |
| `copilot_eval.md`        | Copilot-specific system prompt for eval sessions |
| `claude_eval.md`         | Claude-specific eval prompt                      |
| `microsoft_eval.md`      | Microsoft Agent Framework eval prompt            |
| `goal_seeking_system.md` | Shared goal-seeking system prompt                |
| `learning_task.md`       | Shared learning task template                    |
| `synthesis_template.md`  | Shared synthesis template                        |
| `teaching_system.md`     | Teaching session system prompt                   |

These templates allow per-SDK instruction tuning without modifying shared agent code. All SDKs use the same `LearningAgent` for the learning/answering core, but the per-SDK prompts can influence how the agent processes general tasks via `_run_sdk_agent()`.

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
        pass

    def _get_native_tools(self) -> list[str]:
        return ["tool1", "tool2"]

    def _register_tool_with_sdk(self, tool: AgentTool) -> None:
        # Register a custom AgentTool with your SDK
        pass
```

3. **Add** to `SDKType` enum in `base.py`

4. **Register** in `factory.py`

5. **Add per-SDK eval prompt** in `src/amplihack/agents/goal_seeking/prompts/sdk/new_sdk_eval.md`

6. **Test** using the progressive test suite or matrix eval
