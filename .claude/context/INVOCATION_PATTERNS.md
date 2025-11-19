# Invocation Patterns

Complete guide to how amplihack components invoke each other with real code examples.

## Pattern 1: Command → Workflow

Commands read workflow files to execute structured processes.

**Example**: `/ultrathink` reads DEFAULT_WORKFLOW.md

```yaml
# Frontmatter in ultrathink.md
invokes:
  - type: workflow
    path: .claude/workflow/DEFAULT_WORKFLOW.md
```

**Implementation**:
```markdown
1. Detect task type (investigation vs development)
2. Read workflow: .claude/workflow/DEFAULT_WORKFLOW.md (Read tool)
3. Create TodoWrite list with all steps
4. Execute each step with agent orchestration
```

## Pattern 2: Command → Command

Commands invoke other commands using SlashCommand tool.

**Example**: `/improve` invokes `/reflect`

```yaml
# Frontmatter in improve.md
invokes:
  - type: command
    name: /reflect
```

**Tool invocation**:
```xml
<invoke name="SlashCommand">
  <parameter name="command">/reflect "Analyze patterns"</parameter>
</invoke>
```

## Pattern 3: Command → Skill

Commands invoke skills using Skill tool.

**Example**: Using test-gap-analyzer

```xml
<invoke name="Skill">
  <parameter name="skill">test-gap-analyzer</parameter>
</invoke>
```

**Use case**: Token-efficient specialized capabilities like analysis or generation.

## Pattern 4: Command → Agent

Commands invoke agents using Task tool (subagent invocation).

**Example**: `/fix` invokes fix-agent

```yaml
# Frontmatter in fix.md
invokes:
  - type: subagent
    path: .claude/agents/amplihack/specialized/fix-agent.md
```

**Implementation**:
```markdown
delegate_to_fix_agent(mode="DIAGNOSTIC", context=full_context)
```

## Pattern 5: Skill → Command

Skills recommend commands for follow-up actions.

**Example**: test-gap-analyzer suggests /fix

```markdown
After gap identification:
"Run `/fix test` to address failures"
"Use `/ultrathink` for comprehensive test suite"
```

**Use case**: When skill analysis identifies work requiring command orchestration.

## Pattern 6: Skill → Skill

One skill invokes another for complementary analysis.

**Example**: code-smell-detector using test-gap-analyzer

```xml
<invoke name="Skill">
  <parameter name="skill">test-gap-analyzer</parameter>
</invoke>
```

**Use case**: When one skill's analysis benefits from another's specialized view.

## Pattern 7: Skill → Agent

Skills delegate implementation to specialized agents.

**Example**: test-gap-analyzer delegates to tester agent

```yaml
# From test-gap-analyzer SKILL.md
feeds_into:
  - CI Validation
  - tester agent (for implementation)
```

**Implementation**:
```markdown
After gap analysis, delegate test implementation to tester agent
```

## Pattern 8: Agent → Command

Agents recommend commands for orchestration needs.

**Example**: architect suggests /ultrathink

```markdown
# From architect.md
If Pre-commit is Missing:
Would you like me to:
1. Create pre-commit configuration?
2. Use /ultrathink for comprehensive setup?
```

**Use case**: When agent analysis reveals need for structured workflow execution.

## Pattern 9: Agent → Skill

Agents use skills for specialized capabilities.

**Example**: architect using mermaid-diagram-generator

```xml
<invoke name="Skill">
  <parameter name="skill">mermaid-diagram-generator</parameter>
</invoke>
```

**Use case**: Specialized work like diagramming, analysis, or documentation.

## Pattern 10: Agent → Agent

Agents invoke other agents in workflows (sequential or parallel).

**Sequential** (hard dependencies):
```markdown
# From DEFAULT_WORKFLOW.md
Step 1: prompt-writer agent (clarify)
Step 4: architect agent (design)
Step 5: builder agent (implement)
Step 7: reviewer agent (validate)
```

**Parallel** (independent):
```markdown
# From DEBATE_WORKFLOW.md
Security Perspective: security agent
Performance Perspective: optimizer agent
Simplicity Perspective: cleanup + reviewer agents
```

**Frontmatter declaration**:
```yaml
invokes:
  - type: subagent
    path: .claude/agents/amplihack/core/architect.md
  - type: subagent
    path: .claude/agents/amplihack/core/builder.md
```

## Pattern 11: Workflow Referencing

How components read and reference workflow files.

**Example**: Commands reading workflows

```markdown
# From ultrathink.md
1. Read workflow file using Read tool:
   - Investigation: .claude/workflow/INVESTIGATION_WORKFLOW.md
   - Development: .claude/workflow/DEFAULT_WORKFLOW.md
2. Parse workflow steps
3. Create TodoWrite task list
4. Execute each step systematically
```

**Workflow frontmatter**:
```yaml
---
name: DEFAULT_WORKFLOW
version: 1.0.0
steps: 15
phases: [requirements, design, implementation, testing]
---
```

## Invocation Mechanisms Summary

| Pattern | Mechanism | Tool | Example |
|---------|-----------|------|---------|
| Command → Workflow | Read + Execute | Read | /ultrathink reads DEFAULT_WORKFLOW |
| Command → Command | Direct | SlashCommand | /improve → /reflect |
| Command → Skill | Direct | Skill | Command → test-gap-analyzer |
| Command → Agent | Delegate | Task/Subagent | /fix → fix-agent |
| Skill → Command | Recommend | SlashCommand | test-gap-analyzer → /fix |
| Skill → Skill | Direct | Skill | code-smell-detector → test-gap-analyzer |
| Skill → Agent | Delegate | Task/Subagent | test-gap-analyzer → tester |
| Agent → Command | Recommend | SlashCommand | architect → /ultrathink |
| Agent → Skill | Direct | Skill | architect → mermaid-diagram-generator |
| Agent → Agent | Sequential/Parallel | Task/Subagent | architect → builder → reviewer |
| Workflow Reference | Read + Parse | Read | Commands read workflow files |

## Key Principles

### Sequential vs Parallel

**Sequential** (hard dependencies):
- architect → builder → reviewer (each needs previous output)
- pre-commit → ci-diagnostic (order matters)

**Parallel** (independent):
- [security, optimizer, reviewer] (can run simultaneously)
- [analyzer, patterns, environment] (independent analyses)

### Context Passing

All invocations pass:
- Explicit user requirements (HIGHEST PRIORITY - never optimized away)
- Current state and constraints
- Success criteria
- Philosophy compliance requirements

### Frontmatter Declaration

Components declare invocations in frontmatter for static analysis:

```yaml
invokes:
  - type: workflow
    path: .claude/workflow/DEFAULT_WORKFLOW.md
  - type: subagent
    path: .claude/agents/amplihack/specialized/fix-agent.md
  - type: command
    name: /reflect
```

This enables:
- Dependency graph generation
- Automated workflow validation
- Clear component relationships
- Circular dependency detection

## Tool Syntax Reference

**SlashCommand**: `<invoke name="SlashCommand"><parameter name="command">/cmd args</parameter></invoke>`

**Skill**: `<invoke name="Skill"><parameter name="skill">skill-name</parameter></invoke>`

**Read**: `<invoke name="Read"><parameter name="file_path">/path/to/file</parameter></invoke>`

**Task/Subagent**: Frontmatter declaration + contextual invocation in workflow steps

**TodoWrite**: `<invoke name="TodoWrite"><parameter name="todos">[...]</parameter></invoke>`
