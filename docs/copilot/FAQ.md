# FAQ: Copilot CLI with amplihack

Frequently asked questions about using GitHub Copilot CLI with amplihack.

## General Questions

### What is amplihack?

amplihack be a development framework for AI-assisted coding that provides:

- **37+ specialized agents** for architecture, testing, security, optimization
- **14 foundational patterns** for common development problems
- **Philosophy-driven development** emphasizing ruthless simplicity and modularity
- **Production-ready tools** for code analysis, testing, MCP management

Originally designed for Claude Code, now accessible through GitHub Copilot CLI.

### When should I use Claude vs Copilot?

| Use Claude Code When...          | Use Copilot CLI When...            |
| -------------------------------- | ---------------------------------- |
| Complex multi-step workflows     | Quick tasks and GitHub integration |
| Direct command execution needed  | Cost-effective heavy usage         |
| Full MCP server support required | GitHub-native workflow preferred   |
| Native agent system preferred    | GPT-4 models acceptable            |
| Claude Opus/Sonnet models needed | Subscription-based cost preferred  |

**Best approach:** Use both! They access the same resources and complement each other.

### How does @ notation work?

The `@` notation invokes specialized agents:

```
> @architect: Design caching module
```

This invokes the `architect` agent from `.github/agents/core/architect.md` with context from:
- `.claude/context/PHILOSOPHY.md` (core principles)
- `.claude/context/PATTERNS.md` (proven patterns)
- `.github/copilot-instructions.md` (Copilot-specific context)

### Can I use both Claude and Copilot simultaneously?

**Yes!** Both environments access the same resources:

```
.claude/                    # Shared resources
├── context/                # Philosophy, patterns, trust
├── agents/                 # Claude agents (source)
├── scenarios/              # Python tools
└── workflow/               # Workflow definitions

.github/
├── copilot-instructions.md # Copilot context
└── agents/                 # Converted agents
```

Switch between them freely based on task requirements.

### What are the main differences?

| Feature                | Claude Code          | Copilot CLI              |
| ---------------------- | -------------------- | ------------------------ |
| **Command Execution**  | Direct (/ultrathink) | Reference-based          |
| **Agent Invocation**   | Native Task tool     | @ notation               |
| **Workflow Execution** | Automated            | Manual/guided            |
| **Cost Model**         | API usage            | Subscription             |
| **Model**              | Claude Opus/Sonnet   | GPT-4 variants           |
| **MCP Servers**        | Full support         | Limited                  |
| **Tool Access**        | All amplihack tools  | All amplihack tools      |
| **Context**            | Full                 | Full (via instructions)  |

## Setup & Installation

### Do I need to install amplihack to use Copilot CLI?

**No, but recommended.**

Minimal setup (no amplihack installation):

```bash
npm install -g @github/copilot
gh auth login
copilot
```

Full setup (with amplihack):

```bash
npm install -g @github/copilot
pip install git+https://github.com/rysweet/amplihack
amplihack init          # In your project
amplihack convert-agents
amplihack copilot       # Launch with context
```

Full setup provides agents, patterns, tools, and philosophy.

### How do I initialize a project?

```bash
cd /path/to/your/project
amplihack init
```

This creates:

```
.claude/                # amplihack resources
├── context/            # Philosophy, patterns, trust
├── agents/             # Agent definitions
├── scenarios/          # Tools
└── workflow/           # Workflows

.github/
├── copilot-instructions.md  # Copilot context
└── agents/                  # (Created after convert-agents)
```

### How do I convert agents?

```bash
# Convert Claude agents to Copilot format
amplihack convert-agents

# Verify conversion
ls .github/agents/
cat .github/agents/REGISTRY.json

# Force reconvert (overwrite existing)
amplihack convert-agents --force
```

### Do I need to reconvert agents after updates?

**Yes**, when ye update Claude agents:

```bash
# Edit agent
vim .claude/agents/core/architect.md

# Reconvert
amplihack convert-agents --force

# Verify
git diff .github/agents/
```

### What if I only want to use Copilot (not Claude)?

Still install amplihack for resources:

```bash
pip install git+https://github.com/rysweet/amplihack
amplihack init
amplihack convert-agents
```

Then use only Copilot CLI:

```bash
amplihack copilot
# or
copilot --allow-all-tools --add-dir /path/to/project
```

## Usage Questions

### How do I invoke agents?

Use `@` notation:

```
> @architect: Design authentication module
> @builder: Implement the module from spec
> @reviewer: Check philosophy compliance
```

Agent names must match exactly (check `.github/agents/REGISTRY.json`).

### Can I use multiple agents at once?

**Yes**, reference multiple agents:

```
> @security AND @optimizer: Review this module for both security
  vulnerabilities and performance issues
```

