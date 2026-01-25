# amplihack Integration with GitHub Copilot CLI

**How to leverage amplihack's 35+ agents, 85+ skills, and philosophy from within GitHub Copilot CLI.**

> **Why This Matters**: GitHub Copilot CLI is terminal-native and lightweight. amplihack provides deep project context, specialized agents, and proven patterns. Together, they enable powerful workflows while maintaining ruthless simplicity.

## Quick Start

```bash
# In your amplihack project
cd ~/src/amplihack3

# Launch Copilot CLI
copilot

# Discover available resources
/agent                  # Browse agents
/skills list            # List skills

# Reference agents in prompts
Use the architect agent to design a new feature for user authentication

# Reference philosophy
Review this code for alignment with amplihack's ruthless simplicity philosophy
```

## Integration Architecture

### Symlink Structure

amplihack uses symlinks to expose its resources to GitHub Copilot CLI:

```
.github/                          # Repository root
├── agents/ -> ~/.amplihack/.claude/agents/
├── skills/ -> ~/.amplihack/.claude/skills/
├── hooks/ -> ~/.amplihack/.claude/hooks/
└── instructions/
    └── patterns.instructions.md -> ~/.amplihack/.claude/context/PATTERNS.md
```

**Why symlinks?**

- **Single source of truth**: `~/.amplihack/.claude/` is canonical
- **Per-project access**: Each repo sees the same resources
- **Easy updates**: Change once in `~/.amplihack/`, available everywhere

**Verification**:

```bash
# Check symlinks exist
ls -la .github/agents
ls -la .github/skills

# Expected output:
# .github/agents -> /home/user/.amplihack/.claude/agents
# .github/skills -> /home/user/.amplihack/.claude/skills
```

### Hook System

amplihack hooks extend Copilot CLI with bash wrappers that call Python implementations:

```
.github/hooks/
├── pre-edit.sh           # Bash wrapper
├── post-edit.sh          # Bash wrapper
└── pre-commit.sh         # Bash wrapper
```

Each wrapper sources common setup and invokes Python:

```bash
#!/bin/bash
source "$(dirname "$0")/common.sh"
python3 ~/.amplihack/.claude/hooks/pre_edit.py "$@"
```

**Hook Flow**:

1. Copilot CLI triggers hook (e.g., before editing file)
2. Bash wrapper sets up environment
3. Python hook executes (validation, logging, etc.)
4. Hook returns success/failure to Copilot

### MCP Server Configuration

amplihack can provide custom MCP servers for specialized operations:

**Location**: `~/.copilot/mcp-config.json`

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GH_TOKEN}"
      }
    }
  }
}
```

**Manage in Copilot**:

```bash
/mcp show           # List configured servers
/mcp add            # Add new server
/mcp edit <name>    # Edit configuration
```

## Discovering Resources

### List All Agents

```bash
# Interactive browser
/agent

# Programmatic listing
ls -1 ~/.amplihack/.claude/agents/*.md | xargs basename -s .md

# Count
ls -1 ~/.amplihack/.claude/agents/*.md | wc -l
```

### List All Skills

```bash
# Copilot CLI command
/skills list

# Direct inspection
ls -1 ~/.amplihack/.claude/skills/*/SKILL.md | sed 's|/.*/||; s|/SKILL.md||'

# Count
find ~/.amplihack/.claude/skills -name SKILL.md | wc -l
```

### Common Agents

Quick reference to frequently used agents:

- **architect** - System design and specifications
- **builder** - Implementation following specs
- **reviewer** - Code review and debugging
- **tester** - Test coverage analysis
- **optimizer** - Performance optimization (measure first!)
- **api-designer** - REST/GraphQL API contracts
- **database** - Schema design and queries
- **security** - Auth, encryption, vulnerabilities
- **documentation-writer** - Clear, discoverable docs
- **philosophy-guardian** - Philosophy compliance
- **prompt-writer** - Requirement clarification
- **analyzer** - Code/system analysis (TRIAGE/DEEP/SYNTHESIS)

### Key Skills

Skills that auto-activate based on keywords:

- **documentation-writing** - Eight Rules + Diataxis framework
- **design-patterns-expert** - GoF patterns with progressive disclosure
- **agent-sdk** - Claude Agent SDK architecture
- **code-smell-detector** - Anti-pattern detection
- **azure-kubernetes-expert** - AKS production deployments
- **rust-programming-expert** - Rust memory safety
- **dotnet-install** - .NET SDK installation
- **cybersecurity-analyst** - Security analysis frameworks

For the complete list, run `/skills list` in Copilot CLI or inspect `~/.amplihack/.claude/skills/`.

## Usage Patterns

### Referencing Agents

```bash
# Interactive selection
/agent

