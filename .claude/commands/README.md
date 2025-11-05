# Slash Commands Reference

This directory contains all available slash commands for the Amplihack Agentic Coding Framework. Slash commands are powerful entry points that orchestrate agents, workflows, and specialized tasks.

## Table of Contents

- [Overview](#overview)
- [Command Categories](#command-categories)
- [Complete Command Catalog](#complete-command-catalog)
- [How Commands Work](#how-commands-work)
- [Creating Custom Commands](#creating-custom-commands)
- [Command Structure](#command-structure)
- [Integration Points](#integration-points)

---

## Overview

Slash commands provide a consistent interface for executing complex workflows and coordinating multiple agents. They follow these principles:

- **Declarative**: Commands describe what you want, not how to do it
- **Orchestration**: Commands coordinate multiple agents and tools
- **Workflow-driven**: Commands follow defined workflows for consistency
- **Context-aware**: Commands integrate with project philosophy and patterns

### Quick Start

```bash
# Core workflow commands
/amplihack:ultrathink <task>           # Deep multi-agent analysis for complex tasks
/amplihack:analyze <path>              # Comprehensive code analysis
/amplihack:fix [pattern] [scope]       # Intelligent fix workflow

# Document-Driven Development
/amplihack:ddd:1-plan <feature>        # Plan a feature
/amplihack:ddd:2-docs                  # Update documentation
/amplihack:ddd:3-code-plan             # Plan code implementation
/amplihack:ddd:4-code                  # Implement and verify
/amplihack:ddd:5-finish                # Cleanup and finalize

# Fault tolerance patterns
/amplihack:n-version <task>            # N-version programming for critical code
/amplihack:debate <question>           # Multi-agent debate for decisions
/amplihack:cascade <task>              # Fallback cascade for resilience

# Utility commands
/amplihack:customize set <pref> <val>  # Manage user preferences
/amplihack:reflect [session_id]        # Analyze session for improvements
```

---

## Command Categories

### Core Workflow Commands

High-level orchestration commands for common development tasks.

| Command | Purpose | Typical Use Case |
|---------|---------|------------------|
| `/amplihack:ultrathink` | Deep multi-agent analysis | Complex features, unclear requirements |
| `/amplihack:analyze` | Philosophy compliance review | Code quality checks, architecture review |
| `/amplihack:fix` | Intelligent fix workflow | Bug fixes, CI failures, import issues |
| `/amplihack:improve` | Self-improvement with validation | Enhancing agents, patterns, workflows |

### Document-Driven Development (DDD)

Systematic methodology where documentation is the specification.

| Command | Phase | Purpose |
|---------|-------|---------|
| `/amplihack:ddd:0-help` | Utility | Complete DDD guide and help |
| `/amplihack:ddd:prime` | Utility | Load comprehensive DDD context |
| `/amplihack:ddd:status` | Utility | Check current progress |
| `/amplihack:ddd:1-plan` | Phase 0 | Planning and design |
| `/amplihack:ddd:2-docs` | Phase 1 | Update all non-code files |
| `/amplihack:ddd:3-code-plan` | Phase 3 | Plan code implementation |
| `/amplihack:ddd:4-code` | Phase 4 | Implement and verify code |
| `/amplihack:ddd:5-finish` | Phase 5 | Cleanup and finalize |

**When to use DDD**: New features requiring 10+ files, system redesigns, complex integrations, high-stakes user-facing features.

### Fault Tolerance Patterns

Advanced patterns for critical operations requiring consensus or graceful degradation.

| Command | Pattern | Cost | Benefit | Best For |
|---------|---------|------|---------|----------|
| `/amplihack:n-version` | N-version programming | 3-4x time | 30-65% error reduction | Security code, core algorithms |
| `/amplihack:debate` | Multi-agent debate | 2-3x time | 40-70% better decisions | Architectural trade-offs |
| `/amplihack:cascade` | Fallback cascade | 1.1-2x time | 95%+ reliability | External APIs, code generation |

### Knowledge & Learning

Commands for building knowledge and improving through reflection.

| Command | Purpose | Use When |
|---------|---------|----------|
| `/amplihack:knowledge-builder` | Build comprehensive knowledge base | Researching new topics (3 levels deep) |
| `/amplihack:socratic` | Generate probing Socratic questions | Challenging claims, exploring assumptions |
| `/amplihack:reflect` | Session analysis and improvement | After sessions, enable automatic learning |
| `/amplihack:expert-panel` | Multi-expert review with voting | Byzantine-robust decision-making |

### Development Utilities

Productivity and workflow management tools.

| Command | Purpose |
|---------|---------|
| `/amplihack:customize` | Manage user preferences and workflows |
| `/amplihack:auto` | Autonomous multi-turn agentic loop |
| `/amplihack:lock` | Enable continuous work mode |
| `/amplihack:unlock` | Disable continuous work mode |
| `/amplihack:transcripts` | Conversation context management |
| `/amplihack:modular-build` | Build self-contained modules |

### Integration & Security

Commands for system integration and security management.

| Command | Purpose |
|---------|---------|
| `/amplihack:install` | Install amplihack tools |
| `/amplihack:uninstall` | Uninstall amplihack tools |
| `/amplihack:xpia` | XPIA security system management |
| `/amplihack:reflection` | Manage session reflection system |

---

## Complete Command Catalog

### 29 Available Commands

#### Amplihack Core Commands (20)

1. **`/amplihack:ultrathink <task>`**
   - Deep multi-agent analysis following DEFAULT_WORKFLOW.md
   - Orchestrates 13-step workflow with specialized agents
   - Default execution mode for non-trivial tasks

2. **`/amplihack:analyze <path>`**
   - Comprehensive code analysis and philosophy compliance
   - Reviews simplicity, modularity, Zero-BS compliance
   - Generates detailed report with action items

3. **`/amplihack:fix [pattern] [scope]`**
   - Intelligent fix workflow with pattern recognition
   - Auto-detects: import, ci, test, config, quality, logic
   - Modes: quick (<5 min), diagnostic (root cause), comprehensive (full workflow)

4. **`/amplihack:improve [target]`**
   - Self-improvement with simplicity validation
   - Targets: self, agents, patterns, <path>
   - Uses improvement-workflow agent with progressive review

5. **`/amplihack:debate <question>`**
   - Multi-agent debate for complex decisions
   - 3 perspectives (security, performance, simplicity)
   - 40-70% better decision quality

6. **`/amplihack:n-version <task>`**
   - N-version programming for critical implementations
   - Generates 3+ independent solutions
   - 30-65% error reduction for security/core algorithms

7. **`/amplihack:cascade <task>`**
   - Fallback cascade for resilient operations
   - Graceful degradation: optimal → pragmatic → minimal
   - 95%+ reliability vs 70-80% single approach

8. **`/amplihack:expert-panel <task>`**
   - Expert panel review with voting mechanism
   - Multiple experts cast APPROVE/REJECT/ABSTAIN votes
   - Byzantine-robust decision-making

9. **`/amplihack:socratic <claim>`**
   - Generate Socratic questions using Three-Dimensional Attack
   - Challenges claims with empirical, computational, formal questions
   - Quality threshold: ≥7.5/10 effectiveness

10. **`/amplihack:knowledge-builder <topic>`**
    - Build comprehensive knowledge base (3 levels deep)
    - Generates ~270 questions with web-researched answers
    - Outputs: Knowledge.md, Triplets.md, KeyInfo.md, Sources.md

11. **`/amplihack:reflect [session_id]`**
    - AI-powered session analysis and improvement
    - Creates GitHub issues for high-priority patterns
    - Delegates to UltraThink for PR creation

12. **`/amplihack:reflection <action>`**
    - Manage session reflection system
    - Actions: enable, disable, status, clear-semaphore
    - Controls automatic post-session analysis

13. **`/amplihack:customize <action> [args]`**
    - Manage user preferences and customizations
    - Actions: set, show, reset, learn, list-workflows, set-workflow
    - Modifies USER_PREFERENCES.md directly

14. **`/amplihack:auto [--max-turns <n>] <prompt>`**
    - Autonomous multi-turn agentic loop
    - Workflow: clarify → plan → execute → evaluate
    - Continues until complete or max iterations

15. **`/amplihack:lock`**
    - Enable continuous work mode
    - Blocks stop attempts until unlocked
    - Looks for additional work to execute in parallel

16. **`/amplihack:unlock`**
    - Disable continuous work mode
    - Returns to normal stop behavior

17. **`/amplihack:transcripts [action] [session_id]`**
    - Conversation transcript management
    - Actions: list, restore, search
    - "Never lose context again" approach

18. **`/amplihack:modular-build [mode] [target]`**
    - Build self-contained modules
    - Pipeline: Contract→Spec→Plan→Generate→Review
    - Modes: auto, assist, dry-run

19. **`/amplihack:xpia [subcommand]`**
    - XPIA (Cross-Platform Injection Attack) security management
    - Subcommands: health, scan, remediate
    - Monitors security system health

20. **`/amplihack:install`**
    - Install amplihack tools
    - Runs `.claude/tools/amplihack/install.sh`

21. **`/amplihack:uninstall`**
    - Uninstall amplihack tools
    - Runs `.claude/tools/amplihack/uninstall.sh`

#### Document-Driven Development Commands (7)

22. **`/amplihack:ddd:0-help`**
    - Complete DDD guide and help
    - Loads overview, tips, pitfalls, FAQ
    - Reference for all DDD phases

23. **`/amplihack:ddd:prime`**
    - Load complete DDD context
    - Comprehensive methodology documentation
    - Use at session start for full understanding

24. **`/amplihack:ddd:status`**
    - Check current DDD progress
    - Shows phase, artifacts, next steps
    - Useful for resuming after breaks

25. **`/amplihack:ddd:1-plan [feature]`**
    - Phase 0: Planning and design
    - Creates comprehensive implementation plan
    - Output: `ai_working/ddd/plan.md`

26. **`/amplihack:ddd:2-docs [instructions]`**
    - Phase 1: Update all non-code files
    - Retcon writing: docs as if feature exists
    - Requires manual commit after approval

27. **`/amplihack:ddd:3-code-plan [instructions]`**
    - Phase 3: Plan code implementation
    - Assesses current code vs new docs
    - Requires user approval to proceed

28. **`/amplihack:ddd:4-code [feedback]`**
    - Phase 4: Implement and verify code
    - Writes code matching docs exactly
    - Iterative with user feedback

29. **`/amplihack:ddd:5-finish [instructions]`**
    - Phase 5: Cleanup and finalize
    - Removes temporary files, final verification
    - Explicit authorization for git operations

#### Python Command Scripts (2)

**`/builders`** (builders.py)
- Transcript and codex builders management
- Microsoft Amplifier-style session documentation
- Knowledge extraction from conversations

**`/transcripts`** (transcripts.py)
- Restore conversation context from transcripts
- List, search, and restore sessions
- Context preservation and retrieval

---

## How Commands Work

### Command Anatomy

```markdown
---
description: Brief description shown in command list
argument-hint: <required> [optional] parameters
allowed-tools: Tool1, Tool2, Bash(git:*)
---

# Command Title

## Input Validation
@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage
/command <args>

## Purpose
What this command does...

## Process
Step-by-step execution...
```

### Command Execution Flow

1. **Invocation**: User types `/amplihack:command <args>`
2. **Expansion**: Claude Code loads the command file
3. **Context Loading**: Command imports required context files (@references)
4. **Validation**: Input validation against allowed patterns
5. **Execution**: Command logic orchestrates agents/tools
6. **Output**: Results returned to user with next steps

### Context Loading with @references

Commands can import context files:

```markdown
@.claude/context/PHILOSOPHY.md          # Philosophy and principles
@.claude/workflow/DEFAULT_WORKFLOW.md   # Workflow definition
@docs/document_driven_development/overview.md  # DDD docs
@ai_working/ddd/plan.md                 # Working artifacts
```

### Agent Orchestration

Commands coordinate agents via Task tool:

```markdown
Task("architect", {
  "task": "Design authentication system",
  "context": "Following IMPLEMENTATION_PHILOSOPHY"
})

Task("builder", {
  "task": "Implement design from architect",
  "spec": architect_output
})
```

---

## Creating Custom Commands

### File Location

```
.claude/commands/
├── amplihack/           # Amplihack-specific commands
│   └── my-command.md    # Your custom command
├── ddd/                 # DDD workflow commands
│   └── custom-phase.md  # Custom DDD phase
└── my-category/         # Your custom category
    └── command.md       # Command file
```

### Command Template

```markdown
---
description: One-line description for command list
argument-hint: <required_arg> [optional_arg]
allowed-tools: Read, Write, Edit, Bash(*), Task
---

# Your Command Name

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/your-command <required_arg> [optional_arg]`

## Purpose

Clear explanation of what this command does and when to use it.

## Parameters

- **required_arg**: Description of required parameter
- **optional_arg**: Description of optional parameter (default: value)

## Process

### Step 1: Validate Input

Explain validation logic...

### Step 2: Execute Task

Describe execution steps...

### Step 3: Report Results

What output is provided...

## Example Usage

```bash
/your-command example_value
/your-command example_value optional_value
```

## When to Use

- Use case 1: Description
- Use case 2: Description
- Use case 3: Description

## Integration

- **With UltraThink**: How this integrates with workflow
- **With Agents**: Which agents this coordinates
- **With Other Commands**: Related commands

## Success Metrics

- Metric 1: Target value
- Metric 2: Target value

## Related Commands

- `/related-command` - Brief description
- `/another-command` - Brief description

---

**Version**: 1.0
**Created**: YYYY-MM-DD
**Category**: your-category
```

### Best Practices

1. **Clear Purpose**: One command, one job
2. **Progressive Complexity**: Start simple, add complexity only when justified
3. **Agent Delegation**: Orchestrate, don't implement
4. **Philosophy Alignment**: Follow ruthless simplicity and modular design
5. **Context References**: Use @references for required context
6. **Input Validation**: Always validate inputs with AGENT_INPUT_VALIDATION.md
7. **TodoWrite Integration**: Use TodoWrite for progress tracking
8. **Documentation**: Complete examples and use cases

### Command Development Workflow

1. **Identify Pattern**: Notice repeated manual workflows (2-3 occurrences)
2. **Draft Command**: Create command file following template
3. **Test Locally**: Use command in real scenarios
4. **Iterate**: Refine based on actual usage
5. **Document**: Add examples, edge cases, integration points
6. **Share**: Contribute back if generally useful

---

## Command Structure

### Frontmatter (YAML)

```yaml
---
description: Command description for listings
argument-hint: <arg1> [arg2]
allowed-tools: Tool1, Tool2, Bash(allowed:patterns)
---
```

- **description**: Short description shown in command lists
- **argument-hint**: Parameter format for help text
- **allowed-tools**: Constrain which tools command can use

### Sections

**Standard sections** (recommended order):

1. **Input Validation**: Reference to AGENT_INPUT_VALIDATION.md
2. **Usage**: Command syntax with examples
3. **Purpose**: What and why
4. **Parameters**: Detailed parameter descriptions
5. **Process**: Step-by-step execution flow
6. **Examples**: Real usage examples
7. **When to Use**: Clear use cases
8. **Integration**: How command relates to system
9. **Success Metrics**: Measurable outcomes
10. **Related Commands**: Connected functionality

### Python Command Scripts

For complex commands requiring code execution:

```python
#!/usr/bin/env python3
"""
/command-name - Brief description
Implements specific functionality with full Python power.
"""

import sys
from pathlib import Path

# Framework path resolution
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from amplihack.utils.paths import FrameworkPathResolver

def main():
    """Main command logic."""
    # Your implementation here
    pass

if __name__ == "__main__":
    main()
```

---

## Integration Points

### With Agents

Commands orchestrate agents from `.claude/agents/amplihack/`:

```markdown
# In command file
Task("zen-architect", {
  "task": "Design feature following IMPLEMENTATION_PHILOSOPHY",
  "constraints": "Max 3 components, ruthless simplicity"
})
```

### With Workflows

Commands follow workflows from `.claude/workflow/`:

```markdown
# Read workflow for orchestration
@.claude/workflow/DEFAULT_WORKFLOW.md

# Execute steps with TodoWrite tracking
- [ ] Step 1: Requirement Analysis
- [ ] Step 2: Design Phase
- [ ] Step 3: Implementation
...
```

### With User Preferences

Commands respect user preferences from `.claude/context/USER_PREFERENCES.md`:

```markdown
# Priority hierarchy (highest to lowest):
1. Explicit user requirements (NEVER override)
2. USER_PREFERENCES.md (MANDATORY)
3. Project philosophy (Strong guidance)
4. Default behaviors (Lowest priority)
```

### With Fault Tolerance Patterns

Commands can invoke fault tolerance:

```bash
/amplihack:ultrathink          # Standard workflow
/amplihack:n-version           # Critical code (3-4x cost)
/amplihack:debate              # Complex decisions (2-3x cost)
/amplihack:cascade             # Resilient operations (1.1-2x cost)
```

### With Session Reflection

Commands integrate with learning:

```markdown
# Automatic reflection after sessions
/amplihack:reflect enable

# Manual reflection on specific session
/amplihack:reflect session_20251105_143022
```

---

## Command Categories by Use Case

### Starting a New Project

```bash
/amplihack:customize set-workflow DEFAULT_WORKFLOW
/amplihack:customize set priority_type features
/amplihack:ddd:prime
```

### Developing a Feature

```bash
/amplihack:ddd:1-plan "Add user authentication"
/amplihack:ddd:2-docs
# Review and commit docs
/amplihack:ddd:3-code-plan
/amplihack:ddd:4-code
/amplihack:ddd:5-finish
```

### Fixing Bugs

```bash
/amplihack:fix                 # Auto-detect pattern
/amplihack:fix test            # Test-specific fixes
/amplihack:fix ci diagnostic   # Deep CI analysis
```

### Code Review

```bash
/amplihack:analyze src/module/
/amplihack:expert-panel "Review authentication implementation"
```

### Making Architectural Decisions

```bash
/amplihack:debate "Should we use PostgreSQL or Redis for caching?"
/amplihack:socratic "Microservices are just distributed objects"
```

### Learning & Research

```bash
/amplihack:knowledge-builder "Quantum computing implications for cryptography"
/amplihack:socratic "Static typing is just documentation"
```

### Session Management

```bash
/amplihack:transcripts list    # View past sessions
/amplihack:transcripts restore session_id  # Restore context
/amplihack:reflect             # Analyze last session
```

---

## Command Development Philosophy

Commands follow Amplihack's core principles:

### Ruthless Simplicity

- Start with simplest solution
- Add complexity only when justified
- Question every abstraction
- Clear over clever

### Modular Design (Bricks & Studs)

- **Brick**: Self-contained command with ONE responsibility
- **Stud**: Clear interface (parameters, output)
- **Regeneratable**: Can be rebuilt from specification

### Zero-BS Implementation

- No stubs or placeholders
- No dead code
- Every command must work or not exist

### Agent Orchestration First

- Commands orchestrate, don't implement
- Delegate to specialized agents
- Parallel execution by default
- Sequential only when dependencies exist

---

## Success Metrics

Track command effectiveness:

- **Usage Frequency**: How often command is invoked
- **Success Rate**: % of successful completions
- **Time to Solution**: Average execution time
- **User Satisfaction**: Quality of results

**Example metrics** (from /fix command):

- Fix Success Rate: % of issues resolved completely
- Pattern Recognition Accuracy: Correct pattern identification rate
- Mode Selection Accuracy: Optimal mode selection rate
- Escalation Patterns: When quick fixes escalate to diagnostic/comprehensive

---

## Additional Resources

- **Agent Catalog**: `.claude/agents/CATALOG.md`
- **Workflow Definitions**: `.claude/workflow/`
- **Pattern Library**: `.claude/context/PATTERNS.md`
- **Philosophy Guide**: `.claude/context/PHILOSOPHY.md`
- **Project Overview**: `CLAUDE.md`
- **DDD Documentation**: `docs/document_driven_development/`

---

## Getting Help

### For Specific Commands

```bash
/amplihack:command --help      # Command-specific help
/amplihack:ddd:0-help          # Complete DDD guide
```

### For System Help

- Review `CLAUDE.md` for complete project overview
- Check `.claude/context/PHILOSOPHY.md` for principles
- Look in `.claude/agents/CATALOG.md` for agent capabilities
- Explore `.claude/context/PATTERNS.md` for solutions

### For Development Help

- Study existing commands in this directory
- Follow command template above
- Test with real scenarios before sharing
- Document examples and edge cases

---

**Last Updated**: 2025-11-05
**Total Commands**: 29 (21 amplihack, 7 DDD, 1 builders, 1 transcripts)
**Version**: 1.0.0
