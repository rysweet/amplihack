# CLAUDE.md

This file provides guidance to Claude Code when working with code in this
repository.

## Project Overview

**Microsoft Hackathon 2025 - Agentic Coding Framework**

We are building an advanced agentic coding framework that leverages AI agents to
accelerate software development through intelligent automation, code generation,
and collaborative problem-solving.

## Important Files to Import

When starting a session, import these files for context:

```
@.claude/context/PHILOSOPHY.md
@.claude/context/PROJECT.md
@.claude/context/PATTERNS.md
@.claude/context/TRUST.md
@.claude/context/USER_PREFERENCES.md
@DISCOVERIES.md
```

## Working Philosophy

### Critical Operating Principles

- **Always think through a plan**: For any non-trivial task, break it down and
  use TodoWrite tool to manage a todo list
- **The workflow is authoritative**: The 13-step workflow in
  `.claude/workflow/DEFAULT_WORKFLOW.md` defines the order of operations, git
  workflow, and CI/CD process (users can customize this file)
- **Use UltraThink by default**: For non-trivial tasks, start with `/ultrathink`
  which reads the workflow and orchestrates agents to execute it
- **Maximize agent usage**: Every workflow step should leverage specialized
  agents - delegate aggressively to agents in `.claude/agents/amplihack/*.md`
- **Ask for clarity**: If requirements are unclear, ask questions before
  proceeding
- **Document learnings**: Update DISCOVERIES.md with new insights
- **Session Logs**: All interactions MUST be logged in
  .claude/runtime/logs/<session_id> where <session_id> is a unique identifier
  for the session based on the timestamp.
- **Decision records**: All Agents MUST log their decisions and reasoning in
  .claude/runtime/logs/<session_id>/DECISIONS.md
- **When to record decisions**: Document significant architectural choices,
  trade-offs between approaches, or decisions that affect system design
- **Simple format**: What was decided | Why | Alternatives considered

### Decision Recording

**IMPORTANT**: Record significant decisions in session logs as: What was decided
| Why | Alternatives considered

### Agent Delegation Strategy

**GOLDEN RULE**: You are an orchestrator, not an implementer. ALWAYS delegate to
specialized agents when possible. **DEFAULT TO PARALLEL EXECUTION** unless
dependencies require sequential order.

#### When to Use Agents (ALWAYS IF POSSIBLE)

**Immediate Delegation Triggers:**

- **System Design**: Use `architect.md` for specifications and problem
  decomposition
- **Implementation**: Use `builder.md` for code generation from specs
- **Code Review**: Use `reviewer.md` for philosophy compliance checks
- **Testing**: Use `tester.md` for test generation and validation
- **API Design**: Use `api-designer.md` for contract definitions
- **Performance**: Use `optimizer.md` for bottleneck analysis
- **Security**: Use `security.md` for vulnerability assessment
- **Database**: Use `database.md` for schema and query optimization
- **Integration**: Use `integration.md` for external service connections
- **Cleanup**: Use `cleanup.md` for code simplification
- **Pattern Recognition**: Use `patterns.md` to identify reusable solutions
- **Analysis**: Use `analyzer.md` for deep code understanding
- **Ambiguity**: Use `ambiguity.md` when requirements are unclear

#### Parallel Execution Decision Engine

**AUTOMATIC PARALLEL TRIGGERS** - Always deploy parallel execution for:

**1. Multi-File Operations**

```
TRIGGER: Reading, analyzing, or editing multiple files
ACTION: Batch all file operations in single tool call
EXAMPLE: [Read file1.py, Read file2.py, Read file3.py]
```

**2. Multi-Agent Coordination**

```
TRIGGER: Multiple specialized perspectives needed
ACTION: Deploy all relevant agents simultaneously
EXAMPLE: [architect, security, database, api-designer] for new feature
```

**3. Independent Analysis Tasks**

```
TRIGGER: Multiple components requiring separate analysis
ACTION: Parallel analysis with different agents
EXAMPLE: [patterns analysis, security audit, performance review]
```

**4. Research and Information Gathering**

```
TRIGGER: Multiple data sources or perspectives needed
ACTION: Parallel research with specialized agents
EXAMPLE: [codebase analysis, requirement clarification, dependency check]
```

**5. Diagnostic Workflows**

```
TRIGGER: System state analysis from multiple angles
ACTION: Parallel diagnostic agents
EXAMPLE: [environment check, log analysis, pattern detection]
```

#### Parallel Execution Templates

**Template 1: Feature Development**

```
"I'll coordinate multiple agents for comprehensive feature development"
[Single message with parallel Task calls]:
- architect: Design system architecture and module boundaries
- security: Identify security requirements and threat vectors
- database: Design data schema and migration strategy
- api-designer: Define API contracts and integration points
- tester: Design test strategy and acceptance criteria
```

