---
name: github-copilot-cli-expert
version: 1.0.0
description: Expert knowledge of GitHub Copilot CLI integration with amplihack framework
category: integration
tags: [github-copilot, cli, integration, documentation]
invocation: auto-detect OR explicit Skill() call
auto_triggers:
  - "github copilot"
  - "gh copilot"
  - "copilot cli"
  - "copilot integration"
  - "how do I use copilot with amplihack"
dependencies: []
related_skills:
  - mcp-manager
  - documentation-writing
  - agent-sdk
philosophy_alignment:
  - Ruthless Simplicity
  - Single Source of Truth
  - Zero-BS Implementation
---

# GitHub Copilot CLI Expert

**Expert knowledge of GitHub Copilot CLI integration with amplihack framework.**

## Purpose

This skill provides comprehensive guidance on:
1. Using GitHub Copilot CLI with amplihack
2. Referencing amplihack agents, skills, and patterns
3. MCP server configuration for Copilot
4. Hook integration for Copilot workflows
5. Command conversion and usage patterns
6. Troubleshooting Copilot CLI integration issues

## When to Use

**Auto-triggers** when user mentions:
- "github copilot"
- "gh copilot"
- "copilot cli"
- "copilot integration"
- "how do I use copilot with amplihack"

**Explicitly invoke** via:
```python
Skill(skill="github-copilot-cli-expert")
```

## What This Skill Knows

### 1. Integration Architecture

- **Symlink Architecture**: `.github/` symlinks to `~/.amplihack/.claude/` (source of truth)
- **Hook System**: Bash wrappers calling Python implementations
- **Command Conversion**: Claude Code commands → Copilot-friendly docs
- **MCP Servers**: Filesystem, git, amplihack-specific servers
- **Skills Access**: All 70+ skills available via symlinks

### 2. Usage Patterns

#### Basic Copilot Commands
```bash
# Get suggestions
gh copilot suggest "create a Python function"

# Explain code
gh copilot explain path/to/file.py

# Get command suggestions
gh copilot command "list git branches"
```

#### amplihack-Specific Usage
```bash
# Reference philosophy
gh copilot explain .github/copilot-instructions.md

# Use agents
gh copilot suggest -a .github/agents/amplihack/core/architect.md \
  "design authentication system"

# Reference skills
gh copilot suggest --context .github/agents/skills/code-smell-detector/ \
  "review this code for anti-patterns"

# Reference patterns
gh copilot suggest --context .claude/context/PATTERNS.md \
  "implement safe subprocess wrapper"
```

### 3. Available Resources

#### Agents (Symlinked)
- **Core Agents**: architect, builder, reviewer, tester, optimizer, api-designer
- **Specialized Agents**: 40+ specialized agents (analyzer, cleanup, fix-agent, etc.)
- **Location**: `.github/agents/amplihack/` → `../../.claude/agents/amplihack/`

#### Skills (Symlinked)
- **70+ Skills**: All amplihack skills available
- **Categories**: Development, workflow, domain experts, collaboration, utility
- **Location**: `.github/agents/skills/[skill-name]` → `../../../.claude/skills/[skill-name]`

#### Commands (Converted)
- **24+ Commands**: Converted from Claude Code slash commands
- **Location**: `.github/commands/`
- **Index**: `.github/commands/README.md`

#### MCP Servers
- **amplihack-agents**: Agent invocation server
- **amplihack-workflows**: Workflow orchestration server
- **amplihack-hooks**: Hook triggering server
- **Configuration**: `.github/mcp-servers.json`

### 4. Common Workflows

#### Feature Development with Copilot
```bash
# 1. Understand requirements with architect
gh copilot suggest -a .github/agents/amplihack/core/architect.md \
  "design user authentication feature"

# 2. Reference patterns
gh copilot explain .claude/context/PATTERNS.md

# 3. Implement with builder guidance
gh copilot suggest -a .github/agents/amplihack/core/builder.md \
  --context .claude/context/PATTERNS.md \
  "implement JWT authentication"

# 4. Review for philosophy compliance
gh copilot explain --review src/auth/ \
  --context .claude/context/PHILOSOPHY.md \
  --context .github/agents/amplihack/core/reviewer.md
```

