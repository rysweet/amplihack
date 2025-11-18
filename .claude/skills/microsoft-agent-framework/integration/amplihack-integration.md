# Amplihack Integration Guide

## Overview

Microsoft Agent Framework and amplihack are complementary systems that can work together effectively. This guide explains how to integrate them and when to use each.

## Architecture Comparison

### amplihack

- **Purpose**: Orchestration and task delegation
- **Agent Model**: Stateless, file-based agents
- **Execution**: Sequential or parallel via TodoWrite
- **State**: Conversation context only
- **Strengths**: Rapid prototyping, local operations, token efficiency
- **Use Cases**: Code review, analysis, file operations, development workflows

### Microsoft Agent Framework

- **Purpose**: Stateful conversational agents and workflows
- **Agent Model**: Stateful with persistent threads
- **Execution**: Graph-based workflows with conditional routing
- **State**: Persistent conversation history, workflow state
- **Strengths**: Enterprise features, complex orchestration, multi-turn dialogue
- **Use Cases**: Customer support, tutoring, research pipelines, production agents

## Integration Patterns

### Pattern 1: amplihack Orchestrates, Agent Framework Executes

amplihack manages the high-level workflow, delegating to Agent Framework for stateful conversations.

```python
# amplihack orchestrator (pseudocode)
from claude import Agent as ClaudeAgent
from agents_framework import Agent as AFAgent, Thread

# amplihack orchestrator
orchestrator = ClaudeAgent("orchestrator.md")

# Agent Framework for stateful dialogue
conversational_agent = AFAgent(
    model=ModelClient(model="gpt-4"),
    instructions="Maintain multi-turn conversation context"
)

# amplihack drives the process
plan = orchestrator.process({"task": "customer support session"})

# Agent Framework handles the conversation
thread = Thread()
for step in plan.steps:
    response = await conversational_agent.run(
        thread=thread,
        message=step.message
    )
    # amplihack processes response
    orchestrator.process({"response": response.content})
```

**When to use**:

- Need amplihack's orchestration capabilities
- Require stateful conversations
- Want to leverage both systems' strengths

### Pattern 2: Agent Framework Workflow with amplihack Tools

Agent Framework workflow uses amplihack agents as tools.

```python
from agents_framework import function_tool, Agent, GraphWorkflow
import subprocess

@function_tool
def analyze_code(code_path: str) -> str:
    """Use amplihack code analyzer agent."""
    result = subprocess.run(
        ["claude", "--agent", ".claude/agents/amplihack/analyzer.md", code_path],
        capture_output=True,
        text=True
    )
    return result.stdout

# Agent Framework workflow
workflow = GraphWorkflow()

analyzer_agent = Agent(
    model=model,
    instructions="Coordinate code analysis",
    tools=[analyze_code]
)

workflow.add_node("analyze", analyzer_agent)
result = await workflow.run(initial_state={"code_path": "./src"})
```

**When to use**:

- Agent Framework manages the workflow
- Need amplihack's specialized agents
- Want to use amplihack's file operations

### Pattern 3: Parallel Execution

Run both systems in parallel for different aspects of a task.

```python
import asyncio

async def parallel_processing(task):
    # amplihack for file analysis
    amplihack_task = asyncio.create_task(
        run_amplihack_agent("analyzer.md", task.files)
    )

    # Agent Framework for user interaction
    af_task = asyncio.create_task(
        conversational_agent.run(
            thread=thread,
            message=f"Analyzing {task.files}"
        )
    )

    # Wait for both
    amplihack_result, af_result = await asyncio.gather(
        amplihack_task,
        af_task
    )

    return {
        "analysis": amplihack_result,
        "user_response": af_result.content
    }
```

**When to use**:

- Independent operations can run concurrently
- Maximize throughput
- Different systems handle different aspects

### Pattern 4: Sequential Handoff

Systems pass control back and forth.

```python
async def sequential_handoff(user_query):
    # amplihack for initial analysis
    analysis = amplihack_agent.process({"query": user_query})

    # Agent Framework for dialogue
    thread = Thread()
    response = await conversational_agent.run(
        thread=thread,
        message=f"Based on analysis: {analysis}, help the user"
    )

    # Back to amplihack for execution
    if response.requires_action:
        result = amplihack_agent.process({"action": response.action})
        return result

    return response.content
```

**When to use**:

- Clear handoff points
- Each system handles distinct phases
- Sequential dependencies

## Practical Examples

### Example 1: Code Review with Conversation

