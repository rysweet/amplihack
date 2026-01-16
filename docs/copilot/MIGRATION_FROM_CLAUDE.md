# Migrating from Claude Code to Copilot CLI

Guide for switching from Claude Code to GitHub Copilot CLI while maintaining amplihack capabilities.

## Overview

amplihack was designed for Claude Code but works with GitHub Copilot CLI through:

- **Agent conversion** - Claude agents → Copilot agents
- **Context preservation** - Philosophy, patterns, trust principles
- **Workflow adaptation** - Process concepts without direct execution
- **Tool accessibility** - Python tools callable from any environment

## Why Migrate?

Reasons to use Copilot CLI instead of Claude Code:

| Factor              | Copilot CLI                 | Claude Code              |
| ------------------- | --------------------------- | ------------------------ |
| **Cost**            | GitHub Copilot subscription | Anthropic API usage      |
| **Integration**     | GitHub-native               | Third-party              |
| **Model Selection** | GitHub models               | Claude models            |
| **Tool Ecosystem**  | npm packages                | Custom MCP servers       |
| **Authentication**  | GitHub account              | Anthropic API key        |

Reasons to stay with Claude Code:

| Factor             | Claude Code                | Copilot CLI                  |
| ------------------ | -------------------------- | ---------------------------- |
| **Model Quality**  | Claude Opus/Sonnet         | GPT-4 variants               |
| **Workflow Exec**  | Direct command invocation  | Reference-based              |
| **Agent System**   | Native Task tool           | Converted agents             |
| **MCP Servers**    | Full MCP support           | Limited                      |
| **Skills**         | Direct skill invocation    | Reference-based              |
| **Customization**  | Full amplihack integration | Adapted capabilities         |

## Can I Use Both?

**Yes!** Use both environments:

- **Claude Code** for complex workflows, direct agent invocation
- **Copilot CLI** for quick tasks, GitHub integration, cost efficiency

Both access the same `.claude/` resources.

## Feature Parity Matrix

### Core Features

| Feature                 | Claude Code | Copilot CLI | Notes                        |
| ----------------------- | ----------- | ----------- | ---------------------------- |
| Philosophy Access       | ✓           | ✓           | Both read .claude/context/   |
| Pattern Library         | ✓           | ✓           | Both read PATTERNS.md        |
| Agent Definitions       | ✓           | ✓           | Converted for Copilot        |
| Trust Principles        | ✓           | ✓           | Both follow TRUST.md         |
| User Preferences        | ✓           | ✓           | Both read preferences        |

### Advanced Features

| Feature                 | Claude Code | Copilot CLI | Notes                            |
| ----------------------- | ----------- | ----------- | -------------------------------- |
| Workflow Execution      | ✓ Direct    | ~ Reference | Copilot references, doesn't exec |
| Slash Commands          | ✓ Native    | ~ Reference | Can reference command concepts   |
| Skill Invocation        | ✓ Native    | ~ Reference | Can reference skill patterns     |
| Task Tool               | ✓ Native    | ~ Converted | Agents converted to Copilot      |
| MCP Servers             | ✓ Full      | ~ Limited   | Some MCP tools available         |
| Auto Mode               | ✓ Native    | ~ Reference | Can follow auto mode process     |

### Tools and Scenarios

| Feature                 | Claude Code | Copilot CLI | Notes                        |
| ----------------------- | ----------- | ----------- | ---------------------------- |
| analyze-codebase        | ✓           | ✓           | Python tool, callable        |
| mcp-manager             | ✓           | ✓           | Python tool, callable        |
| Goal Agent Generator    | ✓           | ✓           | Python tool, callable        |
| Test Generation         | ✓           | ✓           | Both can generate tests      |

Legend:
- ✓ = Full support
- ~ = Partial/adapted support
- ✗ = Not supported

## Migration Steps

### Step 1: Install Copilot CLI

```bash
npm install -g @github/copilot
gh auth login
```

### Step 2: Verify amplihack Installation

```bash
# Check amplihack is installed
amplihack --version

# If not, install
pip install git+https://github.com/rysweet/amplihack
```

### Step 3: Initialize Project (if not already done)

```bash
cd /path/to/project
amplihack init
```

### Step 4: Convert Agents

Convert Claude agents to Copilot format:

```bash
# Automatic conversion
amplihack convert-agents

# Manual verification
ls .github/agents/
cat .github/agents/REGISTRY.json
```

This creates:

```
.github/agents/
├── core/
│   ├── architect.md
│   ├── builder.md
│   ├── reviewer.md
│   └── ...
├── specialized/
│   ├── security.md
│   ├── database.md
│   └── ...
└── REGISTRY.json
```

### Step 5: Verify Copilot Context

Launch Copilot CLI and verify context:

```bash
amplihack copilot
```

In session:

```
> What is the amplihack philosophy?
> List available agents
> Show me amplihack patterns
```