#### Multi-Agent Consultation
```bash
# Consult multiple agents simultaneously
gh copilot suggest \
  -a .github/agents/amplihack/core/architect.md \
  -a .github/agents/amplihack/specialized/security.md \
  -a .github/agents/amplihack/specialized/database.md \
  "design secure user database"
```

### 5. Troubleshooting

#### Symlinks Not Working
```bash
# Verify symlinks
ls -la .github/agents/amplihack
ls -la .github/agents/skills/

# Recreate if needed (see COPILOT_CLI.md for instructions)
```

#### Copilot Not Finding Agents
```bash
# Verify agents are accessible
gh copilot explain .github/agents/README.md

# Check symlink validity
file .github/agents/amplihack
```

#### MCP Servers Not Starting
```bash
# Test server manually
npx -y @modelcontextprotocol/server-filesystem $(pwd)

# Check configuration
cat .github/mcp-servers.json
```

## Integration Details

### Directory Structure
```
.github/
├── agents/
│   ├── amplihack/ -> ../../.claude/agents/amplihack/  (symlink)
│   ├── skills/ -> ../../.claude/skills/               (symlinks)
│   ├── README.md
│   └── REGISTRY.json
├── commands/                    # Converted commands
│   ├── [command-name].md
│   └── README.md
├── copilot-instructions.md      # Base instructions
├── hooks/                       # Bash wrappers
│   ├── pre-commit
│   ├── session-start
│   ├── session-stop
│   ├── pre-tool-use
│   ├── post-tool-use
│   └── user-prompt-submit
└── mcp-servers.json             # MCP configuration
```

### Philosophy Alignment

#### Ruthless Simplicity
- **Single source of truth**: `~/.amplihack/.claude/` is source
- **Symlinks not duplication**: No file copying
- **Bash wrappers**: Simple, testable
- **No complex sync**: Convert commands once

#### Zero-BS Implementation
- **All hooks work**: No stubs or placeholders
- **All agents functional**: Real implementations
- **All MCP servers configured**: Proper setup

#### Modular Design
- **Independent components**: Hooks, MCP, commands
- **Clear boundaries**: Each component self-contained
- **Regeneratable**: Can rebuild any component

## Key Files to Reference

### Documentation
- **COPILOT_CLI.md**: Complete integration guide (`docs/COPILOT_CLI.md`)
- **copilot-instructions.md**: Base instructions (`.github/copilot-instructions.md`)
- **Commands README**: Command index (`.github/commands/README.md`)
- **Agents README**: Agent documentation (`.github/agents/README.md`)

### Configuration
- **MCP Servers**: `.github/mcp-servers.json`
- **Hooks Config**: `.github/hooks/amplihack-hooks.json`
- **Commands Registry**: `.github/commands/COMMANDS_REGISTRY.json`
- **Agents Registry**: `.github/agents/REGISTRY.json`

### Core Context
- **Philosophy**: `~/.amplihack/.claude/context/PHILOSOPHY.md`
- **Patterns**: `~/.amplihack/.claude/context/PATTERNS.md`
- **Project**: `~/.amplihack/.claude/context/PROJECT.md`
- **Trust**: `~/.amplihack/.claude/context/TRUST.md`

## Examples

### Example 1: Creating a New Module

**User Question**: "How do I create a new module using Copilot that follows amplihack patterns?"

**Guidance**:
```bash
# 1. Reference brick philosophy
gh copilot explain .claude/context/PHILOSOPHY.md

# 2. Get module template
gh copilot suggest --context .claude/context/PATTERNS.md \
  "create a new Python module following Bricks & Studs pattern"

# 3. Use builder agent for implementation
gh copilot suggest -a .github/agents/amplihack/core/builder.md \
  --context .claude/context/PATTERNS.md \
  "implement [module-name] module with __all__ exports"
```