# Reference in prompts
Use the architect agent to design a new authentication module

# Combine multiple agents
Have the architect design the API, then use api-designer to create the OpenAPI spec

# Delegation workflow
Use the prompt-writer to clarify requirements, then architect to design, then builder to implement
```

### Referencing Skills

```bash
# List available skills
/skills list

# Reference in prompts
Use the documentation-writing skill to create a tutorial for this feature

Load the design-patterns-expert skill and suggest which pattern fits this problem

Apply the code-smell-detector skill to review this module
```

**Auto-activation**: Skills load automatically based on keywords:

- "write documentation" → `documentation-writing`
- "design pattern" → `design-patterns-expert`
- "install .NET" → `dotnet-install`
- "azure kubernetes" → `azure-kubernetes-expert`

### Referencing Philosophy

**Philosophy Location**: See `~/.amplihack/.claude/context/PHILOSOPHY.md` for canonical philosophy documentation.

**How to reference**:

```bash
# Philosophy alignment
Review this code against the amplihack philosophy - is it simple enough?

Does this design follow the brick philosophy from amplihack?

# Pattern application
What amplihack pattern should I use for this error handling?

Show me the amplihack pattern for CLI argument parsing
```

**Core Principles**:

- **Ruthless Simplicity** - Remove everything that doesn't serve the goal
- **Zero-BS Implementation** - No frameworks, minimal dependencies, self-explanatory code
- **Brick Philosophy** - Self-contained, regeneratable modules with clear interfaces
- **Single Source of Truth** - One canonical location for each concept

### Multi-Agent Workflows

```bash
# Sequential workflow
First use prompt-writer to clarify requirements
Then use architect to design the solution
Then use builder to implement
Finally use reviewer to check for issues

# Parallel analysis
Have both the security agent and the database agent review this user schema

# Debate pattern
Use the multi-agent-debate agent to evaluate different approaches to caching
```

## Common Workflows

### Feature Development

```bash
# 1. Clarify requirements
Use the prompt-writer agent to help me clarify the requirements for user authentication

# 2. Design architecture
Use the architect agent to design the authentication module following amplihack philosophy

# 3. Create API contract
Use the api-designer agent to create the OpenAPI spec for the auth endpoints

# 4. Implement
Use the builder agent to implement the authentication module from the spec

# 5. Add tests
Use the tester agent to create comprehensive tests following the testing pyramid

# 6. Review
Use the reviewer agent to check for bugs and the philosophy-guardian to ensure alignment

# 7. Document
Use the documentation-writer agent to create a how-to guide for authentication
```

### Code Review with Philosophy Context

```bash
# Load philosophy context
Review this pull request against amplihack philosophy - check for ruthless simplicity

# Multi-dimensional review
Have the security agent check for vulnerabilities, the reviewer check for bugs, and the philosophy-guardian check for complexity

# Socratic review for learning
Use the socratic-reviewer agent to help me understand what's wrong with this code
```

### Investigation and Understanding

```bash
# Understand existing system
Use the analyzer agent in DEEP mode to investigate how authentication currently works

# Historical context
Use the knowledge-archaeologist agent to understand why this module was designed this way

# Pattern extraction
Use the patterns agent to identify common approaches across our codebase
```

## Troubleshooting

### Symlinks Not Working

**Symptom**: `/agent` shows no custom agents, `/skills list` is empty

**Diagnosis**:

```bash
# Check symlinks exist
ls -la .github/agents
ls -la .github/skills