### Step 6: Test Agent Invocation

```
> @architect: Design a simple caching module
```

Verify the agent:
1. References amplihack philosophy
2. Follows brick pattern
3. Provides complete specification

### Step 7: Adapt Workflows

Claude Code workflows can't execute directly in Copilot. Adapt by referencing:

```
# Claude Code (direct execution)
/ultrathink Implement authentication

# Copilot CLI (reference-based)
> Following the ultrathink workflow from DEFAULT_WORKFLOW.md,
  help me implement authentication
```

## Pattern Translation

### Command Translation

| Claude Code Command        | Copilot CLI Equivalent                                   |
| -------------------------- | -------------------------------------------------------- |
| `/ultrathink [task]`       | `Following ultrathink workflow, [task]`                  |
| `/analyze [target]`        | `@reviewer: Analyze [target] for philosophy compliance`  |
| `/fix [pattern]`           | `@fix-agent: Fix [pattern] using QUICK mode`            |
| `/debate [question]`       | `Using debate workflow, [question]`                      |
| `/amplihack:auto [task]`   | `Using auto mode approach, [task]`                       |

### Agent Translation

Agents work similarly but with @ notation:

| Claude Code                  | Copilot CLI              |
| ---------------------------- | ------------------------ |
| `Task(subagent_type="architect", ...)` | `@architect: ...`        |
| `Task(subagent_type="builder", ...)`   | `@builder: ...`          |
| Multiple agents in parallel  | `@agent1 AND @agent2: ...` |

### Skill Translation

| Claude Code Skill        | Copilot CLI Equivalent                                    |
| ------------------------ | --------------------------------------------------------- |
| `Skill(documentation-writing)` | `Following documentation-writing skill guidelines, ...`   |
| `Skill(code-smell-detector)`   | `Using code-smell-detector patterns, identify issues...`  |
| `Skill(module-spec-generator)` | `Following module-spec-generator, create spec...`         |

### Workflow Translation

Reference workflow steps instead of executing:

```markdown
# Claude Code
/ultrathink executes DEFAULT_WORKFLOW.md automatically

# Copilot CLI
> Following DEFAULT_WORKFLOW.md:
  - Step 1: Clarify requirements
  - Step 2: Create GitHub issue
  - Step 3: Create feature branch
  [continue through all steps]
```

## Maintaining Dual Environment

### Shared Resources

Both environments share:

```
.claude/
├── context/          # Philosophy, patterns, trust
├── agents/           # Claude agent definitions
├── workflow/         # Workflow definitions
└── scenarios/        # Python tools

.github/
├── copilot-instructions.md  # Copilot context
└── agents/                  # Converted agents
```

### Environment-Specific

| Resource             | Claude Code    | Copilot CLI                    |
| -------------------- | -------------- | ------------------------------ |
| Agents               | `.claude/agents/` | `.github/agents/`              |
| Instructions         | `CLAUDE.md`    | `.github/copilot-instructions.md` |
| Hooks                | `.claude/tools/hooks/` | Custom hooks                   |

### Keeping Agents in Sync

When ye update Claude agents, regenerate Copilot agents:

```bash
# Update agent in .claude/agents/
vim .claude/agents/core/architect.md

# Regenerate Copilot agents
amplihack convert-agents --force

# Verify
git diff .github/agents/
```

### Version Control

Both directories should be in version control:

```bash
# .gitignore
# (keep both)
!.claude/
!.github/

# Commit both when updating
git add .claude/agents/ .github/agents/
git commit -m "Update agents for both environments"
```

## Workflow Adaptations

### DEFAULT_WORKFLOW.md

The workflow defines WHAT to do. Adapt HOW based on environment:

| Workflow Step               | Claude Code                 | Copilot CLI                        |
| --------------------------- | --------------------------- | ---------------------------------- |
| 1. Clarify requirements     | Prompt-writer agent         | `@prompt-writer: Clarify...`       |
| 2. Create GitHub issue      | Direct gh CLI               | `Use gh CLI: gh issue create`      |
| 3. Create feature branch    | Direct git commands         | `Use git: git checkout -b`         |
| 4. Design architecture      | Task(architect)             | `@architect: Design...`            |
| 5. Write test specs         | Task(tester)                | `@tester: Write test specs`        |
| 8. Local testing            | Direct pytest               | `Run pytest: pytest tests/`        |
| 9. Commit changes           | Direct git commit           | `Use git: git commit -m`           |
| 12. Review implementation   | Task(reviewer)              | `@reviewer: Review...`             |

### Document-Driven Development

DDD workflow adapts well:

```markdown
# Claude Code
/amplihack:ddd:prime
/amplihack:ddd:1-plan
/amplihack:ddd:2-docs
[continue phases]

# Copilot CLI
> Following DDD workflow:
  Phase 0: Prime context with DDD overview
  Phase 1: Plan and align on goals
  Phase 2: Write documentation (retcon)
  [continue phases manually]
```