**Template 2: Code Analysis**

```
"I'll analyze this codebase from multiple perspectives"
[Single message with parallel analysis]:
- analyzer: Deep code structure and pattern analysis
- security: Security vulnerability assessment
- optimizer: Performance bottleneck identification
- patterns: Reusable pattern detection
- reviewer: Philosophy compliance check
```

**Template 3: Problem Diagnosis**

```
"I'll diagnose this issue comprehensively"
[Single message with parallel diagnosis]:
- analyzer: Root cause analysis
- environment: System and dependency analysis
- patterns: Similar issue pattern matching
- logs: Error and warning pattern analysis
```

#### Sequential Execution (Exception Cases)

**Only use sequential when:**

- **Hard Dependencies**: Output of A required as input for B
- **State Mutations**: Agent A changes state that B depends on
- **Progressive Context**: Each step builds knowledge for next
- **Resource Conflicts**: Agents would conflict on same resources

**Examples of Required Sequential:**

```
architect → builder → reviewer  (specification → implementation → review)
git operations with dependencies (checkout → modify → commit)
test-driven development (write test → implement → validate)
```

### Development Workflow Agents

**Two-Stage Diagnostic Workflow:**

#### Stage 1: Pre-Commit Issues (Before Push)

- **Pre-Commit Workflow**: Use `pre-commit-diagnostic.md` when pre-commit hooks
  fail locally. Handles formatting, linting, type checking, and ensures code is
  committable BEFORE pushing.
- **Trigger**: "Pre-commit failed", "Can't commit", "Hooks failing"

#### Stage 2: CI Issues (After Push)

- **CI Workflow**: Use `ci-diagnostic-workflow.md` after pushing when CI checks
  fail. Monitors CI status, diagnoses failures, fixes issues, and iterates until
  PR is mergeable (but never auto-merges).
- **Trigger**: "CI failing", "Fix CI", "Make PR mergeable"

```
Example - Pre-commit failure:
"My pre-commit hooks are failing"
→ Use pre-commit-diagnostic agent
→ Automatically fixes all issues
→ Ready to commit

Example - CI failure after push:
"CI is failing on my PR"
→ Use ci-diagnostic-workflow agent
→ Iterates until PR is mergeable
→ Never auto-merges without permission
```

#### Creating Custom Agents

For repeated specialized tasks:

1. Identify pattern after 2-3 similar requests
2. Create agent in `.claude/agents/amplihack/specialized/`
3. Define clear role and boundaries
4. Add to delegation triggers above

Remember: Your value is in orchestration and coordination, not in doing
everything yourself.

When faced with a new novel task, it is also OK to create a new specialized
agent to handle that task as an experiment. Use agents to manage context for
granularity of tasks (eg when going off to do something specific where context
from the whole conversation is not necessary, such as managing a git worktree or
cleaning some data).

### Workflow and UltraThink Integration

**The workflow defines WHAT to do, UltraThink orchestrates HOW to do it:**

```
Example - Any Non-Trivial Task:

User: "Add authentication to the API"

1. Invoke /ultrathink with the task
   → UltraThink reads DEFAULT_WORKFLOW.md
   → Follows all 13 steps in order
   → Orchestrates multiple agents at each step

2. Workflow provides the authoritative process:
   → Step order (1-13) must be followed
   → Git operations (branch, commit, push)
   → CI/CD integration points
   → Review and merge requirements

3. Agents execute the actual work:
   → prompt-writer clarifies requirements
   → architect designs the solution
   → builder implements the code
   → reviewer ensures quality
```

The workflow file is the single source of truth - edit it to change the process.

### Parallel Execution Engine

**PARALLEL BY DEFAULT**: Always execute operations in parallel unless
dependencies require sequential order.

#### Automatic Parallel Detection Rules

**RULE 1: File Operations**

```
IF: Multiple files mentioned OR file patterns detected
THEN: Batch all file operations in single tool call
EXAMPLE: "analyze these Python files" → [Read *.py files in parallel]
```

**RULE 2: Multi-Perspective Analysis**

```
IF: Task requires multiple viewpoints OR "comprehensive" mentioned
THEN: Deploy relevant agents in parallel
EXAMPLE: "review this code" → [security, patterns, optimizer, reviewer]
```

**RULE 3: Independent Components**

```
IF: Task involves separate modules OR multiple systems
THEN: Analyze each component in parallel
EXAMPLE: "check frontend and backend" → [frontend analysis, backend analysis]
```

**RULE 4: Information Gathering**

```
IF: Research phase OR multiple data sources needed
THEN: Parallel information collection
EXAMPLE: "understand this system" → [code analysis, docs review, pattern detection]
```

#### Execution Patterns

**Optimal (Parallel by Default):**