### Example 2: Reviewing Code for Philosophy Compliance

**User Question**: "Can Copilot review my code for amplihack philosophy compliance?"

**Guidance**:
```bash
# Review with philosophy context
gh copilot explain --review src/module/ \
  --context .claude/context/PHILOSOPHY.md \
  --context .github/agents/amplihack/core/reviewer.md

# Check for specific anti-patterns
gh copilot suggest --context .github/agents/skills/code-smell-detector/ \
  "review src/module/ for over-engineering"
```

### Example 3: Multi-Agent Architecture Design

**User Question**: "How do I get multiple agents' perspectives on architecture?"

**Guidance**:
```bash
# Consult multiple experts
gh copilot suggest \
  -a .github/agents/amplihack/core/architect.md \
  -a .github/agents/skills/computer-scientist-analyst/ \
  -a .github/agents/skills/security-analyst/ \
  -a .github/agents/skills/performance-analyst/ \
  "design scalable, secure API gateway"
```

### Example 4: Using Workflow Patterns

**User Question**: "Can I reference amplihack workflows in Copilot?"

**Guidance**:
```bash
# Reference workflow pattern
gh copilot explain .github/commands/ultrathink.md

# Apply workflow approach
gh copilot suggest --context .github/commands/ultrathink.md \
  "plan implementation for feature X"

# Reference investigation workflow
gh copilot explain .github/agents/skills/investigation-workflow/
```

## Limitations

### What Copilot CLI Cannot Do

1. **No Direct Agent Execution**: Can reference but not execute agents
2. **No Workflow Orchestration**: Cannot run multi-step workflows
3. **No MCP Automatic Loading**: MCP servers must be manually configured
4. **No @ Notation**: Use relative paths instead

### What Copilot CLI CAN Do

1. **Reference All Content**: Access agents, skills, patterns via symlinks
2. **Generate Code**: Using amplihack patterns and philosophy
3. **Explain Architecture**: Understand and explain amplihack design
4. **Review Code**: Check for philosophy compliance
5. **Suggest Improvements**: Based on amplihack best practices

## Best Practices

### Do
- ✅ Reference philosophy and patterns in context
- ✅ Use multiple agents for complex decisions
- ✅ Check code against reviewer agent
- ✅ Follow brick & studs pattern
- ✅ Test locally before committing
- ✅ Use MCP servers when available

### Don't
- ❌ Duplicate files between `~/.amplihack/.claude/` and `.github/`
- ❌ Create circular symlinks
- ❌ Bypass philosophy for speed
- ❌ Ignore available skills
- ❌ Skip testing and review
- ❌ Use @ notation (Copilot doesn't support it)

## Additional Resources

### Official Documentation
- **GitHub Copilot CLI**: https://docs.github.com/en/copilot/github-copilot-in-the-cli
- **MCP Protocol**: https://modelcontextprotocol.io/
- **amplihack Repository**: https://github.com/[org]/amplihack

### Internal Documentation
- **COPILOT_CLI.md**: Complete integration guide
- **PHILOSOPHY.md**: Core development principles
- **PATTERNS.md**: Proven solutions (14 patterns)
- **TRUST.md**: Anti-sycophancy guidelines

### Skill Dependencies
- **mcp-manager**: MCP server configuration
- **documentation-writing**: Clear documentation
- **agent-sdk**: Agent architecture patterns

## Support

### Getting Help
- **File Issues**: amplihack repository
- **Discussions**: GitHub Discussions
- **Documentation**: `docs/` directory

### Contributing
- See `CONTRIBUTING.md` for guidelines
- Follow amplihack philosophy
- Test all changes
- Update documentation

---

**Version**: 1.0.0
**Skill Type**: Integration Expert
**Auto-detect**: Yes
**Philosophy**: Ruthless Simplicity + Single Source of Truth
