# Complete User Guide: Copilot CLI with amplihack

Comprehensive guide to using GitHub Copilot CLI with the amplihack agentic coding framework.

## Table of Contents

- [Overview](#overview)
- [Core Concepts](#core-concepts)
- [Agent Usage](#agent-usage)
- [Command Invocation](#command-invocation)
- [Skill Usage](#skill-usage)
- [Workflow Execution](#workflow-execution)
- [MCP Servers](#mcp-servers)
- [Auto Mode](#auto-mode)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)

## Overview

### What is amplihack?

amplihack be a development framework that combines:

- **37+ specialized AI agents** for architecture, testing, security, etc.
- **14 foundational patterns** for common development problems
- **Philosophy-driven development** emphasizing simplicity and modularity
- **Production-ready tools** for code analysis, testing, and configuration

### How Copilot CLI Accesses amplihack

When ye launch Copilot CLI with amplihack, it gains access to:

1. **Context files** in `.claude/context/` (philosophy, patterns, trust)
2. **Agent definitions** in `.claude/agents/amplihack/`
3. **Copilot instructions** in `.github/copilot-instructions.md`
4. **Project-specific context** from initialized projects

## Core Concepts

### Philosophy

amplihack follows three core principles:

#### 1. Ruthless Simplicity

```markdown
- Start with simplest solution
- Add complexity only when justified
- Question every abstraction
- Code you don't write has no bugs
```

**Example:**

```
> Design a caching system

Bad: "Let's build a distributed caching layer with Redis, memcached failover..."
Good: "Start with in-memory dict caching, add persistence when needed"
```

#### 2. Brick Philosophy (Modular Design)

Every module be a self-contained "brick":

- **ONE clear responsibility**
- **Public API** (the "studs" others connect to)
- **Regeneratable** (can rebuild from spec)
- **Isolated** (code, tests, fixtures in module folder)

**Example:**

```python
# Good brick - clear interface, single responsibility
# auth_module/__init__.py
from .core import authenticate, validate_token
from .models import User, Token

__all__ = ['authenticate', 'validate_token', 'User', 'Token']
```

#### 3. Zero-BS Implementation

- **No stubs or placeholders**
- **No dead code or TODOs**
- **Every function works or doesn't exist**
- **Quality over speed**

**Example:**

```python
# BAD - stub that does nothing
def process_payment(amount):
    # TODO: Implement Stripe integration
    raise NotImplementedError()

# GOOD - working implementation
def process_payment(amount, ledger_file="payments.json"):
    """Record payment locally - fully functional."""
    payment = {"amount": amount, "timestamp": datetime.now().isoformat()}
    # ... working implementation ...
    return payment
```

### Trust Principles

amplihack emphasizes **trust through honesty, not harmony**:

```markdown
1. Disagree - Point out flaws, explain better approaches
2. Clarify - Never guess on ambiguous requests
3. Propose - Suggest alternatives when better ways exist
4. Admit - Say "I don't know" when you don't
5. Focus - Solve problems, not feelings
6. Challenge - Question wrong assumptions
7. Be Direct - No hedging, clear conclusions
```

**Example:**

```
User: Let's use a microservices architecture
Agent: "That adds significant complexity for this use case. A modular monolith
        would be simpler and faster. Why microservices specifically?"
```

## Agent Usage

### Core Agents (6)

Fundamental development tasks.

#### architect

Design systems and decompose problems.

```
> @architect: Design a rate limiting module for our API

Response includes:
- Module specification
- Public API design
- Dependencies
- Test requirements
```

#### builder

Implement code from specifications.

```
> @builder: Implement the rate limiting module from the architect's spec

Generates:
- Complete working implementation
- No stubs or placeholders
- Following brick philosophy
```

#### reviewer

Review code for philosophy compliance.

```
> @reviewer: Review this PR for amplihack philosophy compliance

Checks:
- Ruthless simplicity
- Modular design (bricks & studs)
- Zero-BS implementation
- Pattern usage
```

#### tester

Generate tests following TDD pyramid.

```
> @tester: Generate tests for the rate limiting module

Produces:
- 60% unit tests
- 30% integration tests
- 10% E2E tests
```

#### api-designer

Design APIs and contracts.

```
> @api-designer: Design REST API for user management

Delivers:
- Endpoint specifications
- Request/response models
- Error handling strategy
- Authentication flow
```

#### optimizer

Analyze performance and bottlenecks.

```
> @optimizer: Analyze performance of the user search function

Provides:
- Bottleneck identification
- Optimization recommendations
- Trade-off analysis
```

### Specialized Agents (23+)

Domain-specific expertise.

#### security

Security audits and vulnerability assessment.

```
> @security: Audit this authentication module

Reviews:
- Vulnerability assessment
- Best practices compliance
- Threat modeling
- Remediation recommendations
```

#### database

Database design and query optimization.

```
> @database: Design schema for multi-tenant application

Designs:
- Table structure
- Indexes and constraints
- Migration strategy
- Query patterns
```

#### cleanup

Code simplification and refactoring.

```
> @cleanup: Simplify this complex function

Results:
- Reduced complexity
- Better naming
- Extracted helper functions
- Preserved behavior
```

#### patterns

Identify and apply reusable patterns.

```
> @patterns: Identify patterns in this error handling code

Identifies:
- Applicable patterns from PATTERNS.md
- Reusable abstractions
- Simplification opportunities
```

#### integration

External service integration.

```
> @integration: Design integration with Stripe payment API

Provides:
- Integration architecture
- Error handling strategy
- Retry logic
- Testing approach
```

#### analyzer

Deep code analysis and understanding.

```
> @analyzer: Analyze this legacy codebase

Delivers:
- Code structure analysis
- Dependency graph
- Technical debt assessment
- Refactoring recommendations
```

#### ambiguity

Clarify ambiguous requirements.

```
> @ambiguity: "We need better performance"

Asks:
- What metric? (latency, throughput, memory)
- Current vs target values?
- What operations are slow?
- What constraints exist?
```

#### fix-agent

Rapid resolution of common error patterns.

```
> @fix-agent: Fix this import error

Modes:
- QUICK: Template-based fix (< 5 min)
- DIAGNOSTIC: Root cause analysis
- COMPREHENSIVE: Full workflow
```

#### knowledge-archaeologist

Understand existing systems through investigation.

```
> @knowledge-archaeologist: How does the authentication system work?

Investigates:
- Code structure discovery
- Documentation analysis
- Integration patterns
- Historical context
```

#### pre-commit-diagnostic

Fix pre-commit hook failures.

```
> @pre-commit-diagnostic: My pre-commit hooks are failing

Handles:
- Formatting issues
- Linting errors
- Type checking
- Test failures
```

#### ci-diagnostic-workflow

Fix CI failures after push.

```
> @ci-diagnostic-workflow: CI failing on my PR

Monitors:
- CI status
- Failure diagnosis
- Automated fixes
- Iteration until mergeable
```

### Agent Invocation Patterns

#### Direct Invocation

```
> @agent-name: [task description]
```

#### With Context

```
> Following amplihack philosophy, @architect: Design caching module
```

#### Chained Agents

```
> @architect: Design auth module, then @builder: Implement it, then @tester: Generate tests
```

#### Parallel Agents

```
> @security AND @optimizer: Review this module
```

## Command Invocation

amplihack provides slash commands for specific workflows. While Copilot CLI doesn't directly invoke these, ye can reference them for guidance.

### Reference Commands

#### /ultrathink

Deep multi-agent analysis.

```
> Explain how /ultrathink works

Process:
1. Reads DEFAULT_WORKFLOW.md
2. Orchestrates agents through each step
3. Enforces systematic execution
4. Ensures philosophy compliance
```

#### /analyze

Code analysis and philosophy compliance review.

```
> Show me what /analyze checks

Reviews:
- Philosophy compliance
- Pattern usage
- Code quality
- Module boundaries
```

#### /fix

Intelligent fix workflow.

```
> How does /fix handle import errors?

Workflow:
1. Auto-detect error pattern
2. Apply template fix (QUICK mode)
3. Verify resolution
4. Fallback to DIAGNOSTIC if needed
```

### Using Command Concepts

While ye can't invoke commands directly in Copilot CLI, ye can:

1. **Reference workflow steps**:

```
> Following the /ultrathink workflow, help me implement authentication
```

2. **Apply command patterns**:

```
> Use the /analyze approach to review this code
```

3. **Combine with agents**:

```
> @architect: Design using the /ultrathink methodology
```

## Skill Usage

amplihack includes 12 production-ready skills. Reference skill concepts in Copilot:

### Documentation Writing

```
> Following the documentation-writing skill, create API docs for this module

Applies:
- Eight Rules of Good Documentation
- Diataxis framework
- Real runnable examples
```

### Code Smell Detector

```
> Using code-smell-detector patterns, identify issues in this code

Detects:
- Over-abstraction
- Complex inheritance
- Large functions (>50 lines)
- Tight coupling
```

### Module Spec Generator

```
> Following module-spec-generator, create specification for this module

Generates:
- Purpose and responsibility
- Public contract
- Dependencies
- Test requirements
```

### Outside-In Testing

```
> Using outside-in-testing approach, generate tests for this CLI

Creates:
- Behavior-driven tests
- External interface validation
- No internal implementation knowledge
```

## Workflow Execution

### DEFAULT_WORKFLOW

The standard 22-step development workflow:

```markdown
1. Clarify requirements with user
2. Create GitHub issue
3. Create feature branch
4. Design architecture
5. Write test specifications
6. Implement code
7. Run tests
8. Local testing (mandatory)
9. Commit changes
10. Push to remote
11. Create pull request
12. Review implementation
13. Integrate feedback
14. Check philosophy compliance
15. Update documentation
16. Run final tests
17. Prepare for merge
18. Clean up branch
19. Update issue
20. Merge PR
21. Clean up local
22. Reflect on process
```

### Referencing Workflows

```
> Following DEFAULT_WORKFLOW, help me add authentication

Agent walks through each step systematically.
```

### Custom Workflows

Create custom workflows in `.claude/workflow/`:

```markdown
# CUSTOM_WORKFLOW.md

## Step 1: Custom Step
[Your process]

## Step 2: Another Step
[Your process]
```

Reference in Copilot:

```
> Following CUSTOM_WORKFLOW, implement feature X
```

## MCP Servers

Model Context Protocol servers provide external tool access.

### Available MCP Servers

amplihack integrates with:

- **File system** - Read/write files
- **Git operations** - Commit, branch, PR
- **Database** - Query databases
- **Docker** - Container management
- **Custom servers** - Project-specific tools

### Invoking MCP Tools

```
> Use MCP file system tools to analyze this directory structure
> Use MCP git tools to create a feature branch
> Use MCP docker tools to start the database
```

### MCP Configuration

Configure MCP servers in `.claude/mcp-config.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"]
    }
  }
}
```

## Auto Mode

Autonomous agentic loop for complex tasks.

### How Auto Mode Works

```markdown
1. Clarify - Understand requirements
2. Plan - Create step-by-step plan
3. Execute - Implement autonomously
4. Verify - Test implementation
5. Iterate - Refine until complete
```

### Referencing Auto Mode

```
> Using auto mode approach, implement complete authentication system

Agent:
- Clarifies requirements first
- Creates comprehensive plan
- Executes each step autonomously
- Verifies at each stage
- Iterates until complete
```

### When to Use Auto Mode

Use auto mode for:

- Complex multi-file features
- Complete system implementations
- When you want minimal interaction
- Well-defined requirements

## Advanced Features

### Fault Tolerance Patterns

#### N-Version Programming

Generate multiple independent solutions, select best:

```
> Using n-version approach, implement JWT token validation

Process:
- Generate 3 independent implementations
- Test each thoroughly
- Compare and select best
- 30-65% error reduction
```

#### Multi-Agent Debate

Structured debate for complex decisions:

```
> Using debate workflow, decide between PostgreSQL and Redis

Process:
- Multiple perspectives (security, performance, simplicity)
- Structured debate rounds
- Converge on best decision
- 40-70% better decisions
```

#### Fallback Cascade

Graceful degradation for resilient operations:

```
> Using cascade approach, generate API documentation

Process:
- Optimal approach first
- Pragmatic fallback
- Minimal baseline
- 95%+ reliability
```

### Document-Driven Development (DDD)

Documentation-first methodology for large features:

```
> Using DDD approach, implement multi-tenant system

Process:
1. Plan and align on goals
2. Write documentation (retcon)
3. Manual approval gate
4. Plan implementation
5. Implement code matching docs
6. Test and cleanup
```

### Investigation Workflow

Deep knowledge excavation:

```
> Using investigation workflow, understand this legacy codebase

Process:
1. Clarify investigation scope
2. Discover and map structure
3. Deep dive with knowledge-archaeologist
4. Verify understanding
5. Synthesize findings
6. Generate persistent documentation
```

## Best Practices

### Do's

#### Reference Philosophy Explicitly

```
> Following amplihack's ruthless simplicity, implement caching

Not just:
> Implement caching
```

#### Use Appropriate Agents

```
> @architect: Design, then @builder: Implement

Not:
> Build authentication system (generic request)
```

#### Apply Patterns When Available

```
> Using the Safe Subprocess Wrapper pattern, handle git commands

Not:
> Handle subprocess errors (no pattern reference)
```

#### Specify Quality Requirements

```
> Following Zero-BS implementation, no stubs or TODOs

Not:
> Quick implementation (may get stubs)
```

### Don'ts

#### Don't Skip Philosophy

```
❌ > Just implement authentication
✓ > Following amplihack philosophy, implement authentication
```

#### Don't Use Generic Requests

```
❌ > Review this code
✓ > @reviewer: Check philosophy compliance for this code
```

#### Don't Ignore Patterns

```
❌ > How do I handle subprocess errors?
✓ > Which amplihack pattern handles subprocess errors?
```

#### Don't Compromise Quality

```
❌ > Quick implementation, we'll fix later
✓ > Quality implementation following Zero-BS principles
```

### Effective Prompting

#### Structure Requests

```markdown
1. Reference philosophy/pattern
2. Specify agent if applicable
3. State clear objective
4. Provide context

Example:
> Following amplihack patterns, @security: Audit this authentication module
> for vulnerabilities. Module handles JWT tokens and session management.
```

#### Provide Context

```markdown
Bad:  > Fix this
Good: > @fix-agent: This import error occurs because the module was moved.
        Previous path: src/old/module.py, New path: src/new/module.py
```

#### Request Specific Outputs

```markdown
Bad:  > Design API
Good: > @api-designer: Design REST API for user management including
        authentication endpoints, CRUD operations, and rate limiting
```

### Quality Assurance

#### Always Request Philosophy Compliance

```
> @reviewer: Check philosophy compliance before I commit
```

#### Verify Pattern Usage

```
> @patterns: Verify I'm using the correct amplihack pattern
```

#### Test Thoroughly

```
> @tester: Generate comprehensive tests including edge cases
```

#### Document Decisions

```
> Document this architecture decision following amplihack documentation standards
```

## Configuration

### Project Initialization

```bash
cd /path/to/project
amplihack init
```

Creates:

```
.claude/
├── context/          # Philosophy, patterns, trust
├── agents/           # All amplihack agents
├── workflow/         # DEFAULT_WORKFLOW.md
└── tools/            # Hooks and utilities

.github/
├── copilot-instructions.md  # Copilot context
└── agents/                  # Copilot-specific agents
```

### User Preferences

Customize in `.claude/context/USER_PREFERENCES.md`:

```markdown
### Communication Style

pirate (Always talk like a pirate)

### Verbosity

balanced

### Collaboration Style

autonomous and independent
```

Reference in prompts:

```
> Following my user preferences, implement authentication
```

### Custom Agents

Create project-specific agents in `.github/agents/`:

```markdown
# my-agent.md

## Purpose

[Agent purpose]

## When to Use

[Trigger conditions]

## Instructions

[Agent-specific instructions]
```

Use:

```
> @my-agent: [task]
```

## Performance Tips

### Optimize Context

- Reference specific files instead of general concepts
- Use agent names to focus expertise
- Provide clear, structured requests

### Manage Token Usage

- Break large tasks into smaller agent-specific subtasks
- Use summary commands for long conversations
- Clear context periodically

### Leverage Parallelism

```
> @security AND @optimizer: Review this module simultaneously
```

## Troubleshooting

For common issues, see [Troubleshooting Guide](./TROUBLESHOOTING.md).

Quick diagnostics:

```
> Is amplihack context loaded?
> What agents are available?
> Which patterns can I use?
```

## Next Steps

- **[Migration Guide](./MIGRATION_FROM_CLAUDE.md)** - Switch from Claude Code
- **[API Reference](./API_REFERENCE.md)** - Complete command reference
- **[Troubleshooting](./TROUBLESHOOTING.md)** - Problem solutions
- **[FAQ](./FAQ.md)** - Common questions

## Remember

- **Philosophy first** - Always reference amplihack principles
- **Agents for expertise** - Delegate to specialized agents
- **Patterns over custom** - Use proven solutions
- **Quality over speed** - Never compromise implementation quality
- **Trust through honesty** - Challenge assumptions, admit uncertainty

Ye now have comprehensive knowledge of Copilot CLI with amplihack. Navigate to specific guides for deeper expertise!