Or chain sequentially:

```
> @architect: Design module, then @builder: Implement, then @tester: Generate tests
```

### How do I apply patterns?

Reference patterns explicitly:

```
> Using the Safe Subprocess Wrapper pattern from PATTERNS.md, handle git commands

> Which amplihack pattern should I use for handling batch processing?

> Apply the Bricks & Studs Module Design pattern to this code
```

### Do commands like /ultrathink work?

**No, not directly.** Commands are reference-only in Copilot CLI:

```markdown
❌ /ultrathink Implement authentication

✓  Following the ultrathink workflow from DEFAULT_WORKFLOW.md,
   implement authentication
```

Reference the command's methodology, not execute directly.

### How do I execute workflows?

Workflows are manual/guided in Copilot:

```
> Following DEFAULT_WORKFLOW.md:
  Step 1: Clarify requirements [let's start here]
  Step 2: Create GitHub issue [after requirements clear]
  Step 3: Create feature branch [after issue created]
  [continue through all steps]
```

Claude Code executes workflows automatically; Copilot guides ye through them.

### Can I use MCP servers?

**Limited support.** Some MCP functionality available but not full Claude Code compatibility.

Workaround: Use direct commands:

```markdown
❌ Use MCP file system tools

✓  Use file commands: ls, cat, find, grep
```

### How do I access Python tools?

All amplihack Python tools work from command line:

```bash
# Code analysis
amplihack analyze ./src

# MCP management
amplihack mcp list

# Goal agent generator
amplihack new "Create deployment automation agent"
```

Reference in Copilot:

```
> Run amplihack analyze ./src and explain the results
> Use amplihack mcp to list configured servers
```

### What's the difference between skills and agents?

| Aspect          | Agents                              | Skills                                |
| --------------- | ----------------------------------- | ------------------------------------- |
| **Purpose**     | Specialized perspectives/expertise  | Reusable capabilities                 |
| **Invocation**  | `@agent-name:`                      | Reference concepts                    |
| **Examples**    | @architect, @security, @optimizer   | documentation-writing, code-smell-detector |
| **In Copilot**  | Direct invocation via @             | Reference methodology/patterns        |

**Agents** provide expertise; **skills** provide methodologies.

### How do I reference philosophy?

Always mention philosophy explicitly:

```
> Following amplihack's ruthless simplicity, implement caching

> Using amplihack brick philosophy, design module with clear public API

> Following Zero-BS implementation principles, no stubs or placeholders
```

## Performance & Cost

### How does cost compare?

| Usage Level         | Claude Code (API)  | Copilot CLI (Subscription) |
| ------------------- | ------------------ | -------------------------- |
| Light (<10 hrs/mo)  | ~$10-50            | $10-20/mo                  |
| Medium (10-40 hrs)  | ~$50-200           | $10-20/mo                  |
| Heavy (>40 hrs)     | ~$200-500+         | $10-20/mo                  |

Copilot CLI more cost-effective for heavy usage due to subscription model.

### Which is faster?

**Claude Code** for automated workflows (direct execution).

**Copilot CLI** for quick one-off tasks (less overhead).

Speed difference matters less than task fit.

### Do I hit token limits faster?

Depends on usage:

- **Claude Code:** 200K context window, but API cost per token
- **Copilot CLI:** Smaller context window, but subscription-based

Break large tasks into smaller chunks for both.

### How can I optimize performance?

**Reduce context:**

```markdown
❌ Analyze entire codebase

✓  @analyzer: Analyze src/auth/core.py
```

**Be specific:**

```markdown
❌ Tell me everything about authentication

✓  @architect: Design JWT authentication for REST API
```

**Chain tasks:**

```markdown
❌ Design, implement, test, and deploy in one request

✓  Step 1: @architect: Design
   Step 2: @builder: Implement from spec
   Step 3: @tester: Generate tests
```

## Troubleshooting

### Agents not responding correctly

**Provide explicit context:**

```markdown
❌ @architect: Design module

✓  Following amplihack brick philosophy from PHILOSOPHY.md,
   @architect: Design authentication module with:
   - Clear public API (__all__)
   - Single responsibility
   - Zero-BS implementation (no stubs)
```

### Philosophy not being followed

**Reference philosophy files explicitly:**

```
> Using the principles from .claude/context/PHILOSOPHY.md,
  implement this feature with ruthless simplicity
```

### Context not loading

**Verify files exist:**

```bash
ls .claude/context/
cat .github/copilot-instructions.md
```

**Reinitialize if needed:**

```bash
amplihack init --force
amplihack convert-agents --force
```

### Commands not working

**Remember:** Commands are reference-only in Copilot.