```python
# amplihack reviews code
from claude import Agent as ClaudeAgent

reviewer = ClaudeAgent(".claude/agents/amplihack/reviewer.md")
review = reviewer.process({"files": ["src/module.py"]})

# Agent Framework discusses with developer
from agents_framework import Agent, Thread

discussion_agent = Agent(
    model=model,
    instructions=f"Discuss code review findings: {review}"
)

thread = Thread()
response = await discussion_agent.run(
    thread=thread,
    message="I have some questions about the review"
)
# Multi-turn conversation continues...
```

### Example 2: Customer Support Pipeline

```python
# Agent Framework handles customer conversation
from agents_framework import Agent, Thread, GraphWorkflow

support_agent = Agent(
    model=model,
    instructions="Provide customer support",
    tools=[search_kb, create_ticket]
)

thread = Thread()
conversation = await support_agent.run(
    thread=thread,
    message="I need help with X"
)

# If escalation needed, use amplihack for analysis
if conversation.requires_escalation:
    from claude import Agent as ClaudeAgent
    analyzer = ClaudeAgent(".claude/agents/amplihack/issue-analyzer.md")
    analysis = analyzer.process({"conversation": thread.messages})

    # Back to Agent Framework with analysis
    response = await support_agent.run(
        thread=thread,
        message=f"Analysis suggests: {analysis}"
    )
```

### Example 3: Research Pipeline

```python
# Agent Framework workflow coordinates
from agents_framework import GraphWorkflow, Agent

workflow = GraphWorkflow()

# Research phase - Agent Framework
researcher = Agent(model=model, instructions="Research topics")
workflow.add_node("research", researcher)

# Analysis phase - amplihack tool
@function_tool
def analyze_findings(findings: str) -> str:
    from claude import Agent as ClaudeAgent
    analyzer = ClaudeAgent(".claude/agents/amplihack/analyzer.md")
    return analyzer.process({"data": findings})

analyst = Agent(model=model, tools=[analyze_findings])
workflow.add_node("analyze", analyst)

# Synthesis phase - Agent Framework
synthesizer = Agent(model=model, instructions="Synthesize findings")
workflow.add_node("synthesize", synthesizer)

workflow.add_edge("research", "analyze")
workflow.add_edge("analyze", "synthesize")

result = await workflow.run(initial_message="Research AI trends")
```

## Configuration & Setup

### Environment Setup

```bash
# Install both systems
pip install agent-framework --pre
# amplihack is already installed via Claude Code

# Environment variables
export OPENAI_API_KEY=sk-...
export AMPLIHACK_AGENTS_PATH=./.claude/agents/amplihack
```

### Project Structure

```
project/
├── .claude/
│   ├── agents/
│   │   └── amplihack/          # amplihack agents
│   └── skills/
│       └── microsoft-agent-framework/  # This skill
├── src/
│   ├── agents/                 # Agent Framework agents
│   ├── workflows/              # Agent Framework workflows
│   └── integration/            # Integration code
└── main.py                     # Entry point
```

## Decision Framework

See `decision-framework.md` for detailed decision criteria.

**Quick Reference**:

| Requirement           | Use amplihack | Use Agent Framework | Use Both |
| --------------------- | ------------- | ------------------- | -------- |
| Stateful conversation | ❌            | ✅                  | ✅       |
| File operations       | ✅            | ❌                  | ✅       |
| Complex orchestration | Limited       | ✅                  | ✅       |
| Rapid prototyping     | ✅            | ❌                  | ❌       |
| Enterprise features   | ❌            | ✅                  | ✅       |
| Token efficiency      | ✅            | ❌                  | Balance  |
| Multi-turn dialogue   | ❌            | ✅                  | ✅       |
| Local tools           | ✅            | Limited             | ✅       |

## Best Practices

1. **Use amplihack for orchestration**: Let amplihack manage high-level workflow
2. **Use Agent Framework for conversations**: Leverage stateful threads for dialogue
3. **Share context efficiently**: Pass only necessary data between systems
4. **Monitor costs**: Track token usage for both systems
5. **Test integration points**: Ensure smooth handoffs between systems
6. **Document decisions**: Record why you chose each system for each component
7. **Start simple**: Begin with one system, add the other only when needed

## Troubleshooting

### Issue: Context loss between systems

**Solution**: Serialize thread state and pass to amplihack, or maintain shared state store

### Issue: Duplicate functionality

**Solution**: Use decision framework to clearly allocate responsibilities

### Issue: Performance overhead

**Solution**: Use parallel execution pattern when possible

### Issue: Complex debugging

**Solution**: Add logging at integration boundaries, use telemetry for both systems

## Future Integration Opportunities

1. **Unified telemetry**: Single dashboard for both systems
2. **Shared context store**: Centralized conversation history
3. **Cross-system tools**: amplihack agents callable as Agent Framework tools
4. **Hybrid workflows**: Workflow definitions that span both systems
5. **Automatic routing**: System auto-selects based on task requirements
