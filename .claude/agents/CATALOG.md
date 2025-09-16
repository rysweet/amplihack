# Agent Catalog

This catalog provides a comprehensive overview of all available agents in the system. Use these agents proactively to leverage specialized expertise.

## Core Agents

These are the fundamental agents for most development tasks.

### 🏗️ Architect
**File**: `core/architect.md`
**Purpose**: Primary architecture and design agent
**Use When**:
- Analyzing new problems or features
- Designing system architecture
- Creating module specifications
- Reviewing code for philosophy compliance

**Example**:
```
"I need to add caching to the API"
→ Use architect to analyze and design the caching architecture
```

### 🔨 Builder
**File**: `core/builder.md`
**Purpose**: Primary implementation agent
**Use When**:
- Implementing modules from specifications
- Creating self-contained components
- Building working code (no stubs)
- Writing tests and documentation

**Example**:
```
"Implement the cache module we designed"
→ Use builder to create the implementation
```

### 🔍 Reviewer
**File**: `core/reviewer.md`
**Purpose**: Code review and debugging specialist
**Use When**:
- Finding and fixing bugs
- Reviewing code quality
- Checking philosophy compliance
- Analyzing performance issues

**Example**:
```
"The API is returning 500 errors"
→ Use reviewer to debug and fix the issue
```

## Specialized Agents

These agents provide domain-specific expertise.

### 💾 Database
**File**: `specialized/database.md`
**Purpose**: Database design and optimization
**Use When**:
- Designing database schemas
- Optimizing slow queries
- Planning migrations
- Choosing storage solutions

**Example**:
```
"Our queries are timing out"
→ Use database agent to analyze and optimize
```

### 🔒 Security
**File**: `specialized/security.md`
**Purpose**: Security and vulnerability assessment
**Use When**:
- Implementing authentication
- Reviewing security vulnerabilities
- Handling sensitive data
- Setting up encryption

**Example**:
```
"Add user authentication to the API"
→ Use security agent for secure implementation
```

### 🔌 Integration
**File**: `specialized/integration.md`
**Purpose**: API and service integration
**Use When**:
- Connecting to external services
- Designing API interfaces
- Implementing webhooks
- Setting up message queues

**Example**:
```
"Integrate with Stripe payment API"
→ Use integration agent for clean interface design
```

## Agent Selection Guide

### Quick Decision Tree

```
Is it a new feature or problem?
├─ YES → Start with Architect
│   └─ Then use Builder for implementation
│   └─ Finally use Reviewer to verify
│
├─ Is it a bug or error?
│   └─ YES → Use Reviewer
│
├─ Is it database-related?
│   └─ YES → Use Database
│
├─ Is it security-related?
│   └─ YES → Use Security
│
└─ Is it about external services?
    └─ YES → Use Integration
```

### Agent Collaboration Patterns

#### Sequential Pattern (Common)
```
Architect → Builder → Reviewer
Design → Implement → Verify
```

#### Parallel Analysis
```
Architect + Security + Database
└─ Gather multiple perspectives
└─ Synthesize recommendations
└─ Implement unified solution
```

#### Iterative Refinement
```
Builder → Reviewer → Builder
└─ Implement
└─ Find issues
└─ Fix and improve
```

## Best Practices

### Do's
- ✅ Use agents proactively for their expertise
- ✅ Provide full context to each agent
- ✅ Chain agents for complex tasks
- ✅ Let specialized agents handle their domains
- ✅ Document agent decisions in DISCOVERIES.md

### Don'ts
- ❌ Try to do everything yourself
- ❌ Skip the architect for complex features
- ❌ Ignore reviewer feedback
- ❌ Use general approach for specialized needs
- ❌ Forget to capture learnings

## Creating New Agents

Need a new specialized agent? Follow this pattern:

1. **Identify the need**: Repeated task or specialized knowledge
2. **Define the purpose**: Single, clear responsibility
3. **Create the agent file**: In appropriate directory
4. **Document in catalog**: Add to this file
5. **Test the agent**: Verify it works as expected

## Agent Performance Metrics

Track agent effectiveness:
- **Usage frequency**: Which agents are most valuable
- **Success rate**: How often agents solve problems
- **Time savings**: Efficiency improvements
- **Quality impact**: Code quality improvements

## Future Agents (Planned)

- **Test Generator**: Automatic test creation
- **Documentation Writer**: Auto-generate docs
- **Performance Optimizer**: Profile and optimize
- **Refactoring Specialist**: Code improvement patterns
- **API Designer**: OpenAPI/GraphQL schemas

---

Remember: Agents are your specialized team members. Use them liberally to leverage their expertise and accelerate development.