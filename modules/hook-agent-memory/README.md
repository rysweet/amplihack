# Agent Memory Hook for Amplifier

Automatically injects relevant memory context before agent execution and extracts learnings after.

## Features

- **Agent Detection** - Detects agent references in prompts:
  - `@agents/architect.md` - Direct agent references
  - `@bundle:agents/builder` - Bundle agent references
  - `/ultrathink`, `/fix` - Slash commands mapped to agents

- **Memory Injection** - Before agent execution:
  - Searches for memories tagged with detected agent types
  - Injects relevant context into the prompt
  - Respects token budget limits

- **Learning Extraction** - After session ends:
  - Extracts decisions, patterns, learnings from conversation
  - Stores tagged with involved agents
  - Deduplicates and limits to prevent noise

## Installation

```bash
pip install -e .
# With memory backend
pip install -e ".[memory]"
```

## Configuration

### In bundle.yaml

```yaml
hooks:
  prompt_hooks:
    - module: amplifier_hook_agent_memory
      config:
        enabled: true
        token_budget: 2000
  session_hooks:
    - module: amplifier_hook_agent_memory
```

## How It Works

### 1. Prompt Submission

When a user submits a prompt:

1. Hook detects agent references (`@agents/architect.md`, `/ultrathink`)
2. Searches memory backend for memories tagged with detected agents
3. Injects memory context before the prompt (up to token_budget)
4. Returns modified prompt to session

### 2. Session End

When a session ends:

1. Hook extracts learnings using pattern matching
2. Categories: decision, pattern, learning, anti-pattern
3. Stores in memory backend tagged with involved agents
4. Available for future sessions

## Supported Slash Commands

| Command | Maps To |
|---------|---------|
| `/ultrathink` | orchestrator |
| `/fix` | fix-agent |
| `/analyze` | analyzer |
| `/improve` | reviewer |
| `/socratic` | ambiguity |
| `/debate` | multi-agent-debate |
| `/reflect` | reflection |
| `/explore` | explorer |
| `/architect` | architect |
| `/build` | builder |
| `/test` | tester |
| `/review` | reviewer |

## Learning Extraction Patterns

The hook extracts learnings from conversation text using these patterns:

- **Decisions**: "decided to...", "choosing X because...", "went with..."
- **Patterns**: "pattern: ...", "best practice: ...", "approach: ..."
- **Learnings**: "learned that...", "discovered that...", "found that..."
- **Anti-patterns**: "avoid...", "don't...", "never..."

## API

```python
from amplifier_hook_agent_memory import (
    AgentMemoryHook,
    detect_agent_references,
    inject_memory_for_agents,
)

# Detect agents in prompt
agents = detect_agent_references("Use @agents/architect.md for this")
# ['architect']

# Create hook
hook = AgentMemoryHook(enabled=True, token_budget=2000)

# Manual injection
enhanced, metadata = inject_memory_for_agents(
    prompt="Design a new API",
    agent_types=["architect"],
    memory_backend=backend,
    session_id="session-123",
)
```

## License

MIT