# Check targets exist
ls ~/.amplihack/.claude/agents/
ls ~/.amplihack/.claude/skills/
```

**Fix**:

```bash
# Recreate symlinks
cd .github
rm -f agents skills hooks
ln -s ~/.amplihack/.claude/agents agents
ln -s ~/.amplihack/.claude/skills skills
ln -s ~/.amplihack/.claude/hooks hooks
```

### Copilot Not Finding Agents

**Symptom**: Prompts referencing agents don't work as expected

**Diagnosis**:

```bash
# Check agent loading locations
ls -la ~/.copilot/agents/
ls -la .github/agents/
```

**Fix**:

```bash
# Ensure .github/agents/ exists and has content
ls .github/agents/*.md

# Check agent YAML frontmatter is valid
head -20 .github/agents/architect.md
```

**Priority order**:

1. `~/.copilot/agents/` (highest priority)
2. `.github/agents/` (repository level)
3. `.github-private/agents/` (org/enterprise)

### MCP Servers Not Starting

**Symptom**: `/mcp show` reports errors, tools unavailable

**Diagnosis**:

```bash
# Check configuration
cat ~/.copilot/mcp-config.json

# Test server manually
npx -y @modelcontextprotocol/server-github
```

**Fix**:

```bash
# Edit configuration
/mcp edit github

# Check environment variables
echo $GH_TOKEN
echo $GITHUB_TOKEN

# Disable problematic server
/mcp disable <server-name>
```

### Philosophy Context Not Loading

**Symptom**: Copilot doesn't seem aware of amplihack philosophy

**Diagnosis**:

```bash
# Check instruction files exist
ls -la .github/instructions/

# Check content
cat .github/instructions/philosophy.instructions.md
```

**Fix**:

```bash
# Recreate instruction symlinks
cd .github/instructions
ln -s ~/.amplihack/.claude/context/PHILOSOPHY.md philosophy.instructions.md
ln -s ~/.amplihack/.claude/context/PATTERNS.md patterns.instructions.md
```

**Note**: Custom instructions load automatically. Restart Copilot CLI if changes aren't detected.

### Agent Not Behaving as Expected

**Symptom**: Agent produces different results than expected

**Debugging**:

```bash
# Check agent definition
cat .github/agents/<agent-name>.md

# Verify agent description matches intent
/agent  # Select and review description

# Try explicit agent selection
copilot --agent=<agent-name> --prompt "Test prompt"
```

**Common issues**:

- Agent name mismatch (Copilot uses filename, not display name)
- Conflicting agents with similar names
- Agent instructions unclear or contradictory

## Related Documentation

- **GitHub Copilot CLI Basics**: See [SKILL.md](./SKILL.md)
- **Full Command Reference**: See [reference.md](./reference.md)
- **Usage Examples**: See [examples.md](./examples.md)
- **amplihack Philosophy**: `~/.amplihack/.claude/context/PHILOSOPHY.md`
- **amplihack Patterns**: `~/.amplihack/.claude/context/PATTERNS.md`

## Quick Reference Card

```bash
# Discover resources
/agent                    # Browse agents
/skills list              # List skills
ls ~/.amplihack/.claude/agents/*.md | wc -l  # Count agents
find ~/.amplihack/.claude/skills -name SKILL.md | wc -l  # Count skills

# Reference in prompts
Use the [agent-name] agent to [task]
Load the [skill-name] skill and [task]
Review against amplihack [philosophy-principle]

# Multi-agent workflows
First [agent-1] then [agent-2] then [agent-3]

# Check configuration
ls -la .github/agents/    # Verify symlinks
/mcp show                 # Check MCP servers
cat ~/.copilot/config.json  # Review config

# Common agents
architect, builder, reviewer, tester, optimizer
api-designer, database, security, documentation-writer
philosophy-guardian, prompt-writer, analyzer

# Key skills
documentation-writing, design-patterns-expert, agent-sdk
code-smell-detector, azure-kubernetes-expert

# Philosophy principles (see PHILOSOPHY.md for details)
ruthless-simplicity, zero-bs, brick-philosophy, single-source-of-truth
```