```
"I'll analyze these components comprehensively"
[Single message: analyzer(component1), security(component1), optimizer(component1),
                analyzer(component2), security(component2), optimizer(component2)]
```

**Sub-optimal (Sequential without justification):**

```
"Let me analyze the first component"
[analyzer(component1)]
"Now the second component"
[analyzer(component2)]
```

#### Parallel Coordination Protocols

**Agent Coordination Guidelines:**

- **Context Sharing**: Each agent receives full task context
- **Output Integration**: Orchestrator synthesizes parallel results
- **Conflict Resolution**: Sequential fallback for resource conflicts
- **Progress Tracking**: TodoWrite manages parallel task completion

**PARALLEL-READY Agents** (can work simultaneously):

- `analyzer`, `security`, `optimizer`, `patterns`, `reviewer`
- `architect`, `api-designer`, `database`, `tester`
- `integration`, `cleanup`, `ambiguity`

**SEQUENTIAL-REQUIRED Agents** (state dependencies):

- `builder` (after `architect`)
- `ci-diagnostic-workflow` (after push)
- `pre-commit-diagnostic` (during commit process)

## Development Principles

### Ruthless Simplicity

- Start with the simplest solution that works
- Add complexity only when justified
- Question every abstraction

### Modular Design (Bricks & Studs)

- **Brick** = Self-contained module with ONE responsibility
- **Stud** = Public contract others connect to
- **Regeneratable** = Can be rebuilt from specification

### Zero-BS Implementation

- No stubs or placeholders - no fake implementations or unimplemented functions
- No dead code - remove unused code
- Every function must work or not exist

## Project Structure

```
.claude/
├── context/          # Philosophy, patterns, project info
├── agents/           # Specialized AI agents
├── commands/         # Slash commands (/ultrathink, /analyze, /improve)
├── tools/            # Hooks and utilities
├── workflow/         # Default workflow definition
│   └── DEFAULT_WORKFLOW.md  # Customizable 13-step workflow
└── runtime/          # Logs, metrics, analysis

Specs/               # Module specifications
```

## Key Commands

### /ultrathink <task>

Default execution mode for non-trivial tasks. UltraThink:

- Reads the workflow from `.claude/workflow/DEFAULT_WORKFLOW.md`
- Follows all steps in the exact order defined
- Orchestrates multiple agents at each step for maximum effectiveness
- Adapts automatically when you customize the workflow file

### /analyze <path>

Comprehensive code review for philosophy compliance

### /improve [target]

Self-improvement and learning capture

## Available Tools

### GitHub Issue Creation

Create GitHub issues programmatically:

```python
from .claude.tools.github_issue import create_issue
result = create_issue(title="Bug report", body="Details here")
```

### CI Status Checker

Check GitHub Actions CI status:

```python
from .claude.tools.ci_status import check_ci_status
status = check_ci_status()  # Check current branch
status = check_ci_status(ref="123")  # Check PR #123
```

## Testing & Validation

After code changes:

1. Run tests if available
2. Check philosophy compliance
3. Verify module boundaries
4. Update DISCOVERIES.md with learnings

## Common Patterns

See `.claude/context/PATTERNS.md` for:

- Claude Code SDK integration
- Resilient batch processing
- File I/O with retries
- Async context management
- Module regeneration structure

## Self-Improvement

The system should continuously improve:

- Track patterns in `.claude/context/PATTERNS.md`
- Document discoveries in `DISCOVERIES.md`
- Update agent definitions as needed
- Create new agents for repeated tasks

## Success Metrics

We measure success by:

- Code simplicity and clarity
- Module independence
- Agent effectiveness
- Knowledge capture rate
- Development velocity

## User Preferences

### Simple Preference Integration

**Ruthlessly Simple Approach:**

1. **Session Start**: USER_PREFERENCES.md is automatically imported at session
   start
2. **Agent Usage**: When invoking agents, include preference context in prompts
   manually as needed
3. **No Complex Systems**: No hooks, validators, or injection frameworks needed

**Example Usage:**

```
"Design an API using pirate communication style"
→ Pass USER_PREFERENCES.md context to architect agent
```

**What We DON'T Do:**

- Complex preference injection hooks
- Automated validation systems
- Multi-file preference architectures
- Over-engineered preference frameworks

**Philosophy**: Simple prompting with preference context is sufficient. Complex
systems add unnecessary overhead for marginal benefit.

## Getting Help

- Review `.claude/context/PHILOSOPHY.md` for principles
- Check `.claude/agents/CATALOG.md` for agent capabilities
- Look in `.claude/context/PATTERNS.md` for solutions
- Update `DISCOVERIES.md` with new learnings

---

Remember: You are the orchestrator working with specialized agents. Delegate
liberally, execute in parallel, and continuously learn.

<!-- Updated for PR #41 -->