```markdown
❌ /analyze this code

✓  @reviewer: Analyze this code for philosophy compliance
```

### Agents not found

**Check agent names:**

```bash
cat .github/agents/REGISTRY.json | grep -A 2 '"name"'
```

**Use exact names:**

```
✓  @architect (correct)
❌ @architecture (wrong)
```

## Advanced Topics

### Can I create custom agents?

**Yes!** Create agents in `.github/agents/`:

```markdown
# .github/agents/my-agent.md

---
name: my-agent
description: Custom agent for specific task
---

## Purpose
[Agent purpose]

## When to Use
[Trigger conditions]

## Instructions
[Detailed instructions]
```

Use:

```
> @my-agent: [task]
```

### How do I customize workflows?

Edit `.claude/workflow/DEFAULT_WORKFLOW.md`:

```markdown
# Add custom step
## Step 23: Custom Verification
[Your custom process]
```

Reference in Copilot:

```
> Following my customized DEFAULT_WORKFLOW.md, implement feature X
```

### Can I use this in CI/CD?

**Yes**, amplihack tools work in CI:

```yaml
# .github/workflows/analyze.yml
- name: Analyze code
  run: amplihack analyze ./src
```

Copilot CLI itself is interactive and not designed for CI.

### How do I share agents with my team?

Commit to version control:

```bash
git add .claude/agents/ .github/agents/
git commit -m "Add amplihack agents"
git push
```

Team members run:

```bash
git pull
amplihack convert-agents --force  # Regenerate from source
```

### Can I use this with other IDEs?

**amplihack resources:** Compatible with any tool that reads markdown.

**Copilot CLI:** Terminal-based, works with any IDE.

**Claude Code:** VS Code extension only.

## Integration Questions

### Does this work with GitHub Actions?

**Yes**, use amplihack tools in workflows:

```yaml
- name: Run analysis
  run: amplihack analyze ./src

- name: Check philosophy compliance
  run: amplihack analyze --check-philosophy ./src
```

### Can I use this with pre-commit hooks?

**Yes**, integrate amplihack tools:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: amplihack-analyze
        name: amplihack analysis
        entry: amplihack analyze
        language: system
```

### Does this work with Docker?

**Yes**, install in Dockerfile:

```dockerfile
RUN pip install git+https://github.com/rysweet/amplihack
RUN npm install -g @github/copilot
```

### Can I integrate with my monitoring?

**Yes**, parse amplihack tool output:

```bash
amplihack analyze ./src --format json > analysis.json
# Parse JSON for metrics
```

## Philosophy Questions

### What is "ruthless simplicity"?

Core principle: **Start simple, add complexity only when justified.**

```python
# Ruthlessly simple
cache = {}

def get(key):
    return cache.get(key)

def set(key, value):
    cache[key] = value
```

Not:

```python
# Premature complexity
class DistributedCacheWithFailoverAndReplicationAndSharding:
    # ... 500 lines before you need it
```

### What is the "brick philosophy"?

**Modules as bricks:**

- **ONE clear responsibility**
- **Public API** (the "studs")
- **Regeneratable** from spec
- **Isolated** (all code/tests in module)

```python
# Good brick
# auth/__init__.py
from .core import authenticate, validate_token
__all__ = ['authenticate', 'validate_token']
```

### What is "Zero-BS implementation"?

**Every function works or doesn't exist:**

- No stubs or placeholders
- No dead code or TODOs
- No fake implementations
- Quality over speed

```python
# Zero-BS ✓
def process_payment(amount, ledger="payments.json"):
    # Fully working implementation
    pass

# BS ❌
def process_payment(amount):
    # TODO: Implement Stripe integration
    raise NotImplementedError()
```

### What are "trust principles"?

**Trust through honesty, not harmony:**

1. **Disagree** when something won't work
2. **Clarify** instead of guessing
3. **Propose** better alternatives
4. **Admit** uncertainty
5. **Focus** on problems, not feelings
6. **Challenge** wrong assumptions
7. **Be direct** with clear conclusions

## Still Have Questions?

### Documentation

- [Getting Started Guide](./GETTING_STARTED.md)
- [Complete User Guide](./USER_GUIDE.md)
- [Migration Guide](./MIGRATION_FROM_CLAUDE.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
- [API Reference](./API_REFERENCE.md)

### Community

- **Discussions:** https://github.com/rysweet/amplihack/discussions
- **Issues:** https://github.com/rysweet/amplihack/issues
- **Docs:** https://rysweet.github.io/amplihack/

### Ask in Copilot

```
> How do I [specific question] with amplihack?
> What amplihack pattern handles [problem]?
> Which agent should I use for [task]?
```

The AI has access to all documentation and can answer questions contextually!
