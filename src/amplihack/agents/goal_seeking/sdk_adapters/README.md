# SDK Adapters for Goal-Seeking Agents

SDK-agnostic abstraction layer for building goal-seeking learning agents across
multiple AI SDKs.

## Quick Start

```python
from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

# Create a Claude-powered learning agent
agent = create_agent(
    name="my_learner",
    sdk="claude",
    instructions="You are a learning agent that acquires knowledge.",
)

# Or use the mini-framework baseline
agent = create_agent(name="baseline", sdk="mini")

# Run a task
result = await agent.run("Learn about photosynthesis from this article...")
print(result.response)
print(result.goal_achieved)
```

## Architecture

```
sdk_adapters/
  base.py        - GoalSeekingAgent ABC, AgentTool, AgentResult, Goal, SDKType
  claude_sdk.py  - ClaudeGoalSeekingAgent (uses claude-agents package)
  factory.py     - create_agent() factory + _MiniFrameworkAdapter
  __init__.py    - Package exports
```

### GoalSeekingAgent (Abstract Base)

All SDK implementations inherit from `GoalSeekingAgent` and implement:

| Method | Purpose |
|--------|---------|
| `_create_sdk_agent()` | Initialize SDK-specific agent |
| `_run_sdk_agent(task, max_turns)` | Execute task through SDK loop |
| `_get_native_tools()` | List SDK-native tools |
| `_register_tool_with_sdk(tool)` | Register custom tool |

### 7 Learning Tools

Registered automatically by the base class:

| Tool | Category | Description |
|------|----------|-------------|
| `learn_from_content` | learning | Extract and store facts from text |
| `search_memory` | memory | Query stored knowledge |
| `explain_knowledge` | teaching | Generate topic explanations |
| `find_knowledge_gaps` | learning | Identify unknowns |
| `verify_fact` | applying | Check consistency |
| `store_fact` | memory | Persist knowledge |
| `get_memory_summary` | memory | Memory statistics |

### Claude SDK Native Tools

When using `sdk="claude"`, these native tools are available:
- `bash` - Shell command execution
- `read_file` / `write_file` / `edit_file` - File operations
- `glob` / `grep` - File search

### MCP Integration

```python
agent = create_agent(
    name="mcp_agent",
    sdk="claude",
    mcp_clients=[mcp_client],  # Pass MCPClient instances
)
```

### Subagent Support (Teaching Sessions)

```python
from amplihack.agents.goal_seeking.sdk_adapters.claude_sdk import ClaudeGoalSeekingAgent

agent = ClaudeGoalSeekingAgent(name="teacher")
with agent.create_teaching_subagent("photosynthesis", "beginner") as sub:
    result = sub.run("Explain photosynthesis step by step")
```

## Supporting Modules

| Module | Purpose |
|--------|---------|
| `learning_agent.py` | Generic LearningAgent with LLM synthesis |
| `cognitive_adapter.py` | 6-type cognitive memory adapter |
| `flat_retriever_adapter.py` | HierarchicalMemory adapter |
| `hierarchical_memory.py` | Kuzu graph-based memory |
| `graph_rag_retriever.py` | Graph RAG knowledge retrieval |
| `similarity.py` | Text similarity (Jaccard) |
| `json_utils.py` | Robust LLM JSON parsing |

## Running Tests

```bash
pytest tests/agents/goal_seeking/test_claude_sdk_adapter.py -v
```

## Running Evaluation

```bash
python run_eval.py --parallel 3
```

Runs L1-L6 progressive evaluation with 3 parallel runs and median scoring.