### Auto Mode

Auto mode becomes guided mode in Copilot:

```markdown
# Claude Code
/amplihack:auto Implement authentication

# Copilot CLI
> Using auto mode approach:
  1. Clarify requirements
  2. Create comprehensive plan
  3. Execute implementation
  4. Verify at each stage
  5. Iterate until complete

  Let's start - what are the authentication requirements?
```

## Tool Usage

### Python Tools

All amplihack Python tools work in both environments:

```bash
# analyze-codebase
amplihack analyze ./src

# mcp-manager
amplihack mcp list

# goal-agent-generator
amplihack new "Create deployment automation agent"
```

Reference in Copilot:

```
> Run amplihack analyze ./src and explain results
> Use amplihack mcp to configure GitHub integration
```

### Shell Commands

Both can use shell commands:

```
> Run pytest tests/ and show results
> Execute git status
> Run make test
```

## Common Pitfalls

### Don't Assume Direct Execution

```markdown
❌ Copilot CLI: /ultrathink Implement auth
✓  Copilot CLI: Following ultrathink workflow, implement auth
```

### Don't Forget Agent Conversion

```markdown
❌ Use Claude agents directly
✓  Convert agents first: amplihack convert-agents
```

### Don't Ignore Philosophy Context

```markdown
❌ Generic request: Implement caching
✓  With context: Following amplihack philosophy, implement caching
```

### Don't Mix Command Syntax

```markdown
❌ Copilot: Task(subagent_type="architect")
✓  Copilot: @architect: Design module
```

## Performance Considerations

### Token Usage

| Aspect                | Claude Code      | Copilot CLI        |
| --------------------- | ---------------- | ------------------ |
| Context Window        | 200K tokens      | Varies by model    |
| Agent Overhead        | Native Task tool | Converted markdown |
| Workflow Execution    | Automated        | Manual steps       |
| Parallel Operations   | Built-in         | Sequential         |

### Cost

| Usage Pattern         | Claude Code (API)  | Copilot CLI (Subscription) |
| --------------------- | ------------------ | -------------------------- |
| Light (<10 hrs/mo)    | ~$10-50            | $10-20/mo                  |
| Medium (10-40 hrs/mo) | ~$50-200           | $10-20/mo                  |
| Heavy (>40 hrs/mo)    | ~$200-500+         | $10-20/mo                  |

Copilot CLI more cost-effective for heavy usage.

### Response Quality

| Aspect                  | Claude Code (Sonnet/Opus) | Copilot CLI (GPT-4)     |
| ----------------------- | ------------------------- | ----------------------- |
| Philosophy Understanding| Excellent                 | Good with context       |
| Code Generation         | Excellent                 | Good                    |
| Pattern Recognition     | Excellent                 | Good with guidance      |
| Complex Reasoning       | Excellent                 | Good                    |
| Long Context            | Excellent                 | Moderate                |

## Troubleshooting Migration

### Agents Not Found

```bash
# Verify agents converted
ls .github/agents/

# If missing, convert
amplihack convert-agents

# Check registry
cat .github/agents/REGISTRY.json
```

### Philosophy Not Referenced

```
# Verify copilot-instructions.md exists
cat .github/copilot-instructions.md

# If missing, regenerate
amplihack init --force
```

### Commands Don't Work

Remember: Commands are reference-only in Copilot CLI.

```markdown
❌ /ultrathink Implement feature
✓  Following ultrathink workflow, implement feature
```

### Agent Responses Generic

Provide explicit context:

```markdown
❌ @architect: Design auth module
✓  Following amplihack brick philosophy, @architect: Design auth module
   with clear public API and zero-BS implementation
```

## Getting Help

### Community Resources

- [GitHub Discussions](https://github.com/rysweet/amplihack/discussions)
- [Issue Tracker](https://github.com/rysweet/amplihack/issues)
- [Documentation](https://rysweet.github.io/amplihack/)

### Migration Support

- [Troubleshooting Guide](./TROUBLESHOOTING.md)
- [FAQ](./FAQ.md)
- [Complete User Guide](./USER_GUIDE.md)

### Debug Commands

```bash
# Verify installation
amplihack --version
copilot --version

# Check agents
amplihack convert-agents --dry-run

# Validate context
cat .github/copilot-instructions.md
```

## Conclusion

Migration from Claude Code to Copilot CLI maintains amplihack's core value:

- ✓ Philosophy and patterns accessible
- ✓ Agents available (converted format)
- ✓ Python tools fully functional
- ✓ Workflows reference-able
- ~ Direct execution becomes guided execution

Choose based on yer needs:

- **Complex workflows, direct execution** → Claude Code
- **GitHub integration, cost efficiency** → Copilot CLI
- **Best of both** → Use both environments

Both paths lead to philosophy-driven, quality code!
