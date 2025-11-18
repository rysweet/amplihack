# Decision Framework: Agent Framework vs amplihack

## Quick Decision Tree

```
START: Need AI agent?
│
├─> Stateful multi-turn conversation?
│   ├─> YES → Use Agent Framework
│   └─> NO → Continue
│
├─> Complex workflow orchestration needed?
│   ├─> YES (conditional routing, parallel)
│   │   └─> Use Agent Framework
│   └─> NO → Continue
│
├─> File-based operations or local tools?
│   ├─> YES → Use amplihack
│   └─> NO → Continue
│
├─> Need enterprise features (telemetry, auth, middleware)?
│   ├─> YES → Use Agent Framework
│   └─> NO → Continue
│
├─> Rapid prototyping/simple task delegation?
│   ├─> YES → Use amplihack
│   └─> NO → Use Agent Framework (default for production)
│
└─> Complex requirements?
    └─> Consider using BOTH (integration patterns)
```

## Detailed Criteria

### Use Microsoft Agent Framework When:

#### 1. Stateful Conversations Required

```
✅ Customer support chatbots
✅ Tutoring systems that remember student progress
✅ Personal assistants with memory
✅ Research pipelines with iterative refinement
❌ One-shot code reviews
❌ Batch file processing
```

**Example**: Multi-turn tech support

```python
# Agent Framework - maintains context
thread = Thread()
await agent.run(thread=thread, message="My app crashed")
await agent.run(thread=thread, message="It happened after the update")
# Agent remembers previous messages
```

#### 2. Complex Orchestration

```
✅ Conditional routing based on output
✅ Parallel agent execution
✅ Iterative refinement loops
✅ Multi-stage approval workflows
❌ Simple sequential tasks
❌ Single-agent operations
```

**Example**: Parallel analysis workflow

```python
workflow.add_edge("START", ["security", "performance", "ux"])
workflow.add_edge(["security", "performance", "ux"], "synthesize")
```

#### 3. Enterprise Features

```
✅ OpenTelemetry integration
✅ Middleware (auth, logging, rate limiting)
✅ Structured outputs (Pydantic models)
✅ Production telemetry and monitoring
❌ Local development workflows
❌ Personal projects
```

#### 4. Tool-Heavy Operations

```
✅ Many external API calls
✅ Database queries
✅ Real-time data integration
✅ Human-in-the-loop approvals
❌ File system operations
❌ Local command execution
```

#### 5. Cross-Platform Requirements

```
✅ Need both Python and C# implementations
✅ .NET ecosystem integration
✅ Azure/Microsoft 365 integration
❌ Python-only projects
❌ Local CLI tools
```

### Use amplihack When:

#### 1. Stateless Task Delegation

```
✅ Code review (one-shot analysis)
✅ File analysis and transformation
✅ Test generation
✅ Architecture documentation
❌ Multi-turn conversations
❌ Persistent user sessions
```

**Example**: Code review

```python
# amplihack - stateless
reviewer = Agent(".claude/agents/amplihack/reviewer.md")
result = reviewer.process({"files": ["src/module.py"]})
```

#### 2. File-Based Operations

```
✅ Reading/writing local files
✅ Git operations
✅ Code generation and editing
✅ Directory structure analysis
❌ API calls to external services
❌ Database operations
```

#### 3. Development Workflows

```
✅ Pre-commit hooks
✅ CI/CD pipelines
✅ Local testing and validation
✅ Documentation generation
❌ Production user-facing systems
❌ Real-time services
```

#### 4. Token Efficiency Priority

```
✅ Minimal context needed
✅ Cost-sensitive operations
✅ Skill-based architecture (load on demand)
❌ Rich conversation context needed
❌ Complex state management
```

#### 5. Rapid Prototyping

```
✅ Quick experiments
✅ One-off scripts
✅ Exploration and discovery
❌ Production systems
❌ Long-term maintenance
```

### Use BOTH When:

#### 1. Hybrid Requirements

```
✅ Stateful conversation + file operations
✅ Complex orchestration + local tools
✅ Enterprise features + rapid iteration
```

**Example**: Code review with discussion

```python
# amplihack reviews code
review = amplihack_reviewer.process({"files": ["src/"]})

# Agent Framework discusses with developer
thread = Thread()
await af_agent.run(thread=thread, message=f"Review: {review}")
await af_agent.run(thread=thread, message="Why this suggestion?")
```

#### 2. Separation of Concerns

```
✅ amplihack: Orchestration
✅ Agent Framework: Execution
```

#### 3. Best-of-Both-Worlds

```
✅ amplihack's file ops + Agent Framework's state
✅ amplihack's simplicity + Agent Framework's features
```

## Scenario Matrix

| Scenario             | amplihack | Agent Framework | Both | Reasoning                   |
| -------------------- | --------- | --------------- | ---- | --------------------------- |
| Customer chatbot     | ❌        | ✅              | -    | Needs stateful conversation |
| Code review          | ✅        | ❌              | -    | Stateless, file-based       |
| Multi-step research  | ❌        | ✅              | -    | Complex orchestration       |
| Pre-commit hook      | ✅        | ❌              | -    | Local, fast, simple         |
| Tutoring system      | ❌        | ✅              | -    | Persistent student context  |
| File batch processor | ✅        | ❌              | -    | File operations, no state   |
| API integration      | ❌        | ✅              | -    | External calls, tools       |
| Documentation gen    | ✅        | ❌              | -    | File-based, one-shot        |
| Support + code fix   | -         | -               | ✅   | Conversation + file ops     |
| Research + synthesis | -         | -               | ✅   | Workflow + analysis         |

## Cost Considerations

### Token Usage

**amplihack**:

- Lower per-interaction cost
- Minimal context overhead
- Skill-based loading (load only what's needed)
- Optimized for Claude Code's token limits

**Agent Framework**:

- Higher per-interaction cost
- Conversation history included in each call
- Full context for statefulness
- Better for long-running conversations (amortized cost)

### Development Cost

**amplihack**:

- Faster prototyping
- Simpler agent definitions (markdown files)
- Less infrastructure needed
- Easier debugging (local)

**Agent Framework**:

- More setup required
- Infrastructure for production (telemetry, etc.)
- Steeper learning curve
- Better for long-term maintenance

## Performance Considerations

### Latency

**amplihack**:

- Lower latency (less overhead)
- Direct tool access
- Local execution

**Agent Framework**:

- Higher latency (state management)
- Network calls for tools
- Middleware overhead

### Throughput

**amplihack**:

- Good for batch operations
- Parallel via TodoWrite
- Limited by Claude Code

**Agent Framework**:

- Excellent for concurrent users
- Built-in parallel workflows
- Scalable architecture

## Migration Path

### From amplihack to Agent Framework

When to migrate:

1. Prototype becomes production system
2. Need stateful conversations
3. Require enterprise features
4. Want cross-platform support

**Migration steps**:

1. Identify stateful components
2. Convert amplihack agents to Agent Framework agents
3. Add thread management
4. Implement workflow orchestration
5. Add telemetry and monitoring
6. Test integration thoroughly

### From Agent Framework to amplihack

When to migrate:

1. Over-engineered for requirements
2. Cost optimization needed
3. Moving to local-only operation
4. Simplifying architecture

**Migration steps**:

1. Identify stateless components
2. Convert to amplihack agents (markdown)
3. Remove state management
4. Simplify tool integration
5. Use file-based operations

## Decision Checklist

Before choosing, answer these questions:

- [ ] Do conversations need to persist across multiple turns?
- [ ] Is complex workflow orchestration required?
- [ ] Are enterprise features (telemetry, auth) needed?
- [ ] Will this be user-facing in production?
- [ ] Are file operations a primary requirement?
- [ ] Is token efficiency critical?
- [ ] Is rapid prototyping the priority?
- [ ] Are there cross-platform requirements?
- [ ] Will this integrate with Microsoft ecosystem?
- [ ] Is this a one-time task or long-term system?

**Scoring**:

- Questions 1-4 YES → Lean toward Agent Framework
- Questions 5-7 YES → Lean toward amplihack
- Questions 8-9 YES → Agent Framework
- Question 10: One-time → amplihack, Long-term → Agent Framework

## Examples of Good Decisions

### ✅ Correct: Customer Support Bot with Agent Framework

**Why**: Multi-turn conversations, persistent user context, production system with monitoring

### ✅ Correct: Code Reviewer with amplihack

**Why**: Stateless analysis, file operations, one-shot reviews, local development

### ✅ Correct: Research Pipeline with Both

**Why**: Agent Framework for workflow + amplihack for file analysis = best of both

### ❌ Incorrect: Simple Script with Agent Framework

**Why**: Over-engineered, high cost, unnecessary complexity

### ❌ Incorrect: Multi-user Chatbot with amplihack

**Why**: No state management, can't maintain conversation context

## Summary

**Default to amplihack for**:

- Development workflows
- File operations
- Rapid prototyping
- Token efficiency

**Default to Agent Framework for**:

- Production user-facing systems
- Stateful conversations
- Complex orchestration
- Enterprise requirements

**Use both when**:

- Best-of-both-worlds needed
- Clear separation of concerns
- Hybrid requirements

When in doubt, start with amplihack for simplicity, add Agent Framework when you need its features.
